from __future__ import annotations

import argparse
import ast
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Hashable, Mapping

from tree_search import (
    MaxIterationsTermination,
    NoBounding,
    NoPruning,
    SearchContext,
    SearchNode,
    SearchState,
    SolutionEvaluation,
    TreeSearchEngine,
    read_problem,
)
from tree_search.components import Branching, NodeSelection
from tree_search.problem_reader import DecisionIndexSpec, ProblemDefinition
from tree_search.components import Pruning


DEFAULT_DSL = Path("problem_instances/1dbp/problem_2_t_zero_based.dsl")


class StackNodeSelection(NodeSelection):
    def select_node(self, state: SearchState, context: SearchContext) -> SearchNode:
        return state.frontier.pop()


def _clone_assignment(assignment: dict[str, Any]) -> dict[str, Any]:
    cloned: dict[str, Any] = {}
    for key, value in assignment.items():
        if isinstance(value, list):
            cloned[key] = value.copy()
        else:
            cloned[key] = value
    return cloned


def _set_decision_value(assignment: dict[str, Any], decision: DecisionIndexSpec, value: int) -> None:
    if decision.index is None:
        assignment[decision.variable_name] = value
        return

    var_value = assignment[decision.variable_name]
    if not isinstance(var_value, list):
        raise TypeError(f"Expected list value for variable '{decision.variable_name}'")
    var_value[decision.index] = value


def _has_unassigned(assignment: dict[str, Any]) -> bool:
    for value in assignment.values():
        if value is None:
            return True
        if isinstance(value, list) and any(item is None for item in value):
            return True
    return False


class Tri(Enum):
    TRUE = 1
    FALSE = 2
    UNKNOWN = 3


@dataclass(frozen=True)
class Interval:
    lo: int
    hi: int

    @property
    def is_exact(self) -> bool:
        return self.lo == self.hi


def _interval_add(a: Interval, b: Interval) -> Interval:
    return Interval(a.lo + b.lo, a.hi + b.hi)


def _interval_sub(a: Interval, b: Interval) -> Interval:
    return Interval(a.lo - b.hi, a.hi - b.lo)


def _interval_mul(a: Interval, b: Interval) -> Interval:
    vals = (a.lo * b.lo, a.lo * b.hi, a.hi * b.lo, a.hi * b.hi)
    return Interval(min(vals), max(vals))


def _tri_from_eq(a: Interval, b: Interval) -> Tri:
    if a.hi < b.lo or b.hi < a.lo:
        return Tri.FALSE
    if a.is_exact and b.is_exact and a.lo == b.lo:
        return Tri.TRUE
    return Tri.UNKNOWN


def _tri_from_ne(a: Interval, b: Interval) -> Tri:
    if a.hi < b.lo or b.hi < a.lo:
        return Tri.TRUE
    if a.is_exact and b.is_exact and a.lo == b.lo:
        return Tri.FALSE
    return Tri.UNKNOWN


def _tri_from_le(a: Interval, b: Interval) -> Tri:
    if a.lo > b.hi:
        return Tri.FALSE
    if a.hi <= b.lo:
        return Tri.TRUE
    return Tri.UNKNOWN


def _tri_from_lt(a: Interval, b: Interval) -> Tri:
    if a.lo >= b.hi:
        return Tri.FALSE
    if a.hi < b.lo:
        return Tri.TRUE
    return Tri.UNKNOWN


def _tri_from_ge(a: Interval, b: Interval) -> Tri:
    if a.hi < b.lo:
        return Tri.FALSE
    if a.lo >= b.hi:
        return Tri.TRUE
    return Tri.UNKNOWN


def _tri_from_gt(a: Interval, b: Interval) -> Tri:
    if a.hi <= b.lo:
        return Tri.FALSE
    if a.lo > b.hi:
        return Tri.TRUE
    return Tri.UNKNOWN


def _tri_not(value: Tri) -> Tri:
    if value == Tri.TRUE:
        return Tri.FALSE
    if value == Tri.FALSE:
        return Tri.TRUE
    return Tri.UNKNOWN


def _tri_and(values: list[Tri]) -> Tri:
    if any(v == Tri.FALSE for v in values):
        return Tri.FALSE
    if all(v == Tri.TRUE for v in values):
        return Tri.TRUE
    return Tri.UNKNOWN


def _tri_or(values: list[Tri]) -> Tri:
    if any(v == Tri.TRUE for v in values):
        return Tri.TRUE
    if all(v == Tri.FALSE for v in values):
        return Tri.FALSE
    return Tri.UNKNOWN


@dataclass
class PartialConstraintPruning(Pruning):
    problem_data: ProblemDefinition
    decisions: list[DecisionIndexSpec]
    active_constraints: list[str]
    variable_to_constraints: dict[str, list[str]]
    infeasible_prefixes: set[Hashable] = field(default_factory=set)

    def _prefix_key(self, assignment: dict[str, Any]) -> tuple[Any, ...]:
        key: list[Any] = []
        for decision in self.decisions:
            key.append(_get_decision_value(assignment, decision))
        return tuple(key)

    def should_prune(self, node: SearchNode, state: SearchState, context: SearchContext) -> bool:
        assignment: dict[str, Any] = node.metadata["assignment"]
        prefix_key = self._prefix_key(assignment)
        if prefix_key in self.infeasible_prefixes:
            return True

        scalar_domains, list_domains = _build_domain_maps(self.decisions, assignment)
        env_base = dict(self.problem_data.constants)
        env_base.update(assignment)

        parent_status = node.parent.metadata.get("constraint_status", {}) if node.parent is not None else {}
        status_map = dict(parent_status)

        last_decision_id = node.metadata.get("last_decision_id")
        if isinstance(last_decision_id, int) and 0 <= last_decision_id < len(self.decisions):
            changed_var = self.decisions[last_decision_id].variable_name
            constraints_to_check = self.variable_to_constraints.get(changed_var, self.active_constraints)
        else:
            constraints_to_check = self.active_constraints

        for constraint_name in constraints_to_check:
            fn_ast = self.problem_data.parsed.constraints.get(constraint_name)
            if fn_ast is None:
                continue

            status = _evaluate_constraint_partial(
                fn_ast=fn_ast,
                env_base=env_base,
                scalar_domains=scalar_domains,
                list_domains=list_domains,
            )
            status_map[constraint_name] = status
            if status == Tri.FALSE:
                self.infeasible_prefixes.add(prefix_key)
                return True

        node.metadata["constraint_status"] = status_map
        return False


def _build_domain_maps(
    decisions: list[DecisionIndexSpec],
    assignment: dict[str, Any],
) -> tuple[dict[str, Interval], dict[str, dict[int, Interval]]]:
    scalar_domains: dict[str, Interval] = {}
    list_domains: dict[str, dict[int, Interval]] = {}

    for decision in decisions:
        d = decision.domain
        if d.lower is None or d.upper is None:
            continue
        interval = Interval(d.lower, d.upper)
        if decision.index is None:
            if decision.variable_name in assignment and assignment[decision.variable_name] is None:
                scalar_domains[decision.variable_name] = interval
            continue
        by_index = list_domains.setdefault(decision.variable_name, {})
        value = assignment.get(decision.variable_name)
        if isinstance(value, list) and 0 <= decision.index < len(value) and value[decision.index] is None:
            by_index[decision.index] = interval

    return scalar_domains, list_domains


def _evaluate_constraint_partial(
    fn_ast: ast.FunctionDef,
    env_base: dict[str, Any],
    scalar_domains: dict[str, Interval],
    list_domains: dict[str, dict[int, Interval]],
) -> Tri:
    env = dict(env_base)
    return _eval_stmt_block(fn_ast.body, env, scalar_domains, list_domains)


def _eval_stmt_block(
    statements: list[ast.stmt],
    env: dict[str, Any],
    scalar_domains: dict[str, Interval],
    list_domains: dict[str, dict[int, Interval]],
) -> Tri:
    for statement in statements:
        status = _eval_stmt(statement, env, scalar_domains, list_domains)
        if status == Tri.FALSE:
            return Tri.FALSE
    return Tri.TRUE


def _eval_stmt(
    statement: ast.stmt,
    env: dict[str, Any],
    scalar_domains: dict[str, Interval],
    list_domains: dict[str, dict[int, Interval]],
) -> Tri:
    if isinstance(statement, ast.Assign):
        if len(statement.targets) != 1:
            return Tri.UNKNOWN
        target = statement.targets[0]
        interval = _eval_numeric_interval(statement.value, env, scalar_domains, list_domains)
        if interval is not None and isinstance(target, ast.Name):
            env[target.id] = interval.lo if interval.is_exact else None
            if not interval.is_exact:
                scalar_domains[target.id] = interval
        return Tri.TRUE

    if isinstance(statement, ast.AnnAssign):
        if isinstance(statement.target, ast.Name):
            if statement.value is not None:
                interval = _eval_numeric_interval(statement.value, env, scalar_domains, list_domains)
                if interval is not None and interval.is_exact:
                    env[statement.target.id] = interval.lo
                else:
                    env[statement.target.id] = None
            else:
                env[statement.target.id] = None
        return Tri.TRUE

    if isinstance(statement, ast.Assert):
        result = _eval_bool_tri(statement.test, env, scalar_domains, list_domains)
        if result == Tri.FALSE:
            return Tri.FALSE
        return Tri.TRUE

    if isinstance(statement, ast.For):
        if not isinstance(statement.target, ast.Name):
            return Tri.UNKNOWN

        range_values = _eval_range_values(statement.iter, env, scalar_domains, list_domains)
        if range_values is None:
            return Tri.UNKNOWN

        for loop_value in range_values:
            env[statement.target.id] = loop_value
            status = _eval_stmt_block(statement.body, env, scalar_domains, list_domains)
            if status == Tri.FALSE:
                return Tri.FALSE
        return Tri.TRUE

    if isinstance(statement, ast.If):
        cond = _eval_bool_tri(statement.test, env, scalar_domains, list_domains)
        if cond == Tri.TRUE:
            return _eval_stmt_block(statement.body, env, scalar_domains, list_domains)
        if cond == Tri.FALSE:
            return _eval_stmt_block(statement.orelse, env, scalar_domains, list_domains)

        env_then = dict(env)
        env_else = dict(env)
        then_status = _eval_stmt_block(statement.body, env_then, dict(scalar_domains), dict(list_domains))
        else_status = _eval_stmt_block(statement.orelse, env_else, dict(scalar_domains), dict(list_domains))
        if then_status == Tri.FALSE and else_status == Tri.FALSE:
            return Tri.FALSE
        return Tri.UNKNOWN

    return Tri.UNKNOWN


def _eval_range_values(
    expr: ast.expr,
    env: dict[str, Any],
    scalar_domains: dict[str, Interval],
    list_domains: dict[str, dict[int, Interval]],
) -> list[int] | None:
    if not isinstance(expr, ast.Call) or not isinstance(expr.func, ast.Name) or expr.func.id != "range":
        return None

    args: list[int] = []
    for arg in expr.args:
        iv = _eval_numeric_interval(arg, env, scalar_domains, list_domains)
        if iv is None or not iv.is_exact:
            return None
        args.append(iv.lo)

    try:
        return list(range(*args))
    except TypeError:
        return None


def _eval_bool_tri(
    expr: ast.expr,
    env: dict[str, Any],
    scalar_domains: dict[str, Interval],
    list_domains: dict[str, dict[int, Interval]],
) -> Tri:
    if isinstance(expr, ast.BoolOp):
        values = [_eval_bool_tri(v, env, scalar_domains, list_domains) for v in expr.values]
        if isinstance(expr.op, ast.And):
            return _tri_and(values)
        if isinstance(expr.op, ast.Or):
            return _tri_or(values)
        return Tri.UNKNOWN

    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        return _tri_not(_eval_bool_tri(expr.operand, env, scalar_domains, list_domains))

    if isinstance(expr, ast.Compare):
        left = _eval_numeric_interval(expr.left, env, scalar_domains, list_domains)
        if left is None:
            return Tri.UNKNOWN

        result = Tri.TRUE
        cur_left = left
        for op, comp in zip(expr.ops, expr.comparators):
            right = _eval_numeric_interval(comp, env, scalar_domains, list_domains)
            if right is None:
                return Tri.UNKNOWN
            if isinstance(op, ast.Eq):
                step = _tri_from_eq(cur_left, right)
            elif isinstance(op, ast.NotEq):
                step = _tri_from_ne(cur_left, right)
            elif isinstance(op, ast.Lt):
                step = _tri_from_lt(cur_left, right)
            elif isinstance(op, ast.LtE):
                step = _tri_from_le(cur_left, right)
            elif isinstance(op, ast.Gt):
                step = _tri_from_gt(cur_left, right)
            elif isinstance(op, ast.GtE):
                step = _tri_from_ge(cur_left, right)
            else:
                return Tri.UNKNOWN

            if step == Tri.FALSE:
                return Tri.FALSE
            if step == Tri.UNKNOWN:
                result = Tri.UNKNOWN
            cur_left = right
        return result

    numeric = _eval_numeric_interval(expr, env, scalar_domains, list_domains)
    if numeric is None:
        return Tri.UNKNOWN
    if numeric.is_exact:
        return Tri.TRUE if numeric.lo != 0 else Tri.FALSE
    if numeric.lo > 0 or numeric.hi < 0:
        return Tri.TRUE
    return Tri.UNKNOWN


def _eval_numeric_interval(
    expr: ast.expr,
    env: dict[str, Any],
    scalar_domains: dict[str, Interval],
    list_domains: dict[str, dict[int, Interval]],
) -> Interval | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, (int, bool)):
        value = int(expr.value)
        return Interval(value, value)

    if isinstance(expr, ast.Name):
        if expr.id in env:
            value = env[expr.id]
            if isinstance(value, bool):
                v = int(value)
                return Interval(v, v)
            if isinstance(value, int):
                return Interval(value, value)
            if value is None and expr.id in scalar_domains:
                return scalar_domains[expr.id]
        if expr.id in scalar_domains:
            return scalar_domains[expr.id]
        return None

    if isinstance(expr, ast.Subscript) and isinstance(expr.value, ast.Name):
        base_name = expr.value.id
        container = env.get(base_name)
        idx_interval = _eval_numeric_interval(expr.slice, env, scalar_domains, list_domains)
        if idx_interval is None or not idx_interval.is_exact:
            return None
        idx = idx_interval.lo

        if isinstance(container, list) and 0 <= idx < len(container):
            item = container[idx]
            if isinstance(item, bool):
                v = int(item)
                return Interval(v, v)
            if isinstance(item, int):
                return Interval(item, item)
            if item is None:
                by_index = list_domains.get(base_name, {})
                if idx in by_index:
                    return by_index[idx]
        return None

    if isinstance(expr, ast.BinOp):
        left = _eval_numeric_interval(expr.left, env, scalar_domains, list_domains)
        right = _eval_numeric_interval(expr.right, env, scalar_domains, list_domains)
        if left is None or right is None:
            return None
        if isinstance(expr.op, ast.Add):
            return _interval_add(left, right)
        if isinstance(expr.op, ast.Sub):
            return _interval_sub(left, right)
        if isinstance(expr.op, ast.Mult):
            return _interval_mul(left, right)
        return None

    if isinstance(expr, ast.UnaryOp):
        operand = _eval_numeric_interval(expr.operand, env, scalar_domains, list_domains)
        if operand is None:
            return None
        if isinstance(expr.op, ast.UAdd):
            return operand
        if isinstance(expr.op, ast.USub):
            return Interval(-operand.hi, -operand.lo)
        return None

    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
        if expr.func.id == "int" and len(expr.args) == 1:
            return _eval_numeric_interval(expr.args[0], env, scalar_domains, list_domains)
        if expr.func.id == "sum" and len(expr.args) == 1:
            arg = expr.args[0]
            if isinstance(arg, ast.Name) and isinstance(env.get(arg.id), list):
                total = Interval(0, 0)
                for idx, item in enumerate(env[arg.id]):
                    if isinstance(item, bool):
                        iv = Interval(int(item), int(item))
                    elif isinstance(item, int):
                        iv = Interval(item, item)
                    elif item is None:
                        iv = list_domains.get(arg.id, {}).get(idx)
                        if iv is None:
                            return None
                    else:
                        return None
                    total = _interval_add(total, iv)
                return total
        return None

    return None


class DecisionAssignmentBranching(Branching):
    def branch(self, node: SearchNode, state: SearchState, context: SearchContext):
        decisions: list[DecisionIndexSpec] = context.extra["decisions"]
        unassigned_ids: tuple[int, ...] = node.metadata["unassigned_ids"]
        if not unassigned_ids:
            return []

        order_key: dict[int, tuple[int, int, int, int]] = context.extra["decision_order_key"]
        decision_id = min(unassigned_ids, key=lambda idx: order_key[idx])
        decision = decisions[decision_id]
        lower = decision.domain.lower
        upper = decision.domain.upper
        if lower is None or upper is None:
            return []

        assignment = node.metadata["assignment"]
        children: list[SearchNode] = []

        random_value_order = bool(context.extra.get("random_value_order", False))
        base_seed = int(context.extra.get("random_seed", 0))
        attempt_id = int(context.extra.get("attempt_id", 0))

        values = list(range(lower, upper + 1))
        if random_value_order and len(values) > 1:
            rng = random.Random(base_seed + 1009 * attempt_id + 131 * node.depth + 17 * decision_id)
            rng.shuffle(values)
            # For LIFO frontier, append in this order so the first sampled value is explored first.
            domain_values = reversed(values)
        else:
            # LIFO node selection pops the last appended child first.
            # Appending values in descending order makes DFS explore lower values first.
            domain_values = range(upper, lower - 1, -1)

        for value in domain_values:
            new_assignment = _clone_assignment(assignment)
            _set_decision_value(new_assignment, decision, value)
            children.append(
                SearchNode(
                    state={
                        "variable": decision.variable_name,
                        "index": decision.index,
                        "value": value,
                    },
                    parent=node,
                    depth=node.depth + 1,
                    metadata={
                        "unassigned_ids": tuple(idx for idx in unassigned_ids if idx != decision_id),
                        "last_decision_id": decision_id,
                        "constraint_status": dict(node.metadata.get("constraint_status", {})),
                        "assignment": new_assignment,
                    },
                )
            )

        return children


@dataclass
class AssignmentEvaluation(SolutionEvaluation):
    problem_data: ProblemDefinition

    def is_solution(self, node: SearchNode, state: SearchState, context: SearchContext) -> bool:
        unassigned_ids: tuple[int, ...] = node.metadata["unassigned_ids"]
        return len(unassigned_ids) == 0

    def evaluate(self, node: SearchNode, state: SearchState, context: SearchContext) -> float:
        assignment: dict[str, Any] = node.metadata["assignment"]
        if _has_unassigned(assignment):
            return float("inf")

        runtime_constraints = self.problem_data.parsed.runtime_constraints
        constraint_asts = self.problem_data.parsed.constraints

        call_results: dict[str, Any] = {}
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
                return float("inf")

        objective = self.problem_data.objective
        if objective is None:
            return 0.0

        if objective.function_name is not None:
            if objective.function_name in call_results and isinstance(call_results[objective.function_name], (int, float)):
                return float(call_results[objective.function_name])

            fn = runtime_constraints.get(objective.function_name)
            fn_ast = constraint_asts.get(objective.function_name)
            if callable(fn) and fn_ast is not None:
                arg_names = [arg.arg for arg in fn_ast.args.args]
                if all(arg_name in assignment for arg_name in arg_names):
                    args = [assignment[arg_name] for arg_name in arg_names]
                    value = fn(*args)
                    if isinstance(value, (int, float)):
                        return float(value)

        if objective.variable_name is not None and objective.variable_name in assignment:
            value = assignment[objective.variable_name]
            if isinstance(value, (int, float)):
                return float(value)

        return float("inf")


def _build_initial_assignment(problem_data: ProblemDefinition, objective_variable_name: str | None) -> dict[str, Any]:
    assignment: dict[str, Any] = {}
    for variable in problem_data.variables.values():
        domain = variable.domain
        if domain is None:
            continue
        if objective_variable_name is not None and variable.name == objective_variable_name:
            continue

        if domain.kind == "int":
            assignment[variable.name] = None
            continue

        if domain.kind == "list" and domain.length is not None:
            assignment[variable.name] = [None for _ in range(domain.length)]

    return assignment


def _build_decision_list(problem_data: ProblemDefinition, objective_variable_name: str | None) -> list[DecisionIndexSpec]:
    decisions: list[DecisionIndexSpec] = []
    for decision in problem_data.decision_indices:
        if objective_variable_name is not None and decision.variable_name == objective_variable_name:
            continue
        if decision.domain.lower is None or decision.domain.upper is None:
            continue
        if decision.domain.lower > decision.domain.upper:
            continue
        decisions.append(decision)
    return decisions


def _get_decision_value(assignment: dict[str, Any], decision: DecisionIndexSpec) -> Any:
    value = assignment.get(decision.variable_name)
    if decision.index is None:
        return value
    if isinstance(value, list) and 0 <= decision.index < len(value):
        return value[decision.index]
    return None


def _constraint_variable_dependencies(
    problem_data: ProblemDefinition,
    active_constraints: list[str],
) -> dict[str, set[str]]:
    variable_names = set(problem_data.variables.keys())
    deps: dict[str, set[str]] = {}
    for constraint_name in active_constraints:
        fn_ast = problem_data.parsed.constraints.get(constraint_name)
        if fn_ast is None:
            deps[constraint_name] = set()
            continue

        used: set[str] = set()
        for node in ast.walk(fn_ast):
            if isinstance(node, ast.Name) and node.id in variable_names:
                used.add(node.id)
            elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in variable_names:
                used.add(node.value.id)
        deps[constraint_name] = used
    return deps


def _build_variable_to_constraints(constraint_deps: dict[str, set[str]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for constraint_name, vars_used in constraint_deps.items():
        for var_name in vars_used:
            mapping.setdefault(var_name, []).append(constraint_name)
    return mapping


def _build_demo_root(initial_assignment: dict[str, Any], n_decisions: int) -> SearchNode:
    return SearchNode(
        state={"root": True},
        depth=0,
        metadata={
            "unassigned_ids": tuple(range(n_decisions)),
            "last_decision_id": None,
            "constraint_status": {},
            "assignment": initial_assignment,
        },
    )


def _build_printable_assignment(variables: Mapping[str, object], assignment: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for variable_name in sorted(variables.keys()):
        output[variable_name] = assignment.get(variable_name, "<unassigned>")
    return output


def _extract_objective_value(
    best_score: float | None,
    objective_sense: str,
) -> str:
    if best_score is None:
        return "<none>"
    if best_score == float("inf"):
        return "<infeasible>"
    return f"{objective_sense} value = {best_score}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generic modular tree search over OptDSL decision variables. "
            "Branches over parsed DSInt/DSList decision domains and evaluates constraints/objective at complete assignments."
        )
    )
    parser.add_argument(
        "dsl_file",
        nargs="?",
        default=str(DEFAULT_DSL),
        help="Path to DSL file (default: problem_instances/1dbp/problem_2_t_zero_based.dsl)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=200_000,
        help="Maximum search iterations.",
    )
    parser.add_argument(
        "--print-assignment",
        action="store_true",
        help="Print best variable assignment found by decision-variable search.",
    )
    parser.add_argument(
        "--disable-partial-pruning",
        action="store_true",
        help="Disable AST-based partial feasibility pruning.",
    )
    parser.add_argument(
        "--retry-without-pruning",
        action="store_true",
        help="If no solution is found, retry once without pruning using the same iteration limit.",
    )
    parser.add_argument(
        "--restarts",
        type=int,
        default=None,
        help="Number of restart attempts with different value-order randomization streams (default: auto).",
    )
    parser.add_argument(
        "--random-value-order",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use randomized value ordering during branching (default: auto).",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=0,
        help="Base random seed for randomized value ordering.",
    )
    args = parser.parse_args()

    dsl_path = Path(args.dsl_file)
    if not dsl_path.exists():
        raise FileNotFoundError(f"DSL file does not exist: {dsl_path}")

    problem_data = read_problem(dsl_path)
    parsed = problem_data.parsed

    objective_variable_name = problem_data.objective.variable_name if problem_data.objective is not None else None
    decisions = _build_decision_list(problem_data, objective_variable_name)
    initial_assignment = _build_initial_assignment(problem_data, objective_variable_name)

    # Large combinatorial models (e.g. CVRP arc decisions) need diversification by default.
    auto_diversify = len(decisions) >= 120
    effective_random_value_order = args.random_value_order if args.random_value_order is not None else auto_diversify
    attempt_count = args.restarts if args.restarts is not None else (3 if auto_diversify else 1)

    active_constraints: list[str] = []
    if parsed.module is not None:
        for node in parsed.module.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                called = node.value.func.id
                if called in {"minimize", "maximize"}:
                    continue
                if called in parsed.constraints:
                    active_constraints.append(called)
    if not active_constraints:
        active_constraints = sorted(parsed.constraints.keys())

    constraint_deps = _constraint_variable_dependencies(problem_data, active_constraints)
    variable_to_constraints = _build_variable_to_constraints(constraint_deps)

    decision_order_key: dict[int, tuple[int, int, int, int, int]] = {}
    for decision_id, decision in enumerate(decisions):
        index_group = decision.index if decision.index is not None else 10**9
        dsize = (decision.domain.upper - decision.domain.lower + 1) if (decision.domain.lower is not None and decision.domain.upper is not None) else 10**9
        touch_count = len(variable_to_constraints.get(decision.variable_name, []))
        scalar_first = 0 if decision.index is None else 1
        decision_order_key[decision_id] = (index_group, dsize, -touch_count, scalar_first, decision_id)

    def run_with_pruning(pruning_rule: Pruning, attempt_id: int):
        context = SearchContext(
            constants=parsed.constants,
            constraints=parsed.constraints,
            objective=parsed.objective.expression if parsed.objective else None,
            objective_sense=parsed.objective.sense if parsed.objective else "minimize",
            extra={
                "dsl_file": str(dsl_path),
                "decisions": decisions,
                "decision_order_key": decision_order_key,
                "attempt_id": attempt_id,
                "random_value_order": effective_random_value_order,
                "random_seed": args.random_seed,
            },
        )
        root = _build_demo_root(_clone_assignment(initial_assignment), len(decisions))
        engine = TreeSearchEngine(
            node_selection=StackNodeSelection(),
            branching=DecisionAssignmentBranching(),
            bounding=NoBounding(),
            pruning=pruning_rule,
            solution_evaluation=AssignmentEvaluation(problem_data=problem_data),
            termination=MaxIterationsTermination(args.max_iterations),
        )
        return engine.run(root, context), context

    primary_pruning: Pruning
    if args.disable_partial_pruning:
        primary_pruning = NoPruning()
    else:
        primary_pruning = PartialConstraintPruning(
            problem_data=problem_data,
            decisions=decisions,
            active_constraints=active_constraints,
            variable_to_constraints=variable_to_constraints,
        )

    attempt_count = max(1, attempt_count)
    best_result, best_context = run_with_pruning(primary_pruning, 0)
    for attempt_id in range(1, attempt_count):
        result, run_context = run_with_pruning(primary_pruning, attempt_id)
        if result.best_node is not None and best_result.best_node is None:
            best_result = result
            best_context = run_context
        elif (
            result.best_node is not None
            and best_result.best_node is not None
            and result.best_score is not None
            and best_result.best_score is not None
            and result.best_score < best_result.best_score
        ):
            best_result = result
            best_context = run_context

        if result.best_node is not None and result.best_score is not None and result.best_score != float("inf"):
            break

    result = best_result
    context = best_context

    used_fallback_no_pruning = False
    if result.best_node is None and args.retry_without_pruning and not isinstance(primary_pruning, NoPruning):
        fallback_best, fallback_context = run_with_pruning(NoPruning(), 0)
        for attempt_id in range(1, attempt_count):
            run_result, run_context = run_with_pruning(NoPruning(), attempt_id)
            if run_result.best_node is not None and fallback_best.best_node is None:
                fallback_best = run_result
                fallback_context = run_context
            elif (
                run_result.best_node is not None
                and fallback_best.best_node is not None
                and run_result.best_score is not None
                and fallback_best.best_score is not None
                and run_result.best_score < fallback_best.best_score
            ):
                fallback_best = run_result
                fallback_context = run_context

            if run_result.best_node is not None and run_result.best_score is not None and run_result.best_score != float("inf"):
                break

        result = fallback_best
        context = fallback_context
        used_fallback_no_pruning = True

    print(f"DSL file: {dsl_path}")
    print(f"Constants ({len(parsed.constants)}): {sorted(parsed.constants.keys())}")
    print(f"Variables ({len(problem_data.variables)}): {sorted(problem_data.variables.keys())}")
    print(f"Constraints ({len(parsed.constraints)}): {sorted(parsed.constraints.keys())}")
    print(f"Decision indices: {len(decisions)}")
    print(f"Runtime-callable constraints: {sorted(parsed.runtime_constraints.keys())}")
    if parsed.objective is None:
        print("Objective: <none detected>")
    else:
        print(f"Objective: {parsed.objective.sense}({parsed.objective.expression})")

    print(
        "Search stats: "
        f"iterations={result.stats.iterations}, "
        f"expanded={result.stats.expanded}, "
        f"generated={result.stats.generated}, "
        f"pruned={result.stats.pruned}, "
        f"solutions={result.stats.solutions_found}"
    )
    if used_fallback_no_pruning:
        print("Search mode: fallback rerun without partial pruning")
    if effective_random_value_order:
        print(f"Search mode: randomized value order, restarts={attempt_count}, seed={args.random_seed}")

    if result.best_node is None:
        print("Best solution: <none>")
        print("Optimization result: <none>")
        if args.print_assignment:
            print("Variable assignment (best solution):")
            print("  <none>")
        return

    print(f"Best score: {result.best_score}")
    print(f"Optimization result: {_extract_objective_value(result.best_score, context.objective_sense)}")

    if args.print_assignment:
        best_assignment = result.best_node.metadata["assignment"]
        assignment_values = _build_printable_assignment(problem_data.variables, best_assignment)
        print("Variable assignment (best solution):")
        for var_name in sorted(assignment_values.keys()):
            print(f"  {var_name} = {assignment_values[var_name]}")


if __name__ == "__main__":
    main()
