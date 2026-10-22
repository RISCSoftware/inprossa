"""Shared record type and expression evaluation utilities for OptDSL "pipeline" models.

``DSRecord`` mirrors OptDSL record semantics (dict with attribute access) so the
same runtime values work both as MiniZinc-style ``.field`` access inside
compiled DSL functions and as plain dict-like decision-variable storage in the
LNS assignment structures.

``eval_dsl_expr`` evaluates the restricted subset of Python expression syntax
used by OptDSL model top-level statements (module-level data flow between
``def``-declared "machines"), which the isolated per-function evaluator in
``lns.py`` does not execute.
"""

from __future__ import annotations

import ast
from typing import Any, Callable


class DSRecord(dict):
    """A dict that also supports attribute access (OptDSL record semantics)."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def make_record_constructor(type_name: str, field_order: list[str]) -> Callable[..., "DSRecord"]:
    """Build a callable mimicking a record type constructor (positional or keyword args).

    Used to bind bare record type names (e.g. ``Board``, ``Interval``) inside
    compiled DSL functions, both for the rare in-function constructor call and
    so the name is defined when it appears in (eagerly evaluated) type
    annotations like ``aux_piece : Piece = ...``.
    """

    def _construct(*args: Any, **kwargs: Any) -> DSRecord:
        values: dict[str, Any] = {}
        for i, value in enumerate(args):
            if i >= len(field_order):
                raise TypeError(f"{type_name}() takes at most {len(field_order)} positional arguments")
            values[field_order[i]] = value
        values.update(kwargs)
        return DSRecord(values)

    _construct.__name__ = type_name
    return _construct


class DictLiteralToRecordTransformer(ast.NodeTransformer):
    """Rewrite ``{"field": value, ...}`` dict literals into ``_dsrecord_literal(...)`` calls.

    OptDSL record construction is written as a plain dict literal (mirroring
    the MiniZinc record syntax); executing it as native Python would produce
    a plain ``dict`` that doesn't support the ``.field`` attribute access used
    elsewhere in the same model. Only literals with simple string keys are
    rewritten (any other dict literal is left untouched).
    """

    def visit_Dict(self, node: ast.Dict) -> ast.AST:
        self.generic_visit(node)
        keywords: list[ast.keyword] = []
        for key_node, value_node in zip(node.keys, node.values):
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                return node
            keywords.append(ast.keyword(arg=key_node.value, value=value_node))
        call = ast.Call(func=ast.Name(id="_dsrecord_literal", ctx=ast.Load()), args=[], keywords=keywords)
        return ast.copy_location(call, node)


def eval_dsl_expr(
    node: ast.expr,
    env: dict[str, Any],
    record_types: dict[str, dict[str, ast.expr]] | None = None,
) -> Any:
    """Evaluate a restricted DSL expression against a runtime environment.

    Supports the subset of Python expression syntax used by OptDSL model
    top-level statements: names, literals, lists/tuples, dict-literal record
    construction, arithmetic, attribute/subscript access, and record
    constructor / a small set of builtin function calls.
    """
    record_types = record_types or {}

    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise KeyError(node.id)
    if isinstance(node, ast.List):
        return [eval_dsl_expr(elt, env, record_types) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(eval_dsl_expr(elt, env, record_types) for elt in node.elts)
    if isinstance(node, ast.Dict):
        values: dict[Any, Any] = {}
        for key_node, value_node in zip(node.keys, node.values):
            key = eval_dsl_expr(key_node, env, record_types) if key_node is not None else None
            values[key] = eval_dsl_expr(value_node, env, record_types)
        return DSRecord(values)
    if isinstance(node, ast.UnaryOp):
        value = eval_dsl_expr(node.operand, env, record_types)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.Not):
            return not value
        raise NotImplementedError(type(node.op).__name__)
    if isinstance(node, ast.BinOp):
        left = eval_dsl_expr(node.left, env, record_types)
        right = eval_dsl_expr(node.right, env, record_types)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left ** right
        raise NotImplementedError(type(node.op).__name__)
    if isinstance(node, ast.Attribute):
        base = eval_dsl_expr(node.value, env, record_types)
        if isinstance(base, dict):
            return base[node.attr]
        return getattr(base, node.attr)
    if isinstance(node, ast.Subscript):
        base = eval_dsl_expr(node.value, env, record_types)
        index_node = node.slice
        if isinstance(index_node, ast.Slice):
            raise NotImplementedError("slice subscripts are not supported")
        index = eval_dsl_expr(index_node, env, record_types)
        return base[index]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        if func_name in record_types:
            field_order = list(record_types[func_name].keys())
            values = {}
            for i, arg in enumerate(node.args):
                values[field_order[i]] = eval_dsl_expr(arg, env, record_types)
            for kw in node.keywords:
                if kw.arg is not None:
                    values[kw.arg] = eval_dsl_expr(kw.value, env, record_types)
            return DSRecord(values)
        simple_funcs: dict[str, Callable[..., Any]] = {
            "sum": sum, "len": len, "abs": abs, "int": int, "min": min,
            "max": max, "float": float, "list": list, "tuple": tuple, "range": range,
        }
        if func_name in simple_funcs:
            args = [eval_dsl_expr(arg, env, record_types) for arg in node.args]
            return simple_funcs[func_name](*args)
        raise NotImplementedError(f"Unsupported call in DSL expression: {func_name}")
    raise NotImplementedError(f"Unsupported DSL expression node: {type(node).__name__}")
