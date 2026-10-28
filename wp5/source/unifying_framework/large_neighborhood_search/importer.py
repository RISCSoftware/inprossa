from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._expr_eval import DSRecord, DictLiteralToRecordTransformer, eval_dsl_expr, make_record_constructor


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
    # name -> {field_name: annotation_ast} for `Name = DSRecord({...})` type aliases.
    record_types: dict[str, dict[str, ast.expr]] = field(default_factory=dict)
    # True when the module has module-level data flow between `def` "machines"
    # (e.g. `x = some_machine(y, z)`), requiring pipeline execution instead of
    # the isolated per-function constraint evaluation.
    is_pipeline_model: bool = False


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
            self._collect_record_type(node, parsed)
            self._collect_constant(node, parsed)
            self._collect_constraint(node, parsed)
            self._collect_objective(node, parsed)
            self._collect_objective_binding(node, parsed)

        # Objective assignment can appear before minimize(...).
        # Resolve once more after objective extraction to be order-independent.
        self._resolve_objective_binding(tree, parsed)

        # Resolve derived constants (stored as unparse strings) into concrete
        # numeric values so compiled DSL functions can use them as loop bounds
        # and array lengths (e.g. `MAX_N_LAYERS = N_BOARDS * 2`).
        self._resolve_constants(parsed)

        # Resolve record-valued constants (e.g. `GIVEN_INITIAL_BOARDS = [Board(...), ...]`)
        # which `ast.literal_eval` cannot handle (constructor calls, not literals).
        self._resolve_record_constants(parsed)

        self._detect_pipeline_model(tree, parsed)

        parsed.runtime_constraints = self._build_runtime_constraints(parsed)

        return parsed

    @staticmethod
    def _collect_record_type(node: ast.AST, parsed: ParsedOptDSLModel) -> None:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return
        value = node.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "DSRecord":
            return
        if not value.args or not isinstance(value.args[0], ast.Dict):
            return
        fields: dict[str, ast.expr] = {}
        for key_node, field_annotation in zip(value.args[0].keys, value.args[0].values):
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                continue
            fields[key_node.value] = field_annotation
        parsed.record_types[node.targets[0].id] = fields

    @staticmethod
    def _resolve_record_constants(parsed: ParsedOptDSLModel) -> None:
        if not parsed.record_types:
            return
        for _ in range(3):
            changed = False
            for key, value in list(parsed.constants.items()):
                if not isinstance(value, str):
                    continue
                try:
                    expr = ast.parse(value, mode="eval").body
                    evaluated = eval_dsl_expr(expr, parsed.constants, parsed.record_types)
                except (SyntaxError, ValueError, TypeError, KeyError, NotImplementedError, IndexError, ZeroDivisionError):
                    continue
                parsed.constants[key] = evaluated
                changed = True
            if not changed:
                break

    @staticmethod
    def _detect_pipeline_model(tree: ast.Module, parsed: ParsedOptDSLModel) -> None:
        """Detect genuine module-level data flow between `def` "machines".

        Only a plain ``Assign`` (e.g. ``x = some_machine(y, z)`` or
        ``a, b = some_machine(y, z)``) counts — this is the pattern that the
        isolated per-function evaluator cannot handle (call arguments don't
        match the callee's parameter names). A bare ``Expr(Call(...))``
        constraint-check statement (e.g. ``cutting_constraints(cut_positions)``)
        does NOT imply a pipeline: that's exactly the "isolated" style already
        supported by matching parameter names directly against decision
        variables, used by every existing non-pipeline model.
        """
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            call_node = node.value
            if not isinstance(call_node.func, ast.Name):
                continue
            if call_node.func.id in parsed.constraints:
                parsed.is_pipeline_model = True
                return

    @staticmethod
    def _resolve_constants(parsed: ParsedOptDSLModel) -> None:
        constants = parsed.constants
        changed = True
        iterations = 0
        max_iterations = max(1, len(constants) * 3)
        while changed and iterations < max_iterations:
            changed = _resolve_constants_pass(constants)
            iterations += 1

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
            runtime_constraints[name] = _make_ast_callable(fn_ast, parsed.constants, parsed.record_types)
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


def _resolve_expr(expr: ast.AST, constants: dict[str, Any]) -> Any:
    """Evaluate a constant expression against the (partially) resolved constants.

    Used to turn derived constants stored as strings (e.g. ``MAX_N_LAYERS``
    resolved as ``'N_BOARDS * 2'``) into concrete numeric values before they
    are injected into the namespace of compiled DSL functions.
    """
    if isinstance(expr, ast.Constant):
        return expr.value
    if isinstance(expr, ast.Name):
        value = constants.get(expr.id)
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return _resolve_expr(ast.parse(value, mode="eval").body, constants)
            except (SyntaxError, ValueError, TypeError):
                return expr  # cannot resolve yet
        return expr
    if isinstance(expr, ast.List):
        elements = [_resolve_expr(elt, constants) for elt in expr.elts]
        if any(isinstance(elt, ast.AST) for elt in elements):
            # An element could not be resolved (e.g. a record constructor call
            # like `Board(...)`) — leave the whole list unresolved so the
            # record-aware constant resolver can handle it afterwards instead
            # of accepting a list that still contains raw AST nodes.
            return expr
        return elements
    if isinstance(expr, ast.Tuple):
        elements = [_resolve_expr(elt, constants) for elt in expr.elts]
        if any(isinstance(elt, ast.AST) for elt in elements):
            return expr
        return tuple(elements)
    if isinstance(expr, ast.BinOp):
        left = _resolve_expr(expr.left, constants)
        right = _resolve_expr(expr.right, constants)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            if isinstance(expr.op, ast.Add):
                return left + right
            if isinstance(expr.op, ast.Sub):
                return left - right
            if isinstance(expr.op, ast.Mult):
                return left * right
            if isinstance(expr.op, ast.Div):
                return left / right
            if isinstance(expr.op, ast.FloorDiv):
                return int(left // right)
            if isinstance(expr.op, ast.Mod):
                return left % right
        return expr
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
        operand = _resolve_expr(expr.operand, constants)
        if isinstance(operand, (int, float)):
            return -operand
        return expr
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
        func = constants.get(expr.func.id)
        if func in (sum, len, abs, int, min, max):
            args = [_resolve_expr(arg, constants) for arg in expr.args]
            try:
                return func(*args)
            except (TypeError, ValueError):
                return expr
        return expr
    return expr


def _resolve_constants_pass(constants: dict[str, Any]) -> bool:
    """One resolution pass over string-valued constants; returns whether any changed."""
    changed = False
    for key, value in list(constants.items()):
        if not isinstance(value, str):
            continue
        try:
            expr = ast.parse(value, mode="eval")
            evaluated = _resolve_expr(expr.body, constants)
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError):
            continue
        # Only accept concrete primitive results (numbers, lists, tuples).
        # An unresolved AST node means the constant is not yet resolvable.
        if isinstance(evaluated, (int, float, list, tuple, bool)):
            constants[key] = evaluated
            changed = True
    return changed


def _make_compiled_callable(
    fn_ast: ast.FunctionDef,
    constants: dict[str, Any],
    record_types: dict[str, dict[str, ast.expr]] | None = None,
) -> Any:
    """Compile a DSL function to native Python bytecode at parse time.

    Reconstructs Python source from the AST and compiles it to a real
    function. This is the single execution path for DSL functions (they are
    resolved through the ``_make_ast_callable`` alias below).

    Every DSL function-local must be initialized with a value (e.g.
    ``x: DSList(N, DSInt(...)) = [0] * N``); a bare annotation with no value
    raises ``UnboundLocalError`` when indexed.

    ``record_types`` (name -> {field: annotation}) are DSL ``DSRecord`` type
    aliases: dict-literal record construction (``{"field": value, ...}``) is
    rewritten to build a ``DSRecord`` (dict subclass supporting ``.field``
    attribute access) instead of a plain ``dict``, and each record type name
    is bound in the exec namespace (both for rare in-body constructor calls
    and because bare annotations like ``x : Piece = ...`` are eagerly
    evaluated by Python at exec time).
    """
    record_types = record_types or {}
    arg_names = [arg.arg for arg in fn_ast.args.args]
    arg_list = ", ".join(arg_names)

    # Generate Python source from AST with proper indentation. Operate on a
    # copy so the shared parsed AST (reused elsewhere, e.g. arg introspection)
    # is not mutated by the dict-literal-to-record rewrite.
    transformed_body = [DictLiteralToRecordTransformer().visit(copy.deepcopy(stmt)) for stmt in fn_ast.body]
    for stmt in transformed_body:
        ast.fix_missing_locations(stmt)

    body_source = ""
    for stmt in transformed_body:
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
        "bool": bool,
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
        "_dsrecord_literal": DSRecord,
        "__builtins__": {
            "range": range,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "len": len,
            "int": int,
            "float": float,
            "bool": bool,
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
    for type_name, fields in record_types.items():
        namespace[type_name] = make_record_constructor(type_name, list(fields.keys()))
    namespace.update(constants)

    code = compile(wrapper, f"<dsl:{fn_ast.name}>", "exec")
    exec(code, namespace)
    return namespace[fn_ast.name]


# DSL functions are compiled to native Python; there is no interpreter fallback.
_make_ast_callable = _make_compiled_callable
