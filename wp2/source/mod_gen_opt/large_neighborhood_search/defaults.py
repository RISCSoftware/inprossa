from __future__ import annotations

import random
from dataclasses import dataclass

from .components import AcceptanceCriterion, DestroyOperator, LNSLogger, NeighborhoodSelector, RepairOperator, StopCriterion
from .models import LNSContext, LNSState


def _decision_keys(context: LNSContext) -> list[tuple[str, int | None]]:
    return context.extra["decision_keys"]


def _domains(context: LNSContext) -> dict[tuple[str, int | None], tuple[int, int]]:
    return context.extra["decision_domains"]


def _set_value(assignment: dict[str, object], key: tuple[str, int | None], value: int | None) -> None:
    var_name, idx = key
    if idx is None:
        assignment[var_name] = value
        return
    var_value = assignment[var_name]
    if isinstance(var_value, list):
        var_value[idx] = value


def _sample_value(rng: random.Random, key: tuple[str, int | None], context: LNSContext) -> int:
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
            if isinstance(value, list) and value[idx] is None:
                value[idx] = _sample_value(rng, key, context)
        return partial_assignment


@dataclass
class SampledRepair(RepairOperator):
    samples: int = 8

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        evaluator = context.extra.get("evaluator")
        if evaluator is None or self.samples <= 1:
            return RandomRepair().repair(partial_assignment, context)

        best_assignment: dict[str, object] | None = None
        best_score = float("inf")
        sense = context.objective_sense

        for _ in range(self.samples):
            candidate = _clone_assignment(partial_assignment)
            candidate = RandomRepair().repair(candidate, context)
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

    def on_finish(self, state: LNSState, _context: LNSContext) -> None:
        print(
            "[lns] run finished "
            f"iterations={state.stats.iterations} "
            f"accepted={state.stats.accepted} "
            f"improvements={state.stats.improvements} "
            f"infeasible={state.stats.infeasible_candidates} "
            f"elapsed={state.stats.elapsed_seconds:.4f}s"
        )
