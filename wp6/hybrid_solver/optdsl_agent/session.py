"""Mutable state for one harness session.

A session owns the formulation text, the artifacts produced so far, and the
budget counters. Tools read and write it; the agent loop and the REPL both drive
it. Keeping this in one object is what makes the REPL feel stateful: after
``/add`` the next ``/solve`` sees the constrained model without the user having
to pass a path again.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import AgentConfig


@dataclass
class Artifact:
    """A file the session produced."""

    kind: str  # "constrained-model" | "operator" | "report" | "solution"
    path: Path
    description: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": str(self.path), "description": self.description}


@dataclass
class Session:
    """One formulation under discussion, plus everything derived from it."""

    config: AgentConfig
    source: str
    path: Path | None = None
    #: Constraints accepted but not yet written to a file.
    pending_constraints: list[dict[str, str]] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    #: Chronological record of tool calls and their outcomes.
    history: list[dict[str, Any]] = field(default_factory=list)
    #: Last exact-solver result, reused by ``compare_runs``.
    last_solve: dict[str, Any] | None = None
    #: Last LNS result, reused by ``compare_runs`` and the tuning loop.
    last_lns: dict[str, Any] | None = None
    #: Warm-start spec captured from the last feasible LNS run. Applied to the
    #: next exact solve without modifying the source file.
    warm_start: dict[str, Any] | None = None
    #: Persisted copy of :attr:`warm_start` (transient, in the output dir).
    warm_start_path: Path | None = None

    llm_calls: int = 0
    tool_calls: int = 0
    started_at: float = field(default_factory=time.perf_counter)

    # -- construction ------------------------------------------------------

    @classmethod
    def from_file(cls, path: str | Path, config: AgentConfig) -> "Session":
        resolved = Path(path).resolve()
        return cls(config=config, source=resolved.read_text(encoding="utf-8"), path=resolved)

    @classmethod
    def from_source(cls, source: str, config: AgentConfig) -> "Session":
        return cls(config=config, source=source)

    # -- model text --------------------------------------------------------

    @property
    def stem(self) -> str:
        return self.path.stem if self.path is not None else "model"

    @property
    def label(self) -> str:
        """Short display name for UI headers."""
        if self.path is not None:
            return self.path.name
        return "new empty problem" if not self.source.strip() else "inline model"

    def replace_source(self, source: str) -> None:
        """Adopt a new formulation text, e.g. after constraints were accepted."""
        self.source = source

    def new_problem(self) -> None:
        """Discard the current model and start from a blank formulation.

        Keeps the config and the budget counters (a session has a hard budget);
        drops the model text, the file binding, derived artifacts, results and
        any captured warm start.
        """
        self.replace_source("")
        self.path = None
        self.pending_constraints = []
        self.artifacts = []
        self.history = []
        self.last_solve = None
        self.last_lns = None
        self.warm_start = None
        self.warm_start_path = None

    def adopt_model(self, source: str) -> None:
        """Adopt a freshly generated model as the session's formulation.

        Keeps the config, budget, artifacts and history; clears results that
        referred to the previous model (solves, LNS, warm start, constraints).
        """
        self.replace_source(source)
        self.path = None
        self.pending_constraints = []
        self.last_solve = None
        self.last_lns = None
        self.warm_start = None
        self.warm_start_path = None

    # -- budget ------------------------------------------------------------

    @property
    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self.started_at

    def budget_exhausted(self) -> str | None:
        """Return the name of the exhausted budget, or ``None``."""
        budget = self.config.budget
        if self.llm_calls >= budget.max_llm_calls:
            return "max_llm_calls"
        if self.tool_calls >= budget.max_tool_calls:
            return "max_tool_calls"
        if self.elapsed_seconds >= budget.max_wall_seconds:
            return "max_wall_seconds"
        return None

    # -- bookkeeping -------------------------------------------------------

    def record(self, tool: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        self.tool_calls += 1
        self.history.append(
            {
                "tool": tool,
                "arguments": _redact(arguments),
                "ok": bool(result.get("ok")),
                "summary": _summarise(result),
            }
        )

    def add_artifact(self, kind: str, path: Path, description: str = "") -> Artifact:
        artifact = Artifact(kind=kind, path=path, description=description)
        self.artifacts.append(artifact)
        return artifact

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path) if self.path else None,
            "stem": self.stem,
            "pendingConstraints": [c.get("name") for c in self.pending_constraints],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "llmCalls": self.llm_calls,
            "toolCalls": self.tool_calls,
            "elapsedSeconds": round(self.elapsed_seconds, 2),
            "history": self.history,
        }


def _redact(arguments: dict[str, Any]) -> dict[str, Any]:
    """Drop large payloads from the history so it stays readable."""
    redacted: dict[str, Any] = {}
    for key, value in arguments.items():
        if key in {"source", "assignment", "solution"}:
            redacted[key] = f"<{len(str(value))} chars>"
        elif isinstance(value, str) and len(value) > 200:
            redacted[key] = value[:197] + "..."
        else:
            redacted[key] = value
    return redacted


def _summarise(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        return str(result.get("error", "failed"))[:200]
    for key in ("summary", "message", "score", "objectiveValue", "accepted"):
        if key in result:
            return f"{key}={result[key]}"
    return "ok"
