"""Estimate the lower bound for a DSL problem via MiniZinc/CP-SAT, optionally using a warm-start assignment."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.optdsl.solver.DSL_solver import DSLSolver


def estimate_lower_bound(
    dsl_path: str | Path,
    warm_assignment: dict[str, Any] | None = None,
    timelimit: float = 30.0,
    solver_name: str = "cp-sat",
    dsl_index_base: int = 0,
) -> dict[str, Any]:
    """Run MiniZinc (CP-SAT) on the DSL problem.

    If *warm_assignment* is given it is injected as a ``@warm_start`` block
    appended to the DSL source so that the solver can tighten its bounds.

    Returns a dict with keys:
      - ``lower_bound``: reported objectiveBound (or None)
      - ``best_objective``: best feasible objective found during the time limit (or None)
      - ``status``: MiniZinc status string
      - ``solver_result``: full raw result from MiniZincRunner
    """
    dsl_text = Path(dsl_path).read_text(encoding="utf-8")

    if warm_assignment is not None:
        dsl_text = _inject_warm_start(dsl_text, warm_assignment)

    solver = DSLSolver(
        code=dsl_text,
        solver_name=solver_name,
        timelimit=timelimit,
        dsl_index_base=dsl_index_base,
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

def _inject_warm_start(dsl_text: str, assignment: dict[str, Any]) -> str:
    """Append a @warm_start-decorated function to *dsl_text* encoding *assignment* as hints.

    2-D list values (e.g. JSSP ``completion``) are skipped because MiniZinc's
    ``warm_start`` annotation only accepts 1-D arrays.  Helper keys produced by
    the JSSP initializer (``completion_0``, ``completion_1``, …) are also
    skipped since they have no corresponding top-level DSL variable.
    """
    lines = ["", "@warm_start", "def _warm_start_hints():"]
    lines.append("    return {")
    for var_name, value in assignment.items():
        # Skip per-row helper keys written by JSSPScheduleInitializer
        if "_" in var_name:
            _, suffix = var_name.rsplit("_", 1)
            if suffix.isdigit():
                continue
        if isinstance(value, list):
            # Skip 2-D arrays — MiniZinc warm_start doesn't support them
            if value and isinstance(value[0], list):
                continue
            formatted = "[" + ", ".join(str(v) if v is not None else "None" for v in value) + "]"
        else:
            formatted = repr(value)
        lines.append(f'        "{var_name}": {formatted},')
    lines.append("    }")
    return dsl_text + "\n".join(lines) + "\n"
