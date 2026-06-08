from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .importer import OptDSLImporter, ParsedOptDSLModel


@dataclass
class VariableSpec:
    """Top-level variable declaration extracted from an optDSL source."""

    name: str
    code: str
    annotation_code: str | None
    value_code: str | None
    ast_node: ast.Assign | ast.AnnAssign
    domain: "VariableDomain | None" = None


@dataclass
class IntDomain:
    """Integer domain bounds for decision variables."""

    lower: int | None
    upper: int | None


@dataclass
class VariableDomain:
    """Parsed decision domain from an optDSL type annotation."""

    kind: str
    int_domain: IntDomain | None = None
    length: int | None = None
    element_domain: IntDomain | None = None


@dataclass
class DecisionIndexSpec:
    """Flattened decision index entry for scalar/list decision variables."""

    variable_name: str
    index: int | None
    domain: IntDomain


@dataclass
class ConstraintSpec:
    """Constraint method metadata with original code and runtime callable."""

    name: str
    code: str
    ast_node: ast.FunctionDef
    runtime_callable: Callable[..., Any] | None


@dataclass
class ProblemObjective:
    """Objective metadata extracted from the optDSL source."""

    sense: str
    expression: str
    code: str | None
    variable_name: str | None
    function_name: str | None


@dataclass
class ProblemDefinition:
    """Generic optDSL problem definition for search components."""

    parsed: ParsedOptDSLModel
    constants: dict[str, Any]
    variables: dict[str, VariableSpec]
    constraints: dict[str, ConstraintSpec]
    objective: ProblemObjective | None
    decision_indices: list[DecisionIndexSpec]


def read_problem(file_path: str | Path) -> ProblemDefinition:
    path = Path(file_path)
    code = path.read_text(encoding="utf-8")
    return read_problem_from_code(code)


def read_problem_from_code(code: str) -> ProblemDefinition:
    importer = OptDSLImporter()
    parsed = importer.from_code(code)
    resolved_constants = _resolve_constants(parsed.constants)
    variables = _collect_variables(parsed.module, resolved_constants)
    decision_indices = _collect_decision_indices(variables)
    constraints = _collect_constraints(parsed)
    objective = _collect_objective(parsed.module, parsed)
    return ProblemDefinition(
        parsed=parsed,
        constants=dict(resolved_constants),
        variables=variables,
        constraints=constraints,
        objective=objective,
        decision_indices=decision_indices,
    )


def _collect_variables(module: ast.Module | None, constants: dict[str, Any]) -> dict[str, VariableSpec]:
    if module is None:
        return {}

    variables: dict[str, VariableSpec] = {}
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if name.isupper():
                continue
            variables[name] = VariableSpec(
                name=name,
                code=ast.unparse(node),
                annotation_code=ast.unparse(node.annotation) if node.annotation is not None else None,
                value_code=ast.unparse(node.value) if node.value is not None else None,
                ast_node=node,
                domain=_parse_variable_domain(node.annotation, constants),
            )
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name.isupper():
                continue
            variables[name] = VariableSpec(
                name=name,
                code=ast.unparse(node),
                annotation_code=None,
                value_code=ast.unparse(node.value),
                ast_node=node,
                domain=None,
            )
    return variables


def _collect_decision_indices(variables: dict[str, VariableSpec]) -> list[DecisionIndexSpec]:
    indices: list[DecisionIndexSpec] = []

    for variable in variables.values():
        domain = variable.domain
        if domain is None:
            continue

        if domain.kind == "int" and domain.int_domain is not None:
            indices.append(
                DecisionIndexSpec(
                    variable_name=variable.name,
                    index=None,
                    domain=domain.int_domain,
                )
            )
            continue

        if domain.kind == "list" and domain.length is not None and domain.element_domain is not None:
            for idx in range(domain.length):
                indices.append(
                    DecisionIndexSpec(
                        variable_name=variable.name,
                        index=idx,
                        domain=domain.element_domain,
                    )
                )

        if domain.kind == "list_2d" and domain.length is not None and domain.element_domain is not None:
            inner = domain.element_domain
            if inner.kind == "list" and inner.length is not None and inner.element_domain is not None:
                for i in range(domain.length):
                    for j in range(inner.length):
                        indices.append(
                            DecisionIndexSpec(
                                variable_name=variable.name,
                                index=(i, j),
                                domain=inner.element_domain,
                            )
                        )

    return indices


def _parse_variable_domain(annotation: ast.expr | None, constants: dict[str, Any]) -> VariableDomain | None:
    if annotation is None or not isinstance(annotation, ast.Call) or not isinstance(annotation.func, ast.Name):
        return None

    func_name = annotation.func.id

    if func_name == "DSInt":
        return VariableDomain(kind="int", int_domain=_parse_int_domain(annotation, constants))

    if func_name == "DSList":
        if len(annotation.args) < 2:
            return None
        length = _safe_eval_int_expr(annotation.args[0], constants)
        elem = annotation.args[1]
        # Handle nested DSList: DSList(N, DSList(M, DSInt(...))) — store a
        # flagged kind so _collect_decision_indices knows to expand both dims.
        if isinstance(elem, ast.Call) and isinstance(elem.func, ast.Name) and elem.func.id == "DSList":
            inner_length = _safe_eval_int_expr(elem.args[0], constants)
            inner_elem = elem.args[1] if len(elem.args) >= 2 else None
            inner_dsint = inner_elem if isinstance(inner_elem, ast.Call) else None
            if inner_dsint is not None and isinstance(inner_dsint.func, ast.Name) and inner_dsint.func.id == "DSInt":
                return VariableDomain(
                    kind="list_2d",
                    length=length,
                    element_domain=VariableDomain(
                        kind="list",
                        length=inner_length,
                        element_domain=_parse_int_domain(inner_dsint, constants),
                    ),
                )
        if not isinstance(elem, ast.Call) or not isinstance(elem.func, ast.Name) or elem.func.id != "DSInt":
            return None
        return VariableDomain(
            kind="list",
            length=length,
            element_domain=_parse_int_domain(elem, constants),
        )

    return None


def _parse_int_domain(dsint_call: ast.Call, constants: dict[str, Any]) -> IntDomain:
    lower: int | None = None
    upper: int | None = None

    if len(dsint_call.args) >= 1:
        lower = _safe_eval_int_expr(dsint_call.args[0], constants)
    if len(dsint_call.args) >= 2:
        upper = _safe_eval_int_expr(dsint_call.args[1], constants)

    return IntDomain(lower=lower, upper=upper)


def _safe_eval_int_expr(expr: ast.AST, constants: dict[str, Any]) -> int | None:
    try:
        value = ast.literal_eval(expr)
        return int(value)
    except (ValueError, SyntaxError, TypeError):
        pass

    try:
        if not isinstance(expr, ast.expr):
            return None
        value = _safe_eval_expr(expr, dict(constants), _safe_functions())
        return int(value)
    except (ValueError, TypeError, KeyError, NotImplementedError, ZeroDivisionError):
        return None


def _resolve_constants(constants: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(constants)
    safe_funcs = _safe_functions()

    changed = True
    iterations = 0
    max_iterations = max(1, len(resolved) * 3)

    while changed and iterations < max_iterations:
        changed = False
        iterations += 1
        for key, value in list(resolved.items()):
            if not isinstance(value, str):
                continue
            try:
                expr = ast.parse(value, mode="eval")
                evaluated = _safe_eval_expr(expr.body, dict(resolved), safe_funcs)
            except (ValueError, TypeError, KeyError, NotImplementedError, ZeroDivisionError, SyntaxError):
                continue
            if evaluated != value:
                resolved[key] = evaluated
                changed = True

    return resolved


def _safe_functions() -> dict[str, Callable[..., Any]]:
    return {
        "sum": sum,
        "min": min,
        "max": max,
        "len": len,
        "int": int,
    }


def _safe_eval_expr(expr: ast.expr, env: dict[str, Any], funcs: dict[str, Callable[..., Any]]) -> Any:
    if isinstance(expr, ast.Constant):
        return expr.value

    if isinstance(expr, ast.Name):
        if expr.id in env:
            return env[expr.id]
        if expr.id in funcs:
            return funcs[expr.id]
        raise KeyError(expr.id)

    if isinstance(expr, ast.List):
        return [_safe_eval_expr(elt, env, funcs) for elt in expr.elts]

    if isinstance(expr, ast.Tuple):
        return tuple(_safe_eval_expr(elt, env, funcs) for elt in expr.elts)

    if isinstance(expr, ast.BinOp):
        left = _safe_eval_expr(expr.left, env, funcs)
        right = _safe_eval_expr(expr.right, env, funcs)
        if isinstance(expr.op, ast.Add):
            return left + right
        if isinstance(expr.op, ast.Sub):
            return left - right
        if isinstance(expr.op, ast.Mult):
            return left * right
        if isinstance(expr.op, ast.Div):
            return left / right
        if isinstance(expr.op, ast.FloorDiv):
            return left // right
        if isinstance(expr.op, ast.Mod):
            return left % right
        if isinstance(expr.op, ast.Pow):
            return left**right
        raise NotImplementedError(type(expr.op).__name__)

    if isinstance(expr, ast.UnaryOp):
        value = _safe_eval_expr(expr.operand, env, funcs)
        if isinstance(expr.op, ast.UAdd):
            return +value
        if isinstance(expr.op, ast.USub):
            return -value
        raise NotImplementedError(type(expr.op).__name__)

    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
        func_name = expr.func.id
        if func_name not in funcs:
            raise NotImplementedError(func_name)
        args = [_safe_eval_expr(arg, env, funcs) for arg in expr.args]
        return funcs[func_name](*args)

    raise NotImplementedError(type(expr).__name__)


def _collect_constraints(parsed: ParsedOptDSLModel) -> dict[str, ConstraintSpec]:
    constraints: dict[str, ConstraintSpec] = {}
    for name, fn_ast in parsed.constraints.items():
        runtime_callable = parsed.runtime_constraints.get(name)
        constraints[name] = ConstraintSpec(
            name=name,
            code=ast.unparse(fn_ast),
            ast_node=fn_ast,
            runtime_callable=runtime_callable if callable(runtime_callable) else None,
        )
    return constraints


def _collect_objective(module: ast.Module | None, parsed: ParsedOptDSLModel) -> ProblemObjective | None:
    if parsed.objective is None:
        return None

    objective_code: str | None = None
    if module is not None:
        for node in module.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id in {"minimize", "maximize"}:
                    objective_code = ast.unparse(node)
                    break

    objective_variable: str | None = None
    expression = parsed.objective.expression
    if isinstance(expression, str) and expression.isidentifier():
        objective_variable = expression

    return ProblemObjective(
        sense=parsed.objective.sense,
        expression=parsed.objective.expression,
        code=objective_code,
        variable_name=objective_variable,
        function_name=parsed.objective_function,
    )


def infer_assignment_variable_name(variables: dict[str, VariableSpec]) -> str:
    """Best-effort utility for examples: pick DSL list decision variable name."""

    for variable in variables.values():
        annotation = variable.annotation_code
        if annotation is not None and "DSList" in annotation and variable.name != "objective":
            return variable.name

    raise ValueError("Could not infer assignment variable name from variables")

__all__ = [
    "ConstraintSpec",
    "DecisionIndexSpec",
    "IntDomain",
    "ProblemDefinition",
    "ProblemObjective",
    "VariableDomain",
    "VariableSpec",
    "infer_assignment_variable_name",
    "read_problem",
    "read_problem_from_code",
]
