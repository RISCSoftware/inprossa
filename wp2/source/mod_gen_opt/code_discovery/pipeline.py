"""CodeDiscoveryPipeline: orchestrates LNS → lower-bound estimation → LLM operator generation → re-evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from large_neighborhood_search import (
    GreedyRandomizedInitializer,
    ImprovingAcceptance,
    LargeNeighborhoodSearchEngine,
    LNSResult,
    MaxIterationsStop,
    NeighborhoodPoolSelector,
    OptDSLEvaluator,
    RandomAssignmentInitializer,
    RandomFractionDestroy,
    SampledRepair,
    StdoutLNSLogger,
    VariableBlockDestroy,
    read_problem_for_lns,
)
from large_neighborhood_search.components import DestroyOperator, RepairOperator
from large_neighborhood_search.models import LNSContext
from llm.llmclient import LLMClient

from .lower_bound import estimate_lower_bound
from .operator_gen import generate_operators_with_llm


@dataclass
class DiscoveryResult:
    """Holds all outputs produced by one :class:`CodeDiscoveryPipeline` run."""

    # Phase 1 – initial LNS
    initial_lns_result: LNSResult | None = None

    # Phase 2 – lower-bound estimation
    lower_bound_result: dict[str, Any] = field(default_factory=dict)

    # Phase 3 – LLM-generated operators (source saved for inspection)
    generated_destroy_name: str = ""
    generated_repair_name: str = ""
    generated_operator_pairs: list[dict[str, Any]] = field(default_factory=list)
    selected_destroy_names: list[str] = field(default_factory=list)
    selected_repair_names: list[str] = field(default_factory=list)
    operator_combo_trials: list[dict[str, Any]] = field(default_factory=list)

    # Phase 4 – LNS with generated operators
    generated_lns_result: LNSResult | None = None

    # Phase 5 – lower-bound estimation with the improved solution
    generated_lower_bound_result: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        lines: list[str] = ["=== Code Discovery Summary ==="]

        if self.initial_lns_result is not None:
            s = self.initial_lns_result.stats
            lines.append(
                f"[Phase 1] Initial LNS  — best score: {self.initial_lns_result.incumbent.score:.4f}"
                f"  ({s.iterations} iterations, {s.elapsed_seconds:.1f}s)"
            )

        lb = self.lower_bound_result
        lines.append(
            f"[Phase 2] Lower bound  — solver best: {lb.get('best_objective')}  "
            f"bound: {lb.get('lower_bound')}  status: {lb.get('status')}"
        )

        lines.append(
            f"[Phase 3] LLM operators— destroy: {self.generated_destroy_name}  "
            f"repair: {self.generated_repair_name}"
        )

        if self.generated_operator_pairs:
            successes = sum(1 for row in self.generated_operator_pairs if row.get("status") == "ok")
            lines.append(
                f"[Phase 3] Generated pairs: {successes}/{len(self.generated_operator_pairs)} successful"
            )

        if self.selected_destroy_names or self.selected_repair_names:
            lines.append(
                "[Phase 4] Selected pools  — "
                f"destroy={self.selected_destroy_names}  repair={self.selected_repair_names}"
            )

        if self.generated_lns_result is not None:
            s2 = self.generated_lns_result.stats
            lines.append(
                f"[Phase 4] Generated LNS— best score: {self.generated_lns_result.incumbent.score:.4f}"
                f"  ({s2.iterations} iterations, {s2.elapsed_seconds:.1f}s)"
            )

        lb2 = self.generated_lower_bound_result
        lines.append(
            f"[Phase 5] Re-estimated — solver best: {lb2.get('best_objective')}  "
            f"bound: {lb2.get('lower_bound')}  status: {lb2.get('status')}"
        )

        return "\n".join(lines)


class CodeDiscoveryPipeline:
    """Full pipeline: LNS → lower bound → LLM operators → LNS again → lower bound.

    Parameters
    ----------
    dsl_path:
        Path to the problem ``.dsl`` file.
    llm_client:
        An initialised :class:`~llm.llmclient.LLMClient`.  Pass ``None`` to
        skip operator generation and use the built-in default operators only.
    lns_iterations:
        Number of LNS iterations for each LNS phase.
    solver_timelimit:
        Wall-clock seconds given to MiniZinc for each lower-bound estimation.
    solver_name:
        MiniZinc backend to use (default ``"cp-sat"`` for OR-Tools CP-SAT solver).
    random_seed:
        Seed for the LNS random number generator.
    verbose:
        Print a :class:`StdoutLNSLogger` during LNS runs.
    """

    def __init__(
        self,
        dsl_path: str | Path,
        llm_client: LLMClient | None = None,
        lns_iterations: int = 200,
        operator_generation_rounds: int = 100,
        operator_tuning_trials: int = 20,
        tuning_iterations: int = 60,
        solver_timelimit: float = 30.0,
        solver_name: str = "cp-sat",
        random_seed: int = 42,
        verbose: bool = True,
    ) -> None:
        self.dsl_path = Path(dsl_path)
        self.llm_client = llm_client
        self.lns_iterations = lns_iterations
        self.operator_generation_rounds = max(1, operator_generation_rounds)
        self.operator_tuning_trials = max(1, operator_tuning_trials)
        self.tuning_iterations = max(10, tuning_iterations)
        self.solver_timelimit = solver_timelimit
        self.solver_name = solver_name
        self.random_seed = random_seed
        self.verbose = verbose

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> DiscoveryResult:
        result = DiscoveryResult()

        # ── Phase 1: run LNS with default operators ──────────────────────
        print("\n[CodeDiscovery] Phase 1: Running initial LNS …")
        problem_data, context = read_problem_for_lns(self.dsl_path, random_seed=self.random_seed)
        evaluator = OptDSLEvaluator(problem_data)
        context.extra["evaluator"] = evaluator

        lns_result = self._run_lns(context, evaluator, use_default_operators=True)
        result.initial_lns_result = lns_result
        print(f"  Best score: {lns_result.incumbent.score}")

        # ── Phase 2: estimate lower bound (warm-start from LNS solution) ─
        print("\n[CodeDiscovery] Phase 2: Estimating lower bound via MiniZinc …")
        lb_result = estimate_lower_bound(
            dsl_path=self.dsl_path,
            warm_assignment=lns_result.incumbent.assignment,
            timelimit=self.solver_timelimit,
            solver_name=self.solver_name,
        )
        result.lower_bound_result = lb_result
        print(f"  Lower bound: {lb_result['lower_bound']}  best: {lb_result['best_objective']}  status: {lb_result['status']}")

        # ── Phase 3: generate many operators with LLM ────────────────────
        print("\n[CodeDiscovery] Phase 3: Generating LNS operators via LLM …")
        dsl_text = self.dsl_path.read_text(encoding="utf-8")
        lns_summary = self._build_lns_summary(lns_result, lb_result)

        generated_destroy_ops: list[DestroyOperator] = []
        generated_repair_ops: list[RepairOperator] = []

        if self.llm_client is not None:
            print(f"  Running {self.operator_generation_rounds} generation rounds …")
            for round_idx in range(self.operator_generation_rounds):
                try:
                    destroy_op, repair_op = generate_operators_with_llm(
                        problem_dsl_text=dsl_text,
                        lns_result_summary=lns_summary,
                        llm_client=self.llm_client,
                    )
                    generated_destroy_ops.append(destroy_op)
                    generated_repair_ops.append(repair_op)
                    record = {
                        "round": round_idx,
                        "status": "ok",
                        "destroy_name": type(destroy_op).__name__,
                        "repair_name": type(repair_op).__name__,
                    }
                    result.generated_operator_pairs.append(record)
                except (RuntimeError, OSError, ValueError) as exc:
                    result.generated_operator_pairs.append(
                        {
                            "round": round_idx,
                            "status": "error",
                            "error": str(exc),
                        }
                    )
            successes = len(generated_destroy_ops)
            print(f"  Generated {successes}/{self.operator_generation_rounds} operator pairs successfully.")
        else:
            print("  No LLMClient provided — skipping operator generation.")

        # ── Phase 4: tune combinations of all operators and rerun LNS ────
        print("\n[CodeDiscovery] Phase 4: Evaluating operator combinations …")
        best_combo = self._evaluate_operator_combinations(
            result=result,
            generated_destroy_ops=generated_destroy_ops,
            generated_repair_ops=generated_repair_ops,
        )

        result.selected_destroy_names = [type(d).__name__ for d in best_combo["destroy_ops"]]
        result.selected_repair_names = [type(r).__name__ for r in best_combo["repair_ops"]]
        result.generated_destroy_name = result.selected_destroy_names[0]
        result.generated_repair_name = result.selected_repair_names[0]

        print(
            "  Selected combination: "
            f"destroy={result.selected_destroy_names}  repair={result.selected_repair_names}"
        )

        print("\n[CodeDiscovery] Phase 4b: Running full LNS with selected operators …")
        problem_data2, context2 = read_problem_for_lns(self.dsl_path, random_seed=self.random_seed + 2000)
        evaluator2 = OptDSLEvaluator(problem_data2)
        context2.extra["evaluator"] = evaluator2

        lns_result2 = self._run_lns_with_operator_pool(
            context=context2,
            evaluator=evaluator2,
            destroy_ops=best_combo["destroy_ops"],
            repair_ops=best_combo["repair_ops"],
            iterations=self.lns_iterations,
        )
        result.generated_lns_result = lns_result2
        print(f"  Best score: {lns_result2.incumbent.score}")

        # ── Phase 5: re-estimate lower bound with the improved solution ───
        print("\n[CodeDiscovery] Phase 5: Re-estimating lower bound …")
        lb_result2 = estimate_lower_bound(
            dsl_path=self.dsl_path,
            warm_assignment=lns_result2.incumbent.assignment,
            timelimit=self.solver_timelimit,
            solver_name=self.solver_name,
        )
        result.generated_lower_bound_result = lb_result2
        print(f"  Lower bound: {lb_result2['lower_bound']}  best: {lb_result2['best_objective']}  status: {lb_result2['status']}")

        print("\n" + result.summary())
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_lns(
        self,
        context: LNSContext,
        evaluator: OptDSLEvaluator,
        use_default_operators: bool = True,
        custom_destroy: DestroyOperator | None = None,
        custom_repair: RepairOperator | None = None,
    ) -> LNSResult:
        if use_default_operators or custom_destroy is None or custom_repair is None:
            destroy_ops: list[DestroyOperator] = [RandomFractionDestroy(fraction=0.2), VariableBlockDestroy()]
            repair_ops: list[RepairOperator] = [SampledRepair()]
        else:
            destroy_ops = [custom_destroy, RandomFractionDestroy(fraction=0.15)]
            repair_ops = [custom_repair, SampledRepair()]

        return self._run_lns_with_operator_pool(
            context=context,
            evaluator=evaluator,
            destroy_ops=destroy_ops,
            repair_ops=repair_ops,
            iterations=self.lns_iterations,
        )

    def _run_lns_with_operator_pool(
        self,
        context: LNSContext,
        evaluator: OptDSLEvaluator,
        destroy_ops: list[DestroyOperator],
        repair_ops: list[RepairOperator],
        iterations: int,
    ) -> LNSResult:
        if not destroy_ops:
            destroy_ops = [RandomFractionDestroy(fraction=0.2), VariableBlockDestroy()]
        if not repair_ops:
            repair_ops = [SampledRepair()]

        # NeighborhoodPoolSelector expects (destroy, repair) pairs.
        neighborhoods = [(d, r) for d in destroy_ops for r in repair_ops]
        selector = NeighborhoodPoolSelector(neighborhoods)
        acceptance = ImprovingAcceptance()
        stop = MaxIterationsStop(iterations)
        logger = StdoutLNSLogger() if self.verbose else None

        initializer: GreedyRandomizedInitializer | RandomAssignmentInitializer
        try:
            initializer = GreedyRandomizedInitializer(candidate_values=3, restarts=1)
        except (TypeError, ValueError):
            initializer = RandomAssignmentInitializer()

        engine = LargeNeighborhoodSearchEngine(
            initializer=initializer,
            selector=selector,
            evaluator=evaluator,
            acceptance=acceptance,
            stop=stop,
            logger=logger,
        )
        return engine.run(context)

    def _evaluate_operator_combinations(
        self,
        result: DiscoveryResult,
        generated_destroy_ops: list[DestroyOperator],
        generated_repair_ops: list[RepairOperator],
    ) -> dict[str, Any]:
        default_destroy_factories: list[Callable[[], DestroyOperator]] = [
            lambda: RandomFractionDestroy(fraction=0.2),
            lambda: VariableBlockDestroy(),
        ]
        default_repair_factories: list[Callable[[], RepairOperator]] = [lambda: SampledRepair()]

        destroy_candidates: list[DestroyOperator] = [factory() for factory in default_destroy_factories]
        repair_candidates: list[RepairOperator] = [factory() for factory in default_repair_factories]
        destroy_candidates.extend(generated_destroy_ops)
        repair_candidates.extend(generated_repair_ops)

        trial_specs: list[dict[str, Any]] = []
        trial_specs.append(
            {
                "label": "default",
                "destroy_ops": [factory() for factory in default_destroy_factories],
                "repair_ops": [factory() for factory in default_repair_factories],
            }
        )

        for fraction in (0.1, 0.15, 0.2, 0.25, 0.3):
            trial_specs.append(
                {
                    "label": f"fraction_{fraction:.2f}",
                    "destroy_ops": [RandomFractionDestroy(fraction=fraction), VariableBlockDestroy()],
                    "repair_ops": [SampledRepair()],
                }
            )

        for idx in range(min(len(generated_destroy_ops), len(generated_repair_ops))):
            trial_specs.append(
                {
                    "label": f"generated_pair_{idx}",
                    "destroy_ops": [generated_destroy_ops[idx], RandomFractionDestroy(fraction=0.15)],
                    "repair_ops": [generated_repair_ops[idx], SampledRepair()],
                }
            )

        if generated_destroy_ops:
            trial_specs.append(
                {
                    "label": "generated_destroy_pool",
                    "destroy_ops": generated_destroy_ops[: min(5, len(generated_destroy_ops))] + [VariableBlockDestroy()],
                    "repair_ops": [SampledRepair()],
                }
            )

        if generated_repair_ops:
            trial_specs.append(
                {
                    "label": "generated_repair_pool",
                    "destroy_ops": [RandomFractionDestroy(fraction=0.2), VariableBlockDestroy()],
                    "repair_ops": generated_repair_ops[: min(5, len(generated_repair_ops))] + [SampledRepair()],
                }
            )

        trial_specs.append(
            {
                "label": "mixed_pool",
                "destroy_ops": destroy_candidates[: min(6, len(destroy_candidates))],
                "repair_ops": repair_candidates[: min(6, len(repair_candidates))],
            }
        )

        max_trials = max(self.operator_tuning_trials, len(trial_specs))
        best_combo = trial_specs[0]
        best_score = float("inf")

        for trial_idx, spec in enumerate(trial_specs[:max_trials]):
            problem_data, context = read_problem_for_lns(
                self.dsl_path,
                random_seed=self.random_seed + 1000 + trial_idx,
            )
            evaluator = OptDSLEvaluator(problem_data)
            context.extra["evaluator"] = evaluator

            trial_result = self._run_lns_with_operator_pool(
                context=context,
                evaluator=evaluator,
                destroy_ops=spec["destroy_ops"],
                repair_ops=spec["repair_ops"],
                iterations=self.tuning_iterations,
            )
            score = float(trial_result.incumbent.score)
            result.operator_combo_trials.append(
                {
                    "trial": trial_idx,
                    "label": spec["label"],
                    "destroy_names": [type(d).__name__ for d in spec["destroy_ops"]],
                    "repair_names": [type(r).__name__ for r in spec["repair_ops"]],
                    "score": score,
                }
            )

            if score < best_score:
                best_score = score
                best_combo = spec

        return best_combo

    @staticmethod
    def _build_lns_summary(lns_result: LNSResult, lb_result: dict[str, Any]) -> str:
        s = lns_result.stats
        parts = [
            f"LNS completed {s.iterations} iterations in {s.elapsed_seconds:.1f}s.",
            f"Best feasible score: {lns_result.incumbent.score}",
            f"Accepted moves: {s.accepted}  Improvements: {s.improvements}",
            f"Infeasible candidates: {s.infeasible_candidates}",
            f"MiniZinc lower bound: {lb_result.get('lower_bound')}",
            f"MiniZinc best objective: {lb_result.get('best_objective')}",
            f"Solver status: {lb_result.get('status')}",
        ]
        return "\n".join(parts)
