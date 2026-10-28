"""Prompt construction for operator synthesis.

The prompt is generated from the live codebase rather than hand-written, so it
cannot drift from the actual operator contract. In particular the
``DestroyOperator``/``RepairOperator`` signatures and the available context keys
are read from ``components.py`` and ``lns.py`` at build time.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from large_neighborhood_search.components import DestroyOperator, RepairOperator
from optdsl_tooling.analysis import ModuleIndex
from optdsl_tooling.fingerprint import ProblemFingerprint


@dataclass
class OperatorSpec:
    """What the caller wants the model to produce."""

    kind: str  # "destroy" | "repair"
    problem_class: str
    objective: str
    target_variables: list[str]
    hyperparameters: dict[str, Any]
    invariants: list[str]
    notes: str = ""
    #: Full OptDSL source of the model. The constraint *bodies* are what an
    #: operator has to respect, so the model needs to see them, not just names.
    model_source: str = ""
    #: One line per decision variable describing how its keys look at runtime,
    #: e.g. ``production: 12 keys like ('production', (0, 0)); domain 0..8``.
    decision_layout: list[str] = field(default_factory=list)


SYSTEM_PROMPT = """\
You write neighborhood operators for a large neighborhood search (LNS) engine.

Rules you must follow exactly:

1. Output ONE complete, self-contained Python module and nothing else: the
   import statements it needs, followed by exactly one operator class. No
   prose, no markdown fences. The module is saved to disk and imported as-is,
   so every name it uses (`dataclass`, `__BASE__`, `set_decision_value`, ...)
   must be imported explicitly at the top.
2. The class must subclass __BASE__ and implement `__METHOD__`.
3. Decorate the class with `@dataclass` and declare every hyperparameter as a
   field with a default value.
4. Import only from: __IMPORTS__.
5. Never call `eval`, `exec`, `open`, `__import__`, or touch dunder attributes.
6. Never mutate the input assignment in place and return it — the engine passes
   a clone, but returning a new dict is safer and always accepted.
7. Read randomness from `context.extra["rng"]` (a `random.Random`). Never use
   the global `random` module, or runs stop being reproducible.
8. Read decision metadata from `context.extra`:
   - `decision_keys`: list of `(variable_name, index)` tuples
   - `decision_domains`: `{(variable_name, index): (lower, upper)}`
   - `keys_by_variable`: `{variable_name: [(variable_name, index), ...]}`
   - `problem_data`: the parsed OptDSL problem
9. Use `set_decision_value(assignment, key, None)` to unassign a decision and
   `get_decision_value(assignment, key)` to read one (both from
   `large_neighborhood_search._utils`). Model constants are in
   `context.constants` (a dict by name).
10. Guard against problems the operator does not apply to: if the required
    constants or variables are missing, return the assignment unchanged.

The engine calls `__METHOD__` once per iteration. It must be fast: the budget is
roughly 1 ms per call for instances with a few thousand decisions.

The expected shape of the module (adapt the logic, keep the structure):

__TEMPLATE__
"""


_TEMPLATES: dict[str, str] = {
    "destroy": '''\
from dataclasses import dataclass

from large_neighborhood_search.components import DestroyOperator
from large_neighborhood_search._utils import set_decision_value


@dataclass
class ExampleBlockDestroy(DestroyOperator):
    """Unassign a random contiguous block of decisions."""

    fraction: float = 0.2

    def destroy(self, assignment, context):
        rng = context.extra["rng"]
        keys = list(context.extra["decision_keys"])
        if not keys:
            return assignment
        count = max(1, int(len(keys) * self.fraction))
        start = rng.randrange(len(keys))
        for offset in range(count):
            set_decision_value(assignment, keys[(start + offset) % len(keys)], None)
        return assignment''',
    "repair": '''\
from dataclasses import dataclass

from large_neighborhood_search.components import RepairOperator
from large_neighborhood_search._utils import get_decision_value, set_decision_value


@dataclass
class ExampleLowestValueRepair(RepairOperator):
    """Assign every missing decision its lower bound."""

    def repair(self, partial_assignment, context):
        domains = context.extra["decision_domains"]
        for key in context.extra["decision_keys"]:
            if get_decision_value(partial_assignment, key) is None:
                set_decision_value(partial_assignment, key, domains[key][0])
        return partial_assignment''',
}


#: Keys the engine guarantees in ``context.extra``. Kept in one place so the
#: prompt and ``contract_reference()`` cannot drift apart.
CONTEXT_KEYS: tuple[str, ...] = (
    "problem_data",
    "rng",
    "decision_specs",
    "decision_keys",
    "decision_domains",
    "keys_by_variable",
    "binary_one_probability_by_variable",
    "value_bias",
    "penalty_base",
    "evaluator",
)


def _imports() -> str:
    return (
        "math, random, dataclasses, typing, collections, itertools, heapq, "
        "large_neighborhood_search.components, large_neighborhood_search.models, "
        "large_neighborhood_search._utils, large_neighborhood_search.defaults"
    )


def build_system_prompt(kind: str) -> str:
    base = "DestroyOperator" if kind == "destroy" else "RepairOperator"
    method = "destroy" if kind == "destroy" else "repair"
    # Plain replacement rather than str.format: the prompt contains literal
    # braces (dict/tuple syntax) that would otherwise be parsed as fields.
    return (
        SYSTEM_PROMPT.replace("__TEMPLATE__", _TEMPLATES["destroy" if kind == "destroy" else "repair"])
        .replace("__BASE__", base)
        .replace("__METHOD__", method)
        .replace("__IMPORTS__", _imports())
    )


def build_user_prompt(
    index: ModuleIndex,
    fingerprint: ProblemFingerprint,
    spec: OperatorSpec,
    examples: list[str] | None = None,
) -> str:
    """Assemble the task prompt from the analysed formulation."""
    lines: list[str] = []

    lines.append(f"# Task\n\nWrite a {spec.kind} operator for this problem: {spec.problem_class}.")
    lines.append(f"\nObjective: {spec.objective}")

    lines.append("\n## Decision variables\n")
    for variable in index.variables.values():
        if not variable.is_decision:
            continue
        marker = " (target)" if variable.name in spec.target_variables else ""
        lines.append(
            f"- `{variable.name}`: {variable.annotation_code} — "
            f"{variable.decision_count} decision indices{marker}"
        )

    if spec.decision_layout:
        lines.append("\n## Decision keys at runtime\n")
        lines.append(
            "Entries of `context.extra[\"decision_keys\"]`; pass them unchanged to "
            "`get_decision_value`/`set_decision_value`."
        )
        for line in spec.decision_layout:
            lines.append(f"- {line}")

    lines.append("\n## Constants\n")
    for constant in index.constants.values():
        lines.append(f"- `{constant.name}` = {_short(constant.value)}")

    lines.append("\n## Constraints\n")
    for predicate in index.predicates.values():
        if predicate.is_warm_start:
            continue
        parameters = ", ".join(p.name for p in predicate.parameters)
        lines.append(f"- `{predicate.name}({parameters})`")

    if spec.model_source:
        lines.append(
            "\n## Model source (OptDSL)\n\n"
            "Every `assert` must hold for a candidate to be feasible; the objective "
            "is what the search minimises/maximises.\n"
        )
        lines.append(f"```python\n{spec.model_source.strip()}\n```")

    if spec.hyperparameters:
        lines.append("\n## Hyperparameters\n")
        for name, default in spec.hyperparameters.items():
            lines.append(f"- `{name}`: default `{default!r}`")

    if spec.invariants:
        lines.append("\n## Invariants the operator must preserve\n")
        for invariant in spec.invariants:
            lines.append(f"- {invariant}")

    if spec.notes:
        lines.append(f"\n## Additional notes\n\n{spec.notes}")

    if examples:
        lines.append("\n## Reference operators from this codebase\n")
        for example in examples:
            lines.append(f"```python\n{example}\n```")

    lines.append(
        "\n## Output\n\n"
        "Return only the complete Python module: its imports followed by the one "
        "operator class. Include a short class docstring explaining the neighborhood."
    )

    return "\n".join(lines)


def _short(value: Any, limit: int = 80) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def contract_reference() -> dict[str, str]:
    """Return the live operator contract, for prompt validation and docs."""
    return {
        "destroy_signature": str(inspect.signature(DestroyOperator.destroy)),
        "repair_signature": str(inspect.signature(RepairOperator.repair)),
        "context_keys": ", ".join(CONTEXT_KEYS),
    }
