"""Symbol table and structural model for an OptDSL module.

OptDSL is syntactically Python, so there is no grammar to parse: the model is
derived from ``ast`` alone. This module produces a :class:`ModuleIndex` that
every other tool (diagnostics, completion, hover, code lens, the synthesis
harness) reads from.

The decision-variable extraction deliberately delegates to
``large_neighborhood_search.problem_reader`` so the editor's view of "what is a
decision variable" can never drift from the runtime's view. That equivalence is
asserted by ``test/test_tooling.py``.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from large_neighborhood_search.problem_reader import (
    IntDomain,
    VariableDomain,
    VariableSpec,
    _collect_decision_indices,
    _collect_variables,
    _resolve_constants,
)
from large_neighborhood_search.importer import OptDSLImporter

from .positions import PositionMapper, Span

#: Names that OptDSL source may reference without declaring them.
BUILTIN_NAMES: frozenset[str] = frozenset(
    {
        "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
        "int", "len", "list", "map", "max", "min", "range", "set", "sorted",
        "sum", "tuple", "zip",
        # OptDSL type constructors.
        "DSInt", "DSFloat", "DSBool", "DSList", "DSRecord",
        # Objective markers.
        "minimize", "maximize",
        # Warm-start decorator.
        "warm_start",
        # Python literals that appear as Name nodes in some contexts.
        "True", "False", "None",
    }
)


@dataclass
class ConstantSymbol:
    """A module-level ``UPPER_CASE`` constant."""

    name: str
    value: Any
    raw_code: str
    span: Span
    annotation_code: str | None = None
    resolved: bool = True


@dataclass
class TypeAliasSymbol:
    """A ``Name = DSRecord({...})`` type alias."""

    name: str
    fields: dict[str, str]
    span: Span


@dataclass
class VariableSymbol:
    """A module-level variable, decision or derived."""

    name: str
    annotation_code: str | None
    value_code: str | None
    span: Span
    domain: VariableDomain | None = None
    is_decision: bool = False
    decision_count: int = 0

    @property
    def kind(self) -> str:
        if self.is_decision:
            return "decision"
        if self.value_code is not None:
            return "derived"
        return "declared"


@dataclass
class ParameterSymbol:
    """A predicate parameter."""

    name: str
    annotation_code: str | None
    span: Span


@dataclass
class PredicateSymbol:
    """A top-level ``def`` — a constraint predicate or a warm-start function."""

    name: str
    parameters: list[ParameterSymbol]
    span: Span
    name_span: Span
    has_assert: bool = False
    is_warm_start: bool = False
    return_names: list[str] = field(default_factory=list)
    invoked_at_top_level: bool = False
    used_as_objective: bool = False


@dataclass
class ObjectiveSymbol:
    """The ``minimize(...)`` / ``maximize(...)`` call."""

    sense: str
    expression: str
    span: Span
    variable_name: str | None = None
    function_name: str | None = None


@dataclass
class DecisionSymbol:
    """One flattened decision index, mirroring ``DecisionIndexSpec``."""

    variable_name: str
    index: int | tuple | None
    domain: IntDomain
    span: Span

    @property
    def cardinality(self) -> int | None:
        if self.domain.lower is None or self.domain.upper is None:
            return None
        return self.domain.upper - self.domain.lower + 1


@dataclass
class ModuleIndex:
    """Everything the tooling knows about one OptDSL module."""

    source: str
    mapper: PositionMapper
    tree: ast.Module | None = None
    syntax_error: SyntaxError | None = None
    constants: dict[str, ConstantSymbol] = field(default_factory=dict)
    type_aliases: dict[str, TypeAliasSymbol] = field(default_factory=dict)
    variables: dict[str, VariableSymbol] = field(default_factory=dict)
    predicates: dict[str, PredicateSymbol] = field(default_factory=dict)
    objective: ObjectiveSymbol | None = None
    objectives: list[ObjectiveSymbol] = field(default_factory=list)
    decisions: list[DecisionSymbol] = field(default_factory=list)
    warm_start_hints: dict[str, Span] = field(default_factory=dict)
    warm_start_bounds: dict[str, Any] = field(default_factory=dict)
    is_pipeline_model: bool = False

    # -- convenience -----------------------------------------------------

    @property
    def decision_variables(self) -> dict[str, VariableSymbol]:
        return {name: var for name, var in self.variables.items() if var.is_decision}

    @property
    def decision_count(self) -> int:
        return len(self.decisions)

    def decisions_for(self, variable_name: str) -> list[DecisionSymbol]:
        return [d for d in self.decisions if d.variable_name == variable_name]

    def span_of(self, node: ast.AST) -> Span:
        return self.mapper.span(node)

    def symbol_at(self, line: int, character: int) -> str | None:
        """Return the identifier under an LSP position, if any.

        Used by hover/definition. Works on the raw line text rather than the
        AST so it also resolves names inside expressions.
        """
        text = self.mapper.line_text(line)
        if not text:
            return None
        start = min(character, len(text))
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
            start -= 1
        end = min(character, len(text))
        while end < len(text) and (text[end].isalnum() or text[end] == "_"):
            end += 1
        candidate = text[start:end]
        return candidate or None


def analyze(source: str) -> ModuleIndex:
    """Build a :class:`ModuleIndex` from OptDSL source.

    Never raises on malformed input: a ``SyntaxError`` is captured on the index
    so the language server can turn it into a diagnostic.
    """
    mapper = PositionMapper(source)
    index = ModuleIndex(source=source, mapper=mapper)

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        index.syntax_error = exc
        return index

    index.tree = tree

    # Reuse the runtime importer for constants/record types/objective so the
    # editor and the solver agree. ``compile_runtime=False`` is essential: the
    # buffer may be untrusted or mid-edit and must never be executed.
    parsed = OptDSLImporter().from_code(source, compile_runtime=False)
    resolved_constants = _resolve_constants(parsed.constants)

    _collect_constants(index, tree, parsed, resolved_constants)
    _collect_type_aliases(index, parsed)
    _collect_variable_symbols(index, tree, parsed, resolved_constants)
    _collect_predicates(index, tree, parsed)
    _collect_objectives(index, tree, parsed)
    _collect_warm_start(index, tree)
    _collect_decisions(index, tree, parsed, resolved_constants)

    index.is_pipeline_model = parsed.is_pipeline_model
    return index


def analyze_file(path: str | Path) -> ModuleIndex:
    return analyze(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# collectors
# ---------------------------------------------------------------------------


def _collect_constants(
    index: ModuleIndex,
    tree: ast.Module,
    parsed: Any,
    resolved: dict[str, Any],
) -> None:
    for node in tree.body:
        name: str | None = None
        value_node: ast.expr | None = None
        annotation: str | None = None

        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            value_node = node.value
            annotation = ast.unparse(node.annotation) if node.annotation is not None else None
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            value_node = node.value

        if name is None or not name.isupper() or value_node is None:
            continue

        value = resolved.get(name, parsed.constants.get(name))
        index.constants[name] = ConstantSymbol(
            name=name,
            value=value,
            raw_code=ast.unparse(value_node),
            span=index.span_of(node),
            annotation_code=annotation,
            resolved=not isinstance(value, str),
        )


def _collect_type_aliases(index: ModuleIndex, parsed: Any) -> None:
    if index.tree is None:
        return
    for node in index.tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in parsed.record_types:
            continue
        fields = {
            field_name: ast.unparse(annotation)
            for field_name, annotation in parsed.record_types[target.id].items()
        }
        index.type_aliases[target.id] = TypeAliasSymbol(
            name=target.id,
            fields=fields,
            span=index.span_of(node),
        )


def _collect_variable_symbols(
    index: ModuleIndex,
    tree: ast.Module,
    parsed: Any,
    resolved: dict[str, Any],
) -> None:
    # Delegate to the runtime collector so "is this a decision variable?" has
    # exactly one answer in the codebase.
    specs: dict[str, VariableSpec] = _collect_variables(tree, resolved, parsed.record_types)

    for name, spec in specs.items():
        index.variables[name] = VariableSymbol(
            name=name,
            annotation_code=spec.annotation_code,
            value_code=spec.value_code,
            span=index.span_of(spec.ast_node),
            domain=spec.domain,
            is_decision=spec.domain is not None,
        )


def _collect_predicates(index: ModuleIndex, tree: ast.Module, parsed: Any) -> None:
    invoked: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                invoked.add(node.value.func.id)
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                invoked.add(node.value.func.id)

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue

        parameters = [
            ParameterSymbol(
                name=arg.arg,
                annotation_code=ast.unparse(arg.annotation) if arg.annotation is not None else None,
                span=index.span_of(arg),
            )
            for arg in node.args.args
        ]

        has_assert = any(isinstance(child, ast.Assert) for child in ast.walk(node))
        is_warm_start = any(_decorator_name(d) == "warm_start" for d in node.decorator_list)

        index.predicates[node.name] = PredicateSymbol(
            name=node.name,
            parameters=parameters,
            span=index.span_of(node),
            name_span=index.span_of(node),
            has_assert=has_assert,
            is_warm_start=is_warm_start,
            return_names=_return_names(node),
            invoked_at_top_level=node.name in invoked,
            used_as_objective=parsed.objective_function == node.name,
        )


def _decorator_name(decorator: ast.expr) -> str | None:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
        return decorator.func.id
    return None


def _return_names(node: ast.FunctionDef) -> list[str]:
    """Mirror ``Predicate._extract_return_names``: only ``return name`` / ``return (a, b)``."""
    for child in node.body:
        if not isinstance(child, ast.Return) or child.value is None:
            continue
        if isinstance(child.value, ast.Name):
            return [child.value.id]
        if isinstance(child.value, ast.Tuple):
            return [elt.id for elt in child.value.elts if isinstance(elt, ast.Name)]
    return []


def _collect_objectives(index: ModuleIndex, tree: ast.Module, parsed: Any) -> None:
    for node in tree.body:
        call: ast.Call | None = None
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
        if call is None or not isinstance(call.func, ast.Name):
            continue
        if call.func.id not in ("minimize", "maximize") or not call.args:
            continue

        expression = ast.unparse(call.args[0])
        index.objectives.append(
            ObjectiveSymbol(
                sense=call.func.id,
                expression=expression,
                span=index.span_of(node),
                variable_name=expression if expression.isidentifier() else None,
                function_name=parsed.objective_function,
            )
        )

    if index.objectives:
        index.objective = index.objectives[0]


def _collect_warm_start(index: ModuleIndex, tree: ast.Module) -> None:
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(_decorator_name(d) == "warm_start" for d in node.decorator_list):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            for keyword in decorator.keywords:
                if keyword.arg in ("lower_bound", "upper_bound"):
                    try:
                        index.warm_start_bounds[keyword.arg] = ast.literal_eval(keyword.value)
                    except (ValueError, SyntaxError):
                        index.warm_start_bounds[keyword.arg] = ast.unparse(keyword.value)

        for child in node.body:
            if not isinstance(child, ast.Return) or not isinstance(child.value, ast.Dict):
                continue
            for key_node in child.value.keys:
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                    index.warm_start_hints[key_node.value] = index.span_of(key_node)


def _collect_decisions(
    index: ModuleIndex,
    tree: ast.Module,
    parsed: Any,
    resolved: dict[str, Any],
) -> None:
    specs = _collect_variables(tree, resolved, parsed.record_types)
    for spec in _collect_decision_indices(specs):
        variable = index.variables.get(spec.variable_name)
        span = variable.span if variable is not None else Span(0, 0, 0, 0)
        index.decisions.append(
            DecisionSymbol(
                variable_name=spec.variable_name,
                index=spec.index,
                domain=spec.domain,
                span=span,
            )
        )

    for decision in index.decisions:
        variable = index.variables.get(decision.variable_name)
        if variable is not None:
            variable.decision_count += 1
