from __future__ import annotations

import ast
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .components import Evaluator, FeasibilityClassifier, Initializer, run_mcmc
from .models import LNSContext
from .problem_reader import ProblemDefinition, read_problem
from ._expr_eval import DSRecord, eval_dsl_expr
from ._utils import (
    clone_assignment,
    get_decision_value,
    has_unassigned,
    is_better_feasibility_lex,
    is_better_score,
    is_penalty_score,
    set_decision_value,
    _deep_copy_value,
    _list_get,
    _list_set,
)


def build_lns_context(
    problem_data: ProblemDefinition,
    random_seed: int = 0,
    excluded_decision_variables: set[str] | None = None,
    feasibility_classifier: FeasibilityClassifier | None = None,
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

    # Default feasibility classifier if not provided
    if feasibility_classifier is None:
        from .defaults import OptDSLFeasibilityClassifier
        feasibility_classifier = OptDSLFeasibilityClassifier(penalty_base=1e9)

    return LNSContext(
        constants=dict(problem_data.constants),
        objective_sense=problem_data.objective.sense if problem_data.objective is not None else "minimize",
        feasibility_classifier=feasibility_classifier,
        extra={
            "problem_data": problem_data,
            "rng": random.Random(random_seed),
            "decision_specs": decisions,
            "decision_keys": decision_keys,
            "decision_domains": decision_domains,
            "keys_by_variable": keys_by_variable,
            "binary_one_probability_by_variable": binary_one_probability_by_variable,
            "value_bias": auto_value_bias,
            "penalty_base": 1e9,  # Backward compatibility
        },
    )


def read_problem_for_lns(
    path: str | Path,
    random_seed: int = 0,
    excluded_decision_variables: set[str] | None = None,
    feasibility_classifier: FeasibilityClassifier | None = None,
) -> tuple[ProblemDefinition, LNSContext]:
    problem = read_problem(path)
    context = build_lns_context(
        problem,
        random_seed=random_seed,
        excluded_decision_variables=excluded_decision_variables,
        feasibility_classifier=feasibility_classifier,
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
            set_decision_value(assignment, key, value)

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
                    if is_better_score(trial_score, candidate_best_score, context.objective_sense):
                        candidate_best_score = trial_score
                        best_value = value

                set_decision_value(assignment, key, best_value)

            assignment = self._post_fixup(assignment, context, evaluator)
            failed, objective_score, _ = self._evaluate_detailed_triplet(assignment, evaluator, context)

            if (
                best_assignment is None
                or is_better_feasibility_lex(
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
                current_value = get_decision_value(assignment, key)
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
                    trial = clone_assignment(assignment)
                    set_decision_value(trial, key, int(candidate_value))
                    cand_failed, cand_objective, cand_score = self._evaluate_detailed_triplet(trial, evaluator, context)

                    if is_better_feasibility_lex(
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
                    set_decision_value(assignment, key, best_value)
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
        best_assignment = clone_assignment(assignment)
        best_failed = current_failed
        best_objective = current_objective
        best_score = current_score

        if current_failed == 0:
            return assignment, current_failed, current_objective, current_score

        for _ in range(steps):
            key = rng.choice(decision_keys)
            current_value = get_decision_value(assignment, key)
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
            trial = clone_assignment(assignment)
            set_decision_value(trial, key, int(candidate_value))
            cand_failed, cand_objective, cand_score = self._evaluate_detailed_triplet(trial, evaluator, context)

            strictly_better = is_better_feasibility_lex(
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

                if is_better_feasibility_lex(
                    current_failed,
                    current_objective,
                    best_failed,
                    best_objective,
                    context.objective_sense,
                ):
                    best_assignment = clone_assignment(assignment)
                    best_failed = current_failed
                    best_objective = current_objective
                    best_score = current_score

                if current_failed == 0:
                    return assignment, current_failed, current_objective, current_score

            if best_failed == 0:
                break

            # If the walk is not improving from the initial failed count, occasionally restart from best-so-far.
            if current_failed >= initial_failed and rng.random() < 0.01:
                assignment = clone_assignment(best_assignment)
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
        failed_constraints = 10**9 if is_penalty_score(score, context) else 0
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
            trial = clone_assignment(base_assignment)
            set_decision_value(trial, key, value)
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
                failed_constraints = 0 if not is_penalty_score(score, context) else 10**9
                objective_score = score

            if self.scoring_mode == "feasibility_first":
                if is_better_feasibility_lex(
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
                if is_better_score(score, best, context.objective_sense):
                    best = score

        return best


@dataclass
class MCMCInitializer(Initializer):
    """MCMC initializer (Metropolis-Hastings + simulated annealing).

    Delegates to the generic :func:`run_mcmc` driver.  When the problem is
    detected as CVRP, uses route-structure-preserving mutation (remove k customers, re-insert).

    Fallback: for non-CVRP problems, uses _constructive initialization + random decision mutation.
    """

    max_steps: int = 5000
    initial_temperature: float = 1000.0
    cooling_rate: float = 0.998
    min_temperature: float = 0.1
    num_muted_decisions: int = 3
    max_muted_decisions: int = 20
    stall_threshold: int = 200
    stall_batch_increment: int = 3
    objective_weight: float = 1.0
    penalty_scale: float = 100.0

    def initialize(self, context: LNSContext) -> dict[str, object]:
        evaluator = context.extra.get("evaluator")
        if evaluator is None:
            return RandomAssignmentInitializer().initialize(context)

        rng: random.Random = context.extra["rng"]

        # --- Seed: constructive if available (CVRP), else random ---
        seed = clone_assignment(_build_initializer_seed(context, rng))

        # --- Build problem-aware mutation callback ---
        mutate_fn = _build_cvrp_or_generic_mutation(context, rng)

        # --- callbacks ---
        callbacks = type(
            "_LCBs",
            (),
            {
                "clone": lambda _, a: clone_assignment(a),
                "evaluate_detailed": lambda _, a: _evaluate_detailed(a, evaluator, context)[:2],
                "mutate": lambda _, a, bs, bk: mutate_fn(a, bs),
                "better": lambda _, af, ao, bf, bo: is_better_feasibility_lex(af, ao, bf, bo, context.objective_sense),
            },
        )()

        return run_mcmc(
            seed_assignment=seed,
            callbacks=callbacks,  # type: ignore[arg-type]
            rng=rng,
            max_steps=self.max_steps,
            initial_temperature=self.initial_temperature,
            cooling_rate=self.cooling_rate,
            min_temperature=self.min_temperature,
            initial_batch_size=self.num_muted_decisions,
            max_batch_size=self.max_muted_decisions,
            stall_threshold=self.stall_threshold,
            stall_batch_increment=self.stall_batch_increment,
            penalty_scale=self.penalty_scale,
            objective_weight=self.objective_weight,
            objective_sense=context.objective_sense,
        )


def _build_initializer_seed(
    context: LNSContext,
    _rng: random.Random,
) -> dict[str, object]:
    """Return a good starting assignment: constructive if available, else random."""
    try:
        from .problems.cvrp import CVRPRouteInitializer

        init = CVRPRouteInitializer(
            restarts=8,
            randomization=0.3,
        )
        candidate = init.initialize(context)
        # Check if feasible-looking (not all random)
        evaluator = context.extra.get("evaluator")
        if evaluator is not None:
            failed, _, _ = _evaluate_detailed(candidate, evaluator, context)
            if failed < 7:  # better than pure random for CVRP
                return candidate

    except ImportError:
        pass

    return RandomAssignmentInitializer().initialize(context)


def _build_cvrp_or_generic_mutation(
    context: LNSContext,
    rng: random.Random,
) -> Any:
    """Return a mutate(assignment, batch_size) -> assignment callable.

    Returns CVRP route-aware mutation (destroy+repair) if CVRP is detected,
    otherwise falls back to generic random decision mutation.
    """
    # Try to detect CVRP and use route-structure-aware mutation
    try:
        from .problems.cvrp_operators import _cvrp, _cvrp_arc_mutation

        if _cvrp(context) is not None:
            # CVRP detected — use destroy+repair (remove k customers, re-insert)
            return lambda a, bs: _cvrp_arc_mutation(
                a, context, rng, customer_count=min(max(bs, 1), 5),
            )
    except ImportError:
        pass

    # Fallback: generic random decision mutation
    return lambda a, bs: _multi_decision_mutation(a, context, rng, count=bs)


def _evaluate_detailed(
    assignment: dict[str, object],
    evaluator: Any,
    context: LNSContext,
) -> tuple[int, float, float]:
    """Return (failed_constraints, objective_value, score)."""
    diagnostics = getattr(evaluator, "evaluate_detailed", None)
    if callable(diagnostics):
        detailed = diagnostics(assignment, context)
        failed_constraints = int(getattr(detailed, "failed_constraints", 10**9))
        objective_value = getattr(detailed, "objective_value", None)
        if objective_value is None:
            objective_score = float("inf") if context.objective_sense != "maximize" else float("-inf")
        else:
            objective_score = float(objective_value)
        score = float(getattr(detailed, "score", evaluator.evaluate(assignment, context)))
        return failed_constraints, objective_score, score

    score = float(evaluator.evaluate(assignment, context))
    failed_constraints = 10**9 if is_penalty_score(score, context) else 0
    return failed_constraints, score, score

def _multi_decision_mutation(
    assignment: dict[str, object],
    context: LNSContext,
    rng: random.Random,
    count: int = 1,
    biased_keys: list[tuple[str, int | None]] | None = None,
) -> dict[str, object]:
    """Mutate *count* random decision positions in the assignment.

    When *biased_keys* is non-empty, each mutation has a 70 % chance of
    picking from the biased set (variables involved in failed constraints)
    and 30 % chance of a fully uniform pick.
    """
    proposal = clone_assignment(assignment)
    decision_keys: list[tuple[str, int | None]] = list(context.extra["decision_keys"])
    n_decisions = len(decision_keys)
    if n_decisions == 0:
        return proposal

    k = min(count, n_decisions)
    chosen_keys = rng.sample(decision_keys, k)
    if count > k:
        chosen_keys.extend(rng.choices(decision_keys, k=max(0, count - k)))

    for chosen in chosen_keys:
        key = chosen
        if (biased_keys and len(biased_keys) > 0 and rng.random() < 0.7):
            key = rng.choice(biased_keys)
        set_decision_value(proposal, key, _sample_value_for_key(key, context, rng))

    return proposal


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

        if has_unassigned(assignment):
            return EvaluationDetails(failed_constraints=10_000, objective_value=None, score=self._penalty_score(10_000, context.objective_sense))

        # Reject assignments with negative values in any decision variable — they violate
        # DSInt(0, …) lower bounds and correspond to infeasible/invalid states.
        # (has_unassigned already checks this recursively, incl. record fields;
        # kept as a fast top-level guard too, matching prior behavior.)
        for value in assignment.values():
            if isinstance(value, (int, float)) and value < 0:
                return EvaluationDetails(failed_constraints=10_000, objective_value=None, score=self._penalty_score(10_000, context.objective_sense))

        if self.problem_data.parsed.is_pipeline_model:
            return self._evaluate_pipeline(assignment, context)

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

    def _evaluate_pipeline(self, assignment: dict[str, object], context: LNSContext) -> EvaluationDetails:
        """Execute the full module-level "pipeline" (data flow between machines).

        Used for models where `def`-declared functions are chained via
        module-level assignments (``x = some_machine(y, z)``) rather than
        each being an isolated constraint over decision variables directly.
        See ``ParsedOptDSLModel.is_pipeline_model``.
        """
        try:
            return self._evaluate_pipeline_unsafe(assignment, context)
        except Exception:
            # Defensive fallback: an unanticipated expression/statement shape
            # should not crash the search; treat as a failed evaluation.
            return EvaluationDetails(
                failed_constraints=1,
                objective_value=None,
                score=self._penalty_score(1, context.objective_sense),
            )

    def _evaluate_pipeline_unsafe(self, assignment: dict[str, object], context: LNSContext) -> EvaluationDetails:
        parsed = self.problem_data.parsed
        module = parsed.module
        if module is None:
            return EvaluationDetails(failed_constraints=1, objective_value=None, score=self._penalty_score(1, context.objective_sense))

        record_types = parsed.record_types
        runtime_constraints = parsed.runtime_constraints
        objective = self.problem_data.objective
        objective_name = objective.variable_name if objective is not None else None

        env: dict[str, Any] = dict(self.problem_data.constants)
        failed_constraints = 0

        for node in module.body:
            if isinstance(node, ast.FunctionDef):
                continue

            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id in ("minimize", "maximize")
            ):
                continue

            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                value_node = node.value
                if isinstance(target, ast.Name) and target.id.isupper():
                    continue  # constant, already resolved
                if (
                    isinstance(value_node, ast.Call)
                    and isinstance(value_node.func, ast.Name)
                    and value_node.func.id.startswith("DS")
                ):
                    continue  # type alias assignment (e.g. Board = DSRecord({...}))

                if (
                    isinstance(value_node, ast.Call)
                    and isinstance(value_node.func, ast.Name)
                    and value_node.func.id in runtime_constraints
                ):
                    fn = runtime_constraints[value_node.func.id]
                    args = [eval_dsl_expr(a, env, record_types) for a in value_node.args]
                    try:
                        result = fn(*args)
                    except AssertionError:
                        failed_constraints += 1
                        break
                    if isinstance(target, ast.Tuple):
                        result_tuple = result if isinstance(result, tuple) else (result,)
                        if len(result_tuple) != len(target.elts):
                            failed_constraints += 1
                            break
                        for elt, value in zip(target.elts, result_tuple):
                            if isinstance(elt, ast.Name):
                                env[elt.id] = value
                    elif isinstance(target, ast.Name):
                        env[target.id] = result
                    continue

                # Plain (non-predicate) assignment, e.g. `initial_boards = GIVEN_INITIAL_BOARDS`.
                if isinstance(target, ast.Name):
                    env[target.id] = _deep_copy_value(eval_dsl_expr(value_node, env, record_types))
                continue

            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if name.isupper():
                    continue  # constant
                if node.value is None:
                    # Bare declaration. Only a genuine free decision variable
                    # (non-None domain) must come from the LNS assignment —
                    # otherwise this is a forward declaration overwritten by a
                    # later top-level `Assign` (e.g. `x: T(...)` then
                    # `x = some_machine(...)`), so it's a no-op here.
                    var_spec = self.problem_data.variables.get(name)
                    if var_spec is not None and var_spec.domain is not None:
                        if name not in assignment or assignment[name] is None:
                            failed_constraints += 1
                            break
                        env[name] = _deep_copy_value(assignment[name])
                else:
                    env[name] = _deep_copy_value(eval_dsl_expr(node.value, env, record_types))
                continue

            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id in runtime_constraints
            ):
                fn = runtime_constraints[node.value.func.id]
                args = [eval_dsl_expr(a, env, record_types) for a in node.value.args]
                try:
                    fn(*args)
                except AssertionError:
                    failed_constraints += 1
                continue

            # Any other top-level statement shape is ignored defensively.

        if failed_constraints > 0:
            return EvaluationDetails(
                failed_constraints=failed_constraints,
                objective_value=None,
                score=self._penalty_score(failed_constraints, context.objective_sense),
            )

        if objective_name is not None and objective_name in env and isinstance(env[objective_name], (int, float)):
            obj = float(env[objective_name])
            return EvaluationDetails(failed_constraints=0, objective_value=obj, score=obj)

        return EvaluationDetails(failed_constraints=1, objective_value=None, score=self._penalty_score(1, context.objective_sense))

    def _penalty_score(self, failed_count: int, objective_sense: str) -> float:
        penalty = self.penalty_base + float(failed_count)
        if objective_sense == "maximize":
            return -penalty
        return penalty





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
        elif domain.kind == "list_2d" and domain.length is not None:
            # 2D decision variable: rows × inner-length.  Reconstruct from the
            # element_domain to get the inner length.
            inner_domain = domain.element_domain
            inner_length = inner_domain.length if inner_domain is not None else 1
            assignment[var.name] = [[None for _ in range(inner_length)] for _ in range(domain.length)]
        elif domain.kind == "list_of_record" and domain.length is not None and domain.record_fields is not None:
            record_fields = domain.record_fields
            assignment[var.name] = [
                DSRecord({
                    field_name: (
                        [None for _ in range(field_domain.length)]
                        if field_domain.kind == "list" and field_domain.length is not None
                        else None
                    )
                    for field_name, field_domain in record_fields.items()
                })
                for _ in range(domain.length)
            ]
    return assignment





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
    """Randomly fill all unassigned decision variables in place.
    
    Handles 1D, 2D, and scalar decision variables correctly using _list_get/_list_set.
    """
    for key in context.extra["decision_keys"]:
        var_name, idx = key
        if idx is None:
            if assignment.get(var_name) is None:
                assignment[var_name] = _sample_value_for_key(key, context, rng)
            continue

        value = assignment.get(var_name)
        if isinstance(value, list):
            # Use _list_get to handle both 1D (int) and 2D (tuple) indices correctly
            if _list_get(value, idx) is None:
                _list_set(value, idx, _sample_value_for_key(key, context, rng))





def _apply_pre_evaluation_hook(assignment: dict[str, object], context: LNSContext) -> None:
    hook = context.extra.get("pre_evaluate_assignment_hook")
    if callable(hook):
        hook(assignment, context)
