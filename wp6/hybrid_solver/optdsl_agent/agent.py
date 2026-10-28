"""The agent loop: model in, tool calls out, results back in.

The loop is deliberately thin. It owns three things and nothing else:

* **Message history** — the conversation the model sees.
* **Budget enforcement** — checked before every model call and every tool call.
* **Tool dispatch** — via :class:`~optdsl_agent.tools.ToolRegistry`.

Everything else (what a tool does, how a prompt is built) lives elsewhere, so
the loop can be tested with a scripted client and no network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .llm import ChatClient, LLMError, LLMResponse, ToolCall
from .prompts import build_system_prompt
from .session import Session
from .tools import ToolRegistry, build_registry, tool_result_json

#: Safety valve: a model that keeps calling tools without concluding would
#: otherwise loop until the budget runs out, producing nothing useful.
MAX_STEPS_PER_TURN = 12


@dataclass
class Turn:
    """One user request and everything the agent did in response."""

    request: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    final_text: str = ""
    stopped_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "finalText": self.final_text,
            "stoppedReason": self.stopped_reason,
            "toolCalls": self.tool_calls,
        }


class AgentLoop:
    """Drives a conversation against a model, with tools."""

    def __init__(
        self,
        session: Session,
        client: ChatClient,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.registry = registry or build_registry()
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt()}
        ]

    # -- public ------------------------------------------------------------

    def run(self, request: str, *, context: str | None = None) -> Turn:
        """Handle one user request to completion."""
        turn = Turn(request=request)

        content = request if context is None else f"{request}\n\n{context}"
        self.messages.append({"role": "user", "content": content})

        for _ in range(MAX_STEPS_PER_TURN):
            exhausted = self.session.budget_exhausted()
            if exhausted:
                turn.stopped_reason = exhausted
                turn.final_text = f"Stopped: the {exhausted} budget is exhausted."
                self.messages.append({"role": "assistant", "content": turn.final_text})
                return turn

            self.session.llm_calls += 1
            try:
                response = self.client.chat(self.messages, tools=self.registry.schemas())
            except LLMError as exc:
                turn.stopped_reason = "llm_error"
                turn.final_text = f"The model call failed: {exc}"
                return turn

            if not response.wants_tools:
                turn.final_text = response.content.strip()
                self.messages.append({"role": "assistant", "content": response.content})
                return turn

            self._append_assistant_tool_calls(response)
            for call in response.tool_calls:
                result = self._dispatch(call, turn)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": tool_result_json(result),
                    }
                )

        turn.stopped_reason = "max_steps"
        turn.final_text = (
            f"Stopped after {MAX_STEPS_PER_TURN} tool steps without a conclusion. "
            "The last tool results are above."
        )
        self.messages.append({"role": "assistant", "content": turn.final_text})
        return turn

    def reset(self) -> None:
        """Drop the conversation but keep the session state."""
        self.messages = [{"role": "system", "content": build_system_prompt()}]

    # -- internals ---------------------------------------------------------

    def _append_assistant_tool_calls(self, response: LLMResponse) -> None:
        """Record the assistant turn in the shape the API expects back.

        The tool calls must be echoed verbatim, otherwise the follow-up `tool`
        messages have no matching `tool_calls` entry and the endpoint rejects
        the conversation.
        """
        self.messages.append(
            {
                "role": "assistant",
                "content": response.content or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                    for call in response.tool_calls
                ],
            }
        )

    def _dispatch(self, call: ToolCall, turn: Turn) -> dict[str, Any]:
        result = self.registry.call(call.name, self.session, call.arguments)
        turn.tool_calls.append(
            {
                "name": call.name,
                "arguments": call.arguments,
                "ok": bool(result.get("ok")),
                "summary": result.get("summary") or result.get("error"),
            }
        )
        return result


def run_single_shot(
    session: Session,
    client: ChatClient,
    request: str,
    *,
    context: str | None = None,
) -> Turn:
    """Convenience wrapper for the one-shot subcommands."""
    return AgentLoop(session, client).run(request, context=context)
