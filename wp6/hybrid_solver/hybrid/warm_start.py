"""Warm-start snapshot files for the hybrid solver.

An LNS run can export the incumbent assignment to a dedicated warm-start file
(a small JSON document) instead of duplicating the whole problem DSL.  The
MiniZinc backend then consumes that file together with the *original* problem
DSL, keeping the problem file untouched and letting a problem swap between
different warm starts freely.

File format (JSON)::

    {
        "version": 1,
        "problem": "problem_instances/cvrp/random_euclidean_cvrp_8.dsl",
        "objective_sense": "minimize" | "maximize",
        "objective_variable": "<dsl objective variable>",
        "score": 123.0,
        "event": "incumbent_update",
        "iteration": 42,
        "hints": { "<dsl-var>": <literal>, ... }
    }

``hints`` (plus the ``lower_bound``/``upper_bound`` derived from
``score``+``objective_sense``) are exactly what the MiniZinc translator picks
up from a ``@warm_start`` block.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from src.optdsl.solver.warm_start import (
    normalise_hints,
    warm_start_block,
    inject_warm_start,
)

WARM_START_VERSION = 1


def spec_from_assignment(
    assignment: Mapping[str, Any],
    *,
    score: float | None = None,
    objective_sense: str | None = None,
    objective_variable: str | None = None,
    problem: str | None = None,
    event: str | None = None,
    iteration: int | None = None,
) -> dict[str, Any]:
    """Build a warm-start spec from a decision-variable assignment.

    Hints are normalised for the MiniZinc backend (unassigned values, helper
    keys, and nested arrays are dropped).  A feasible *score* becomes an
    objective bound — the upper bound for minimization problems, the lower
    bound for maximization problems.
    """
    lower_bound = None
    upper_bound = None
    if score is not None and objective_sense is not None:
        if objective_sense == "maximize":
            lower_bound = float(score)
        else:
            upper_bound = float(score)

    spec: dict[str, Any] = {
        "hints": dict(normalise_hints(assignment)),
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "score": score,
        "objective_sense": objective_sense,
        "objective_variable": objective_variable,
        "problem": problem,
        "event": event,
        "iteration": iteration,
    }
    return spec


def save_warm_start(path: str | Path, spec: Mapping[str, Any]) -> None:
    """Serialize a warm-start spec (see ``spec_from_assignment``) to JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "version": WARM_START_VERSION,
        "problem": spec.get("problem"),
        "objective_sense": spec.get("objective_sense"),
        "objective_variable": spec.get("objective_variable"),
        "score": spec.get("score"),
        "event": spec.get("event"),
        "iteration": spec.get("iteration"),
        "hints": spec.get("hints") or {},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_warm_start(path: str | Path) -> dict[str, Any]:
    """Load a warm-start snapshot file and return it as a backend spec.

    Raises :class:`ValueError` for an unsupported version or a missing
    ``hints`` mapping.
    """
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"warm start file {path} must contain a JSON object")

    version = payload.get("version")
    if version != WARM_START_VERSION:
        raise ValueError(
            f"unsupported warm start version {version!r} in {path} "
            f"(expected {WARM_START_VERSION})"
        )

    hints = payload.get("hints")
    if not isinstance(hints, dict):
        raise ValueError(f"warm start file {path} must contain a 'hints' object")

    score = payload.get("score")
    objective_sense = payload.get("objective_sense")
    lower_bound = None
    upper_bound = None
    if score is not None and objective_sense == "maximize":
        lower_bound = float(score)
    elif score is not None:
        upper_bound = float(score)

    return {
        "hints": hints,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "score": score,
        "objective_sense": objective_sense,
        "objective_variable": payload.get("objective_variable"),
        "problem": payload.get("problem"),
        "event": payload.get("event"),
        "iteration": payload.get("iteration"),
    }


__all__ = [
    "WARM_START_VERSION",
    "spec_from_assignment",
    "save_warm_start",
    "load_warm_start",
    "warm_start_block",
    "inject_warm_start",
]
