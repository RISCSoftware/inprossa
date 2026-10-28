"""Diagnostics for OptDSL modules.

Every rule here is *static*: it reads the :class:`~optdsl_tooling.analysis.ModuleIndex`
and never executes the source. Rules are grouped by the failure mode they
prevent, because OptDSL's failure modes are unusually quiet:

* The MiniZinc translator raises on unsupported constructs, but only when you
  run it.
* The LNS importer silently treats an unrecognised annotation as "not a
  decision variable", so a typo turns a decision into a constant.
* The evaluator silently *skips* a constraint whose parameter names do not
  match variable names, so a mis-wired constraint never fires.

The last two are the reason this module exists: they produce a solver that runs
happily and returns a wrong answer.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Iterable

from .analysis import BUILTIN_NAMES, ModuleIndex
from .positions import Span


class Severity(IntEnum):
    """Mirrors ``lsprotocol.types.DiagnosticSeverity``."""

    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


@dataclass
class Diagnostic:
    code: str
    message: str
    span: Span
    severity: Severity = Severity.ERROR
    related: list[tuple[Span, str]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


#: ``DS*`` constructor arities: name -> (min_args, max_args).
_DS_ARITY: dict[str, tuple[int, int]] = {
    "DSInt": (0, 2),
    "DSFloat": (0, 2),
    "DSBool": (0, 0),
    "DSList": (2, 2),
    "DSRecord": (1, 1),
}


def check(index: ModuleIndex) -> list[Diagnostic]:
    """Run every rule and return the diagnostics, sorted by position."""
    if index.syntax_error is not None:
        return [_syntax_diagnostic(index)]

    diagnostics: list[Diagnostic] = []
    diagnostics += _check_ds_constructors(index)
    diagnostics += _check_unknown_names(index)
    diagnostics += _check_objective(index)
    diagnostics += _check_predicates(index)
    diagnostics += _check_decisions(index)
    diagnostics += _check_constants(index)
    diagnostics += _check_warm_start(index)

    diagnostics.sort(key=lambda d: (d.span.start_line, d.span.start_character, d.code))
    return diagnostics


# ---------------------------------------------------------------------------
# syntax
# ---------------------------------------------------------------------------


def _syntax_diagnostic(index: ModuleIndex) -> Diagnostic:
    exc = index.syntax_error
    assert exc is not None
    line = max(0, (exc.lineno or 1) - 1)
    character = max(0, (exc.offset or 1) - 1)
    return Diagnostic(
        code="syntax-error",
        message=exc.msg or "invalid syntax",
        span=Span(line, character, line, character + 1),
        severity=Severity.ERROR,
    )


# ---------------------------------------------------------------------------
# DS* constructors
# ---------------------------------------------------------------------------


def _check_ds_constructors(index: ModuleIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if index.tree is None:
        return diagnostics

    for node in ast.walk(index.tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name not in _DS_ARITY:
            continue

        minimum, maximum = _DS_ARITY[name]
        # ``DSList(N, elem_type=Piece)`` is a legal keyword form used by the
        # pipeline models, so keyword arguments count towards the arity.
        count = len(node.args) + len(node.keywords)
        if minimum <= count <= maximum:
            continue

        expected = f"{minimum}" if minimum == maximum else f"{minimum}..{maximum}"
        diagnostics.append(
            Diagnostic(
                code="ds-arity",
                message=f"{name}() takes {expected} positional argument(s), got {count}",
                span=index.span_of(node),
                severity=Severity.ERROR,
            )
        )

    return diagnostics


# ---------------------------------------------------------------------------
# unknown names
# ---------------------------------------------------------------------------


def _check_unknown_names(index: ModuleIndex) -> list[Diagnostic]:
    if index.tree is None:
        return []

    module_names = set(index.constants) | set(index.variables) | set(index.predicates) | set(index.type_aliases)
    module_names |= BUILTIN_NAMES

    for node in index.tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module_names.add((alias.asname or alias.name).split(".")[0])

    diagnostics: list[Diagnostic] = []
    for node in index.tree.body:
        if isinstance(node, ast.FunctionDef):
            diagnostics += _check_function_names(index, node, module_names)
        else:
            diagnostics += _check_names_in(index, node, module_names, module_names)

    return diagnostics


def _check_function_names(
    index: ModuleIndex,
    function: ast.FunctionDef,
    module_names: set[str],
) -> list[Diagnostic]:
    local_names: set[str] = {arg.arg for arg in function.args.args}
    local_names |= {arg.arg for arg in function.args.kwonlyargs}
    if function.args.vararg is not None:
        local_names.add(function.args.vararg.arg)
    if function.args.kwarg is not None:
        local_names.add(function.args.kwarg.arg)

    # Collect every binding in the function body, excluding nested scopes.
    for node in _walk_shallow(function.body):
        local_names |= _bound_names(node)

    scope = module_names | local_names
    diagnostics: list[Diagnostic] = []
    for statement in function.body:
        diagnostics += _check_names_in(index, statement, scope, scope)
    return diagnostics


def _walk_shallow(body: Iterable[ast.stmt]) -> Iterable[ast.AST]:
    """Walk statements without descending into nested function/lambda scopes."""
    stack = list(body)
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            stack.append(child)


def _bound_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Assign):
        for target in node.targets:
            names |= _target_names(target)
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        names |= _target_names(node.target)
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        names |= _target_names(node.target)
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        for item in node.items:
            if item.optional_vars is not None:
                names |= _target_names(item.optional_vars)
    elif isinstance(node, ast.ExceptHandler) and node.name:
        names.add(node.name)
    elif isinstance(node, ast.comprehension):
        names |= _target_names(node.target)
    elif isinstance(node, ast.NamedExpr):
        names |= _target_names(node.target)
    return names


def _target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names |= _target_names(element)
        return names
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return set()


def _check_names_in(
    index: ModuleIndex,
    node: ast.AST,
    scope: set[str],
    module_names: set[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Name) or not isinstance(child.ctx, ast.Load):
            continue
        if child.id in scope:
            continue
        diagnostics.append(
            Diagnostic(
                code="unknown-name",
                message=f"'{child.id}' is not defined",
                span=index.span_of(child),
                severity=Severity.ERROR,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# objective
# ---------------------------------------------------------------------------


def _check_objective(index: ModuleIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if not index.objectives:
        diagnostics.append(
            Diagnostic(
                code="missing-objective",
                message="no objective declared; add `minimize(<expr>)` or `maximize(<expr>)`",
                span=Span(0, 0, 0, 0),
                severity=Severity.WARNING,
            )
        )
        return diagnostics

    if len(index.objectives) > 1:
        for extra in index.objectives[1:]:
            diagnostics.append(
                Diagnostic(
                    code="duplicate-objective",
                    message="only the first objective is used; remove this one",
                    span=extra.span,
                    severity=Severity.ERROR,
                    related=[(index.objectives[0].span, "first objective declared here")],
                )
            )

    objective = index.objectives[0]
    if objective.variable_name is not None:
        variable = index.variables.get(objective.variable_name)
        if variable is None:
            diagnostics.append(
                Diagnostic(
                    code="objective-unknown-variable",
                    message=f"objective refers to '{objective.variable_name}', which is not a module-level variable",
                    span=objective.span,
                    severity=Severity.ERROR,
                )
            )
        elif variable.is_decision:
            diagnostics.append(
                Diagnostic(
                    code="objective-is-decision",
                    message=(
                        f"'{objective.variable_name}' is a free decision variable, so the objective is "
                        "unconstrained; bind it to a predicate result instead"
                    ),
                    span=objective.span,
                    severity=Severity.WARNING,
                )
            )

    return diagnostics


# ---------------------------------------------------------------------------
# predicates
# ---------------------------------------------------------------------------


def _check_predicates(index: ModuleIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for predicate in index.predicates.values():
        if predicate.is_warm_start:
            continue

        if not predicate.has_assert and not predicate.return_names:
            diagnostics.append(
                Diagnostic(
                    code="predicate-no-effect",
                    message=(
                        f"'{predicate.name}' contains no `assert` and returns nothing, "
                        "so it constrains nothing"
                    ),
                    span=predicate.span,
                    severity=Severity.WARNING,
                )
            )

        if not predicate.invoked_at_top_level and not predicate.used_as_objective:
            diagnostics.append(
                Diagnostic(
                    code="predicate-unused",
                    message=(
                        f"'{predicate.name}' is never invoked; add a top-level call "
                        f"`{predicate.name}(...)` to enforce it"
                    ),
                    span=predicate.span,
                    severity=Severity.WARNING,
                )
            )

        # In isolated (non-pipeline) mode the evaluator only calls a predicate
        # when every parameter name is also a key in the assignment. A
        # parameter that is not a variable name therefore disables the whole
        # constraint without any error.
        if not index.is_pipeline_model:
            for parameter in predicate.parameters:
                if parameter.name in index.variables or parameter.name in index.constants:
                    continue
                diagnostics.append(
                    Diagnostic(
                        code="predicate-parameter-unbound",
                        message=(
                            f"parameter '{parameter.name}' does not match any variable or constant; "
                            "the LNS evaluator will skip this constraint entirely"
                        ),
                        span=parameter.span,
                        severity=Severity.WARNING,
                    )
                )

    return diagnostics


# ---------------------------------------------------------------------------
# decisions
# ---------------------------------------------------------------------------


def _check_decisions(index: ModuleIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for variable in index.variables.values():
        if not variable.is_decision:
            continue

        domain = variable.domain
        if domain is None:
            continue

        if domain.kind == "int" and domain.int_domain is not None:
            if domain.int_domain.lower is None or domain.int_domain.upper is None:
                diagnostics.append(
                    Diagnostic(
                        code="unbounded-domain",
                        message=(
                            f"'{variable.name}' has no finite domain; the LNS engine cannot sample it. "
                            "Use DSInt(lower, upper)."
                        ),
                        span=variable.span,
                        severity=Severity.ERROR,
                    )
                )
        elif domain.length is None:
            diagnostics.append(
                Diagnostic(
                    code="unknown-length",
                    message=(
                        f"the length of '{variable.name}' is not statically known; "
                        "the LNS engine cannot enumerate its decision indices"
                    ),
                    span=variable.span,
                    severity=Severity.ERROR,
                )
            )

        if variable.decision_count == 0:
            diagnostics.append(
                Diagnostic(
                    code="decision-not-enumerated",
                    message=(
                        f"'{variable.name}' looks like a decision variable but no decision indices "
                        "could be derived from its annotation"
                    ),
                    span=variable.span,
                    severity=Severity.WARNING,
                )
            )

        if not _is_referenced_in_predicates(index, variable.name):
            diagnostics.append(
                Diagnostic(
                    code="decision-unconstrained",
                    message=(
                        f"'{variable.name}' is a decision variable but no constraint references it; "
                        "the search can set it to any value"
                    ),
                    span=variable.span,
                    severity=Severity.WARNING,
                )
            )

    return diagnostics


def _is_referenced_in_predicates(index: ModuleIndex, name: str) -> bool:
    """True if ``name`` is read anywhere outside its own declaration.

    Pipeline models reference decision variables at module level (e.g.
    ``swapped_boards = reordering_board_machine(initial_boards, swapping_decisions_boards)``),
    so scanning only function bodies would produce false positives.
    """
    if index.tree is None:
        return True
    for node in ast.walk(index.tree):
        if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load):
            return True
    return False


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------


def _check_constants(index: ModuleIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if index.tree is None:
        return diagnostics

    usage = _name_usage(index.tree)

    for constant in index.constants.values():
        if not constant.resolved:
            diagnostics.append(
                Diagnostic(
                    code="unresolved-constant",
                    message=(
                        f"'{constant.name}' could not be evaluated statically; "
                        "the LNS engine needs a concrete value for loop bounds and array lengths"
                    ),
                    span=constant.span,
                    severity=Severity.WARNING,
                )
            )

        # One occurrence is the definition itself.
        if usage.get(constant.name, 0) <= 1:
            diagnostics.append(
                Diagnostic(
                    code="unused-constant",
                    message=f"'{constant.name}' is declared but never used",
                    span=constant.span,
                    severity=Severity.HINT,
                )
            )

    return diagnostics


def _name_usage(tree: ast.Module) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            counts[node.id] = counts.get(node.id, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# warm start
# ---------------------------------------------------------------------------


def _check_warm_start(index: ModuleIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for name, span in index.warm_start_hints.items():
        if name in index.variables or name in index.constants:
            continue
        diagnostics.append(
            Diagnostic(
                code="warm-start-unknown-target",
                message=(
                    f"@warm_start hint '{name}' does not match any variable; "
                    "the translator will ignore it"
                ),
                span=span,
                severity=Severity.ERROR,
            )
        )

    lower = index.warm_start_bounds.get("lower_bound")
    upper = index.warm_start_bounds.get("upper_bound")
    if isinstance(lower, (int, float)) and isinstance(upper, (int, float)) and lower > upper:
        diagnostics.append(
            Diagnostic(
                code="warm-start-bounds",
                message=f"lower_bound ({lower}) exceeds upper_bound ({upper})",
                span=Span(0, 0, 0, 0),
                severity=Severity.ERROR,
            )
        )

    return diagnostics
