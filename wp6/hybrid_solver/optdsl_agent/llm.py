"""Model access over any OpenAI-compatible ``/chat/completions`` endpoint.

Two deliberate choices:

* **No SDK.** The project's only runtime dependency is ``minizinc``. Adding
  ``openai`` for one POST would be a poor trade, and ``urllib.request`` reaches
  OpenAI, Azure OpenAI, Ollama, vLLM and LM Studio equally well.
* **Tool calling with a fallback.** Native ``tools`` is the better protocol, but
  not every compatible endpoint implements it. When the endpoint rejects the
  request, the client degrades to a JSON-action protocol carried in the message
  body, so the agent loop is identical either way.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import AgentConfig

#: Status codes worth retrying: rate limits and transient server failures.
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class LLMError(RuntimeError):
    """Raised when the endpoint cannot be reached or keeps failing."""


@dataclass
class ToolCall:
    """One tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """A normalised model reply."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class ChatClient(Protocol):
    """What the agent loop needs from a model client.

    Declared as a protocol so tests can pass a scripted stub without subclassing
    anything or patching the network.
    """

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse: ...


class LLMClient:
    """Minimal OpenAI-compatible chat client with retries and tool fallback."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self._tools_unsupported = False

    # -- public ------------------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send one conversation turn and return the normalised reply."""
        use_tools = bool(tools) and not self._tools_unsupported

        try:
            payload = self._post(messages, tools if use_tools else None)
        except _ToolsRejected:
            # The endpoint does not understand `tools`. Remember that and retry
            # with the JSON-action protocol instead of failing the whole run.
            self._tools_unsupported = True
            payload = self._post(messages, None)

        return self._normalise(payload, tools_expected=use_tools)

    # -- transport ---------------------------------------------------------

    def _post(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        data = json.dumps(body).encode("utf-8")
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key or ''}",
        }

        last_error: Exception | None = None
        for attempt in range(4):
            request = urllib.request.Request(endpoint, data=data, headers=headers)
            try:
                with urllib.request.urlopen(
                    request, timeout=self.config.budget.request_timeout
                ) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as exc:
                detail = _read_error_body(exc)
                if exc.code == 400 and tools and _looks_like_tools_rejection(detail):
                    raise _ToolsRejected(detail) from exc
                if exc.code not in _RETRYABLE_STATUS:
                    raise LLMError(f"HTTP {exc.code} from {endpoint}: {detail}") from exc
                last_error = exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc

            if attempt < 3:
                time.sleep(2**attempt)

        raise LLMError(f"could not reach {endpoint}: {last_error}")

    # -- normalisation -----------------------------------------------------

    def _normalise(self, payload: dict[str, Any], *, tools_expected: bool) -> LLMResponse:
        try:
            choice = payload["choices"][0]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"malformed response: {json.dumps(payload)[:500]}") from exc

        message = choice.get("message") or {}
        content = message.get("content") or ""
        if isinstance(content, list):
            # Some providers return content parts instead of a plain string.
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )

        calls: list[ToolCall] = []
        for index, raw_call in enumerate(message.get("tool_calls") or []):
            function = raw_call.get("function") or {}
            calls.append(
                ToolCall(
                    id=raw_call.get("id") or f"call_{index}",
                    name=function.get("name", ""),
                    arguments=_parse_arguments(function.get("arguments")),
                )
            )

        if not calls and tools_expected:
            # Fallback protocol: the model was told to answer with a JSON action.
            action = _parse_json_action(content)
            if action is not None:
                calls.append(action)

        return LLMResponse(
            content=content,
            tool_calls=calls,
            finish_reason=choice.get("finish_reason"),
            raw=payload,
        )


class _ToolsRejected(Exception):
    """Internal signal: the endpoint refused the ``tools`` parameter."""


def _read_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:1000]
    except Exception:  # noqa: BLE001 - error reporting must never mask the error
        return str(exc)


def _looks_like_tools_rejection(detail: str) -> bool:
    lowered = detail.lower()
    return "tool" in lowered or "function" in lowered or "unsupported" in lowered


def _parse_arguments(raw: Any) -> dict[str, Any]:
    """Tool arguments arrive as a JSON string, but some providers send an object."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_json_action(content: str) -> ToolCall | None:
    """Extract ``{"action": ..., "arguments": {...}}`` from a plain-text reply.

    Tolerates fenced blocks and surrounding prose, because models add both even
    when the instructions forbid it.
    """
    text = content.strip()
    if not text:
        return None

    candidates = [text]
    if "```" in text:
        for chunk in text.split("```"):
            stripped = chunk.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                candidates.append(stripped)

    for candidate in candidates:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            continue
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        action = parsed.get("action") or parsed.get("tool")
        if not isinstance(action, str) or not action:
            continue
        arguments = parsed.get("arguments") or parsed.get("args") or {}
        return ToolCall(
            id=f"json_{action}",
            name=action,
            arguments=arguments if isinstance(arguments, dict) else {},
        )

    return None


class StubClient:
    """Deterministic offline client used by ``--dry-run`` and by tests.

    It replays a scripted list of replies and then returns a final message, so
    the agent loop can be exercised end to end without a network call.
    """

    def __init__(self, script: list[LLMResponse] | None = None) -> None:
        self._script = list(script or [])
        self.calls: list[list[dict[str, Any]]] = []

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        if self._script:
            return self._script.pop(0)
        return LLMResponse(content="[dry-run] no further actions.", finish_reason="stop")
