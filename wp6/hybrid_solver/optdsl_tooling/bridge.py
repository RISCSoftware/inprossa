"""JSON-in/JSON-out bridge for editor integrations.

The VS Code extension shells out to this module rather than reimplementing any
OptDSL semantics. One request object on stdin, one JSON object on stdout.

Commands
--------
``analyze``
    Static analysis of a formulation.
``validateConstraint``
    Validate LLM-proposed constraints, including the vacuity check.
``fingerprint``
    Problem-class detection.
``translate``
    OptDSL -> MiniZinc text.
``solve``
    Run MiniZinc.
``lns``
    Run the LNS engine.
``synthesizeOperator``
    Validate (and optionally generate) an LNS operator.

Every command returns ``{"ok": true, ...}`` or ``{"ok": false, "error": "..."}``.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from .analysis import analyze
from .diagnostics import Severity, check
from .fingerprint import fingerprint


def main() -> int:
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        _emit({"ok": False, "error": f"invalid request JSON: {exc}"})
        return 2

    command = request.get("command")
    handler = _COMMANDS.get(command)
    if handler is None:
        _emit({"ok": False, "error": f"unknown command '{command}'"})
        return 2

    try:
        result = handler(request)
    except Exception:
        _emit({"ok": False, "error": traceback.format_exc(limit=5)})
        return 1

    _emit({"ok": True, **result})
    return 0


def _emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def _cmd_analyze(request: dict[str, Any]) -> dict[str, Any]:
    index = analyze(request["source"])
    problem = fingerprint(index)

    return {
        "syntaxError": str(index.syntax_error) if index.syntax_error else None,
        "decisionCount": index.decision_count,
        "variables": {
            name: {
                "decision": variable.is_decision,
                "indices": variable.decision_count,
                "annotation": variable.annotation_code,
                "value": variable.value_code,
            }
            for name, variable in index.variables.items()
        },
        "constants": {name: _preview(constant.value) for name, constant in index.constants.items()},
        "predicates": {
            name: {
                "parameters": [parameter.name for parameter in predicate.parameters],
                "invoked": predicate.invoked_at_top_level,
                "objective": predicate.used_as_objective,
            }
            for name, predicate in index.predicates.items()
        },
        "objective": (
            {"sense": index.objective.sense, "expression": index.objective.expression}
            if index.objective
            else None
        ),
        "problemClass": problem.best.name if problem.best else None,
        "problemScore": round(problem.score, 4),
        "diagnostics": [
            {
                "code": diagnostic.code,
                "message": diagnostic.message,
                "severity": int(diagnostic.severity),
                "line": diagnostic.span.start_line,
            }
            for diagnostic in check(index)
        ],
    }


def _cmd_fingerprint(request: dict[str, Any]) -> dict[str, Any]:
    index = analyze(request["source"])
    problem = fingerprint(index)
    return {
        "best": problem.best.name if problem.best else None,
        "score": round(problem.score, 4),
        "matched": problem.matched,
        "explanation": problem.explain(),
        "candidates": [
            {"name": candidate.name, "score": round(score, 4)}
            for candidate, score in problem.candidates
        ],
    }


def _cmd_validate_constraint(request: dict[str, Any]) -> dict[str, Any]:
    """Validate proposed constraints against the current formulation.

    Three checks, in increasing cost:

    1. The combined source still parses and produces no new errors.
    2. The constraint is not vacuous — it must be violated by at least one
       random assignment, otherwise it constrains nothing.
    3. The constraint is not over-constrained — it must be satisfiable by at
       least one random assignment, otherwise it likely encodes a mistake.
    """
    from .constraint_validation import validate_constraints

    return validate_constraints(
        request["source"],
        request.get("constraints", []),
        samples=int(request.get("samples", 200)),
        seed=int(request.get("seed", 0)),
    )


def _cmd_translate(request: dict[str, Any]) -> dict[str, Any]:
    from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator

    translator = MiniZincTranslator(request["source"], dsl_index_base=int(request.get("indexBase", 0)))
    return {"model": translator.unroll_translation()}


def _cmd_solve(request: dict[str, Any]) -> dict[str, Any]:
    from src.optdsl.solver.DSL_solver import DSLSolver

    solver = DSLSolver(
        request["source"],
        solver_name=request.get("solver", "cp-sat"),
        timelimit=float(request.get("timelimit", 30)),
        dsl_index_base=int(request.get("indexBase", 0)),
    )
    return {"result": solver.run()}


def _cmd_lns(request: dict[str, Any]) -> dict[str, Any]:
    from large_neighborhood_search.lns import OptDSLEvaluator, read_problem_for_lns
    from large_neighborhood_search.engine import LargeNeighborhoodSearchEngine
    from large_neighborhood_search.defaults import (
        ImprovingAcceptance,
        MaxIterationsStop,
        NeighborhoodPoolSelector,
        SampledRepair,
    )
    from large_neighborhood_search.registry import create_destroy

    import large_neighborhood_search.builtin_operators  # noqa: F401

    problem_data, context = read_problem_for_lns(
        request["path"], random_seed=int(request.get("seed", 0))
    )
    evaluator = OptDSLEvaluator(problem_data)
    context.extra["evaluator"] = evaluator
    context.extra["penalty_base"] = evaluator.penalty_base

    destroy = create_destroy(
        request.get("destroy", "RandomFractionDestroy"),
        **request.get("destroyArgs", {}),
    )
    repair = SampledRepair(samples=int(request.get("repairSamples", 4)))

    engine = LargeNeighborhoodSearchEngine(
        initializer=_initializer(request.get("initializer", "greedy"), context),
        selector=NeighborhoodPoolSelector(neighborhoods=[(destroy, repair)]),
        evaluator=evaluator,
        acceptance=ImprovingAcceptance(),
        stop=MaxIterationsStop(int(request.get("iterations", 200))),
    )
    result = engine.run(context)

    return {
        "score": result.incumbent.score,
        "stats": {
            "iterations": result.stats.iterations,
            "accepted": result.stats.accepted,
            "improvements": result.stats.improvements,
            "infeasibleCandidates": result.stats.infeasible_candidates,
            "elapsedSeconds": round(result.stats.elapsed_seconds, 3),
            "stopReason": result.stats.stop_reason,
        },
    }


def _initializer(name: str, context: Any) -> Any:
    from large_neighborhood_search.lns import (
        GreedyRandomizedInitializer,
        RandomAssignmentInitializer,
    )

    if name == "random":
        return RandomAssignmentInitializer()
    return GreedyRandomizedInitializer()


def _cmd_synthesize_operator(request: dict[str, Any]) -> dict[str, Any]:
    from operator_synthesis.harness import AcceptancePolicy, evaluate_candidate

    verdict = evaluate_candidate(
        request["source"],
        request.get("kind", "destroy"),
        request["instance"],
        repo_root=request.get("repoRoot", "."),
        policy=AcceptancePolicy(
            require_improvement=bool(request.get("requireImprovement", True))
        ),
        iterations=int(request.get("iterations", 200)),
        seed=int(request.get("seed", 0)),
    )
    return verdict.to_dict()


def _preview(value: Any, limit: int = 200) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


_COMMANDS = {
    "analyze": _cmd_analyze,
    "fingerprint": _cmd_fingerprint,
    "validateConstraint": _cmd_validate_constraint,
    "translate": _cmd_translate,
    "solve": _cmd_solve,
    "lns": _cmd_lns,
    "synthesizeOperator": _cmd_synthesize_operator,
}


if __name__ == "__main__":
    raise SystemExit(main())
