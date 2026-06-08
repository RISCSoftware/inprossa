from __future__ import annotations

import random
from dataclasses import dataclass
from typing import cast

from .components import AcceptanceCriterion, DestroyOperator, Initializer, LNSLogger, NeighborhoodSelector, RepairOperator, StopCriterion
from .models import LNSContext, LNSState


def _decision_keys(context: LNSContext) -> list[tuple[str, int | tuple[int, int] | None]]:
    return context.extra["decision_keys"]


def _domains(context: LNSContext) -> dict[tuple[str, int | tuple[int, int] | None], tuple[int, int]]:
    return context.extra["decision_domains"]


def _list_get(value: list, idx: int | tuple[int, int]) -> object:
    """Safely index into a list for both 1-D and 2-D decision indices."""
    if isinstance(idx, tuple):
        i, j = idx
        return value[i][j]
    return value[idx]


def _list_set(value: list, idx: int | tuple[int, int], v: object) -> None:
    """Safely set a list element for both 1-D and 2-D decision indices."""
    if isinstance(idx, tuple):
        i, j = idx
        value[i][j] = v
    else:
        value[idx] = v


def _set_value(assignment: dict[str, object], key: tuple[str, int | tuple[int, int] | None], value: int | None) -> None:
    var_name, idx = key
    if idx is None:
        assignment[var_name] = value
        return
    var_value = assignment[var_name]
    if isinstance(var_value, list):
        if isinstance(idx, tuple):
            i, j = idx
            var_value[i][j] = value
        else:
            var_value[idx] = value


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
            _set_value(assignment, key, None)
        return assignment


class VariableBlockDestroy(DestroyOperator):
    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        grouped: dict[str, list[tuple[str, int | None]]] = context.extra["keys_by_variable"]
        if not grouped:
            return assignment
        var_name = rng.choice(list(grouped.keys()))
        for key in grouped[var_name]:
            _set_value(assignment, key, None)
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
            _set_value(assignment, keys[idx], None)
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
            _set_value(assignment, key, _sample_value(rng, key, context))

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

            if score != float("inf"):
                # Early stop as soon as one feasible repaired candidate appears.
                break

        return best_assignment if best_assignment is not None else partial_assignment


def _clone_assignment(assignment: dict[str, object]) -> dict[str, object]:
    cloned: dict[str, object] = {}
    for key, value in assignment.items():
        if isinstance(value, list):
            cloned[key] = value.copy()
        else:
            cloned[key] = value
    return cloned


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
