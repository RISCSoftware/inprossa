"""Estimate the lower bound for a DSL problem via MiniZinc/CP-SAT, optionally using a warm-start assignment."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from src.optdsl.solver.DSL_solver import DSLSolver
from hybrid.warm_start import load_warm_start, spec_from_assignment


def estimate_lower_bound(
    dsl_path: str | Path,
    warm_assignment: Mapping[str, Any] | str | Path | None = None,
    timelimit: float = 30.0,
    solver_name: str = "cp-sat",
    dsl_index_base: int = 0,
    warm_score: float | None = None,
    warm_objective_sense: str | None = None,
    warm_objective_variable: str | None = None,
) -> dict[str, Any]:
    """Run MiniZinc (CP-SAT) on the DSL problem.

    *warm_assignment* may be:

    - a mapping of decision-variable names to values, or
    - a full warm-start spec dict produced by ``hybrid.warm_start``, or
    - a path to a warm-start snapshot file (see ``hybrid/warm_start.py``).

    When a spec/file is supplied its score may add an objective bound; for a
    plain assignment that feature is only enabled via *warm_score* together
    with *warm_objective_sense*.

    Returns a dict with keys:
      - ``lower_bound``: reported objectiveBound (or None)
      - ``best_objective``: best feasible objective found during the time limit (or None)
      - ``status``: MiniZinc status string
      - ``solver_result``: full raw result from MiniZincRunner
    """
    dsl_text = Path(dsl_path).read_text(encoding="utf-8")

    spec = _resolve_warm_start(
        warm_assignment,
        warm_score=warm_score,
        warm_objective_sense=warm_objective_sense,
        warm_objective_variable=warm_objective_variable,
        problem=str(dsl_path),
    )

    solver = DSLSolver(
        code=dsl_text,
        solver_name=solver_name,
        timelimit=timelimit,
        dsl_index_base=dsl_index_base,
        warm_start=spec,
    )
    raw = solver.run()

    objectives: list[float] = raw.get("objectives", [])
    best_obj = objectives[-1] if objectives else None
    lower_bound = raw.get("objective_bound")

    return {
        "lower_bound": float(lower_bound) if lower_bound is not None else None,
        "best_objective": float(best_obj) if best_obj is not None else None,
        "status": str(raw.get("status", "unknown")),
        "solver_result": raw,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_warm_start(
    warm_assignment: Mapping[str, Any] | str | Path | None,
    *,
    warm_score: float | None,
    warm_objective_sense: str | None,
    warm_objective_variable: str | None,
    problem: str | None,
) -> dict[str, Any] | None:
    """Convert *warm_assignment* into a warm-start spec (or None).

    - Mapping with ``hints``          -> treated as a full spec dict
    - str/Path                        -> a warm-start snapshot file
    - Plain assignment mapping        -> spec built from the assignment
    """
    if warm_assignment is None:
        return None
    if isinstance(warm_assignment, (str, Path)):
        spec = load_warm_start(warm_assignment)
        spec["problem"] = problem
        return spec
    if not isinstance(warm_assignment, Mapping):
        raise TypeError(
            "warm_assignment must be a mapping, a warm-start spec dict, "
            "or a path to a warm-start file"
        )
    if "hints" in warm_assignment:
        spec = dict(warm_assignment)
        # Allow overriding an empty objective bound with explicit arguments.
        if spec.get("lower_bound") is None and spec.get("upper_bound") is None:
            if warm_score is not None and warm_objective_sense is not None:
                spec["score"] = warm_score
                spec["objective_sense"] = warm_objective_sense
                spec["lower_bound"], spec["upper_bound"] = _bounds(
                    warm_score, warm_objective_sense
                )
        spec["problem"] = spec.get("problem") or problem
        return spec
    # Plain assignment mapping -> spec without objective bound information,
    # unless an explicit score/sense is supplied by the caller.
    return spec_from_assignment(
        warm_assignment,
        score=warm_score,
        objective_sense=warm_objective_sense,
        objective_variable=warm_objective_variable,
        problem=problem,
    )


def _bounds(score: float, objective_sense: str | None) -> tuple[float | None, float | None]:
    """Derive objective bounds from a feasible *score* and the solve sense."""
    if objective_sense == "maximize":
        return float(score), None
    return None, float(score)
