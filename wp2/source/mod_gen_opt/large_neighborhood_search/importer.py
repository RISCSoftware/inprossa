from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ObjectiveSpec:
    """Objective specification extracted from optDSL source."""

    sense: str
    expression: str


@dataclass
class ParsedOptDSLModel:
    """Structured representation extracted from an optDSL Python file."""

    constants: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, ast.FunctionDef] = field(default_factory=dict)
    runtime_constraints: dict[str, Any] = field(default_factory=dict)
    objective: ObjectiveSpec | None = None
    objective_function: str | None = None
    module: ast.Module | None = None


class OptDSLImporter:
    """AST-based importer for optDSL-like Python formulations.

    Extraction rules:
    - Constants: top-level names in uppercase (AnnAssign or Assign)
    - Constraints: top-level function definitions
    - Objective: top-level call to minimize(<expr>)
    """

    def from_file(self, file_path: str | Path) -> ParsedOptDSLModel:
        path = Path(file_path)
        code = path.read_text(encoding="utf-8")
        return self.from_code(code)

    def from_code(self, code: str) -> ParsedOptDSLModel:
        tree = ast.parse(code)
        parsed = ParsedOptDSLModel(module=tree)

        for node in tree.body:
            self._collect_constant(node, parsed)
            self._collect_constraint(node, parsed)
            self._collect_objective(node, parsed)
            self._collect_objective_binding(node, parsed)

        # Objective assignment can appear before minimize(...).
        # Resolve once more after objective extraction to be order-independent.
        self._resolve_objective_binding(tree, parsed)

        parsed.runtime_constraints = self._build_runtime_constraints(parsed)

        return parsed

    @staticmethod
    def _resolve_objective_binding(tree: ast.Module, parsed: ParsedOptDSLModel) -> None:
        if parsed.objective is None or parsed.objective_function is not None:
            return

        objective_name = parsed.objective.expression
        if not isinstance(objective_name, str):
            return

        for node in tree.body:
            value_node: ast.AST | None = None
            target_name: str | None = None

            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                target_name = node.target.id
                value_node = node.value
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                target_name = node.targets[0].id
                value_node = node.value

            if target_name != objective_name or not isinstance(value_node, ast.Call):
                continue

            if isinstance(value_node.func, ast.Name):
                parsed.objective_function = value_node.func.id
                return

    @staticmethod
    def _build_runtime_constraints(parsed: ParsedOptDSLModel) -> dict[str, Any]:
        if parsed.module is None or not parsed.constraints:
            return {}

        runtime_constraints: dict[str, Any] = {}
        for name, fn_ast in parsed.constraints.items():
            runtime_constraints[name] = _make_ast_callable(fn_ast, parsed.constants)
        return runtime_constraints

    @staticmethod
    def _collect_constant(node: ast.AST, parsed: ParsedOptDSLModel) -> None:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if name.isupper() and node.value is not None:
                parsed.constants[name] = OptDSLImporter._safe_eval_or_unparse(node.value)
            return

        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                return
            name = node.targets[0].id
            if name.isupper():
                parsed.constants[name] = OptDSLImporter._safe_eval_or_unparse(node.value)

    @staticmethod
    def _collect_constraint(node: ast.AST, parsed: ParsedOptDSLModel) -> None:
        if isinstance(node, ast.FunctionDef):
            parsed.constraints[node.name] = node

    @staticmethod
    def _collect_objective(node: ast.AST, parsed: ParsedOptDSLModel) -> None:
        if parsed.objective is not None:
            return

        call_node: ast.Call | None = None
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call_node = node.value
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call_node = node.value

        if call_node is None:
            return

        if isinstance(call_node.func, ast.Name) and call_node.func.id == "minimize" and call_node.args:
            parsed.objective = ObjectiveSpec(
                sense="minimize",
                expression=ast.unparse(call_node.args[0]),
            )

    @staticmethod
    def _collect_objective_binding(node: ast.AST, parsed: ParsedOptDSLModel) -> None:
        if parsed.objective is None or parsed.objective_function is not None:
            return

        objective_name = parsed.objective.expression
        if not isinstance(objective_name, str):
            return

        value_node: ast.AST | None = None
        target_name: str | None = None

        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value_node = node.value

        if target_name != objective_name or not isinstance(value_node, ast.Call):
            return

        if isinstance(value_node.func, ast.Name):
            parsed.objective_function = value_node.func.id

    @staticmethod
    def _safe_eval_or_unparse(node: ast.AST) -> Any:
        try:
            return ast.literal_eval(node)
        except (SyntaxError, ValueError):
            return ast.unparse(node)


def _dsl_make_list(length: Any) -> list[Any]:
    try:
        n = int(length)
    except (TypeError, ValueError):
        n = 0
    if n < 0:
        n = 0
    return [0 for _ in range(n)]


class _ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


def _make_compiled_callable(fn_ast: ast.FunctionDef, constants: dict[str, Any]) -> Any:
    """Compile DSL function to native Python bytecode at parse time.

    Generates Python source from the AST, wraps it with runtime guards,
    and compiles to a real function. Falls back to interpreter on failure.
    """
    arg_names = [arg.arg for arg in fn_ast.args.args]
    arg_list = ", ".join(arg_names)

    # Generate Python source from AST with proper indentation
    body_source = ""
    for stmt in fn_ast.body:
        unparsed = ast.unparse(stmt)
        # Indent all lines in this statement by one level (4 spaces)
        if unparsed:
            indented = "\n".join("    " + line for line in unparsed.split("\n"))
            body_source += indented + "\n"

    # Build function with native builtins and proper DSList/DSInt handling
    wrapper = f"""def {fn_ast.name}({arg_list}):
{body_source}"""

    # Build namespace with constants and native builtins
    namespace: dict[str, Any] = {
        "range": range,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "len": len,
        "int": int,
        "float": float,
        "list": list,
        "tuple": tuple,
        "dict": dict,
        "set": set,
        "any": any,
        "all": all,
        "sorted": sorted,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "DSInt": lambda *a, **k: int if not a else a[0],
        "DSList": lambda length, *a, **k: [0] * int(length),
        "__builtins__": {
            "range": range,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "len": len,
            "int": int,
            "float": float,
            "list": list,
            "tuple": tuple,
            "dict": dict,
            "set": set,
            "any": any,
            "all": all,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "True": True,
            "False": False,
            "None": None,
            "AssertionError": AssertionError,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "IndexError": IndexError,
            "KeyError": KeyError,
        },
    }
    namespace.update(constants)

    try:
        code = compile(wrapper, f"<dsl:{fn_ast.name}>", "exec")
        exec(code, namespace)
        return namespace[fn_ast.name]
    except Exception:
        # Fall back to interpreter if compilation fails
        return _make_ast_callable_interpreter(fn_ast, constants)


def _make_ast_callable_interpreter(fn_ast: ast.FunctionDef, constants: dict[str, Any]):
    """Original AST interpreter-based callable (kept for comparison)."""
    arg_names = [arg.arg for arg in fn_ast.args.args]

    def _callable(*args: Any) -> Any:
        if len(args) != len(arg_names):
            raise TypeError(f"{fn_ast.name} expects {len(arg_names)} argument(s), got {len(args)}")

        env: dict[str, Any] = {
            "range": range,
            "sum": sum,
            "DSInt": lambda *a, **k: int,
            "DSList": lambda *a, **k: list,
        }
        env.update(constants)
        for name, value in zip(arg_names, args):
            env[name] = value

        try:
            _exec_block(fn_ast.body, env)
        except _ReturnSignal as ret:
            return ret.value
        return None

    return _callable


# Alias: default to compiled version
_make_ast_callable = _make_compiled_callable


def _exec_block(statements: list[ast.stmt], env: dict[str, Any]) -> None:
    for statement in statements:
        _exec_stmt(statement, env)


def _exec_stmt(statement: ast.stmt, env: dict[str, Any]) -> None:
    if isinstance(statement, ast.Assign):
        value = _eval_expr(statement.value, env)
        for target in statement.targets:
            _assign_target(target, value, env)
        return

    if isinstance(statement, ast.AnnAssign):
        if statement.value is not None:
            value = _eval_expr(statement.value, env)
        else:
            value = _default_from_annotation(statement.annotation, env)
        _assign_target(statement.target, value, env)
        return

    if isinstance(statement, ast.For):
        iter_value = _eval_expr(statement.iter, env)
        for loop_value in iter_value:
            _assign_target(statement.target, loop_value, env)
            _exec_block(statement.body, env)
        return

    if isinstance(statement, ast.If):
        if _truthy(_eval_expr(statement.test, env)):
            _exec_block(statement.body, env)
        else:
            _exec_block(statement.orelse, env)
        return

    if isinstance(statement, ast.Assert):
        if not _truthy(_eval_expr(statement.test, env)):
            raise AssertionError("DSL assert failed")
        return

    if isinstance(statement, ast.Return):
        return_value = _eval_expr(statement.value, env) if statement.value is not None else None
        raise _ReturnSignal(return_value)

    if isinstance(statement, ast.Expr):
        _eval_expr(statement.value, env)
        return

    raise NotImplementedError(f"Unsupported DSL statement: {type(statement).__name__}")


def _assign_target(target: ast.expr, value: Any, env: dict[str, Any]) -> None:
    if isinstance(target, ast.Name):
        env[target.id] = value
        return

    if isinstance(target, ast.Subscript):
        container = _eval_expr(target.value, env)
        index = _eval_expr(target.slice, env)
        container[index] = value
        return

    raise NotImplementedError(f"Unsupported assignment target: {type(target).__name__}")


def _default_from_annotation(annotation: ast.expr, env: dict[str, Any]) -> Any:
    if isinstance(annotation, ast.Call) and isinstance(annotation.func, ast.Name) and annotation.func.id == "DSList":
        length_expr = annotation.args[0] if annotation.args else ast.Constant(value=0)
        length = _eval_expr(length_expr, env)
        return _dsl_make_list(length)
    return 0


def _eval_expr(expr: ast.expr, env: dict[str, Any]) -> Any:
    if isinstance(expr, ast.Constant):
        return expr.value

    if isinstance(expr, ast.Name):
        return env[expr.id]

    if isinstance(expr, ast.List):
        return [_eval_expr(element, env) for element in expr.elts]

    if isinstance(expr, ast.Tuple):
        return tuple(_eval_expr(element, env) for element in expr.elts)

    if isinstance(expr, ast.Subscript):
        container = _eval_expr(expr.value, env)
        index = _eval_expr(expr.slice, env)
        return container[index]

    if isinstance(expr, ast.BinOp):
        left = _eval_expr(expr.left, env)
        right = _eval_expr(expr.right, env)
        if isinstance(expr.op, ast.Add):
            return left + right
        if isinstance(expr.op, ast.Sub):
            return left - right
        if isinstance(expr.op, ast.Mult):
            return left * right
        if isinstance(expr.op, ast.Div):
            return left / right
        raise NotImplementedError(f"Unsupported binary operator: {type(expr.op).__name__}")

    if isinstance(expr, ast.UnaryOp):
        value = _eval_expr(expr.operand, env)
        if isinstance(expr.op, ast.USub):
            return -value
        if isinstance(expr.op, ast.UAdd):
            return +value
        if isinstance(expr.op, ast.Not):
            return not _truthy(value)
        raise NotImplementedError(f"Unsupported unary operator: {type(expr.op).__name__}")

    if isinstance(expr, ast.Compare):
        left = _eval_expr(expr.left, env)
        for operator, comparator in zip(expr.ops, expr.comparators):
            right = _eval_expr(comparator, env)
            if isinstance(operator, ast.Eq):
                ok = left == right
            elif isinstance(operator, ast.NotEq):
                ok = left != right
            elif isinstance(operator, ast.Lt):
                ok = left < right
            elif isinstance(operator, ast.LtE):
                ok = left <= right
            elif isinstance(operator, ast.Gt):
                ok = left > right
            elif isinstance(operator, ast.GtE):
                ok = left >= right
            else:
                raise NotImplementedError(f"Unsupported compare operator: {type(operator).__name__}")
            if not ok:
                return False
            left = right
        return True

    if isinstance(expr, ast.BoolOp):
        if isinstance(expr.op, ast.And):
            return all(_truthy(_eval_expr(value, env)) for value in expr.values)
        if isinstance(expr.op, ast.Or):
            return any(_truthy(_eval_expr(value, env)) for value in expr.values)
        raise NotImplementedError(f"Unsupported boolean operator: {type(expr.op).__name__}")

    if isinstance(expr, ast.Call):
        if isinstance(expr.func, ast.Name):
            func_name = expr.func.id
            args = [_eval_expr(arg, env) for arg in expr.args]
            if func_name == "range":
                return range(*args)
            if func_name == "sum":
                return sum(*args)
            if func_name == "int":
                return int(*args)
            if func_name in env and callable(env[func_name]):
                return env[func_name](*args)
        raise NotImplementedError("Unsupported function call in DSL expression")

    raise NotImplementedError(f"Unsupported DSL expression: {type(expr).__name__}")


def _truthy(value: Any) -> bool:
    return bool(value)
