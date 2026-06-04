from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tree_search.problem_reader import ProblemDefinition, read_problem

from .components import Evaluator, Initializer
from .models import LNSContext


def build_lns_context(
    problem_data: ProblemDefinition,
    random_seed: int = 0,
    excluded_decision_variables: set[str] | None = None,
) -> LNSContext:
    objective_variable = problem_data.objective.variable_name if problem_data.objective is not None else None
    excluded_variables = excluded_decision_variables or set()

    decisions = [
        d
        for d in problem_data.decision_indices
        if (objective_variable is None or d.variable_name != objective_variable)
        and d.variable_name not in excluded_variables
        and d.domain.lower is not None
        and d.domain.upper is not None
        and d.domain.lower <= d.domain.upper
    ]

    decision_keys: list[tuple[str, int | None]] = []
    decision_domains: dict[tuple[str, int | None], tuple[int, int]] = {}
    keys_by_variable: dict[str, list[tuple[str, int | None]]] = {}
    binary_keys_by_variable: dict[str, int] = {}
    binary_count = 0
    for d in decisions:
        assert d.domain.lower is not None and d.domain.upper is not None
        lower = int(d.domain.lower)
        upper = int(d.domain.upper)
        key = (d.variable_name, d.index)
        decision_keys.append(key)
        decision_domains[key] = (lower, upper)
        keys_by_variable.setdefault(d.variable_name, []).append(key)
        if lower == 0 and upper == 1:
            binary_count += 1
            binary_keys_by_variable[d.variable_name] = binary_keys_by_variable.get(d.variable_name, 0) + 1

    binary_ratio = (binary_count / len(decision_keys)) if decision_keys else 0.0
    auto_value_bias = "lower" if binary_ratio >= 0.6 else "uniform"
    binary_one_probability_by_variable: dict[str, float] = {}
    for variable_name, count in binary_keys_by_variable.items():
        # Large binary vectors are typically sparse (e.g., routing/assignment incidence vectors).
        p_one = 1.0 / max(1.0, float(count) ** 0.5)
        binary_one_probability_by_variable[variable_name] = max(0.02, min(0.2, p_one))

    return LNSContext(
        constants=dict(problem_data.constants),
        objective_sense=problem_data.objective.sense if problem_data.objective is not None else "minimize",
        extra={
            "problem_data": problem_data,
            "rng": random.Random(random_seed),
            "decision_specs": decisions,
            "decision_keys": decision_keys,
            "decision_domains": decision_domains,
            "keys_by_variable": keys_by_variable,
            "binary_one_probability_by_variable": binary_one_probability_by_variable,
            "value_bias": auto_value_bias,
        },
    )


def read_problem_for_lns(
    path: str | Path,
    random_seed: int = 0,
    excluded_decision_variables: set[str] | None = None,
) -> tuple[ProblemDefinition, LNSContext]:
    problem = read_problem(path)
    context = build_lns_context(
        problem,
        random_seed=random_seed,
        excluded_decision_variables=excluded_decision_variables,
    )
    return problem, context


@dataclass
class RandomAssignmentInitializer(Initializer):
    def initialize(self, context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        assignment = _build_empty_assignment(context)

        for key in context.extra["decision_keys"]:
            lo, hi = context.extra["decision_domains"][key]
            value = rng.randint(lo, hi)
            _set_decision_value(assignment, key, value)

        return assignment


@dataclass
class GreedyRandomizedInitializer(Initializer):
    candidate_values: int = 4
    completion_samples: int = 2
    shuffle_order: bool = True
    scoring_mode: str = "objective"
    restarts: int = 1
    post_fixup_rounds: int = 1
    post_fixup_walk_steps: int = 0
    post_fixup_plateau_prob: float = 0.05

    def initialize(self, context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        evaluator = context.extra.get("evaluator")
        if evaluator is None:
            return RandomAssignmentInitializer().initialize(context)

        best_assignment: dict[str, object] | None = None
        best_failed = 10**9
        best_objective = float("-inf") if context.objective_sense == "maximize" else float("inf")

        for _ in range(max(1, self.restarts)):
            assignment = _build_empty_assignment(context)
            decision_keys: list[tuple[str, int | None]] = list(context.extra["decision_keys"])
            if self.shuffle_order:
                rng.shuffle(decision_keys)

            for key in decision_keys:
                candidates = _candidate_values_for_key(
                    key,
                    context,
                    rng,
                    max(1, self.candidate_values),
                )
                best_value = candidates[0]
                candidate_best_score = float("inf") if context.objective_sense != "maximize" else float("-inf")

                for value in candidates:
                    trial_score = self._score_value_choice(
                        key=key,
                        value=value,
                        base_assignment=assignment,
                        context=context,
                        evaluator=evaluator,
                        samples=max(1, self.completion_samples),
                    )
                    if _is_better_score(trial_score, candidate_best_score, context.objective_sense):
                        candidate_best_score = trial_score
                        best_value = value

                _set_decision_value(assignment, key, best_value)

            assignment = self._post_fixup(assignment, context, evaluator)
            failed, objective_score, _ = self._evaluate_detailed_triplet(assignment, evaluator, context)

            if (
                best_assignment is None
                or _is_better_feasibility_lex(
                    failed,
                    objective_score,
                    best_failed,
                    best_objective,
                    context.objective_sense,
                )
            ):
                best_assignment = assignment
                best_failed = failed
                best_objective = objective_score

            if best_failed == 0:
                break

        if best_assignment is not None:
            return best_assignment

        return _build_empty_assignment(context)

    def _post_fixup(
        self,
        assignment: dict[str, object],
        context: LNSContext,
        evaluator: Any,
    ) -> dict[str, object]:
        rounds = max(0, self.post_fixup_rounds)
        if rounds == 0:
            return assignment

        rng: random.Random = context.extra["rng"]
        decision_keys: list[tuple[str, int | None]] = list(context.extra["decision_keys"])
        current_failed, current_objective, current_score = self._evaluate_detailed_triplet(assignment, evaluator, context)
        if current_failed == 0:
            return assignment

        for _ in range(rounds):
            improved = False
            rng.shuffle(decision_keys)

            for key in decision_keys:
                current_value = _get_decision_value(assignment, key)
                if current_value is None:
                    continue

                lo, hi = context.extra["decision_domains"][key]
                domain_size = hi - lo + 1
                if domain_size <= max(8, self.candidate_values):
                    candidates = list(range(lo, hi + 1))
                else:
                    candidates = _candidate_values_for_key(key, context, rng, max(2, self.candidate_values))

                if current_value not in candidates:
                    candidates.append(int(current_value))

                best_value = int(current_value)
                best_failed = current_failed
                best_objective = current_objective
                best_score = current_score

                for candidate_value in candidates:
                    if candidate_value == current_value:
                        continue
                    trial = _clone_assignment(assignment)
                    _set_decision_value(trial, key, int(candidate_value))
                    cand_failed, cand_objective, cand_score = self._evaluate_detailed_triplet(trial, evaluator, context)

                    if _is_better_feasibility_lex(
                        cand_failed,
                        cand_objective,
                        best_failed,
                        best_objective,
                        context.objective_sense,
                    ):
                        best_value = int(candidate_value)
                        best_failed = cand_failed
                        best_objective = cand_objective
                        best_score = cand_score

                if best_value != current_value:
                    _set_decision_value(assignment, key, best_value)
                    current_failed = best_failed
                    current_objective = best_objective
                    current_score = best_score
                    improved = True
                    if current_failed == 0:
                        return assignment

            if not improved:
                break

        if current_failed > 0:
            assignment, current_failed, _, _ = self._stochastic_feasibility_walk(
                assignment=assignment,
                context=context,
                evaluator=evaluator,
                initial_failed=current_failed,
            )

        return assignment

    def _stochastic_feasibility_walk(
        self,
        assignment: dict[str, object],
        context: LNSContext,
        evaluator: Any,
        initial_failed: int,
    ) -> tuple[dict[str, object], int, float, float]:
        rng: random.Random = context.extra["rng"]
        steps = max(0, self.post_fixup_walk_steps)
        plateau_prob = max(0.0, min(1.0, self.post_fixup_plateau_prob))
        if steps == 0:
            failed, objective, score = self._evaluate_detailed_triplet(assignment, evaluator, context)
            return assignment, failed, objective, score

        decision_keys: list[tuple[str, int | None]] = list(context.extra["decision_keys"])
        if not decision_keys:
            failed, objective, score = self._evaluate_detailed_triplet(assignment, evaluator, context)
            return assignment, failed, objective, score

        current_failed, current_objective, current_score = self._evaluate_detailed_triplet(assignment, evaluator, context)
        best_assignment = _clone_assignment(assignment)
        best_failed = current_failed
        best_objective = current_objective
        best_score = current_score

        if current_failed == 0:
            return assignment, current_failed, current_objective, current_score

        for _ in range(steps):
            key = rng.choice(decision_keys)
            current_value = _get_decision_value(assignment, key)
            if current_value is None:
                continue

            lo, hi = context.extra["decision_domains"][key]
            if lo == hi:
                continue

            if hi - lo + 1 <= max(8, self.candidate_values):
                candidate_values = [v for v in range(lo, hi + 1) if v != current_value]
            else:
                sampled = _candidate_values_for_key(key, context, rng, max(2, self.candidate_values))
                candidate_values = [v for v in sampled if v != current_value]
            if not candidate_values:
                continue

            candidate_value = rng.choice(candidate_values)
            trial = _clone_assignment(assignment)
            _set_decision_value(trial, key, int(candidate_value))
            cand_failed, cand_objective, cand_score = self._evaluate_detailed_triplet(trial, evaluator, context)

            strictly_better = _is_better_feasibility_lex(
                cand_failed,
                cand_objective,
                current_failed,
                current_objective,
                context.objective_sense,
            )
            same_failed = cand_failed == current_failed
            same_or_better_objective = (
                cand_objective >= current_objective if context.objective_sense == "maximize" else cand_objective <= current_objective
            )

            if strictly_better or (same_failed and (same_or_better_objective or rng.random() < plateau_prob)):
                assignment = trial
                current_failed = cand_failed
                current_objective = cand_objective
                current_score = cand_score

                if _is_better_feasibility_lex(
                    current_failed,
                    current_objective,
                    best_failed,
                    best_objective,
                    context.objective_sense,
                ):
                    best_assignment = _clone_assignment(assignment)
                    best_failed = current_failed
                    best_objective = current_objective
                    best_score = current_score

                if current_failed == 0:
                    return assignment, current_failed, current_objective, current_score

            if best_failed == 0:
                break

            # If the walk is not improving from the initial failed count, occasionally restart from best-so-far.
            if current_failed >= initial_failed and rng.random() < 0.01:
                assignment = _clone_assignment(best_assignment)
                current_failed = best_failed
                current_objective = best_objective
                current_score = best_score

        return best_assignment, best_failed, best_objective, best_score

    def _evaluate_detailed_triplet(
        self,
        assignment: dict[str, object],
        evaluator: Any,
        context: LNSContext,
    ) -> tuple[int, float, float]:
        diagnostics = getattr(evaluator, "evaluate_detailed", None)
        if callable(diagnostics):
            detailed = diagnostics(assignment, context)
            failed_constraints = int(getattr(detailed, "failed_constraints", 10**9))
            objective_value = getattr(detailed, "objective_value", None)
            if objective_value is None:
                objective_score = float("-inf") if context.objective_sense == "maximize" else float("inf")
            else:
                objective_score = float(objective_value)
            score = float(getattr(detailed, "score", evaluator.evaluate(assignment, context)))
            return failed_constraints, objective_score, score

        score = float(evaluator.evaluate(assignment, context))
        failed_constraints = 10**9 if _is_penalty_score(score, context) else 0
        objective_score = score
        return failed_constraints, objective_score, score

    def _score_value_choice(
        self,
        key: tuple[str, int | None],
        value: int,
        base_assignment: dict[str, object],
        context: LNSContext,
        evaluator: Any,
        samples: int,
    ) -> float:
        best = float("inf") if context.objective_sense != "maximize" else float("-inf")
        best_failed = 10**9
        best_objective = float("inf") if context.objective_sense != "maximize" else float("-inf")
        rng: random.Random = context.extra["rng"]

        for _ in range(samples):
            trial = _clone_assignment(base_assignment)
            _set_decision_value(trial, key, value)
            _random_complete_unassigned(trial, context, rng)
            diagnostics = getattr(evaluator, "evaluate_detailed", None)
            if callable(diagnostics):
                detailed = diagnostics(trial, context)
                failed_constraints = int(getattr(detailed, "failed_constraints", 10**9))
                objective_value = getattr(detailed, "objective_value", None)
                if objective_value is None:
                    objective_score = float("inf") if context.objective_sense != "maximize" else float("-inf")
                else:
                    objective_score = float(objective_value)
                score = float(getattr(detailed, "score", evaluator.evaluate(trial, context)))
            else:
                score = float(evaluator.evaluate(trial, context))
                failed_constraints = 0 if not _is_penalty_score(score, context) else 10**9
                objective_score = score

            if self.scoring_mode == "feasibility_first":
                if _is_better_feasibility_lex(
                    failed_constraints,
                    objective_score,
                    best_failed,
                    best_objective,
                    context.objective_sense,
                ):
                    best_failed = failed_constraints
                    best_objective = objective_score
                    best = score
            else:
                if _is_better_score(score, best, context.objective_sense):
                    best = score

        return best


@dataclass
class EvaluationDetails:
    failed_constraints: int
    objective_value: float | None
    score: float


@dataclass
class OptDSLEvaluator(Evaluator):
    problem_data: ProblemDefinition
    penalty_base: float = 1e9

    def evaluate(self, assignment: dict[str, object], context: LNSContext) -> float:
        return self.evaluate_detailed(assignment, context).score

    def evaluate_detailed(self, assignment: dict[str, object], context: LNSContext) -> EvaluationDetails:
        _apply_pre_evaluation_hook(assignment, context)

        if _has_unassigned(assignment):
            return EvaluationDetails(failed_constraints=10_000, objective_value=None, score=self._penalty_score(10_000, context.objective_sense))

        runtime_constraints = self.problem_data.parsed.runtime_constraints
        constraint_asts = self.problem_data.parsed.constraints

        call_results: dict[str, Any] = {}
        failed_constraints = 0
        for name, fn in runtime_constraints.items():
            fn_ast = constraint_asts.get(name)
            if fn_ast is None or not callable(fn):
                continue

            arg_names = [arg.arg for arg in fn_ast.args.args]
            if not all(arg_name in assignment for arg_name in arg_names):
                continue

            args = [assignment[arg_name] for arg_name in arg_names]
            try:
                call_results[name] = fn(*args)
            except AssertionError:
                failed_constraints += 1

        if failed_constraints > 0:
            return EvaluationDetails(
                failed_constraints=failed_constraints,
                objective_value=None,
                score=self._penalty_score(failed_constraints, context.objective_sense),
            )

        objective = self.problem_data.objective
        if objective is None:
            return EvaluationDetails(failed_constraints=0, objective_value=0.0, score=0.0)

        if objective.function_name is not None:
            if objective.function_name in call_results and isinstance(call_results[objective.function_name], (int, float)):
                obj = float(call_results[objective.function_name])
                return EvaluationDetails(failed_constraints=0, objective_value=obj, score=obj)

            fn = runtime_constraints.get(objective.function_name)
            fn_ast = constraint_asts.get(objective.function_name)
            if callable(fn) and fn_ast is not None:
                arg_names = [arg.arg for arg in fn_ast.args.args]
                if all(arg_name in assignment for arg_name in arg_names):
                    args = [assignment[arg_name] for arg_name in arg_names]
                    value = fn(*args)
                    if isinstance(value, (int, float)):
                        obj = float(value)
                        return EvaluationDetails(failed_constraints=0, objective_value=obj, score=obj)

        if objective.variable_name is not None and objective.variable_name in assignment:
            value = assignment[objective.variable_name]
            if isinstance(value, (int, float)):
                obj = float(value)
                return EvaluationDetails(failed_constraints=0, objective_value=obj, score=obj)

        return EvaluationDetails(failed_constraints=1, objective_value=None, score=self._penalty_score(1, context.objective_sense))

    def _penalty_score(self, failed_count: int, objective_sense: str) -> float:
        penalty = self.penalty_base + float(failed_count)
        if objective_sense == "maximize":
            return -penalty
        return penalty


def _set_decision_value(assignment: dict[str, object], key: tuple[str, int | None], value: int | None) -> None:
    var_name, idx = key
    if idx is None:
        assignment[var_name] = value
        return

    var_value = assignment[var_name]
    if isinstance(var_value, list):
        var_value[idx] = value


def _get_decision_value(assignment: dict[str, object], key: tuple[str, int | None]) -> int | None:
    var_name, idx = key
    if idx is None:
        value = assignment.get(var_name)
        return int(value) if isinstance(value, int) else None

    var_value = assignment.get(var_name)
    if isinstance(var_value, list):
        item = var_value[idx]
        return int(item) if isinstance(item, int) else None
    return None


def _build_empty_assignment(context: LNSContext) -> dict[str, object]:
    problem_data: ProblemDefinition = context.extra["problem_data"]
    objective_variable = problem_data.objective.variable_name if problem_data.objective is not None else None

    assignment: dict[str, object] = {}
    for var in problem_data.variables.values():
        domain = var.domain
        if domain is None:
            continue
        if objective_variable is not None and var.name == objective_variable:
            continue

        if domain.kind == "int":
            assignment[var.name] = None
        elif domain.kind == "list" and domain.length is not None:
            assignment[var.name] = [None for _ in range(domain.length)]
    return assignment


def _clone_assignment(assignment: dict[str, object]) -> dict[str, object]:
    cloned: dict[str, object] = {}
    for key, value in assignment.items():
        if isinstance(value, list):
            cloned[key] = value.copy()
        else:
            cloned[key] = value
    return cloned


def _sample_value_for_key(key: tuple[str, int | None], context: LNSContext, rng: random.Random) -> int:
    lo, hi = context.extra["decision_domains"][key]
    bias: str = context.extra.get("value_bias", "uniform")
    var_name, _ = key
    binary_probabilities: dict[str, float] = context.extra.get("binary_one_probability_by_variable", {})

    if lo == hi:
        return lo
    if lo == 0 and hi == 1 and bias == "lower":
        p_one = float(binary_probabilities.get(var_name, 0.2))
        return 1 if rng.random() < p_one else 0
    if bias == "lower" and rng.random() < 0.8:
        return lo
    if bias == "upper" and rng.random() < 0.8:
        return hi
    return rng.randint(lo, hi)


def _candidate_values_for_key(
    key: tuple[str, int | None],
    context: LNSContext,
    rng: random.Random,
    max_values: int,
) -> list[int]:
    lo, hi = context.extra["decision_domains"][key]
    domain_size = hi - lo + 1
    if domain_size <= max_values:
        return list(range(lo, hi + 1))

    values = {lo, hi}
    while len(values) < max_values:
        values.add(_sample_value_for_key(key, context, rng))
    return list(values)


def _random_complete_unassigned(assignment: dict[str, object], context: LNSContext, rng: random.Random) -> None:
    for key in context.extra["decision_keys"]:
        var_name, idx = key
        if idx is None:
            if assignment.get(var_name) is None:
                assignment[var_name] = _sample_value_for_key(key, context, rng)
            continue

        value = assignment.get(var_name)
        if isinstance(value, list) and value[idx] is None:
            value[idx] = _sample_value_for_key(key, context, rng)


def _is_better_score(candidate: float, best: float, objective_sense: str) -> bool:
    if objective_sense == "maximize":
        return candidate > best
    return candidate < best


def _is_better_feasibility_lex(
    cand_failed: int,
    cand_objective: float,
    best_failed: int,
    best_objective: float,
    objective_sense: str,
) -> bool:
    if cand_failed != best_failed:
        return cand_failed < best_failed
    if objective_sense == "maximize":
        return cand_objective > best_objective
    return cand_objective < best_objective


def _is_penalty_score(score: float, context: LNSContext) -> bool:
    penalty_base = context.extra.get("penalty_base")
    if not isinstance(penalty_base, (int, float)):
        return False
    if context.objective_sense == "maximize":
        return score <= -float(penalty_base)
    return score >= float(penalty_base)


def _has_unassigned(assignment: dict[str, object]) -> bool:
    for value in assignment.values():
        if value is None:
            return True
        if isinstance(value, list) and any(item is None for item in value):
            return True
    return False


def _apply_pre_evaluation_hook(assignment: dict[str, object], context: LNSContext) -> None:
    hook = context.extra.get("pre_evaluate_assignment_hook")
    if callable(hook):
        hook(assignment, context)
