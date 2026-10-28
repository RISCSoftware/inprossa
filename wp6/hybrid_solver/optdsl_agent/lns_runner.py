"""A single, reusable entry point for running LNS.

The engine is fully composable but has no convenience wrapper: every caller
repeats the same eight lines of wiring, and two of those lines are easy to get
wrong (``context.extra["evaluator"]`` and the CVRP pre-evaluation hook). This
module owns that wiring once.

It also adds what the engine deliberately does not provide: a per-iteration
trajectory. The engine only exposes aggregate counters, which is enough to
report a score but not enough to diagnose *why* a run stalled — and diagnosis is
the whole point of the self-tuning loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from large_neighborhood_search.components import (
    AcceptanceCriterion,
    DestroyOperator,
    Initializer,
    LNSLogger,
    RepairOperator,
)
from large_neighborhood_search.defaults import (
    AdaptiveNeighborhoodSelector,
    ImprovingAcceptance,
    MaxIterationsStop,
    NeighborhoodPoolSelector,
    SampledRepair,
    SimulatedAnnealingAcceptance,
)
from large_neighborhood_search.engine import LargeNeighborhoodSearchEngine
from large_neighborhood_search.lns import (
    GreedyRandomizedInitializer,
    MCMCInitializer,
    OptDSLEvaluator,
    RandomAssignmentInitializer,
    read_problem_for_lns,
)
from large_neighborhood_search.models import LNSContext, LNSResult, LNSState
from large_neighborhood_search.registry import create_destroy, create_repair


@dataclass
class LNSRunConfig:
    """Everything needed for one LNS run.

    Operators may be given by registry name or as instances. Instances matter
    for the tuning loop, which evaluates a candidate class that is not
    registered anywhere.
    """

    instance: str | Path
    seed: int = 0
    iterations: int = 500
    initializer: str | Any = "greedy"
    acceptance: str = "improving"
    #: Registry names, or ``DestroyOperator``/``RepairOperator`` instances.
    destroys: list[str | DestroyOperator] = field(default_factory=list)
    repairs: list[str | RepairOperator] = field(default_factory=list)
    destroy_args: dict[str, Any] = field(default_factory=dict)
    repair_samples: int = 8
    adaptive: bool = False
    max_runtime_seconds: float | None = None
    no_improvement_iterations: int | None = None
    sa_temperature: float = 2.0
    sa_cooling: float = 0.995
    #: Record every iteration. Costs memory on long runs; off by default.
    record_trajectory: bool = True


@dataclass
class LNSRunResult:
    """Outcome of one LNS run, with the objective separated from the score."""

    instance: str
    seed: int
    score: float
    objective_value: float | None
    feasible: bool
    failed_constraints: int
    objective_sense: str
    assignment: dict[str, Any]
    iterations: int
    accepted: int
    improvements: int
    infeasible_candidates: int
    restarts: int
    stop_reason: str
    elapsed_seconds: float
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    operator_weights: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    #: Human-readable rendering of the incumbent, produced by a problem-specific
    #: printer. ``None`` when no printer matched.
    rendered: str | None = None
    #: What the run actually used, so every log/report shows the configuration.
    initializer_name: str | None = None
    neighborhoods: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self, *, include_assignment: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "error": self.error,
            "instance": self.instance,
            "seed": self.seed,
            "score": self.score,
            "objectiveValue": self.objective_value,
            "feasible": self.feasible,
            "failedConstraints": self.failed_constraints,
            "objectiveSense": self.objective_sense,
            "iterations": self.iterations,
            "accepted": self.accepted,
            "improvements": self.improvements,
            "infeasibleCandidates": self.infeasible_candidates,
            "restarts": self.restarts,
            "stopReason": self.stop_reason,
            "elapsedSeconds": round(self.elapsed_seconds, 3),
            "operatorWeights": self.operator_weights,
            "initializer": self.initializer_name,
            "neighborhoods": self.neighborhoods,
        }
        if self.rendered:
            payload["rendered"] = self.rendered
        if include_assignment:
            payload["assignment"] = self.assignment
        if self.trajectory:
            payload["trajectory"] = self.trajectory
        return payload


class RecordingLogger(LNSLogger):
    """Captures a per-iteration trace of the search.

    The engine calls ``on_iteration`` after every candidate, which is the only
    place the current and incumbent scores are both visible. Recording here
    avoids re-running the search just to plot it.
    """

    def __init__(self, *, max_points: int = 5000) -> None:
        self.max_points = max_points
        self.trajectory: list[dict[str, Any]] = []
        self._stride = 1

    def reset_for_run(self, _context: LNSContext) -> None:
        self.trajectory = []
        self._stride = 1

    def on_iteration(
        self,
        iteration: int,
        destroy_name: str,
        repair_name: str,
        candidate_score: float,
        accepted: bool,
        improved: bool,
        state: LNSState,
        _context: LNSContext,
    ) -> None:
        # Keep the trace bounded: on a 100k-iteration run, storing every point
        # costs more memory than the search itself. Halve the resolution instead.
        if len(self.trajectory) >= self.max_points:
            self.trajectory = self.trajectory[::2]
            self._stride *= 2
        if iteration % self._stride:
            return
        self.trajectory.append(
            {
                "iteration": iteration,
                "current": _finite(state.current.score),
                "incumbent": _finite(state.incumbent.score),
                "candidate": _finite(candidate_score),
                "accepted": accepted,
                "improved": improved,
                "destroy": destroy_name,
                "repair": repair_name,
            }
        )


def run_lns(config: LNSRunConfig) -> LNSRunResult:
    """Run LNS once and return a fully populated result.

    Never raises for expected failures (missing instance, unknown operator,
    engine error): the agent needs a result object it can report on, not an
    exception that aborts the conversation.
    """
    instance = str(config.instance)
    try:
        problem_data, context = read_problem_for_lns(instance, random_seed=config.seed)
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return _failed(instance, config.seed, f"could not read instance: {exc}")

    evaluator = OptDSLEvaluator(problem_data)
    # Both keys are required: initializers and SampledRepair read `evaluator`,
    # and the engine's feasibility fallback reads `penalty_base`. Without them
    # the search silently degrades to random behaviour.
    context.extra["evaluator"] = evaluator
    context.extra["penalty_base"] = evaluator.penalty_base

    try:
        initializer = _build_initializer(config.initializer, context)
        neighborhoods = _build_neighborhoods(config, context)
    except Exception as exc:  # noqa: BLE001
        return _failed(instance, config.seed, str(exc))

    if not neighborhoods:
        return _failed(instance, config.seed, "no neighborhoods configured")

    selector = (
        AdaptiveNeighborhoodSelector(neighborhoods=neighborhoods)
        if config.adaptive
        else NeighborhoodPoolSelector(neighborhoods=neighborhoods)
    )
    acceptance = _build_acceptance(config)
    logger = RecordingLogger() if config.record_trajectory else None

    engine = LargeNeighborhoodSearchEngine(
        initializer=initializer,
        selector=selector,
        evaluator=evaluator,
        acceptance=acceptance,
        stop=MaxIterationsStop(config.iterations),
        logger=logger,
        max_runtime_seconds=config.max_runtime_seconds,
        no_improvement_iterations=config.no_improvement_iterations,
    )

    try:
        result = engine.run(context)
    except Exception as exc:  # noqa: BLE001
        return _failed(instance, config.seed, f"engine failed: {exc}")

    details = evaluator.evaluate_detailed(result.incumbent.assignment, context)
    feasible = _is_feasible(result.incumbent.score, context)

    return LNSRunResult(
        instance=instance,
        seed=config.seed,
        score=result.incumbent.score,
        objective_value=details.objective_value,
        feasible=feasible,
        failed_constraints=details.failed_constraints,
        objective_sense=context.objective_sense,
        assignment=result.incumbent.assignment,
        iterations=result.stats.iterations,
        accepted=result.stats.accepted,
        improvements=result.stats.improvements,
        infeasible_candidates=result.stats.infeasible_candidates,
        restarts=result.stats.restarts,
        stop_reason=result.stats.stop_reason,
        elapsed_seconds=result.stats.elapsed_seconds,
        trajectory=logger.trajectory if logger is not None else [],
        operator_weights=_weights(selector, neighborhoods),
        rendered=_render(
            result.incumbent.assignment,
            problem_data,
            details.objective_value,
            context,
            feasible,
        ),
        initializer_name=type(initializer).__name__,
        neighborhoods=[
            f"{type(destroy).__name__}+{type(repair).__name__}" for destroy, repair in neighborhoods
        ],
    )


# ---------------------------------------------------------------------------
# component construction
# ---------------------------------------------------------------------------


def _build_initializer(name: str | object, context: LNSContext) -> Initializer:
    """Resolve an initializer by name, falling back to the generic greedy one.

    Problem-specific initializers are much stronger than the generic one, so
    they are worth the extra import. They are imported lazily because
    ``large_neighborhood_search.problems`` pulls in every adapter.

    An initializer *instance* (e.g. a synthesized feasibility initializer) is
    returned as-is.
    """
    if not isinstance(name, str):
        return name  # already an instance
    if name == "random":
        return RandomAssignmentInitializer()
    if name == "mcmc":
        return MCMCInitializer()

    try:
        from large_neighborhood_search.problems import (
            CVRPRouteInitializer,
            CuttingPackingInitializer,
            JSSPScheduleInitializer,
            WoodcuttingPipelineInitializer,
            detect_2dbp_problem,
            detect_cutting_packing_problem,
            detect_cvrp_problem,
            detect_woodcutting_pipeline_problem,
            prepare_cvrp_assignment_for_evaluation,
        )
    except Exception:  # noqa: BLE001 - adapters are optional
        return GreedyRandomizedInitializer()

    if name == "cvrp" or (name == "auto" and detect_cvrp_problem(context)):
        context.extra["pre_evaluate_assignment_hook"] = prepare_cvrp_assignment_for_evaluation
        return CVRPRouteInitializer()
    if name == "jssp":
        return JSSPScheduleInitializer()
    if name == "cutting_packing" or (name == "auto" and detect_cutting_packing_problem(context)):
        return CuttingPackingInitializer()
    if name == "woodcutting_pipeline" or (
        name == "auto" and detect_woodcutting_pipeline_problem(context)
    ):
        return WoodcuttingPipelineInitializer()
    if name == "2dbp" or (name == "auto" and detect_2dbp_problem(context)):
        return GreedyRandomizedInitializer(scoring_mode="objective")

    return GreedyRandomizedInitializer()


def _build_neighborhoods(
    config: LNSRunConfig,
    context: LNSContext | None = None,
) -> list[tuple[DestroyOperator, RepairOperator]]:
    # Importing this module is what populates the registry; without it every
    # create_destroy()/create_repair() call raises KeyError.
    import large_neighborhood_search.builtin_operators  # noqa: F401

    destroys = [_resolve(item, "destroy", config.destroy_args) for item in config.destroys]
    repairs = [_resolve(item, "repair", {}) for item in config.repairs]

    if not destroys and not repairs and context is not None:
        # A generic random destroy paired with a sampled repair is a poor
        # baseline on structured problems: on CVRP it produces almost only
        # infeasible candidates, which makes any comparison meaningless. Use
        # the problem-specific pair when one is detected.
        defaults = _problem_defaults(context)
        if defaults is not None:
            return [defaults]

    if not destroys:
        destroys = [create_destroy("RandomFractionDestroy")]
    if not repairs:
        repairs = [SampledRepair(samples=config.repair_samples)]

    # Cartesian product, matching example_lns.py: every destroy is paired with
    # every repair so the selector can learn which combination works.
    return [(destroy, repair) for destroy in destroys for repair in repairs]


def _problem_defaults(
    context: LNSContext,
) -> tuple[DestroyOperator, RepairOperator] | None:
    """A sensible default destroy/repair pair for the detected problem class.

    Returns ``None`` when no adapter matches, so the caller falls back to the
    generic pair.
    """
    try:
        from large_neighborhood_search.problems import (
            CVRPInsertionRepair,
            CVRPShawDestroy,
            JSSPGanttRepair,
            JSSPJobLevelDestroy,
            detect_cvrp_problem,
            detect_jssp_problem,
        )
    except Exception:  # noqa: BLE001 - adapters are optional
        return None

    if detect_cvrp_problem(context):
        return CVRPShawDestroy(), CVRPInsertionRepair()

    if detect_jssp_problem(context.constants, context.extra.get("keys_by_variable", {})):
        return JSSPJobLevelDestroy(), JSSPGanttRepair()

    return None


def _resolve(
    item: str | DestroyOperator | RepairOperator,
    kind: str,
    kwargs: dict[str, Any],
) -> Any:
    if not isinstance(item, str):
        return item
    if kind == "destroy":
        return create_destroy(item, **kwargs)
    return create_repair(item, **kwargs)


def _build_acceptance(config: LNSRunConfig) -> AcceptanceCriterion:
    if config.acceptance == "sa":
        return SimulatedAnnealingAcceptance(
            temperature=config.sa_temperature, cooling=config.sa_cooling
        )
    return ImprovingAcceptance()


def _weights(
    selector: Any,
    neighborhoods: list[tuple[DestroyOperator, RepairOperator]],
) -> dict[str, float]:
    """Per-neighborhood selection weights, when the selector tracks them."""
    weights = getattr(selector, "weights", None)
    if not isinstance(weights, list) or len(weights) != len(neighborhoods):
        return {}
    return {
        f"{type(destroy).__name__}+{type(repair).__name__}": round(weight, 4)
        for (destroy, repair), weight in zip(neighborhoods, weights)
    }


def _is_feasible(score: float, context: LNSContext) -> bool:
    if context.feasibility_classifier is not None:
        return context.feasibility_classifier.is_feasible(score)
    penalty_base = context.extra.get("penalty_base", 1e9)
    if context.objective_sense == "maximize":
        return score > -float(penalty_base)
    return score < float(penalty_base)


def _finite(value: float) -> float | None:
    """JSON has no infinity; report it as null rather than emitting ``Infinity``."""
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def _render(
    assignment: dict[str, Any],
    problem_data: Any,
    objective_value: float | None,
    context: LNSContext,
    feasible: bool,
) -> str | None:
    """Render the incumbent with the printer for this problem class.

    A failure to render is not a failure of the run, so it degrades to ``None``
    and the caller falls back to the raw statistics.
    """
    from .printers import format_solution

    return format_solution(
        assignment,
        dict(context.constants),
        problem_class=_problem_class(problem_data),
        objective_value=objective_value,
        objective_sense=context.objective_sense,
        feasible=feasible,
    )


def _problem_class(problem_data: Any) -> str | None:
    """Detect the problem class from the parsed model.

    The fingerprint works on source text, which the LNS reader does not keep, so
    the class is inferred from the constants and variables instead — the same
    markers the fingerprint uses.
    """
    constants = problem_data.constants
    variables = set(problem_data.variables)

    if all(k in constants for k in ("DEPOT", "DEMANDS", "VEHICLE_CAPACITY", "N_CITIES", "N_VEHICLES")):
        return "cvrp" if "arcs" in variables else "cvrp_tour"
    if all(k in constants for k in ("N_JOBS", "N_MACHINES", "PROCESSING_TIMES", "MACHINE_SEQUENCE")):
        return "jssp"
    if all(k in constants for k in ("BOX_CAPACITIES", "ITEM_WEIGHTS")):
        return "1dbp"
    if all(
        k in constants
        for k in (
            "NBOXES",
            "NITEMS",
            "ITEM_WIDTHS",
            "ITEM_HEIGHTS",
            "BOX_WIDTH_CAPACITIES",
            "BOX_HEIGHT_CAPACITIES",
        )
    ):
        return "2dbp"
    if all(k in constants for k in ("LAYER_LENGTH", "N_LAYERS", "N_SEGMENTS")):
        return "cutting_packing"
    if all(k in constants for k in ("GIVEN_INITIAL_BOARDS", "MAX_N_CUTS_PER_BOARD")):
        return "woodcutting"

    return None


def _failed(instance: str, seed: int, error: str) -> LNSRunResult:
    return LNSRunResult(
        instance=instance,
        seed=seed,
        score=float("inf"),
        objective_value=None,
        feasible=False,
        failed_constraints=0,
        objective_sense="minimize",
        assignment={},
        iterations=0,
        accepted=0,
        improvements=0,
        infeasible_candidates=0,
        restarts=0,
        stop_reason="error",
        elapsed_seconds=0.0,
        error=error,
    )
