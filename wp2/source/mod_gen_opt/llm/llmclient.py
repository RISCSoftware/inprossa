"""Provides a lightweight chat-completions client with optional tool-calling helpers."""

import datetime
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests


MAX_TOOL_STDOUT_CHARS = 20000
HTTP_ERROR_BODY_CHARS = 2000

# Optional per-request chat log destination.
_chat_log_path: Optional[Path] = None


def set_chat_log_path(path: str | Path | None) -> None:
    """Set the path for subsequent LLM chat log files. Pass None to disable."""
    global _chat_log_path
    _chat_log_path = Path(path) if path is not None else None


def _log_chatRound(purpose: str, messages: List[Dict[str, Any]], response: Dict[str, Any]) -> None:
    """Append one request/response round to the chat log, if enabled."""
    if _chat_log_path is None:
        return
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "purpose": purpose,
        "request_messages": messages,
        "raw_response": response,
    }
    _chat_log_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if _chat_log_path.exists() else "w"
    with _chat_log_path.open(mode, encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")

class LLMClient:
    def __init__(self, url: str, model: str):
        self.url = url
        self.model = model

    def chat(self, messages, **kwargs):
        return call_llm(
            messages=messages,
            model=self.model,
            url=self.url,
            **kwargs
        )

    def chat_with_simulation_tool(
        self,
        messages: List[Dict[str, Any]],
        source_file_path: str,
        problem_file_path: str,
        simulation_api_base_url: str = "http://127.0.0.1:8010",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Runs one tool-calling round with the simulator endpoint as a function tool.

        Flow:
        1) Send request with tool schema.
        2) If model asks for tool call, execute /simulate.
        3) Send tool result back and return final model response.
        """

        tools = [build_simulation_tool_definition()]
        first = self.chat(messages=messages, tools=tools, tool_choice="auto", **kwargs)

        tool_calls = _extract_tool_calls(first)
        if not tool_calls:
            return first

        history = list(messages)
        assistant_message = first["choices"][0]["message"]
        history.append(
            {
                "role": "assistant",
                "content": assistant_message.get("content"),
                "tool_calls": assistant_message.get("tool_calls", []),
            }
        )

        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            raw_args = tool_call.get("function", {}).get("arguments", "{}")
            try:
                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except json.JSONDecodeError:
                parsed_args = {}

            if tool_name != "run_woodcutter_simulation":
                tool_result = {
                    "status": "error",
                    "message": f"Unknown tool: {tool_name}",
                }
            else:
                tool_result = call_simulation_api(
                    simulation_api_base_url=simulation_api_base_url,
                    source_file_path=source_file_path,
                    problem_file_path=problem_file_path,
                    generator_args=str(parsed_args.get("generator_args", "")),
                    java_bin=str(parsed_args.get("java_bin", "java")),
                    classpath=parsed_args.get("classpath"),
                    main_class=str(parsed_args.get("main_class", "WoodCutter")),
                )

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_name,
                    "content": json.dumps(_compact_tool_result(tool_result)),
                }
            )

        return self.chat(messages=history, tools=tools, tool_choice="auto", **kwargs)

def call_llm(
    messages: List[Dict[str, str]],
    #model: str = "nvidia/MiniMax-M2.7-NVFP4",
    model: str = "Qwen/Qwen3.6-27B-FP8",
    url: str = "http://ada01.risc.local:8002/v1/chat/completions",
    temperature: float = 0.7,
    max_tokens: int = 43690,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = "auto",
) -> Dict[str, Any]:
    """
    Simple abstraction over a Chat Completions-compatible LLM endpoint.

    Args:
        messages: OpenAI-style messages [{"role": ..., "content": ...}]
        model: model id
        url: endpoint URL
        temperature: sampling temperature
        max_tokens: max output tokens to generate (default 43690)
        tools: optional tool definitions
        tool_choice: "auto", "none", or specific tool config

    Returns:
        Parsed JSON response from the LLM.
    """

    # Send as max_completion_tokens (OpenAI standard) — not max_tokens,
    # which some servers interpret differently for thinking-enabled models.
    # Also set thinking budget so model doesn't exhaust tokens on reasoning alone.
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "max_completion_tokens": max_tokens,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    response = requests.post(url, json=payload, timeout=300)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body_preview = (response.text or "")[:HTTP_ERROR_BODY_CHARS]
        raise RuntimeError(
            f"LLM endpoint HTTP {response.status_code}. Response body (truncated): {body_preview}"
        ) from exc

    parsed = response.json()
    _log_chatRound(purpose="operator-generation", messages=messages, response=parsed)
    return parsed


def build_simulation_tool_definition() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "run_woodcutter_simulation",
            "description": (
                "Runs the local /simulate endpoint from simulation_api.py and executes the full pipeline: "
                "(1) run a Python generator script that outputs JSON with SimulatorCommands, then "
                "(2) run WoodCutter with those commands. "
                "Use this tool whenever the user asks for simulation results, machine states, or total cost. "
                "The host application always supplies source_file and problem_file; do not ask the user for them. "
                "Success result contains status='ok' and simulator_stdout (plain-text transcript). "
                "Failure result contains status='error', http_status, and error_body."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "generator_args": {
                        "type": "string",
                        "description": (
                            "Optional extra CLI args passed to the generator script. "
                            "Default is empty string."
                        ),
                        "default": "",
                    },
                    "java_bin": {
                        "type": "string",
                        "description": "Java executable to invoke WoodCutter (for example 'java').",
                        "default": "java",
                    },
                    "classpath": {
                        "type": ["string", "null"],
                        "description": (
                            "Optional Java classpath override. Use null to keep server default classpath."
                        ),
                        "default": None,
                    },
                    "main_class": {
                        "type": "string",
                        "description": "Java main class name for the simulator, normally 'WoodCutter'.",
                        "default": "WoodCutter",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    }


def call_simulation_api(
    simulation_api_base_url: str,
    source_file_path: str,
    problem_file_path: str,
    generator_args: str = "",
    java_bin: str = "java",
    classpath: Optional[str] = None,
    main_class: str = "WoodCutter",
) -> Dict[str, Any]:
    endpoint = simulation_api_base_url.rstrip("/") + "/simulate"

    data: Dict[str, str] = {
        "generator_args": generator_args,
        "java_bin": java_bin,
        "main_class": main_class,
    }
    if classpath is not None:
        data["classpath"] = classpath

    with open(source_file_path, "rb") as src_handle, open(problem_file_path, "rb") as problem_handle:
        files = {
            "source_file": (source_file_path.split("/")[-1].split("\\")[-1], src_handle, "text/x-python"),
            "problem_file": (problem_file_path.split("/")[-1].split("\\")[-1], problem_handle, "application/json"),
        }
        response = requests.post(endpoint, data=data, files=files, timeout=600)

    if response.ok:
        return {
            "status": "ok",
            "http_status": response.status_code,
            "simulator_stdout": response.text,
        }

    return {
        "status": "error",
        "http_status": response.status_code,
        "error_body": response.text,
    }


def _extract_tool_calls(response_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    choices = response_payload.get("choices", [])
    if not choices:
        return []
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        return tool_calls
    return []


def _compact_tool_result(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """Keep tool payload small enough for follow-up LLM calls."""
    if tool_result.get("status") != "ok":
        return tool_result

    stdout = str(tool_result.get("simulator_stdout", ""))
    total_cost = _extract_total_cost(stdout)

    compact: Dict[str, Any] = {
        "status": tool_result.get("status"),
        "http_status": tool_result.get("http_status"),
        "final_total_cost": total_cost,
        "simulator_stdout_truncated": len(stdout) > MAX_TOOL_STDOUT_CHARS,
    }

    if len(stdout) <= MAX_TOOL_STDOUT_CHARS:
        compact["simulator_stdout"] = stdout
        return compact

    head_len = MAX_TOOL_STDOUT_CHARS // 2
    tail_len = MAX_TOOL_STDOUT_CHARS - head_len
    compact["simulator_stdout_excerpt"] = (
        stdout[:head_len]
        + "\n\n... [TRUNCATED FOR TOOL CONTEXT SIZE] ...\n\n"
        + stdout[-tail_len:]
    )
    compact["simulator_stdout_chars"] = len(stdout)
    return compact


def _extract_total_cost(simulator_stdout: str) -> Optional[int]:
    matches = re.findall(r'"TotalCost"\s*:\s*(\d+)', simulator_stdout)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None