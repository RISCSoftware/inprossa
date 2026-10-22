"""Iterative code-discovery pipeline — four-phase workflow.

Phase 1  Construction heuristic discovery (steps 1-3)
  The LLM generates 2-3 construction heuristics.  Each is tried; the first
  that produces a feasible solution (score < 1 × 10⁹) is kept.  Retried up to
  *max_init_retries* times.  Falls back to the built-in initializer on failure.

Phase 2  Warm-up LNS (steps 4-5)
  LNS is run from the Phase-1 solution using built-in operators for
  *warmup_iterations* iterations.  A MiniZinc lower bound is computed.

Phase 3  Operator discovery loop (steps 6-10)
  The LLM receives the DSL source, the MiniZinc output, the full history of
  prior rounds, and the previous operator source code.  It generates new
  destroy/repair operators.  LNS is run, MiniZinc re-evaluated, and the cycle
  repeats until a termination criterion is met.

Phase 4  Save (step 11)
  The best operators and initializer are saved as a ready-to-import Python
  profile module in a problem-specific subdirectory.
"""
from __future__ import annotations

import copy
import datetime
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from large_neighborhood_search import (
    CVRPRouteInitializer,
    GreedyRandomizedInitializer,
    ImprovingAcceptance,
    JSSPConstraintAwareRepair,
    JSSPGanttRepair,
    JSSPJobLevelDestroy,
    JSSPMachineLevelDestroy,
    JSSPScheduleInitializer,
    JSSPShiftTimesDestroy,
    JSSPShuffleDestroy,
    JSSPSwapDestroy,
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
    build_lns_context,
    prepare_cvrp_assignment_for_evaluation,
    read_problem_for_lns,
)
from large_neighborhood_search.components import DestroyOperator, Initializer, RepairOperator
from large_neighborhood_search.models import LNSContext
from llm.llmclient import LLMClient

from .lower_bound import estimate_lower_bound
from .operator_gen import generate_initializers_with_llm, generate_operators_with_llm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FEASIBILITY_THRESHOLD = 1_000_000_000.0

# ---------------------------------------------------------------------------
# Module-level helper classes
# ---------------------------------------------------------------------------


class _FixedInitializer(Initializer):
    """Wraps a pre-computed assignment so the LNS engine starts from it."""

    def __init__(self, assignment: dict[str, object]) -> None:
        self._assignment = copy.deepcopy(assignment)

    def initialize(self, context: LNSContext) -> dict[str, object]:
        return copy.deepcopy(self._assignment)


def _format_assignment_for_llm(assignment: dict[str, object], max_keys: int = 30) -> str:
    """Format the current best assignment as a compact text block for LLM feedback."""
    parts = ["CURRENT BEST SOLUTION (decision variable values):"]
    entries = list(assignment.items())
    # Show up to max_keys, then summarize
    for key, value in entries[:max_keys]:
        if isinstance(value, (list, tuple)):
            # Truncate long lists
            if len(value) > 10:
                value_str = f"[{', '.join(str(v) for v in value[:5])}, ... ({len(value)} items)]"
            else:
                value_str = str(list(value))
        else:
            value_str = str(value)
        parts.append(f"  {key} = {value_str}")

    if len(entries) > max_keys:
        parts.append(f"  ... ({len(entries) - max_keys} more keys omitted)")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Operator pool with deduplication
# ---------------------------------------------------------------------------

def _operator_checksum(destroy: DestroyOperator, repair: RepairOperator) -> str:
    """Compute a checksum for a destroy-repair pair to detect duplicates."""
    src = destroy.__class__.__name__ + "|" + repair.__class__.__name__
    if hasattr(destroy, '__module__') and 'generated' in (destroy.__module__ or ''):
        src += str(id(destroy.__class__))
    if hasattr(repair, '__module__') and 'generated' in (repair.__module__ or ''):
        src += str(id(repair.__class__))
    return src


class OperatorPool:
    """Accumulates distinct operator pairs across discovery rounds."""

    def __init__(self) -> None:
        self.pool: list[tuple[DestroyOperator, RepairOperator]] = []
        self.seen_checksums: set[str] = set()
        self.duplicate_count: int = 0
        self.total_generated: int = 0

    def try_add(self, destroy: DestroyOperator, repair: RepairOperator) -> bool:
        """Add the operator pair if it's distinct. Returns True if added."""
        self.total_generated += 1
        checksum = _operator_checksum(destroy, repair)
        if checksum in self.seen_checksums:
            self.duplicate_count += 1
            return False
        self.seen_checksums.add(checksum)
        self.pool.append((destroy, repair))
        return True

    def get_neighborhoods(self) -> list[tuple[DestroyOperator, RepairOperator]]:
        return list(self.pool)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class InitPhaseResult:
    """Result of the Phase-1 construction-heuristic discovery."""

    source_code: str          # LLM-generated Python source, or "" for built-in
    assignment: dict[str, object]
    score: float
    attempts: int
    source_origin: str = "built-in"  # "llm" or "built-in"


@dataclass
class RoundSummary:
    """Measurements from a single operator-discovery round (Phase 3)."""

    round_index: int
    lns_score: float
    lower_bound: float | None
    solver_best: float | None
    solver_status: str
    elapsed_seconds: float
    lns_iterations_run: int
    lns_improvements: int
    lns_accepted: int
    lns_infeasible: int
    destroy_name: str
    repair_name: str
    generated_code_ok: bool
    generation_error: str = ""
    execution_error: str = ""       # runtime error when executing generated code
    operator_source_code: str = ""   # passed back to LLM in next round
    solver_summary: str = ""         # formatted MiniZinc output for LLM prompt

    @property
    def code_status(self) -> str:
        """Classify the outcome: working, non-working, improving, non-improving."""
        if not self.generated_code_ok:
            return "generation-failed"
        if self.execution_error:
            return "runtime-error"
        if self.lns_improvements > 0:
            return "improving"
        # Compare score to lower bound to check if it's reasonable
        if self.gap_percent is not None and self.gap_percent > 200:
            return "non-improving"
        return "working"

    @property
    def gap_percent(self) -> float | None:
        """Relative gap (LNS score − lower_bound) / lower_bound × 100."""
        if self.lower_bound is None or self.lower_bound == 0:
            return None
        if self.lns_score <= 0:
            return 0.0
        return max(0.0, (self.lns_score - self.lower_bound) / abs(self.lower_bound) * 100.0)

    def one_line(self) -> str:
        gap = f"{self.gap_percent:.1f}%" if self.gap_percent is not None else "n/a"
        return (
            f"Round {self.round_index:>2}  score={self.lns_score:.4f}  "
            f"lb={self.lower_bound}  gap={gap}  "
            f"ops={self.destroy_name}/{self.repair_name}  "
            f"accept={self.lns_accepted} improv={self.lns_improvements} "
            f"infeas={self.lns_infeasible}  ({self.elapsed_seconds:.1f}s)"
        )


@dataclass
class IterativeDiscoveryResult:
    """Aggregate result of the full iterative discovery run."""

    rounds: list[RoundSummary] = field(default_factory=list)
    best_round_index: int = -1
    stopped_reason: str = ""

    # Best operators discovered (instances — not classes)
    best_destroy_op: DestroyOperator | None = None
    best_repair_op: RepairOperator | None = None

    # Phase 1 result
    init_result: InitPhaseResult | None = None

    # Phase 2 warm-up stats
    warmup_score: float | None = None
    warmup_lb: float | None = None

    # Phase 4 output
    profile_path: Path | None = None

    @property
    def best_score(self) -> float | None:
        if not self.rounds:
            return None
        return self.rounds[self.best_round_index].lns_score if self.best_round_index >= 0 else None

    def _code_statistics(self) -> dict[str, int]:
        """Count outcomes: working, non-working, improving, non-improving, etc."""
        stats = {
            "generated": 0,
            "working": 0,
            "non_working": 0,
            "improving": 0,
            "non_improving": 0,
            "generation_failed": 0,
            "runtime_error": 0,
        }
        for r in self.rounds:
            if r.generated_code_ok:
                stats["generated"] += 1
            else:
                stats["generation_failed"] += 1
                stats["non_working"] += 1
                continue
            s = r.code_status
            if s == "runtime-error":
                stats["runtime_error"] += 1
                stats["non_working"] += 1
            elif s == "improving":
                stats["improving"] += 1
                stats["working"] += 1
            elif s == "non-improving":
                stats["non_improving"] += 1
                stats["working"] += 1
            else:  # "working"
                stats["working"] += 1
        # Fix totals
        stats["non_working"] = stats["generation_failed"] + stats["runtime_error"]
        return stats

    def summary(self) -> str:
        lines = ["=== Iterative Code Discovery Summary ==="]
        if self.init_result:
            lines.append(
                f"Phase 1  initial_score={self.init_result.score:.4f}  "
                f"origin={self.init_result.source_origin}  attempts={self.init_result.attempts}"
            )
        if self.warmup_score is not None:
            lines.append(f"Warmup   score={self.warmup_score:.4f}  lb={self.warmup_lb}")
        lines.append("")
        for r in self.rounds:
            marker = " ← best" if r.round_index == self.best_round_index else ""
            status_tag = ""
            if not r.generated_code_ok:
                status_tag = " [gen-failed]"
            elif r.execution_error:
                status_tag = f" [exec-error]: {r.execution_error[:60]}"
            elif r.lns_improvements > 0:
                status_tag = " [improving]"
            lines.append(f"  {r.one_line()}{marker}{status_tag}")
        lines.append(f"Stopped: {self.stopped_reason}")
        if self.best_round_index >= 0 and self.rounds:
            best = self.rounds[self.best_round_index]
            gap_str = f"{best.gap_percent:.1f}%" if best.gap_percent is not None else "n/a"
            lines.append(
                f"Best result  score={best.lns_score:.4f}  lb={best.lower_bound}  gap={gap_str}"
            )

        # Code generation statistics
        stats = self._code_statistics()
        total = len(self.rounds)
        lines += [
            "",
            "=== Code Generation Statistics ===",
            f"  Total rounds          : {total}",
            f"  Generation failed     : {stats['generation_failed']}",
            f"  Runtime errors        : {stats['runtime_error']}",
            f"  Working (no error)    : {stats['working']}",
            f"    - Improving         : {stats['improving']}",
            f"    - Non-improving     : {stats['non_improving']}",
            f"  Non-working total     : {stats['non_working']}",
        ]
        if self.profile_path:
            lines.append(f"Profile saved: {self.profile_path}")

        # Operator pool statistics
        if self.rounds:
            # Count duplicates from round summaries
            total_ops = sum(1 for r in self.rounds if r.generated_code_ok)
            working_ops = stats['working']
            dup_count = total_ops - working_ops  # approximation
            lines += [
                "",
                "=== Operator Pool Statistics ===",
                f"  Total generated       : {total_ops}",
                f"  Distinct working      : {working_ops}",
                f"  Duplicates filtered   : {dup_count}",
            ]

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline class
# ---------------------------------------------------------------------------

class IterativeCodeDiscoveryPipeline:
    """Four-phase iterative code-discovery pipeline.

    See module docstring for the phase descriptions.
    """

    def __init__(
        self,
        dsl_path: str | Path,
        llm_client: LLMClient | None = None,
        max_rounds: int = 10,
        quality_threshold: float = 5.0,
        improvement_epsilon: float = 1e-3,
        no_improvement_patience: int = 3,
        lns_iterations: int = 150,
        warmup_iterations: int = 500,
        initializer: str = "greedy",
        init_restarts: int = 1,
        max_init_retries: int = 3,
        lns_destroy_fraction: float = 0.25,
        lns_repair: str = "constraint_aware",
        solver_timelimit: float = 20.0,
        solver_name: str = "cp-sat",
        random_seed: int = 42,
        verbose: bool = True,
        output_dir: str | Path | None = None,
        save_profile: bool = True,
    ) -> None:
        self.dsl_path = Path(dsl_path)
        self.llm_client = llm_client
        self.max_rounds = max(1, max_rounds)
        self.quality_threshold = quality_threshold
        self.improvement_epsilon = improvement_epsilon
        self.no_improvement_patience = no_improvement_patience
        self.lns_iterations = lns_iterations
        self.warmup_iterations = max(1, warmup_iterations)
        self.initializer = initializer
        self.init_restarts = max(1, init_restarts)
        self.max_init_retries = max(1, max_init_retries)
        self.lns_destroy_fraction = max(0.05, min(0.95, lns_destroy_fraction))
        self.lns_repair = lns_repair
        self.solver_timelimit = solver_timelimit
        self.solver_name = solver_name
        self.random_seed = random_seed
        self.verbose = verbose
        self.output_dir = Path(output_dir) if output_dir is not None else None
        self.save_profile = save_profile

        self._dsl_text: str = self.dsl_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> IterativeDiscoveryResult:
        result = IterativeDiscoveryResult()

        print(f"\n[IterativeDiscovery] Starting on {self.dsl_path.name}")
        print(
            f"  max_rounds={self.max_rounds}  quality_threshold={self.quality_threshold}%  "
            f"lns_iterations={self.lns_iterations}  warmup_iterations={self.warmup_iterations}"
        )
        print(f"  LLM available: {self.llm_client is not None}  initializer={self.initializer}")

        # Read problem once — reused across all rounds.
        excluded_vars = {"u", "vehicle_used"} if self.initializer == "cvrp" else None
        problem_data, _ = read_problem_for_lns(
            self.dsl_path,
            random_seed=self.random_seed,
            excluded_decision_variables=excluded_vars,
        )
        evaluator = OptDSLEvaluator(problem_data)

        # ── Phase 1: construction heuristic ───────────────────────────────
        print(f"\n{'═' * 60}")
        print("[Phase 1] Constructing initial feasible solution …")
        context_p1 = self._build_context(problem_data, self.random_seed)
        init_phase = self._phase1_construction(problem_data, context_p1, evaluator)
        result.init_result = init_phase
        print(
            f"  Initial score: {init_phase.score:.4f}  "
            f"origin={init_phase.source_origin}  attempts={init_phase.attempts}"
        )

        # ── Phase 2: warm-up LNS ──────────────────────────────────────────
        print(f"\n[Phase 2] Warm-up LNS ({self.warmup_iterations} iterations) …")
        context_p2 = self._build_context(problem_data, self.random_seed + 1)
        wu_destroy, wu_repair = self._default_operators_for_round(0)
        warmup_result = self._run_lns(
            context_p2, evaluator, wu_destroy, wu_repair,
            initial_assignment=init_phase.assignment,
            n_iterations=self.warmup_iterations,
        )
        warmup_score = float(warmup_result.incumbent.score)
        result.warmup_score = warmup_score
        print(
            f"  Warmup score: {warmup_score:.4f}  "
            f"({warmup_result.stats.iterations} iters, "
            f"improvements={warmup_result.stats.improvements})"
        )

        # Step 5: MiniZinc lower bound from warm-up solution.
        print(f"  Estimating lower bound (timelimit={self.solver_timelimit}s) …")
        lb_result = estimate_lower_bound(
            dsl_path=self.dsl_path,
            warm_assignment=warmup_result.incumbent.assignment,
            timelimit=self.solver_timelimit,
            solver_name=self.solver_name,
        )
        result.warmup_lb = lb_result.get("lower_bound")
        print(
            f"  LB={lb_result['lower_bound']}  "
            f"solver_best={lb_result['best_objective']}  status={lb_result['status']}"
        )

        # ── Phase 3: operator discovery loop ─────────────────────────────
        print(f"\n{'═' * 60}")
        print("[Phase 3] Operator discovery loop …")

        best_assignment = warmup_result.incumbent.assignment
        best_score = warmup_score
        history: list[RoundSummary] = []
        rounds_without_improvement = 0
        prev_op_source = ""           # Prior operator source code (for prompt reference)
        prev_assistant_code = ""      # Prior LLM raw response (for conversation history as assistant message)
        prev_feedback = ""            # Prior execution/score feedback (for user follow-up)
        same_error_count = 0          # Count consecutive identical errors
        prev_execution_error = ""     # Track previous execution error for repeat detection
        op_pool = OperatorPool()      # Accumulate working operators across rounds
        destroy_op, repair_op = self._default_operators_for_round(0)

        for round_idx in range(self.max_rounds):
            print(f"\n{'─' * 60}")
            print(f"[Round {round_idx}] Generating / testing operators …")
            t_start = time.monotonic()

            # Step 6 / 9: LLM operator generation.
            generated_ok = False
            generation_error = ""
            op_source = ""

            if self.llm_client is not None:
                solver_summary = _format_solver_summary(lb_result)
                history_prompt = self._build_history_prompt(history, prev_op_source)
                combined_summary = solver_summary + "\n\n" + history_prompt
                try:
                    destroy_op, repair_op, op_source = generate_operators_with_llm(
                        problem_dsl_text=self._dsl_text,
                        lns_result_summary=combined_summary,
                        llm_client=self.llm_client,
                        prior_operator_source=prev_op_source,
                        prior_assistant_code=prev_assistant_code,
                        prior_feedback=prev_feedback,
                    )
                    generated_ok = True
                    prev_op_source = op_source
                    prev_assistant_code = op_source  # Keep raw response for next round
                    prev_feedback = ""  # Reset feedback (code was valid)
                    print(
                        f"  LLM generated: destroy={type(destroy_op).__name__}  "
                        f"repair={type(repair_op).__name__}"
                    )
                except (RuntimeError, ValueError, OSError) as exc:
                    generation_error = str(exc)
                    print(f"  LLM generation failed (using defaults): {exc}")
                    prev_feedback = f"Generation failed: {exc}"
                    destroy_op, repair_op = self._default_operators_for_round(round_idx)
            else:
                destroy_op, repair_op = self._default_operators_for_round(round_idx)

            # Step 7: run LNS with the operator pool (all distinct operators).
            context_r = self._build_context(problem_data, self.random_seed + 100 + round_idx)
            execution_error = ""
            try:
                # Build neighborhood list: pool operators + generated one + defaults
                neighborhoods = op_pool.get_neighborhoods()

                # Add this round's generated operator to the list
                if generated_ok and not execution_error:
                    neighborhoods.append((destroy_op, repair_op))

                # Add default operators
                for di in range(round_idx % 5):
                    dd, dr = self._default_operators_for_round(di)
                    if (dd, dr) not in neighborhoods:
                        neighborhoods.append((dd, dr))

                lns_result = self._run_lns_with_pool(
                    context_r, evaluator, neighborhoods,
                    initial_assignment=best_assignment,
                    n_iterations=self.lns_iterations,
                )
                score = float(lns_result.incumbent.score)
                print(
                    f"  LNS score: {score:.4f}  "
                    f"pool_size={len(neighborhoods)}  "
                    f"accepted={lns_result.stats.accepted} "
                    f"improvements={lns_result.stats.improvements} "
                    f"infeasible={lns_result.stats.infeasible_candidates}"
                )

                # Add working operator to pool (dedup happens inside)
                if generated_ok:
                    added = op_pool.try_add(destroy_op, repair_op)
                    if not added:
                        print(f"  ⚠ Duplicate operator, skipped (pool={len(op_pool.pool)})")
                    else:
                        print(f"  ✓ Added to pool (pool={len(op_pool.pool)})")

            except Exception as exc:
                execution_error = f"{type(exc).__name__}: {exc}"
                print(f"  Generated code execution FAILED: {execution_error}")
                score = float(best_score)  # keep previous best
                lns_result = None  # no new incumbent
                # Pass execution error back to LLM for next round
                prev_feedback = (
                    f"EXECUTION ERROR: {execution_error}\n"
                    f"The generated code crashed during LNS execution. Fix the error and regenerate."
                )

            # Step 8: MiniZinc lower bound from this round's LNS solution (skip on error).
            if lns_result is not None:
                print(f"  Estimating lower bound (timelimit={self.solver_timelimit}s) …")
                lb_result = estimate_lower_bound(
                    dsl_path=self.dsl_path,
                    warm_assignment=lns_result.incumbent.assignment,
                    timelimit=self.solver_timelimit,
                    solver_name=self.solver_name,
                )
                print(
                    f"  LB={lb_result['lower_bound']}  "
                    f"solver_best={lb_result['best_objective']}  status={lb_result['status']}"
                )

            # Set feedback for next LLM round (after LB is available).
            # Format current best solution for LLM feedback
            current_solution_text = _format_assignment_for_llm(best_assignment)

            # Set feedback for next LLM round (after LB is available).
            if generated_ok and execution_error:
                # Detect repeating errors — escalate feedback if same error persists
                if execution_error == prev_execution_error:
                    same_error_count += 1
                else:
                    same_error_count = 1
                prev_execution_error = execution_error

                # Extract the problematic key from common KeyError patterns
                error_key_match = re.search(r"KeyError:\s*'([^']+)'", execution_error)
                extra_hint = ""
                if error_key_match:
                    bad_key = error_key_match.group(1)
                    # Extract constant names from DSL (uppercase before :)
                    avail_keys = sorted({
                        m.group(1) for m in re.finditer(r'^([A-Z][A-Z0-9_]*)\s*[:=]', self._dsl_text, re.MULTILINE)
                    })
                    # Try uppercase match
                    upper = bad_key.upper()
                    if upper in avail_keys:
                        extra_hint = (
                            f"\n  ⚠️  CRITICAL (error repeated {same_error_count}×): "
                            f"You used '{bad_key}' but the correct key is '{upper}'. "
                            f"Available keys: {', '.join(avail_keys)}. "
                            f"Keys are CASE-SENSITIVE."
                        )
                    else:
                        extra_hint = (
                            f"\n  Available constant keys: {', '.join(avail_keys)}. "
                            f"Check your spelling and case."
                        )

                if same_error_count >= 3:
                    prev_feedback = (
                        f"REPEATED EXECUTION ERROR ({same_error_count}× identical failures):\n"
                        f"{execution_error}{extra_hint}\n\n"
                        f"{current_solution_text}\n\n"
                        f"The LLM has failed {same_error_count} consecutive times with the same error.\n"
                        f"Generate the SIMPLEST possible operators that just work:\n"
                        f"- Destroy: randomly nullify some keys in assignment\n"
                        f"- Repair: fill None values with rng.randint(lo, hi)\n"
                        f"DO NOT try to be clever. Just produce valid code."
                    )
                else:
                    prev_feedback = (
                        f"EXECUTION ERROR: {execution_error}\n"
                        f"Fix the error and regenerate.{extra_hint}\n\n"
                        f"{current_solution_text}"
                    )
            elif lns_result is not None and score < best_score - self.improvement_epsilon:
                best_assignment = lns_result.incumbent.assignment
                best_score = score
                prev_feedback = (
                    f"SUCCESS: Score improved to {score:.4f}. "
                    f"Lower bound: {lb_result['lower_bound']}. "
                    f"Keep improving with more aggressive destroy or smarter repair strategies.\n\n"
                    f"{current_solution_text}"
                )
            elif generated_ok and lns_result is not None and not execution_error:
                lb = lb_result["lower_bound"]
                gap = ((score - lb) / abs(lb) * 100) if lb and lb != 0 else 0
                prev_feedback = (
                    f"NO IMPROVEMENT: Score stays at {score:.4f}, lower bound {lb}, gap {gap:.1f}%. "
                    f"Try a different strategy — destroy larger neighborhoods or use problem-specific repair heuristics.\n\n"
                    f"{current_solution_text}"
                )

            elapsed = time.monotonic() - t_start
            summary = RoundSummary(
                round_index=round_idx,
                lns_score=score,
                lower_bound=lb_result["lower_bound"] if lns_result else None,
                solver_best=lb_result["best_objective"] if lns_result else None,
                solver_status=lb_result["status"] if lns_result else "ERROR",
                elapsed_seconds=elapsed,
                lns_iterations_run=lns_result.stats.iterations if lns_result else 0,
                lns_improvements=lns_result.stats.improvements if lns_result else 0,
                lns_accepted=lns_result.stats.accepted if lns_result else 0,
                lns_infeasible=lns_result.stats.infeasible_candidates if lns_result else 0,
                destroy_name=type(destroy_op).__name__,
                repair_name=type(repair_op).__name__,
                generated_code_ok=generated_ok,
                generation_error=generation_error,
                execution_error=execution_error,
                operator_source_code=op_source,
                solver_summary=_format_solver_summary(lb_result) if lns_result else "",
            )
            history.append(summary)
            result.rounds.append(summary)
            print(f"  {summary.one_line()}")

            # Track best round.
            if result.best_round_index < 0 or score < result.rounds[result.best_round_index].lns_score - self.improvement_epsilon:
                result.best_round_index = round_idx
                result.best_destroy_op = destroy_op
                result.best_repair_op = repair_op
                rounds_without_improvement = 0
                print("  ★ New best!")
            else:
                rounds_without_improvement += 1
                print(
                    f"  No improvement "
                    f"({rounds_without_improvement}/{self.no_improvement_patience})"
                )

            # Step 10: termination check.
            gap = summary.gap_percent
            if gap is not None and self.quality_threshold > 0 and gap <= self.quality_threshold:
                result.stopped_reason = (
                    f"Quality threshold reached: gap={gap:.2f}% ≤ {self.quality_threshold}%"
                )
                print(f"\n  ✓ {result.stopped_reason}")
                break

            if rounds_without_improvement >= self.no_improvement_patience:
                result.stopped_reason = (
                    f"No improvement for {self.no_improvement_patience} consecutive rounds"
                )
                print(f"\n  ✓ {result.stopped_reason}")
                break

        else:
            result.stopped_reason = f"Reached max_rounds={self.max_rounds}"
            print(f"\n  ✓ {result.stopped_reason}")

        # ── Save all generated operators to file ────────────────────────
        try:
            generated_sources = [r.operator_source_code for r in result.rounds
                                 if r.operator_source_code.strip()]
            if generated_sources:
                stem = self.dsl_path.stem
                out_dir = (self.output_dir / stem) if self.output_dir else (self.dsl_path.parent / stem)
                out_dir.mkdir(parents=True, exist_ok=True)
                ops_file = out_dir / "all_generated_operators.py"
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with open(ops_file, "w", encoding="utf-8") as f:
                    f.write(f'"""\n')
                    f.write(f'All LLM-generated operators from iterative discovery.\n\n')
                    f.write(f'DSL source    : {self.dsl_path}\n')
                    f.write(f'Generated     : {now}\n')
                    f.write(f'Total rounds  : {len(result.rounds)}\n')
                    f.write(f'Distinct ops  : {len(op_pool.pool)}\n')
                    f.write(f'Duplicates    : {op_pool.duplicate_count}\n')
                    f.write(f'"""\n\n')
                    f.write("from __future__ import annotations\n")
                    f.write("from large_neighborhood_search.components import DestroyOperator, RepairOperator\n")
                    f.write("from large_neighborhood_search.models import LNSContext\n\n")

                    for idx, src in enumerate(generated_sources):
                        f.write(f"# --- Round {idx} ---\n")
                        f.write(src.strip())
                        f.write("\n\n")

                print(f"  Generated operators saved: {ops_file}")
        except Exception as exc:
            print(f"  Warning: could not save generated operators: {exc}")

        # ── Phase 4: save profile ──────────────────────────────────────────
        if self.save_profile:
            print("\n[Phase 4] Saving discovery profile …")
            try:
                profile_path = self._save_profile(result)
                result.profile_path = profile_path
                print(f"  Profile saved: {profile_path}")
            except Exception as exc:
                print(f"  Warning: could not save profile: {exc}")

        print("\n" + result.summary())
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _phase1_construction(
        self,
        problem_data: Any,
        context: LNSContext,
        evaluator: OptDSLEvaluator,
    ) -> InitPhaseResult:
        """Steps 1-3: discover a feasible initial solution via built-in initializer.

        NOTE: LLM-based initializer generation is temporarily disabled.
        Only operator code (Phase 3) is generated via LLM.
        """
        print("  Skipping LLM initializer generation (operator-only mode).")
        return self._builtin_construction(context, evaluator)

    def _builtin_construction(
        self, context: LNSContext, evaluator: OptDSLEvaluator
    ) -> InitPhaseResult:
        init = self._build_initializer()
        assignment = init.initialize(context)
        score = float(evaluator.evaluate(assignment, context))
        return InitPhaseResult(
            source_code="",
            assignment=assignment,
            score=score,
            attempts=1,
            source_origin="built-in",
        )

    def _build_context(self, problem_data: Any, seed: int) -> LNSContext:
        """Build a fresh LNSContext with the given random seed."""
        excluded_vars = {"u", "vehicle_used"} if self.initializer == "cvrp" else None
        context = build_lns_context(
            problem_data,
            random_seed=seed,
            excluded_decision_variables=excluded_vars,
        )
        if self.initializer == "cvrp":
            context.extra["pre_evaluate_assignment_hook"] = prepare_cvrp_assignment_for_evaluation
        return context

    def _run_lns_with_pool(
        self,
        context: LNSContext,
        evaluator: OptDSLEvaluator,
        neighborhoods: list[tuple[DestroyOperator, RepairOperator]],
        *,
        initial_assignment: dict[str, object] | None = None,
        n_iterations: int | None = None,
    ) -> LNSResult:
        """Run LNS with a pool of neighborhood operators."""
        lns_init = _FixedInitializer(initial_assignment) if initial_assignment is not None else self._build_initializer()
        selector = NeighborhoodPoolSelector(neighborhoods)
        acceptance = ImprovingAcceptance()
        iters = n_iterations if n_iterations is not None else self.lns_iterations
        stop = MaxIterationsStop(iters)
        logger: StdoutLNSLogger | None = StdoutLNSLogger() if self.verbose else None
        engine = LargeNeighborhoodSearchEngine(
            initializer=lns_init,
            selector=selector,
            evaluator=evaluator,
            acceptance=acceptance,
            stop=stop,
            logger=logger,
        )
        return engine.run(context)

    def _run_lns(
        self,
        context: LNSContext,
        evaluator: OptDSLEvaluator,
        destroy_op: DestroyOperator,
        repair_op: RepairOperator,
        *,
        initial_assignment: dict[str, object] | None = None,
        n_iterations: int | None = None,
    ) -> LNSResult:
        if self.initializer == "jssp":
            frac = self.lns_destroy_fraction
            jssp_repair: RepairOperator = (
                JSSPGanttRepair()
                if self.lns_repair == "gantt"
                else JSSPConstraintAwareRepair()
            )
            neighborhoods: list[tuple[DestroyOperator, RepairOperator]] = [
                (JSSPJobLevelDestroy(fraction=frac), jssp_repair),
                (JSSPMachineLevelDestroy(fraction=frac), jssp_repair),
                (JSSPShuffleDestroy(fraction=frac), jssp_repair),
                (JSSPSwapDestroy(fraction=frac), jssp_repair),
                (JSSPShiftTimesDestroy(fraction=frac), jssp_repair),
            ]
            if not isinstance(destroy_op, (JSSPJobLevelDestroy, JSSPMachineLevelDestroy,
                                           JSSPShuffleDestroy, JSSPSwapDestroy, JSSPShiftTimesDestroy)):
                llm_repair = repair_op if not isinstance(repair_op, SampledRepair) else jssp_repair
                neighborhoods.insert(0, (destroy_op, llm_repair))
        else:
            default_destroy = RandomFractionDestroy(fraction=0.2)
            default_repair = SampledRepair()
            destroy_ops: list[DestroyOperator] = [destroy_op, default_destroy, VariableBlockDestroy()]
            repair_ops: list[RepairOperator] = [repair_op, default_repair]
            neighborhoods = [(d, r) for d in destroy_ops for r in repair_ops]

        lns_init = _FixedInitializer(initial_assignment) if initial_assignment is not None else self._build_initializer()
        selector = NeighborhoodPoolSelector(neighborhoods)
        acceptance = ImprovingAcceptance()
        iters = n_iterations if n_iterations is not None else self.lns_iterations
        stop = MaxIterationsStop(iters)
        logger: StdoutLNSLogger | None = StdoutLNSLogger() if self.verbose else None
        engine = LargeNeighborhoodSearchEngine(
            initializer=lns_init,
            selector=selector,
            evaluator=evaluator,
            acceptance=acceptance,
            stop=stop,
            logger=logger,
        )
        return engine.run(context)

    def _build_initializer(self) -> Initializer:
        name = self.initializer
        if name == "random":
            return RandomAssignmentInitializer()
        if name == "cvrp":
            return CVRPRouteInitializer(restarts=self.init_restarts)
        if name == "jssp":
            return JSSPScheduleInitializer(restarts=self.init_restarts)
        try:
            return GreedyRandomizedInitializer(candidate_values=3, restarts=self.init_restarts)
        except (TypeError, ValueError):
            return RandomAssignmentInitializer()

    def _default_operators_for_round(
        self, round_idx: int
    ) -> tuple[DestroyOperator, RepairOperator]:
        if self.initializer == "jssp":
            frac = self.lns_destroy_fraction
            jssp_repair: RepairOperator = (
                JSSPGanttRepair()
                if self.lns_repair == "gantt"
                else JSSPConstraintAwareRepair()
            )
            ops: list[DestroyOperator] = [
                JSSPJobLevelDestroy(fraction=frac),
                JSSPMachineLevelDestroy(fraction=frac),
                JSSPShuffleDestroy(fraction=frac),
                JSSPSwapDestroy(fraction=frac),
                JSSPShiftTimesDestroy(fraction=frac),
            ]
            return ops[round_idx % len(ops)], jssp_repair
        fractions = [0.1, 0.15, 0.2, 0.25, 0.3]
        fraction = fractions[round_idx % len(fractions)]
        if round_idx % 2 == 0:
            return RandomFractionDestroy(fraction=fraction), SampledRepair()
        return VariableBlockDestroy(), SampledRepair()

    @staticmethod
    def _build_history_prompt(history: list[RoundSummary], prior_source: str = "") -> str:
        """Multi-round history string for the LLM, including errors and prior source."""
        if not history:
            base = "No prior rounds yet — this is the first attempt."
        else:
            lines = [f"History of {len(history)} prior operator evaluation round(s):", ""]
            for r in history:
                gap_str = f"{r.gap_percent:.1f}%" if r.gap_percent is not None else "n/a"
                status_parts = [
                    f"  Round {r.round_index}: ",
                    f"destroy={r.destroy_name}  repair={r.repair_name}  ",
                    f"LNS_score={r.lns_score:.4f}  lower_bound={r.lower_bound}  gap={gap_str}  ",
                    f"improvements={r.lns_improvements}  accepted={r.lns_accepted}  ",
                    f"infeasible={r.lns_infeasible}  iters={r.lns_iterations_run}  ",
                    f"solver_status={r.solver_status}",
                ]
                if not r.generated_code_ok:
                    status_parts.append(f"  [GENERATION_FAILED: {r.generation_error[:120]}]")
                if r.execution_error:
                    status_parts.append(f"  [EXECUTION_FAILED: {r.execution_error[:120]}]")
                lines.append("".join(status_parts))
            best = min(history, key=lambda r: r.lns_score)
            latest = history[-1]
            lines += [
                "",
                f"Best so far: Round {best.round_index} — score={best.lns_score:.4f}"
                + (f"  gap={best.gap_percent:.1f}%" if best.gap_percent is not None else "  gap=n/a"),
                f"Latest: score={latest.lns_score:.4f}  solver_best={latest.solver_best}  "
                f"lower_bound={latest.lower_bound}",
                "",
                "Focus on improving the weaknesses observed above. "
                "If the previous code had execution errors, fix them in the new version.",
            ]
            base = "\n".join(lines)

        if prior_source.strip():
            return base + "\n\nPREVIOUS OPERATOR SOURCE (improve upon this):\n" + prior_source
        return base

    def _save_profile(self, result: IterativeDiscoveryResult) -> Path:
        """Phase 4: save operators + initializer as a ready-to-import Python module."""
        stem = self.dsl_path.stem
        profile_dir = (self.output_dir / stem) if self.output_dir else (self.dsl_path.parent / stem)
        profile_dir.mkdir(parents=True, exist_ok=True)

        best_round = result.rounds[result.best_round_index] if result.best_round_index >= 0 and result.rounds else None
        best_score_str = f"{result.best_score:.4f}" if result.best_score is not None else "n/a"
        lb_str = str(best_round.lower_bound) if best_round else "n/a"
        gap_str = (
            f"{best_round.gap_percent:.1f}%"
            if best_round and best_round.gap_percent is not None
            else "n/a"
        )
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines: list[str] = [
            '"""',
            f"Auto-generated LNS discovery profile for {stem}",
            "",
            f"DSL source    : {self.dsl_path}",
            f"Generated     : {now}",
            f"Best LNS score: {best_score_str}",
            f"Lower bound   : {lb_str}",
            f"Gap           : {gap_str}",
            f"Rounds run    : {len(result.rounds)}",
            '"""',
            "from __future__ import annotations",
            "",
            "import random",
            "from large_neighborhood_search.components import DestroyOperator, Initializer, RepairOperator",
            "from large_neighborhood_search.models import LNSContext",
            "",
        ]

        # Initializer section.
        init_result = result.init_result
        if init_result and init_result.source_code.strip():
            lines += [
                "",
                "# ── Generated construction heuristic ────────────────────────────────────",
                init_result.source_code,
                "",
            ]
            init_cls = _first_class_name(init_result.source_code)
            make_init_body = f"return {init_cls}()" if init_cls else "pass  # TODO: fix class name"
        else:
            lines += [
                "",
                f"# ── Built-in initializer: {self.initializer} ─────────────────────────────────────",
            ]
            make_init_body = _builtin_init_expr(self.initializer, self.init_restarts)

        # Operator section.
        best_op_source = ""
        if best_round and best_round.operator_source_code.strip():
            best_op_source = best_round.operator_source_code
        else:
            for r in reversed(result.rounds):
                if r.operator_source_code.strip():
                    best_op_source = r.operator_source_code
                    break

        if best_op_source:
            lines += [
                "",
                "# ── Generated LNS operators ──────────────────────────────────────────────",
                best_op_source,
                "",
            ]
            d_cls = _first_class_of_kind(best_op_source, "DestroyOperator")
            r_cls = _first_class_of_kind(best_op_source, "RepairOperator")
            make_ops_body = (
                f"return [({d_cls}(), {r_cls}())]"
                if d_cls and r_cls
                else _builtin_ops_expr(self.initializer, self.lns_destroy_fraction, self.lns_repair)
            )
        else:
            destroy_name = best_round.destroy_name if best_round else "n/a"
            repair_name = best_round.repair_name if best_round else "n/a"
            lines += [
                "",
                f"# ── Built-in operators: {destroy_name} / {repair_name} ─────────",
            ]
            make_ops_body = _builtin_ops_expr(self.initializer, self.lns_destroy_fraction, self.lns_repair)

        lines += [
            "",
            "",
            "# ── Profile API ───────────────────────────────────────────────────────────────",
            "def make_initializer() -> Initializer:",
            '    """Return the best construction heuristic found by code discovery."""',
            f"    {make_init_body}",
            "",
            "",
            "def make_operators() -> list[tuple[DestroyOperator, RepairOperator]]:",
            '    """Return the best (destroy, repair) pair found by code discovery."""',
            f"    {make_ops_body}",
            "",
        ]

        profile_path = profile_dir / "auto_profile.py"
        profile_path.write_text("\n".join(lines), encoding="utf-8")
        return profile_path


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _format_solver_summary(lb_result: dict[str, Any]) -> str:
    return (
        "MiniZinc solver output:\n"
        f"  status       : {lb_result.get('status', 'unknown')}\n"
        f"  lower_bound  : {lb_result.get('lower_bound', 'n/a')}\n"
        f"  best_objective: {lb_result.get('best_objective', 'n/a')}"
    )


def _first_class_name(source: str) -> str | None:
    m = re.search(r"class\s+(\w+)\s*\(", source)
    return m.group(1) if m else None


def _first_class_of_kind(source: str, base: str) -> str | None:
    m = re.search(rf"class\s+(\w+)\s*\(\s*{re.escape(base)}\s*\)", source)
    return m.group(1) if m else None


def _builtin_init_expr(initializer: str, restarts: int) -> str:
    if initializer == "jssp":
        return (
            f"from large_neighborhood_search import JSSPScheduleInitializer; "
            f"return JSSPScheduleInitializer(restarts={restarts})"
        )
    if initializer == "cvrp":
        return (
            f"from large_neighborhood_search import CVRPRouteInitializer; "
            f"return CVRPRouteInitializer(restarts={restarts})"
        )
    if initializer == "random":
        return (
            "from large_neighborhood_search import RandomAssignmentInitializer; "
            "return RandomAssignmentInitializer()"
        )
    return (
        f"from large_neighborhood_search import GreedyRandomizedInitializer; "
        f"return GreedyRandomizedInitializer(restarts={restarts})"
    )


def _builtin_ops_expr(initializer: str, fraction: float, repair: str) -> str:
    if initializer == "jssp":
        repair_cls = "JSSPGanttRepair" if repair == "gantt" else "JSSPConstraintAwareRepair"
        return (
            f"from large_neighborhood_search import JSSPJobLevelDestroy, {repair_cls}; "
            f"return [(JSSPJobLevelDestroy(fraction={fraction:.2f}), {repair_cls}())]"
        )
    return (
        f"from large_neighborhood_search import RandomFractionDestroy, SampledRepair; "
        f"return [(RandomFractionDestroy(fraction={fraction:.2f}), SampledRepair())]"
    )
