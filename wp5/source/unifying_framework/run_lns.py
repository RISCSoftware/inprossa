from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from large_neighborhood_search import (
    AdaptiveNeighborhoodSelector,
    CVRPRouteInitializer,
    CVRPClusterDestroy,
    CVRPInterRouteRepair,
    CVRPRouteBreakDestroy,
    CVRPSegmentDestroy,
    CVRPShawDestroy,
    CVRPTwoOptRepair,
    CVRPWCUSTOMERDestroy,
    CVRPInsertionRepair,
    CVRPRegretInsertionRepair,
    CVRPOROptRepair,
    DBPClearBoxesDestroy,
    DBPClearItemsDestroy,
    DBPFullRepackRepair,
    DBPGreedyPlacementRepair,
    FillMissingPermutationRepair,
    GiantTourCutRepair,
    GiantTourInitializer,
    GreedyRandomizedInitializer,
    MCMCInitializer,
    PermutationPreservingInitializer,
    ImprovingAcceptance,
    LargeNeighborhoodSearchEngine,
    MaxIterationsStop,
    NeighborhoodPoolSelector,
    OptDSLEvaluator,
    PermutationSegmentDestroy,
    RandomAssignmentInitializer,
    RandomFractionDestroy,
    SampledRepair,
    SimulatedAnnealingAcceptance,
    StdoutLNSLogger,
    VariableBlockDestroy,
    has_permutation_decisions,
    prepare_cvrp_assignment_for_evaluation,
    read_problem_for_lns,
    JSSPJobLevelDestroy,
    JSSPMachineLevelDestroy,
    JSSPGanttRepair,
    JSSPScheduleInitializer,
    JSSPShiftTimesDestroy,
    JSSPShuffleDestroy,
    JSSPSwapDestroy,
    JSSPConstraintAwareRepair,
    JSSPCriticalPathDestroy,
    JSSPInsertionRepair,
    JSSPNonDelayRepair,
    JSSPCriticalBlockDestroy,
    JSSPCriticalBlockReinsertRepair,
    JSSPTimeWindowDestroy,
    JSSPBottleneckMachineDestroy,
    JSSPGapDestroy,
    JSSPOptActiveScheduleRepair,
    JSSPRemainingWorkRepair,
    JSSPMachineBalanceRepair,
    CuttingPackingInitializer,
    CuttingPackingLayerDestroy,
    CuttingPackingPieceDestroy,
    CuttingPackingRepackRepair,
    CuttingPackingInsertionRepair,
    CuttingPackingRecutRepair,
    WoodcuttingCarryThreadDestroy,
    WoodcuttingCarryThreadRepair,
    WoodcuttingCutDestroy,
    WoodcuttingCutRepair,
    WoodcuttingKeepDestroy,
    WoodcuttingKeepRepair,
    WoodcuttingPipelineInitializer,
    WoodcuttingSwapDestroy,
    WoodcuttingSwapRepair,
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
        "--restart-no-improve",
        type=int,
        default=0,
        help="Restart the current search trajectory after this many consecutive non-improving iterations (0 disables).",
    )
    parser.add_argument(
        "--restart-max",
        type=int,
        default=0,
        help="Maximum number of stagnation-triggered restarts within one LNS run (0 disables).",
    )
    parser.add_argument(
        "--lns-run-restarts",
        type=int,
        default=1,
        help="Independent full LNS runs with incremented seeds; best run is reported.",
    )
    parser.add_argument(
        "--lns-run-seed-step",
        type=int,
        default=1,
        help="Seed increment between LNS run restarts.",
    )
    parser.add_argument(
        "--initializer",
        choices=["greedy", "random", "mcmc", "cvrp", "giant_tour", "jssp", "2dbp", "cutting_packing", "woodcutting_pipeline"],
        default="greedy",
        help="Initialization strategy before LNS iterations. 'mcmc' is the generic Metropolis-Hastings initializer; 'cvrp' (arc encoding) and 'giant_tour' (permutation encoding) are CVRP-specific; 'jssp', '2dbp', 'cutting_packing', 'woodcutting_pipeline' are problem-specific.",
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
        "--giant-tour-init-restarts",
        type=int,
        default=8,
        help="Restart attempts for the giant-tour constructive initializer.",
    )
    parser.add_argument(
        "--giant-tour-init-randomization",
        type=float,
        default=0.1,
        help="Probability of random tie-break in giant-tour nearest-neighbor construction.",
    )
    parser.add_argument(
        "--giant-tour-init-improve-steps",
        type=int,
        default=20000,
        help="Bounded 2-opt improvement steps applied to the giant-tour initializer result.",
    )
    parser.add_argument(
        "--giant-tour-init-or-opt-steps",
        type=int,
        default=20000,
        help="Bounded Or-opt improvement steps applied to the giant-tour initializer result.",
    )
    parser.add_argument(
        "--lns-init-restarts",
        type=int,
        default=16,
        help="Restart attempts for the constructive initializer.",
    )
    parser.add_argument(
        "--lns-destroy-fraction",
        type=float,
        default=0.25,
        help="Fraction of elements to destroy per neighborhood iteration.",
    )
    parser.add_argument(
        "--lns-repair",
        type=str,
        action="append",
        default=[],
        choices=[
            "gantt", "constraint_aware", "insertion", "nondelay", "opt_active",
            "remaining_work", "machine_balance", "critical_reinsert",
            "CVRPInsertionRepair", "CVRPRegretInsertionRepair", "CVRPOROptRepair",
            "CVRPTwoOptRepair", "CVRPInterRouteRepair",
            "DBPGreedyPlacementRepair", "DBPFullRepackRepair",
            "CuttingPackingRepackRepair", "CuttingPackingInsertionRepair", "CuttingPackingRecutRepair",
            "WoodcuttingCutRepair", "WoodcuttingKeepRepair", "WoodcuttingSwapRepair", "WoodcuttingCarryThreadRepair"
        ],
        metavar="NAME",
        help=(
            "Repair strategy (repeatable): JSSP: 'gantt', 'constraint_aware' (default), 'insertion', 'nondelay', 'opt_active', "
            "'remaining_work', 'machine_balance', 'critical_reinsert'; CVRP: 'CVRPInsertionRepair', 'CVRPRegretInsertionRepair', "
            "'CVRPOROptRepair', 'CVRPTwoOptRepair', 'CVRPInterRouteRepair'; 2DBP: 'DBPGreedyPlacementRepair', 'DBPFullRepackRepair'; "
            "Cutting/packing: 'CuttingPackingRepackRepair', 'CuttingPackingInsertionRepair', 'CuttingPackingRecutRepair'; "
            "Woodcutting pipeline: 'WoodcuttingCutRepair', 'WoodcuttingKeepRepair', 'WoodcuttingSwapRepair', 'WoodcuttingCarryThreadRepair'. "
            "Use multiple times for multiple repairs."
        ),
    )
    parser.add_argument(
        "--lns-destroy",
        type=str,
        action="append",
        default=[],
        choices=[
            "job", "machine", "shuffle", "swap", "shift", "critical", "critical_neighbor",
            "critical_block", "gap", "time_window", "bottleneck_machine",
            "CVRPRouteBreakDestroy", "CVRPWCUSTOMERDestroy",
            "CVRPShawDestroy", "CVRPClusterDestroy", "CVRPSegmentDestroy",
            "DBPClearBoxesDestroy", "DBPClearItemsDestroy",
            "CuttingPackingLayerDestroy", "CuttingPackingPieceDestroy",
            "WoodcuttingCutDestroy", "WoodcuttingKeepDestroy", "WoodcuttingSwapDestroy", "WoodcuttingCarryThreadDestroy"
        ],
        metavar="NAME",
        help=(
            "Destroy strategy (repeatable): JSSP: 'job', 'machine', 'shuffle', 'swap', 'shift', 'critical', 'critical_neighbor', "
            "'critical_block', 'gap', 'time_window', 'bottleneck_machine'; CVRP: 'CVRPRouteBreakDestroy', 'CVRPWCUSTOMERDestroy', "
            "'CVRPShawDestroy', 'CVRPClusterDestroy', 'CVRPSegmentDestroy'; "
            "2DBP: 'DBPClearBoxesDestroy', 'DBPClearItemsDestroy'; "
            "Cutting/packing: 'CuttingPackingLayerDestroy', 'CuttingPackingPieceDestroy'; "
            "Woodcutting pipeline: 'WoodcuttingCutDestroy', 'WoodcuttingKeepDestroy', 'WoodcuttingSwapDestroy', 'WoodcuttingCarryThreadDestroy'. "
            "Use multiple times for multiple destroys. If omitted, defaults to generic."
        ),
    )
    parser.add_argument(
        "--lns-adaptive-selection",
        action="store_true",
        default=False,
        help="Use adaptive operator selection (ALNS weight scheme) instead of uniform pool selection.",
    )
    parser.add_argument(
        "--lns-adaptive-destroy-intensity",
        action="store_true",
        default=False,
        help="Enable adaptive destroy intensity scaling (stall-based up/down). Only effective with --lns-adaptive-selection.",
    )
    parser.add_argument(
        "--jssp-critical-min-destroy",
        type=int,
        default=0,
        help="Minimum number of (job,op) pairs to destroy for critical-path destroy.",
    )
    parser.add_argument(
        "--jssp-gap-fraction",
        type=float,
        default=0.35,
        help="Fraction of operations to destroy for gap (tight-gap bottleneck) destroy.",
    )
    parser.add_argument(
        "--jssp-gap-min-destroy",
        type=int,
        default=2,
        help="Minimum number of operations to destroy for gap destroy.",
    )
    parser.add_argument(
        "--jssp-opt-active-passes",
        type=int,
        default=3,
        help="Back-shift improvement passes for opt_active repair.",
    )
    parser.add_argument(
        "--jssp-opt-active-lookahead",
        type=int,
        default=1,
        help="Look-ahead window size for opt_active repair insertion.",
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
    parser.add_argument(
        "--mcmc-steps",
        type=int,
        default=5000,
        help="Maximum MCMC walk steps (used by --initializer mcmc).",
    )
    parser.add_argument(
        "--mcmc-init-temperature",
        type=float,
        default=1000.0,
        help="Initial MCMC simulated-annealing temperature.",
    )
    parser.add_argument(
        "--mcmc-min-temperature",
        type=float,
        default=0.1,
        help="Minimum MCMC temperature floor.",
    )
    parser.add_argument(
        "--mcmc-init-batch",
        type=int,
        default=3,
        help="Initial MCMC mutation batch size (decisions mutated per proposal).",
    )
    parser.add_argument(
        "--mcmc-max-mutations",
        type=int,
        default=20,
        help="Maximum MCMC mutation batch size (grows when stalled).",
    )
    parser.add_argument(
        "--mcmc-stall-threshold",
        type=int,
        default=200,
        help="MCMC steps at same failure count before increasing batch size.",
    )
    parser.add_argument("--log-every", type=int, default=0, help="Iteration logging frequency (0 disables)")
    parser.add_argument("--repair-samples", type=int, default=16, help="Number of random completion samples per repair step")
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=None,
        help="Wall-clock time limit for LNS in seconds. Stops after this many seconds regardless of iterations (default: no limit).",
    )
    parser.add_argument(
        "--no-improvement-iterations",
        type=int,
        default=None,
        help="Stop LNS early if no improvement for this many consecutive iterations (default: no convergence stop).",
    )
    parser.add_argument(
        "--value-bias",
        choices=["auto", "uniform", "lower", "upper"],
        default="auto",
        help="Domain value sampling bias used by repair operators.",
    )
    parser.add_argument(
        "--operator-profile",
        choices=["generic", "permutation"],
        default="generic",
        help=(
            "Neighborhood/repair profile selection. "
            "generic uses standard operators; permutation enables permutation-preserving initializer/repair/destroy."
        ),
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
    parser.add_argument(
        "--export-assignment-json",
        default=None,
        help="Write the incumbent decision-variable assignment as JSON to this path (for downstream processing/visualization).",
    )
    args = parser.parse_args()

    dsl_path = Path(args.dsl_file)
    if not dsl_path.exists():
        raise FileNotFoundError(f"DSL file does not exist: {dsl_path}")

    excluded_decision_variables: set[str] | None = None
    if args.initializer == "cvrp":
        excluded_decision_variables = {"u", "vehicle_used"}

    run_restarts = max(1, args.lns_run_restarts)
    seed_step = max(1, args.lns_run_seed_step)

    best_result = None
    best_problem_data = None
    best_context = None
    best_evaluator = None

    for run_idx in range(run_restarts):
        run_seed = args.random_seed + run_idx * seed_step

        problem_data, context = read_problem_for_lns(
            dsl_path,
            random_seed=run_seed,
            excluded_decision_variables=excluded_decision_variables,
        )
        evaluator = OptDSLEvaluator(problem_data)
        context.extra["evaluator"] = evaluator
        context.extra["penalty_base"] = evaluator.penalty_base
        if args.restart_no_improve > 0 and args.restart_max > 0:
            context.extra["stagnation_restart_after"] = args.restart_no_improve
            context.extra["stagnation_restart_limit"] = args.restart_max

        effective_init_scoring = args.init_scoring
        effective_init_restarts = max(1, args.init_restarts)

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

        detected_permutation_shape = has_permutation_decisions(context)
        use_permutation_tools = args.operator_profile == "permutation"
        use_jssp_tools = args.initializer == "jssp"
        use_2dbp_tools = args.initializer == "2dbp"
        use_cvrp_tools = args.initializer == "cvrp"
        use_giant_tour_tools = args.initializer == "giant_tour"
        use_cutting_packing_tools = args.initializer == "cutting_packing"
        use_woodcutting_pipeline_tools = args.initializer == "woodcutting_pipeline"
        
        # Check if CVRP/2DBP/cutting-packing/woodcutting operators are explicitly requested via --lns-destroy or --lns-repair
        lns_destroy_names = set(args.lns_destroy) if args.lns_destroy else set()
        lns_repair_names = set(args.lns_repair) if args.lns_repair else set()
        
        cvrp_destroy_names = {"CVRPRouteBreakDestroy", "CVRPWCUSTOMERDestroy", "CVRPShawDestroy", "CVRPClusterDestroy", "CVRPSegmentDestroy"}
        cvrp_repair_names = {"CVRPInsertionRepair", "CVRPRegretInsertionRepair", "CVRPOROptRepair", "CVRPTwoOptRepair", "CVRPInterRouteRepair"}
        dbp_destroy_names = {"DBPClearBoxesDestroy", "DBPClearItemsDestroy"}
        dbp_repair_names = {"DBPGreedyPlacementRepair", "DBPFullRepackRepair"}
        cp_destroy_names = {"CuttingPackingLayerDestroy", "CuttingPackingPieceDestroy"}
        cp_repair_names = {"CuttingPackingRepackRepair", "CuttingPackingInsertionRepair", "CuttingPackingRecutRepair"}
        wc_destroy_names = {"WoodcuttingCutDestroy", "WoodcuttingKeepDestroy", "WoodcuttingSwapDestroy", "WoodcuttingCarryThreadDestroy"}
        wc_repair_names = {"WoodcuttingCutRepair", "WoodcuttingKeepRepair", "WoodcuttingSwapRepair", "WoodcuttingCarryThreadRepair"}
        
        use_cvrp_operators = (lns_destroy_names & cvrp_destroy_names) or (lns_repair_names & cvrp_repair_names) or use_cvrp_tools
        use_2dbp_operators = (lns_destroy_names & dbp_destroy_names) or (lns_repair_names & dbp_repair_names) or use_2dbp_tools
        use_cutting_packing_operators = (lns_destroy_names & cp_destroy_names) or (lns_repair_names & cp_repair_names) or use_cutting_packing_tools
        use_woodcutting_pipeline_operators = (lns_destroy_names & wc_destroy_names) or (lns_repair_names & wc_repair_names) or use_woodcutting_pipeline_tools
        
        neighborhoods: list[tuple[Any, Any]] = []

        if use_giant_tour_tools:
            # The giant-tour encoding is permutation-shaped by construction, so
            # the permutation destroy/repair tooling is the right neighbourhood.
            use_permutation_tools = True

        if use_permutation_tools and not detected_permutation_shape:
            print(
                "[WARNING] --operator-profile permutation was requested, "
                "but no permutation-shaped decisions were detected. "
                "Falling back to generic operators."
            )
            use_permutation_tools = False

        # Build repair pool from explicit requests or defaults
        repair_pool = []
        
        # Determine repair names to use
        if args.lns_repair:
            # User explicitly requested repairs
            repair_names = set(args.lns_repair)
        elif use_jssp_tools:
            # Default JSSP repairs
            repair_names = {"gantt", "insertion", "nondelay", "opt_active", "remaining_work", "machine_balance", "critical_reinsert"}
        elif use_cvrp_operators:
            # Default CVRP repairs
            repair_names = {"CVRPInsertionRepair", "CVRPRegretInsertionRepair", "CVRPOROptRepair", "CVRPTwoOptRepair", "CVRPInterRouteRepair"}
        elif use_2dbp_operators:
            # Default 2DBP repairs
            repair_names = {"DBPGreedyPlacementRepair", "DBPFullRepackRepair"}
        elif use_cutting_packing_operators:
            # Default cutting/packing repairs
            repair_names = {"CuttingPackingRepackRepair", "CuttingPackingInsertionRepair", "CuttingPackingRecutRepair"}
        elif use_woodcutting_pipeline_operators:
            # Default woodcutting pipeline repairs
            repair_names = {"WoodcuttingCutRepair", "WoodcuttingKeepRepair", "WoodcuttingSwapRepair", "WoodcuttingCarryThreadRepair"}
        else:
            # Default generic problem: no domain-specific repair. Falls back to
            # the generic SampledRepair below. Do NOT force a JSSP-specific
            # repair here — woodcutting / bin-packing / other generic DSL models
            # do not expose the JSSP schedule structure and would crash.
            repair_names = set()
        
        # Iterate in sorted order: ``repair_names`` is a ``set`` whose iteration
        # order depends on PYTHONHASHSEED; iterating it directly would make the
        # operator-pool order (and therefore the LNS results for a fixed random
        # seed) differ between processes.
        for rname in sorted(repair_names):
            if rname == "gantt":
                repair_pool.append(JSSPGanttRepair())
            elif rname == "insertion":
                repair_pool.append(JSSPInsertionRepair(order="priority", improve=True))
            elif rname == "nondelay":
                repair_pool.append(JSSPNonDelayRepair(selection="spt", passes=2))
            elif rname == "opt_active":
                repair_pool.append(JSSPOptActiveScheduleRepair(
                    look_ahead=args.jssp_opt_active_lookahead,
                    passes=args.jssp_opt_active_passes,
                ))
            elif rname == "remaining_work":
                repair_pool.append(JSSPRemainingWorkRepair())
            elif rname == "machine_balance":
                repair_pool.append(JSSPMachineBalanceRepair())
            elif rname == "critical_reinsert":
                repair_pool.append(JSSPCriticalBlockReinsertRepair())
            elif rname == "constraint_aware":
                repair_pool.append(JSSPConstraintAwareRepair())
            elif rname == "CVRPInsertionRepair":
                repair_pool.append(CVRPInsertionRepair(strategy="cheapest"))
            elif rname == "CVRPRegretInsertionRepair":
                repair_pool.append(CVRPRegretInsertionRepair())
            elif rname == "CVRPOROptRepair":
                repair_pool.append(CVRPOROptRepair(or_opt_max=2, passes=5))
            elif rname == "CVRPTwoOptRepair":
                repair_pool.append(CVRPTwoOptRepair(passes=3))
            elif rname == "CVRPInterRouteRepair":
                repair_pool.append(CVRPInterRouteRepair(passes=3))
            elif rname == "DBPGreedyPlacementRepair":
                repair_pool.append(DBPGreedyPlacementRepair(restarts=8))
            elif rname == "DBPFullRepackRepair":
                repair_pool.append(DBPFullRepackRepair(restarts=16))
            elif rname == "CuttingPackingRepackRepair":
                repair_pool.append(CuttingPackingRepackRepair(restarts=8))
            elif rname == "CuttingPackingInsertionRepair":
                repair_pool.append(CuttingPackingInsertionRepair())
            elif rname == "CuttingPackingRecutRepair":
                repair_pool.append(CuttingPackingRecutRepair(restarts=8))
            elif rname == "WoodcuttingCutRepair":
                repair_pool.append(WoodcuttingCutRepair())
            elif rname == "WoodcuttingKeepRepair":
                repair_pool.append(WoodcuttingKeepRepair())
            elif rname == "WoodcuttingSwapRepair":
                repair_pool.append(WoodcuttingSwapRepair(samples=12))
            elif rname == "WoodcuttingCarryThreadRepair":
                repair_pool.append(WoodcuttingCarryThreadRepair())

        # Build destroy operators from explicit requests
        destroy_operators = []
        
        if lns_destroy_names:
            # Explicit destroy operators requested.
            # Sorted iteration keeps the pool order independent of
            # PYTHONHASHSEED (see the repair_pool note above).
            for dname in sorted(lns_destroy_names):
                # JSSP destroys
                jssp_destroy_fraction = max(0.1, min(0.9, args.lns_destroy_fraction))
                if dname == "job":
                    destroy_operators.append(JSSPJobLevelDestroy(fraction=jssp_destroy_fraction))
                elif dname == "machine":
                    destroy_operators.append(JSSPMachineLevelDestroy(fraction=jssp_destroy_fraction))
                elif dname == "shuffle":
                    destroy_operators.append(JSSPShuffleDestroy(fraction=jssp_destroy_fraction))
                elif dname == "swap":
                    destroy_operators.append(JSSPSwapDestroy(fraction=jssp_destroy_fraction))
                elif dname == "shift":
                    destroy_operators.append(JSSPShiftTimesDestroy(fraction=jssp_destroy_fraction))
                elif dname == "critical":
                    destroy_operators.append(JSSPCriticalPathDestroy(
                        fraction=jssp_destroy_fraction,
                        strategy="critical",
                        min_destroy=args.jssp_critical_min_destroy,
                    ))
                elif dname == "critical_neighbor":
                    destroy_operators.append(JSSPCriticalPathDestroy(
                        fraction=jssp_destroy_fraction,
                        strategy="neighbor",
                        min_destroy=args.jssp_critical_min_destroy,
                    ))
                elif dname == "critical_block":
                    destroy_operators.append(JSSPCriticalBlockDestroy(
                        block_size=max(3, args.jssp_critical_min_destroy or 3),
                    ))
                elif dname == "gap":
                    destroy_operators.append(JSSPGapDestroy(
                        gap_fraction=args.jssp_gap_fraction,
                        min_destroy=args.jssp_gap_min_destroy,
                    ))
                elif dname == "time_window":
                    destroy_operators.append(JSSPTimeWindowDestroy(
                        window_fraction=0.25,
                        destroy_fraction=jssp_destroy_fraction,
                        min_destroy=max(2, args.jssp_gap_min_destroy),
                    ))
                elif dname == "bottleneck_machine":
                    destroy_operators.append(JSSPBottleneckMachineDestroy(
                        machine_fraction=0.4,
                        destroy_fraction=jssp_destroy_fraction,
                        min_destroy=max(2, args.jssp_gap_min_destroy),
                    ))
                # CVRP destroys
                elif dname == "CVRPRouteBreakDestroy":
                    destroy_operators.append(CVRPRouteBreakDestroy(route_count=1, strategy="random"))
                    destroy_operators.append(CVRPRouteBreakDestroy(route_count=2, strategy="worst"))
                elif dname == "CVRPWCUSTOMERDestroy":
                    destroy_operators.append(CVRPWCUSTOMERDestroy(fraction=args.lns_destroy_fraction, strategy="worst"))
                    destroy_operators.append(CVRPWCUSTOMERDestroy(customer_count=5, strategy="random"))
                elif dname == "CVRPShawDestroy":
                    destroy_operators.append(CVRPShawDestroy(fraction=args.lns_destroy_fraction, seed_strategy="random"))
                    destroy_operators.append(CVRPShawDestroy(fraction=args.lns_destroy_fraction, seed_strategy="worst"))
                elif dname == "CVRPClusterDestroy":
                    destroy_operators.append(CVRPClusterDestroy(fraction=args.lns_destroy_fraction))
                elif dname == "CVRPSegmentDestroy":
                    destroy_operators.append(CVRPSegmentDestroy(fraction=args.lns_destroy_fraction))
                # 2DBP destroys
                elif dname == "DBPClearBoxesDestroy":
                    destroy_operators.append(DBPClearBoxesDestroy(box_count=1, strategy="random"))
                    destroy_operators.append(DBPClearBoxesDestroy(box_count=2, strategy="largest_load"))
                elif dname == "DBPClearItemsDestroy":
                    destroy_operators.append(DBPClearItemsDestroy(fraction=max(0.1, min(0.9, args.lns_destroy_fraction))))
                # Cutting/packing destroys
                elif dname == "CuttingPackingLayerDestroy":
                    destroy_operators.append(CuttingPackingLayerDestroy(layer_count=1, strategy="random"))
                    destroy_operators.append(CuttingPackingLayerDestroy(layer_count=2, strategy="fullest"))
                elif dname == "CuttingPackingPieceDestroy":
                    destroy_operators.append(CuttingPackingPieceDestroy(fraction=max(0.1, min(0.9, args.lns_destroy_fraction))))
                # Woodcutting pipeline destroys
                elif dname == "WoodcuttingCutDestroy":
                    destroy_operators.append(WoodcuttingCutDestroy(board_count=1))
                elif dname == "WoodcuttingKeepDestroy":
                    destroy_operators.append(WoodcuttingKeepDestroy(fraction=max(0.1, min(0.9, args.lns_destroy_fraction))))
                elif dname == "WoodcuttingSwapDestroy":
                    destroy_operators.append(WoodcuttingSwapDestroy(fraction=max(0.1, min(0.9, args.lns_destroy_fraction))))
                elif dname == "WoodcuttingCarryThreadDestroy":
                    destroy_operators.append(WoodcuttingCarryThreadDestroy())
        elif use_jssp_tools:
            # Default JSSP destroys
            jssp_destroy_fraction = max(0.1, min(0.9, args.lns_destroy_fraction))
            destroy_operators = [
                JSSPJobLevelDestroy(fraction=jssp_destroy_fraction),
                JSSPMachineLevelDestroy(fraction=jssp_destroy_fraction),
                JSSPShuffleDestroy(fraction=jssp_destroy_fraction),
                JSSPSwapDestroy(fraction=jssp_destroy_fraction),
                JSSPShiftTimesDestroy(fraction=jssp_destroy_fraction),
                JSSPCriticalPathDestroy(
                    fraction=jssp_destroy_fraction,
                    strategy="critical",
                    min_destroy=args.jssp_critical_min_destroy,
                ),
                JSSPCriticalPathDestroy(
                    fraction=jssp_destroy_fraction,
                    strategy="neighbor",
                    min_destroy=args.jssp_critical_min_destroy,
                ),
                JSSPCriticalBlockDestroy(
                    block_size=max(3, args.jssp_critical_min_destroy or 3),
                ),
                JSSPGapDestroy(
                    gap_fraction=args.jssp_gap_fraction,
                    min_destroy=args.jssp_gap_min_destroy,
                ),
                JSSPTimeWindowDestroy(
                    window_fraction=0.25,
                    destroy_fraction=jssp_destroy_fraction,
                    min_destroy=max(2, args.jssp_gap_min_destroy),
                ),
                JSSPBottleneckMachineDestroy(
                    machine_fraction=0.4,
                    destroy_fraction=jssp_destroy_fraction,
                    min_destroy=max(2, args.jssp_gap_min_destroy),
                ),
            ]
        elif use_cvrp_operators:
            # Default CVRP destroys
            destroy_operators = [
                CVRPRouteBreakDestroy(route_count=1, strategy="random"),
                CVRPRouteBreakDestroy(route_count=2, strategy="worst"),
                CVRPWCUSTOMERDestroy(fraction=args.lns_destroy_fraction, strategy="worst"),
                CVRPWCUSTOMERDestroy(customer_count=5, strategy="random"),
                CVRPShawDestroy(fraction=args.lns_destroy_fraction, seed_strategy="random"),
                CVRPShawDestroy(fraction=args.lns_destroy_fraction, seed_strategy="worst"),
                CVRPClusterDestroy(fraction=args.lns_destroy_fraction),
                CVRPSegmentDestroy(fraction=args.lns_destroy_fraction),
            ]
        elif use_2dbp_operators:
            # Default 2DBP destroys
            destroy_fraction = max(0.1, min(0.9, args.lns_destroy_fraction))
            destroy_operators = [
                DBPClearBoxesDestroy(box_count=1, strategy="random"),
                DBPClearBoxesDestroy(box_count=2, strategy="largest_load"),
                DBPClearItemsDestroy(fraction=destroy_fraction),
            ]
        elif use_cutting_packing_operators:
            # Default cutting/packing destroys
            destroy_fraction = max(0.1, min(0.9, args.lns_destroy_fraction))
            destroy_operators = [
                CuttingPackingLayerDestroy(layer_count=1, strategy="random"),
                CuttingPackingLayerDestroy(layer_count=2, strategy="fullest"),
                CuttingPackingPieceDestroy(fraction=destroy_fraction),
            ]
        elif use_woodcutting_pipeline_operators:
            # Default woodcutting pipeline destroys
            destroy_fraction = max(0.1, min(0.9, args.lns_destroy_fraction))
            destroy_operators = [
                WoodcuttingCutDestroy(board_count=1),
                WoodcuttingKeepDestroy(fraction=destroy_fraction),
                WoodcuttingSwapDestroy(fraction=destroy_fraction),
                WoodcuttingCarryThreadDestroy(),
            ]
        elif use_permutation_tools:
            destroy_operators = [
                PermutationSegmentDestroy(fraction=max(0.15, args.destroy_rate)),
            ]
        else:
            destroy_operators = [
                RandomFractionDestroy(fraction=args.destroy_rate),
                VariableBlockDestroy(),
            ]
        
        # Build neighborhoods from all combinations (or single repair if not set)
        if repair_pool:
            neighborhoods = [(d, r) for d in destroy_operators for r in repair_pool]
        else:
            # Fallback repair
            if use_giant_tour_tools:
                repair = SampledRepair(
                    samples=max(1, args.repair_samples),
                    base_repair=GiantTourCutRepair(),
                )
            elif use_permutation_tools:
                repair = SampledRepair(
                    samples=max(1, args.repair_samples),
                    base_repair=FillMissingPermutationRepair(),
                )
            else:
                repair = SampledRepair(samples=max(1, args.repair_samples))
            neighborhoods = [(d, repair) for d in destroy_operators]
        
        # Setup CVRP hook if CVRP operators are used
        if use_cvrp_operators:
            context.extra["pre_evaluate_assignment_hook"] = prepare_cvrp_assignment_for_evaluation

        if args.acceptance == "improving":
            acceptance = ImprovingAcceptance()
        else:
            acceptance = SimulatedAnnealingAcceptance(
                temperature=args.sa_temperature,
                cooling=args.sa_cooling,
            )

        if args.initializer == "random":
            if use_permutation_tools:
                initializer = PermutationPreservingInitializer()
            else:
                initializer = RandomAssignmentInitializer()
        elif args.initializer == "mcmc":
            initializer = MCMCInitializer(
                max_steps=args.mcmc_steps,
                initial_temperature=args.mcmc_init_temperature,
                min_temperature=args.mcmc_min_temperature,
                num_muted_decisions=args.mcmc_init_batch,
                max_muted_decisions=args.mcmc_max_mutations,
                stall_threshold=args.mcmc_stall_threshold,
            )
        elif args.initializer == "cvrp":
            initializer = CVRPRouteInitializer(
                restarts=max(1, args.cvrp_init_restarts),
                randomization=max(0.0, min(1.0, args.cvrp_init_randomization)),
            )
            context.extra["pre_evaluate_assignment_hook"] = prepare_cvrp_assignment_for_evaluation
        elif args.initializer == "giant_tour":
            initializer = GiantTourInitializer(
                restarts=max(1, args.giant_tour_init_restarts),
                randomization=max(0.0, min(1.0, args.giant_tour_init_randomization)),
                improve_steps=max(0, args.giant_tour_init_improve_steps),
                or_opt_steps=max(0, args.giant_tour_init_or_opt_steps),
            )
        elif args.initializer == "jssp":
            initializer = JSSPScheduleInitializer(restarts=max(1, args.lns_init_restarts))
        elif args.initializer == "2dbp":
            initializer = GreedyRandomizedInitializer(
                candidate_values=max(1, args.init_candidates),
                completion_samples=max(1, args.init_completion_samples),
                scoring_mode="objective",
                restarts=max(1, args.lns_init_restarts),
            )
        elif args.initializer == "cutting_packing":
            initializer = CuttingPackingInitializer(restarts=max(1, args.lns_init_restarts))
        elif args.initializer == "woodcutting_pipeline":
            initializer = WoodcuttingPipelineInitializer(restarts=max(1, args.lns_init_restarts))
        elif use_permutation_tools:
            initializer = PermutationPreservingInitializer()
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

        if args.lns_adaptive_selection:
            selector = AdaptiveNeighborhoodSelector(
                neighborhoods=neighborhoods,
                adaptive_intensity=args.lns_adaptive_destroy_intensity,
            )
        else:
            selector = NeighborhoodPoolSelector(neighborhoods=neighborhoods)

        engine = LargeNeighborhoodSearchEngine(
            initializer=initializer,
            selector=selector,
            evaluator=evaluator,
            acceptance=acceptance,
            stop=MaxIterationsStop(args.max_iterations),
            logger=StdoutLNSLogger(log_every=args.log_every),
            max_runtime_seconds=args.max_runtime_seconds,
            no_improvement_iterations=args.no_improvement_iterations,
        )

        result = engine.run(context)

        print(
            f"[run {run_idx + 1}/{run_restarts}] seed={run_seed} "
            f"best={result.incumbent.score} accepted={result.stats.accepted} "
            f"improvements={result.stats.improvements} infeasible={result.stats.infeasible_candidates} "
            f"restarts={result.stats.restarts}"
        )

        if best_result is None:
            best_result = result
            best_problem_data = problem_data
            best_context = context
            best_evaluator = evaluator
        else:
            sense = context.objective_sense
            cur = result.incumbent.score
            best = best_result.incumbent.score
            if (sense == "maximize" and cur > best) or (sense != "maximize" and cur < best):
                best_result = result
                best_problem_data = problem_data
                best_context = context
                best_evaluator = evaluator

    if best_result is None or best_problem_data is None or best_context is None or best_evaluator is None:
        raise RuntimeError("LNS did not produce any run result")

    result = best_result
    problem_data = best_problem_data
    context = best_context
    evaluator = best_evaluator

    parsed = problem_data.parsed
    print(f"DSL file: {dsl_path}")
    if run_restarts > 1:
        print(f"LNS run restarts: {run_restarts} (seed step {seed_step})")
    print(
        "Operator profile: "
        f"{args.operator_profile} "
        f"(perm_enabled={use_permutation_tools}, perm_shape={detected_permutation_shape})"
    )
    print(f"Initializer: {args.initializer}")
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
        f"restarts={result.stats.restarts}, "
        f"elapsed={result.stats.elapsed_seconds:.4f}s"
    )
    print(f"Best score: {result.incumbent.score}")
    print(f"Stop reason: {result.stats.stop_reason}")
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

    if args.export_assignment_json:
        export_path = Path(args.export_assignment_json)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(json.dumps(result.incumbent.assignment, indent=2), encoding="utf-8")
        print(f"Assignment exported to {export_path}")


if __name__ == "__main__":
    main()
