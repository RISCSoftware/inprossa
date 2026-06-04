from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping

from large_neighborhood_search import (
    CVRPRouteInitializer,
    GreedyRandomizedInitializer,
    ImprovingAcceptance,
    LargeNeighborhoodSearchEngine,
    MaxIterationsStop,
    NeighborhoodPoolSelector,
    OptDSLEvaluator,
    RandomAssignmentInitializer,
    RandomFractionDestroy,
    SampledRepair,
    SimulatedAnnealingAcceptance,
    StdoutLNSLogger,
    VariableBlockDestroy,
    prepare_cvrp_assignment_for_evaluation,
    read_problem_for_lns,
)

DEFAULT_DSL = Path("problem_instances/1dbp/problem_2_t_zero_based.dsl")


def _extract_objective_value(score: float | None, objective_sense: str, penalty_base: float | None) -> str:
    if score is None:
        return "<none>"
    if score == float("inf"):
        return "<infeasible>"
    if penalty_base is not None:
        if objective_sense == "maximize" and score <= -penalty_base:
            return "<infeasible>"
        if objective_sense != "maximize" and score >= penalty_base:
            return "<infeasible>"
    return f"{objective_sense} value = {score}"


def _build_printable_assignment(variables: Mapping[str, object], assignment: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    for variable_name in sorted(variables.keys()):
        output[variable_name] = assignment.get(variable_name, "<unassigned>")
    return output


def _inject_objective_for_display(
    assignment_values: dict[str, object],
    objective_variable_name: str | None,
    score: float | None,
    objective_sense: str,
    penalty_base: float | None,
) -> None:
    if objective_variable_name is None or objective_variable_name not in assignment_values:
        return
    if assignment_values[objective_variable_name] != "<unassigned>":
        return
    if score is None or not isinstance(score, (int, float)):
        return
    if penalty_base is not None:
        if objective_sense == "maximize" and score <= -penalty_base:
            return
        if objective_sense != "maximize" and score >= penalty_base:
            return
    assignment_values[objective_variable_name] = float(score)


def _to_dsl_literal(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_to_dsl_literal(item) for item in value) + "]"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "None"
    return repr(value)


def _write_dsl_solution_snapshot(
    source_dsl_text: str,
    output_path: Path,
    assignment: Mapping[str, object],
    score: float,
    objective_sense: str,
    event: str,
    iteration: int,
    objective_variable_name: str | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(source_dsl_text.rstrip())
    lines.append("")
    lines.append("# --- LNS warm start hint ---")
    lines.append(f"# event: {event}")
    lines.append(f"# iteration: {iteration}")
    lines.append(f"# score: {score}")
    lines.append(f"# objective_sense: {objective_sense}")

    if objective_sense == "maximize":
        decorator_args = f"lower_bound={score}"
    else:
        decorator_args = f"upper_bound={score}"

    hint_items: list[str] = []
    for name in sorted(assignment.keys()):
        if name == objective_variable_name:
            continue
        value = assignment[name]
        if value is None:
            continue
        hint_items.append(f'        "{name}": {_to_dsl_literal(value)},')

    lines.append(f"@warm_start({decorator_args})")
    lines.append("def ws():")
    lines.append("    return {")
    lines.extend(hint_items)
    lines.append("    }")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generic LNS over OptDSL decision variables. "
            "Reads constants/variables/constraints/objective via the same parser path as tree search."
        )
    )
    parser.add_argument("dsl_file", nargs="?", default=str(DEFAULT_DSL), help="Path to DSL file")
    parser.add_argument("--max-iterations", type=int, default=10_000, help="Maximum LNS iterations")
    parser.add_argument("--random-seed", type=int, default=42, help="Seed for neighborhood randomness")
    parser.add_argument(
        "--initializer",
        choices=["greedy", "random", "cvrp"],
        default="greedy",
        help="Initialization strategy before LNS iterations. 'cvrp' is a problem-specific constructive initializer.",
    )
    parser.add_argument(
        "--cvrp-init-restarts",
        type=int,
        default=16,
        help="Restart attempts for CVRP constructive initializer.",
    )
    parser.add_argument(
        "--cvrp-init-randomization",
        type=float,
        default=0.3,
        help="Probability of random tie-break in CVRP nearest-neighbor construction.",
    )
    parser.add_argument(
        "--init-candidates",
        type=int,
        default=4,
        help="Candidate values tested per decision in greedy randomized initialization.",
    )
    parser.add_argument(
        "--init-completion-samples",
        type=int,
        default=2,
        help="Random completion samples per candidate during greedy randomized initialization.",
    )
    parser.add_argument(
        "--init-scoring",
        choices=["objective", "feasibility-first"],
        default="objective",
        help="Greedy initializer scoring mode.",
    )
    parser.add_argument(
        "--init-restarts",
        type=int,
        default=1,
        help="Independent restart attempts for greedy initializer (best is kept).",
    )
    parser.add_argument(
        "--init-fixup-rounds",
        type=int,
        default=1,
        help="Deterministic coordinate-descent rounds in initializer post-fixup.",
    )
    parser.add_argument(
        "--init-fixup-walk-steps",
        type=int,
        default=0,
        help="Stochastic min-conflicts walk steps in initializer post-fixup.",
    )
    parser.add_argument(
        "--init-fixup-plateau-prob",
        type=float,
        default=0.05,
        help="Probability for accepting plateau moves during stochastic initializer walk.",
    )
    parser.add_argument(
        "--acceptance",
        choices=["improving", "sa"],
        default="sa",
        help="Acceptance strategy: improving-only or simulated annealing.",
    )
    parser.add_argument(
        "--destroy-rate",
        type=float,
        default=0.2,
        help="Fraction of decision variables removed by random destroy operator.",
    )
    parser.add_argument("--sa-temperature", type=float, default=2.0, help="Initial SA temperature")
    parser.add_argument("--sa-cooling", type=float, default=0.995, help="SA cooling factor")
    parser.add_argument("--log-every", type=int, default=0, help="Iteration logging frequency (0 disables)")
    parser.add_argument("--repair-samples", type=int, default=16, help="Number of random completion samples per repair step")
    parser.add_argument(
        "--value-bias",
        choices=["auto", "uniform", "lower", "upper"],
        default="auto",
        help="Domain value sampling bias used by repair operators.",
    )
    parser.add_argument(
        "--emit-feasible-dsl",
        default=None,
        help=(
            "Write feasible assignment snapshots merged with original DSL text. "
            "Supports placeholders: {iteration}, {event}, {score}."
        ),
    )
    parser.add_argument(
        "--emit-feasible-on",
        choices=["incumbent", "accepted", "candidate", "all"],
        default="incumbent",
        help="Select which feasible events trigger DSL snapshot writing.",
    )
    parser.add_argument(
        "--emit-feasible-every",
        type=int,
        default=1,
        help="Write every N matching feasible events.",
    )
    parser.add_argument("--print-assignment", action="store_true", help="Print incumbent assignment")
    args = parser.parse_args()

    dsl_path = Path(args.dsl_file)
    if not dsl_path.exists():
        raise FileNotFoundError(f"DSL file does not exist: {dsl_path}")

    excluded_decision_variables: set[str] | None = None
    if args.initializer == "cvrp":
        excluded_decision_variables = {"u", "vehicle_used"}

    problem_data, context = read_problem_for_lns(
        dsl_path,
        random_seed=args.random_seed,
        excluded_decision_variables=excluded_decision_variables,
    )
    evaluator = OptDSLEvaluator(problem_data)
    context.extra["evaluator"] = evaluator
    context.extra["penalty_base"] = evaluator.penalty_base
    context.extra["max_iterations"] = max(0, args.max_iterations)
    if args.value_bias != "auto":
        context.extra["value_bias"] = args.value_bias

    # Auto-tune greedy initialization for dense packing-style models where
    # objective-only single-restart initialization often stays infeasible.
    is_2dbp_like = (
        {"assignments", "x_positions", "y_positions"}.issubset(problem_data.variables.keys())
        and "no_overlap" in problem_data.parsed.constraints
    )
    effective_init_scoring = args.init_scoring
    effective_init_restarts = max(1, args.init_restarts)
    if (
        is_2dbp_like
        and args.initializer == "greedy"
        and args.init_scoring == "objective"
        and args.init_restarts == 1
    ):
        effective_init_scoring = "feasibility-first"
        effective_init_restarts = 32

    if args.emit_feasible_dsl:
        source_dsl_text = dsl_path.read_text(encoding="utf-8")
        _objective_variable_name = problem_data.objective.variable_name if problem_data.objective is not None else None
        emit_event_counter = {"count": 0}
        event_groups = {
            "incumbent": {"initial", "incumbent_update"},
            "accepted": {"accepted_feasible"},
            "candidate": {"candidate_feasible"},
            "all": {"initial", "candidate_feasible", "accepted_feasible", "incumbent_update"},
        }
        selected_events = event_groups[args.emit_feasible_on]
        emit_every = max(1, args.emit_feasible_every)

        def _feasible_solution_callback(
            assignment: dict[str, object],
            score: float,
            info: dict[str, object],
            _context: object,
        ) -> None:
            event = str(info.get("event", ""))
            if event not in selected_events:
                return
            emit_event_counter["count"] += 1
            if emit_event_counter["count"] % emit_every != 0:
                return
            iteration_raw = info.get("iteration", 0)
            if isinstance(iteration_raw, int):
                iteration = iteration_raw
            elif isinstance(iteration_raw, float):
                iteration = int(iteration_raw)
            elif isinstance(iteration_raw, str):
                try:
                    iteration = int(iteration_raw)
                except ValueError:
                    iteration = 0
            else:
                iteration = 0
            output_str = args.emit_feasible_dsl.format(
                iteration=iteration,
                event=event,
                score=score,
            )
            _write_dsl_solution_snapshot(
                source_dsl_text=source_dsl_text,
                output_path=Path(output_str),
                assignment=assignment,
                score=score,
                objective_sense=context.objective_sense,
                event=event,
                iteration=iteration,
                objective_variable_name=_objective_variable_name,
            )

        context.extra["on_feasible_solution"] = _feasible_solution_callback

    repair = SampledRepair(samples=max(1, args.repair_samples))

    neighborhoods = [
        (RandomFractionDestroy(fraction=args.destroy_rate), repair),
        (VariableBlockDestroy(), repair),
    ]

    if args.acceptance == "improving":
        acceptance = ImprovingAcceptance()
    else:
        acceptance = SimulatedAnnealingAcceptance(
            temperature=args.sa_temperature,
            cooling=args.sa_cooling,
        )

    if args.initializer == "random":
        initializer = RandomAssignmentInitializer()
    elif args.initializer == "cvrp":
        initializer = CVRPRouteInitializer(
            restarts=max(1, args.cvrp_init_restarts),
            randomization=max(0.0, min(1.0, args.cvrp_init_randomization)),
        )
        context.extra["pre_evaluate_assignment_hook"] = prepare_cvrp_assignment_for_evaluation
        context.extra["infeasible_fallback_initializer"] = CVRPRouteInitializer(
            restarts=max(1, min(4, args.cvrp_init_restarts)),
            randomization=max(0.0, min(1.0, args.cvrp_init_randomization)),
        )
    else:
        initializer = GreedyRandomizedInitializer(
            candidate_values=max(1, args.init_candidates),
            completion_samples=max(1, args.init_completion_samples),
            scoring_mode=("feasibility_first" if effective_init_scoring == "feasibility-first" else "objective"),
            restarts=effective_init_restarts,
            post_fixup_rounds=max(0, args.init_fixup_rounds),
            post_fixup_walk_steps=max(0, args.init_fixup_walk_steps),
            post_fixup_plateau_prob=max(0.0, min(1.0, args.init_fixup_plateau_prob)),
        )

    engine = LargeNeighborhoodSearchEngine(
        initializer=initializer,
        selector=NeighborhoodPoolSelector(neighborhoods=neighborhoods),
        evaluator=evaluator,
        acceptance=acceptance,
        stop=MaxIterationsStop(args.max_iterations),
        logger=StdoutLNSLogger(log_every=args.log_every),
    )

    result = engine.run(context)

    parsed = problem_data.parsed
    print(f"DSL file: {dsl_path}")
    print(f"Constants ({len(parsed.constants)}): {sorted(parsed.constants.keys())}")
    print(f"Variables ({len(problem_data.variables)}): {sorted(problem_data.variables.keys())}")
    print(f"Constraints ({len(parsed.constraints)}): {sorted(parsed.constraints.keys())}")
    print(f"Decision indices: {len(context.extra['decision_keys'])}")
    if parsed.objective is None:
        print("Objective: <none detected>")
    else:
        print(f"Objective: {parsed.objective.sense}({parsed.objective.expression})")

    print(
        "LNS stats: "
        f"iterations={result.stats.iterations}, "
        f"accepted={result.stats.accepted}, "
        f"improvements={result.stats.improvements}, "
        f"infeasible={result.stats.infeasible_candidates}, "
        f"elapsed={result.stats.elapsed_seconds:.4f}s"
    )
    print(f"Best score: {result.incumbent.score}")
    print(
        f"Optimization result: "
        f"{_extract_objective_value(result.incumbent.score, context.objective_sense, evaluator.penalty_base)}"
    )

    if args.print_assignment:
        assignment_values = _build_printable_assignment(problem_data.variables, result.incumbent.assignment)
        objective_var_name = None
        if problem_data.objective is not None:
            objective_var_name = problem_data.objective.variable_name
        _inject_objective_for_display(
            assignment_values,
            objective_var_name,
            result.incumbent.score,
            context.objective_sense,
            evaluator.penalty_base,
        )
        print("Variable assignment (best solution):")
        for var_name in sorted(assignment_values.keys()):
            print(f"  {var_name} = {assignment_values[var_name]}")


if __name__ == "__main__":
    main()
