"""LLM harness for OptDSL formulations and their two backends.

The package drives a formulation through a conversation: analyse it, explain it,
add constraints, solve it exactly with MiniZinc, solve it heuristically with
LNS, synthesize neighborhood operators, and tune those operators by comparing
LNS against the exact solver.

Entry points::

    python -m optdsl_agent analyze  <file.dsl>
    python -m optdsl_agent explain  <file.dsl>
    python -m optdsl_agent solve    <file.dsl>
    python -m optdsl_agent lns      <file.dsl>
    python -m optdsl_agent tune     <file.dsl> [...]
    python -m optdsl_agent chat     <file.dsl>

The library surface is intentionally small: :class:`AgentConfig`,
:class:`AgentSession`, and the tool functions in :mod:`optdsl_agent.tools`.
"""

from __future__ import annotations

from . import _paths  # noqa: F401  (must run before the sibling-package imports below)
from .config import AgentConfig, Budget
from .digest import ModelSummary, model_digest, model_summary
from .lns_runner import LNSRunConfig, LNSRunResult, run_lns

__all__ = [
    "AgentConfig",
    "Budget",
    "LNSRunConfig",
    "LNSRunResult",
    "ModelSummary",
    "model_digest",
    "model_summary",
    "run_lns",
]

__version__ = "0.1.0"
