"""Configuration for the OptDSL agent harness.

Everything that varies between machines or runs lives here, so the rest of the
package never reads ``os.environ`` directly. That keeps the tool layer testable:
a test constructs an :class:`AgentConfig` and never touches the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

#: Repository root, derived from this file's location (``optdsl_agent/config.py``).
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MODEL = "gpt-4o"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


@dataclass
class Budget:
    """Hard limits for one agent session.

    The agent loop checks these before every model call and every tool call, so
    an unattended run cannot spin forever or burn an unbounded amount of money.
    """

    max_llm_calls: int = 40
    max_tool_calls: int = 120
    max_wall_seconds: float = 1800.0
    #: Per-request HTTP timeout for the model endpoint.
    request_timeout: float = 180.0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "max_llm_calls": self.max_llm_calls,
            "max_tool_calls": self.max_tool_calls,
            "max_wall_seconds": self.max_wall_seconds,
            "request_timeout": self.request_timeout,
        }


@dataclass
class AgentConfig:
    """Resolved settings for one harness invocation."""

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = None
    temperature: float = 0.2
    budget: Budget = field(default_factory=Budget)

    #: Where accepted constraints and operators are written. Never the source.
    output_dir: Path = field(default_factory=lambda: REPO_ROOT / "optdsl_agent" / "out")
    #: Where synthesized operators are written so the registry can load them.
    operator_dir: Path = field(
        default_factory=lambda: REPO_ROOT / "large_neighborhood_search" / "problems" / "generated"
    )
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)

    #: MiniZinc settings used by the exact backend.
    solver_name: str = "cp-sat"
    solve_timelimit: float = 30.0
    dsl_index_base: int = 0

    #: LNS defaults.
    lns_iterations: int = 500
    lns_seed: int = 0
    #: ``"auto"`` picks the problem-specific initializer when one is detected.
    lns_initializer: str = "auto"

    #: When true, no network calls are made; a deterministic stub proposer is used.
    dry_run: bool = False

    @classmethod
    def from_env(cls, **overrides: object) -> "AgentConfig":
        """Build a config from stored settings, environment, then overrides.

        Precedence, highest first:

        1. Explicit overrides (CLI flags)
        2. Environment variables
        3. The stored profile (see :mod:`optdsl_agent.settings`)
        4. Built-in defaults

        Environment beating the stored profile is deliberate: a CI job or a
        one-off shell can override a saved profile without editing it.

        Recognised variables:

        ``OPTDSL_AGENT_API_KEY``
            Bearer token for the model endpoint. Preferred over
            ``OPENAI_API_KEY`` because it is not tied to one vendor.
        ``OPENAI_API_KEY``
            Fallback bearer token, kept for compatibility with the existing
            ``operator_synthesis`` CLI.
        ``OPTDSL_AGENT_MODEL``
            Model name; defaults to ``gpt-4o``.
        ``OPTDSL_AGENT_BASE_URL``
            OpenAI-compatible base URL, e.g. ``http://localhost:11434/v1``.
        ``OPTDSL_AGENT_OUT``
            Output directory for generated artifacts.
        ``OPTDSL_AGENT_PROFILE``
            Which stored profile to use.
        """
        from .settings import Settings

        profile_name = overrides.pop("profile", None) or os.environ.get("OPTDSL_AGENT_PROFILE")
        stored = Settings.load().profile(profile_name)

        config = cls(
            model=(
                os.environ.get("OPTDSL_AGENT_MODEL")
                or stored.model
                or DEFAULT_MODEL
            ),
            base_url=(
                os.environ.get("OPTDSL_AGENT_BASE_URL")
                or stored.base_url
                or DEFAULT_BASE_URL
            ),
            api_key=(
                os.environ.get("OPTDSL_AGENT_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or stored.api_key
                or None
            ),
        )
        if stored.temperature is not None:
            config.temperature = stored.temperature
        if out := os.environ.get("OPTDSL_AGENT_OUT"):
            config.output_dir = Path(out)
        for key, value in overrides.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
        return config

    @property
    def has_credentials(self) -> bool:
        """True when a model call has a chance of succeeding.

        A local endpoint (Ollama, vLLM, LM Studio) needs no key, so a non-default
        base URL counts as configured.
        """
        return bool(self.api_key) or self.base_url.rstrip("/") != DEFAULT_BASE_URL

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.operator_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, object]:
        """Serialisable view, with the API key redacted."""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key": "***" if self.api_key else None,
            "temperature": self.temperature,
            "budget": self.budget.to_dict(),
            "output_dir": str(self.output_dir),
            "operator_dir": str(self.operator_dir),
            "repo_root": str(self.repo_root),
            "solver_name": self.solver_name,
            "solve_timelimit": self.solve_timelimit,
            "dsl_index_base": self.dsl_index_base,
            "lns_iterations": self.lns_iterations,
            "lns_seed": self.lns_seed,
            "lns_initializer": self.lns_initializer,
            "dry_run": self.dry_run,
        }
