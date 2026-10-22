from __future__ import annotations

import random
from dataclasses import dataclass
from typing import cast

from .components import AcceptanceCriterion, DestroyOperator, Initializer, LNSLogger, NeighborhoodSelector, RepairOperator, StopCriterion
from .models import LNSContext, LNSState
from ._utils import _list_get, _list_set, clone_assignment, set_decision_value


def _decision_keys(context: LNSContext) -> list[tuple[str, int | tuple[int, int] | None]]:
    return context.extra["decision_keys"]


def _domains(context: LNSContext) -> dict[tuple[str, int | tuple[int, int] | None], tuple[int, int]]:
    return context.extra["decision_domains"]



def _sample_value(rng: random.Random, key: tuple[str, int | tuple[int, int] | None], context: LNSContext) -> int:
    lo, hi = _domains(context)[key]
    bias: str = context.extra.get("value_bias", "uniform")
    var_name, _ = key
    binary_probabilities: dict[str, float] = context.extra.get("binary_one_probability_by_variable", {})

    if lo == hi:
        return lo

    if lo == 0 and hi == 1 and bias == "lower":
        p_one = float(binary_probabilities.get(var_name, 0.2))
        return 1 if rng.random() < p_one else 0

    if bias == "lower":
        if rng.random() < 0.8:
            return lo
    elif bias == "upper":
        if rng.random() < 0.8:
            return hi

    return rng.randint(lo, hi)


def _permutation_specs(context: LNSContext) -> dict[str, tuple[int, int, int]]:
    """Return variable -> (length, lower, upper) for permutation-shaped decision lists."""
    specs: dict[str, tuple[int, int, int]] = {}
    grouped: dict[str, list[tuple[str, int | None]]] = context.extra.get("keys_by_variable", {})
    domains = _domains(context)

    for var_name, keys in grouped.items():
        if not keys:
            continue
        indexed_keys = [k for k in keys if isinstance(k[1], int)]
        if len(indexed_keys) != len(keys):
            continue

        sorted_keys = sorted(indexed_keys, key=lambda k: cast(int, k[1]))
        indices = [cast(int, k[1]) for k in sorted_keys]
        if indices != list(range(len(indices))):
            continue

        base_lo, base_hi = domains[sorted_keys[0]]
        if any(domains[k] != (base_lo, base_hi) for k in sorted_keys[1:]):
            continue

        length = len(sorted_keys)
        if base_hi - base_lo + 1 != length:
            continue

        specs[var_name] = (length, base_lo, base_hi)

    return specs


def has_permutation_decisions(context: LNSContext) -> bool:
    return bool(_permutation_specs(context))


@dataclass
class RandomFractionDestroy(DestroyOperator):
    fraction: float = 0.2

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        keys = _decision_keys(context)
        if not keys:
            return assignment

        n_destroy = max(1, int(len(keys) * max(0.0, min(1.0, self.fraction))))
        chosen = rng.sample(keys, min(n_destroy, len(keys)))
        for key in chosen:
            set_decision_value(assignment, key, None)
        return assignment


class VariableBlockDestroy(DestroyOperator):
    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        grouped: dict[str, list[tuple[str, int | None]]] = context.extra["keys_by_variable"]
        if not grouped:
            return assignment
        var_name = rng.choice(list(grouped.keys()))
        for key in grouped[var_name]:
            set_decision_value(assignment, key, None)
        return assignment


@dataclass
class PermutationSegmentDestroy(DestroyOperator):
    """Destroy a contiguous segment in a permutation-shaped decision vector."""

    fraction: float = 0.25
    min_segment: int = 2

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        specs = _permutation_specs(context)
        if not specs:
            return RandomFractionDestroy(fraction=self.fraction).destroy(assignment, context)

        grouped: dict[str, list[tuple[str, int | None]]] = context.extra.get("keys_by_variable", {})
        var_name = rng.choice(list(specs.keys()))
        length, _, _ = specs[var_name]
        if length <= 0:
            return assignment

        requested = int(round(length * max(0.0, min(1.0, self.fraction))))
        segment_len = max(1, min(length, max(self.min_segment, requested)))
        start = rng.randint(0, max(0, length - 1))

        keys = sorted(grouped[var_name], key=lambda k: cast(int, k[1]))
        for offset in range(segment_len):
            idx = (start + offset) % length
            set_decision_value(assignment, keys[idx], None)
        return assignment


@dataclass
class PermutationPreservingInitializer(Initializer):
    """Initialize permutation-shaped decision vectors with valid random permutations."""

    def initialize(self, context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        specs = _permutation_specs(context)

        assignment: dict[str, object] = {}
        grouped: dict[str, list[tuple[str, int | None]]] = context.extra.get("keys_by_variable", {})

        for var_name, keys in grouped.items():
            idx_keys = [k for k in keys if isinstance(k[1], int)]
            if idx_keys:
                size = max(cast(int, k[1]) for k in idx_keys) + 1
                assignment[var_name] = [None for _ in range(size)]
            else:
                assignment[var_name] = None

        # Fill all decisions randomly first.
        for key in _decision_keys(context):
            set_decision_value(assignment, key, _sample_value(rng, key, context))

        # Overwrite permutation-shaped vectors with proper permutations.
        for var_name, (length, lo, hi) in specs.items():
            values = list(range(lo, hi + 1))
            rng.shuffle(values)
            assignment[var_name] = values[:length]

        return assignment


@dataclass
class RandomRepair(RepairOperator):
    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        for key in _decision_keys(context):
            var_name, idx = key
            if idx is None:
                if partial_assignment.get(var_name) is None:
                    partial_assignment[var_name] = _sample_value(rng, key, context)
                continue

            value = partial_assignment.get(var_name)
            if isinstance(value, list) and _list_get(value, idx) is None:
                _list_set(value, idx, _sample_value(rng, key, context))
        return partial_assignment


@dataclass
class FillMissingPermutationRepair(RepairOperator):
    """Repair permutation-shaped vectors by filling missing values without duplicates."""

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        specs = _permutation_specs(context)
        permutation_keys: set[tuple[str, int | None]] = set()
        grouped: dict[str, list[tuple[str, int | None]]] = context.extra.get("keys_by_variable", {})

        for var_name, (length, lo, hi) in specs.items():
            keys = sorted(grouped[var_name], key=lambda k: cast(int, k[1]))
            permutation_keys.update(keys)

            current = partial_assignment.get(var_name)
            if not isinstance(current, list):
                current = cast(list[int | None], [None for _ in range(length)])
                partial_assignment[var_name] = current
            elif len(current) < length:
                current.extend([None for _ in range(length - len(current))])
            current = cast(list[int | None], current)

            seen: set[int] = set()
            holes: list[int] = []
            for idx in range(length):
                value = current[idx]
                if not isinstance(value, int) or value < lo or value > hi or value in seen:
                    current[idx] = None
                    holes.append(idx)
                else:
                    seen.add(value)

            missing = [v for v in range(lo, hi + 1) if v not in seen]
            rng.shuffle(missing)
            for idx, value in zip(holes, missing):
                current[idx] = value

        # Fill all remaining non-permutation decisions with random values.
        for key in _decision_keys(context):
            if key in permutation_keys:
                continue
            var_name, idx = key
            if idx is None:
                if partial_assignment.get(var_name) is None:
                    partial_assignment[var_name] = _sample_value(rng, key, context)
                continue
            value = partial_assignment.get(var_name)
            if isinstance(value, list) and _list_get(value, idx) is None:
                _list_set(value, idx, _sample_value(rng, key, context))

        return partial_assignment


@dataclass
class SampledRepair(RepairOperator):
    samples: int = 8
    base_repair: RepairOperator | None = None

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        evaluator = context.extra.get("evaluator")
        base_repair = self.base_repair or RandomRepair()
        if evaluator is None or self.samples <= 1:
            return base_repair.repair(partial_assignment, context)

        best_assignment: dict[str, object] | None = None
        best_score = float("inf")
        sense = context.objective_sense

        for _ in range(self.samples):
            candidate = _clone_assignment(partial_assignment)
            candidate = base_repair.repair(candidate, context)
            score = evaluator.evaluate(candidate, context)

            if best_assignment is None:
                best_assignment = candidate
                best_score = score
                continue

            if (sense == "maximize" and score > best_score) or (sense != "maximize" and score < best_score):
                best_assignment = candidate
                best_score = score

            # Use FeasibilityClassifier to determine if this is feasible, default to checking for infinity
            is_feasible = False
            if context.feasibility_classifier is not None:
                is_feasible = context.feasibility_classifier.is_feasible(score)
            elif score != float("inf"):
                is_feasible = True
            
            if is_feasible:
                # Early stop as soon as one feasible repaired candidate appears.
                break

        return best_assignment if best_assignment is not None else partial_assignment


def _clone_assignment(assignment: dict[str, object]) -> dict[str, object]:
    return clone_assignment(assignment)


@dataclass
class NeighborhoodPoolSelector(NeighborhoodSelector):
    neighborhoods: list[tuple[DestroyOperator, RepairOperator]]
    weights: list[float] | None = None

    def select(self, state: LNSState, context: LNSContext) -> tuple[DestroyOperator, RepairOperator]:
        rng: random.Random = context.extra["rng"]
        if not self.neighborhoods:
            raise ValueError("No neighborhoods configured")
        if self.weights is None:
            return rng.choice(self.neighborhoods)
        return rng.choices(self.neighborhoods, weights=self.weights, k=1)[0]


@dataclass
class AdaptiveNeighborhoodSelector(NeighborhoodSelector):
    """Adaptive (ALNS) neighborhood selector with roulette-wheel weighting.

    Uses the ``AdaptiveOperatorContext`` to track per-pair performance and
    adjusts selection probabilities based on success rate and improvement
    magnitude.  Implements the classic Ropke & Pisinger weight-update scheme:

    * Each operator pair has a weight ``w = rho * w + (1-rho) * score``.
    * ``score`` is updated after each application: +sigma1 for a new global
      best, +sigma2 for better-than-current, +sigma3 for accepted (worse).
    * Selection is roulette-wheel over the normalised weights.

    Additionally modulates destroy intensity: scales the ``fraction`` /
      ``customer_count`` / ``segment_len`` fields of destroy operators up when
      the search stalls (cap 0.4) and down after an improvement (floor 0.1).

    The selector is designed to be a drop-in replacement for
    ``NeighborhoodPoolSelector`` — same ``select()`` interface, no engine
    changes required.  Feedback is collected via ``record_result()`` which
    the engine (or a logger adapter) calls after each iteration.
    """
    neighborhoods: list[tuple[DestroyOperator, RepairOperator]]
    # ALNS weight-update parameters.
    rho: float = 0.3              # decay factor (0=all-new, 1=no-update)
    sigma1: float = 33.0          # new global best
    sigma2: float = 9.0           # better than current
    sigma3: float = 13.0          # accepted but worse
    sigma4: float = 0.0           # rejected
    min_weight: float = 1.0       # floor so no operator starves
    # Adaptive destroy intensity.
    adaptive_intensity: bool = True
    intensity_floor: float = 0.1
    intensity_cap: float = 0.4
    stall_threshold: int = 50     # iters without improvement before scaling up

    def __post_init__(self) -> None:
        self._weights: list[float] = [1.0] * len(self.neighborhoods)
        self._last_selected: int = -1
        self._last_was_improvement: bool = False
        self._last_was_accepted: bool = False
        self._iterations: int = 0
        self._stalled: int = 0

    def _pair_name(self, idx: int) -> str:
        d, r = self.neighborhoods[idx]
        return f"{type(d).__name__}+{type(r).__name__}"

    def select(self, state: LNSState, context: LNSContext) -> tuple[DestroyOperator, RepairOperator]:
        rng: random.Random = context.extra["rng"]
        if not self.neighborhoods:
            raise ValueError("No neighborhoods configured")
        # Adaptive destroy intensity: adjust before selection so the chosen
        # destroy operator sees the updated fraction.
        if self.adaptive_intensity:
            self._adjust_intensity(state)
        # Roulette-wheel selection.
        total = sum(self._weights)
        pick = rng.uniform(0, total)
        cumulative = 0.0
        idx = 0
        for i, w in enumerate(self._weights):
            cumulative += w
            if pick <= cumulative:
                idx = i
                break
        self._last_selected = idx
        return self.neighborhoods[idx]

    def _adjust_intensity(self, state: LNSState) -> None:
        """Scale destroy operators' fraction/customer_count up when stalled."""
        if state.stats.iterations > 0 and state.stats.iterations == state.stats.last_improvement_iteration:
            self._stalled = 0
        else:
            self._stalled += 1

        if self._stalled > self.stall_threshold:
            scale = 1.05
        elif self._stalled == 0:
            scale = 0.95
        else:
            scale = 1.0

        for d, _ in self.neighborhoods:
            if hasattr(d, "fraction"):
                d.fraction = max(self.intensity_floor, min(self.intensity_cap, d.fraction * scale))  # type: ignore[attr-defined]
            if hasattr(d, "customer_count") and d.customer_count > 0:  # type: ignore[attr-defined]
                d.customer_count = max(1, int(d.customer_count * scale))  # type: ignore[attr-defined]
            if hasattr(d, "segment_len"):
                d.segment_len = max(2, min(20, int(d.segment_len * scale)))  # type: ignore[attr-defined]

    def record_result(
        self,
        was_accepted: bool,
        is_improvement: bool,
        is_new_best: bool,
        improvement: float = 0.0,
    ) -> None:
        """Called after each iteration to update operator weights.

        Args:
            was_accepted: True if the candidate was accepted by the acceptance criterion.
            is_improvement: True if candidate improves the current solution.
            is_new_best: True if candidate is a new global best.
            improvement: Absolute improvement magnitude (>= 0).
        """
        if self._last_selected < 0:
            return
        if is_new_best:
            score = self.sigma1
        elif is_improvement:
            score = self.sigma2
        elif was_accepted:
            score = self.sigma3
        else:
            score = self.sigma4
        idx = self._last_selected
        self._weights[idx] = max(
            self.min_weight,
            self.rho * self._weights[idx] + (1 - self.rho) * score,
        )
        self._iterations += 1
        self._last_was_improvement = is_improvement
        self._last_was_accepted = was_accepted

    def reset_for_run(self, context: LNSContext) -> None:
        self._weights = [1.0] * len(self.neighborhoods)
        self._last_selected = -1
        self._iterations = 0
        self._stalled = 0

    @property
    def weights(self) -> list[float]:
        """Current normalised weights for inspection/logging."""
        total = sum(self._weights)
        if total <= 0:
            return [1.0 / len(self._weights)] * len(self._weights)
        return [w / total for w in self._weights]


class ImprovingAcceptance(AcceptanceCriterion):
    def accept(
        self,
        current_score: float,
        candidate_score: float,
        best_score: float,
        state: LNSState,
        context: LNSContext,
    ) -> bool:
        if current_score == float("inf") and candidate_score == float("inf"):
            return True

        sense = context.objective_sense
        if sense == "maximize":
            return candidate_score >= current_score
        return candidate_score <= current_score


@dataclass
class SimulatedAnnealingAcceptance(AcceptanceCriterion):
    temperature: float = 1.0
    cooling: float = 0.995
    min_temperature: float = 1e-5

    def accept(
        self,
        current_score: float,
        candidate_score: float,
        best_score: float,
        state: LNSState,
        context: LNSContext,
    ) -> bool:
        rng: random.Random = context.extra["rng"]
        sense = context.objective_sense

        if current_score == float("inf") and candidate_score == float("inf"):
            self.temperature = max(self.min_temperature, self.temperature * self.cooling)
            return True

        better = candidate_score > current_score if sense == "maximize" else candidate_score < current_score
        if better:
            self.temperature = max(self.min_temperature, self.temperature * self.cooling)
            return True

        delta = (current_score - candidate_score) if sense == "maximize" else (candidate_score - current_score)
        if self.temperature <= 0.0:
            return False

        # Accept uphill move with Metropolis probability.
        prob = pow(2.718281828459045, -delta / max(self.temperature, self.min_temperature))
        self.temperature = max(self.min_temperature, self.temperature * self.cooling)
        return rng.random() < prob


@dataclass
class MaxIterationsStop(StopCriterion):
    max_iterations: int

    def should_stop(self, state: LNSState, context: LNSContext) -> bool:
        return state.stats.iterations >= self.max_iterations


@dataclass
class StdoutLNSLogger(LNSLogger):
    log_every: int = 0

    def on_start(self, _state: LNSState, context: LNSContext) -> None:
        decision_count = len(context.extra.get("decision_keys", []))
        max_iterations = context.extra.get("max_iterations")
        if isinstance(max_iterations, int) and max_iterations > 0:
            print(
                "[lns] run started "
                f"sense={context.objective_sense} decisions={decision_count} "
                f"max_iterations={max_iterations} log_every={self.log_every}"
            )
            return

        print(
            "[lns] run started "
            f"sense={context.objective_sense} decisions={decision_count} log_every={self.log_every}"
        )

    def on_iteration(
        self,
        iteration: int,
        destroy_name: str,
        repair_name: str,
        candidate_score: float,
        accepted: bool,
        improved: bool,
        state: LNSState,
        context: LNSContext,
    ) -> None:
        if self.log_every > 0 and iteration % self.log_every == 0:
            elapsed = max(1e-12, state.stats.elapsed_seconds)
            accept_rate = state.stats.accepted / max(1, state.stats.iterations)
            improve_rate = state.stats.improvements / max(1, state.stats.iterations)
            infeasible_rate = state.stats.infeasible_candidates / max(1, state.stats.iterations)
            iter_per_sec = state.stats.iterations / elapsed

            progress_text = ""
            max_iterations = context.extra.get("max_iterations")
            if isinstance(max_iterations, int) and max_iterations > 0:
                progress = 100.0 * min(1.0, state.stats.iterations / max_iterations)
                progress_text = f" progress={progress:.1f}%"

            print(
                f"[lns] it={iteration}{progress_text} elapsed={elapsed:.2f}s ips={iter_per_sec:.1f} "
                f"current={state.current.score} best={state.incumbent.score} cand={candidate_score} "
                f"accepted_now={accepted} improved_now={improved} "
                f"accept_rate={accept_rate:.3f} improve_rate={improve_rate:.3f} infeasible_rate={infeasible_rate:.3f} "
                f"destroy={destroy_name} repair={repair_name}"
            )

    def on_restart(
        self,
        iteration: int,
        restart_count: int,
        score: float,
        state: LNSState,
        _context: LNSContext,
    ) -> None:
        elapsed = max(1e-12, state.stats.elapsed_seconds)
        print(
            f"[lns] restart it={iteration} count={restart_count} elapsed={elapsed:.2f}s "
            f"current={score} best={state.incumbent.score}"
        )

    def on_finish(self, state: LNSState, _context: LNSContext) -> None:
        print(
            "[lns] run finished "
            f"iterations={state.stats.iterations} "
            f"accepted={state.stats.accepted} "
            f"improvements={state.stats.improvements} "
            f"infeasible={state.stats.infeasible_candidates} "
            f"restarts={state.stats.restarts} "
            f"elapsed={state.stats.elapsed_seconds:.4f}s"
        )


# ---------------------------------------------------------------------------
# Feasibility Classifiers
# ---------------------------------------------------------------------------


@dataclass
class PenaltyBasedFeasibilityClassifier:
    """Fallback: checks if score >= penalty_base to detect infeasibility.
    
    Works with any evaluator that returns penalty-based scores.
    Less precise than OptDSLFeasibilityClassifier (doesn't distinguish 1e9 vs objective=1e9),
    but works when failed_constraints is unavailable.
    """

    penalty_base: float = 1e9

    def is_feasible(self, score: float) -> bool:
        return score < self.penalty_base

    def is_infeasible(self, score: float) -> bool:
        return score >= self.penalty_base


class OptDSLFeasibilityClassifier:
    """Uses OptDSLEvaluator's penalty_base to detect infeasibility.
    
    Most robust for OptDSL problems: directly checks if score >= penalty_base.
    Can distinguish true objective values from penalty scores.
    """

    def __init__(self, penalty_base: float = 1e9) -> None:
        self.penalty_base = penalty_base

    def is_feasible(self, score: float) -> bool:
        return score < self.penalty_base

    def is_infeasible(self, score: float) -> bool:
        return score >= self.penalty_base

