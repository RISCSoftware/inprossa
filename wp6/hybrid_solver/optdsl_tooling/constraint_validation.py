"""Validation of LLM-proposed constraints.

A constraint that parses is not necessarily a constraint. The two failure modes
that matter are silent:

* **Vacuous** — always true, so it constrains nothing. A model asked to "make
  sure every item is assigned" can emit ``assert True`` or a condition that is
  trivially satisfied by the domain bounds, and the solver will happily accept
  it.
* **Over-constrained** — always false, so the model becomes infeasible. This
  usually means the model misread a constant or an index base.

Both are detected the same way: sample random assignments from the declared
domains and count violations. A useful constraint violates *some* samples but
not *all* of them.

This is a heuristic, not a proof. It cannot detect a constraint that is
satisfiable but semantically wrong — that still needs a human. It does catch
the two failure modes that waste the most time.
"""

from __future__ import annotations

import ast
import random
from typing import Any

from .analysis import analyze
from .diagnostics import Severity, check
from large_neighborhood_search.problem_reader import IntDomain


def validate_constraints(
    source: str,
    constraints: list[dict[str, str]],
    *,
    samples: int = 200,
    seed: int = 0,
) -> dict[str, Any]:
    """Validate proposed constraints against ``source``.

    ``constraints`` is a list of ``{"name", "code", "invocation"}`` dicts, as
    produced by the LLM proposal schema.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not constraints:
        return {"ok": False, "errors": ["no constraints were proposed"], "warnings": []}

    # --- gate 1: the combined module must parse and stay clean -------------
    combined = append_constraints(source, constraints)

    combined_index = analyze(combined)
    if combined_index.syntax_error is not None:
        return {
            "ok": False,
            "errors": [f"the combined formulation does not parse: {combined_index.syntax_error}"],
            "warnings": [],
        }

    baseline_codes = {d.code for d in check(analyze(source)) if d.severity == Severity.ERROR}
    new_errors = [
        d
        for d in check(combined_index)
        if d.severity == Severity.ERROR and d.code not in baseline_codes
    ]
    if new_errors:
        errors.extend(f"{d.code}: {d.message}" for d in new_errors)

    # --- gate 2/3: vacuity and over-constraint ----------------------------
    violation_rate: float | None = None
    baseline_violation_rate: float | None = None
    baseline_feasible: float = 0.0
    vacuous = False
    over_constrained = False

    if not errors:
        violation_rate, baseline_violation_rate, baseline_feasible = _measure_violation_rate(
            combined, constraints, samples=samples, seed=seed
        )
        if violation_rate is not None:
            if violation_rate == 0.0:
                vacuous = True
                errors.append(
                    "the constraint is never violated by random assignments, "
                    "so it does not constrain anything"
                )
            elif baseline_feasible == 0.0:
                # Random sampling never satisfies the model's own constraints
                # (e.g. routing/tour constraints), so the wild region says
                # nothing about how strict the new constraint is. Refusing it
                # would be a false positive - flag it for review instead.
                over_constrained = False
                warnings.append(
                    "random assignments never satisfy the model's existing constraints, "
                    "so strictness of the new constraint could not be measured; "
                    "it was added but should be reviewed manually"
                )
            elif baseline_violation_rate == 1.0:
                over_constrained = True
                errors.append(
                    "the constraint is violated by every random assignment that already "
                    "satisfies the model, which usually means a misread constant or index base"
                )
            elif baseline_violation_rate >= 0.95:
                warnings.append(
                    f"the constraint is violated by {baseline_violation_rate:.0%} of "
                    "feasible random assignments; verify it is not too strict"
                )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "violationRate": violation_rate,
        "baselineViolationRate": baseline_violation_rate,
        "baselineFeasible": baseline_feasible,
        "vacuous": vacuous,
        "overConstrained": over_constrained,
    }


def append_constraints(source: str, constraints: list[dict[str, str]]) -> str:
    """Insert the proposed predicates before the objective call.

    Placing them before ``minimize(...)`` keeps the file's conventional shape
    and means the objective expression can reference them.

    This is the only supported way to add constraints to a formulation: there
    is no model object to mutate and no ``.dsl`` serializer, so the edit is
    text insertion at a well-defined anchor.
    """
    blocks = []
    for constraint in constraints:
        code = constraint.get("code", "").rstrip()
        invocation = constraint.get("invocation", "").strip()
        if code:
            blocks.append(code)
        if invocation:
            blocks.append(invocation)

    insertion = "\n\n" + "\n\n".join(blocks) + "\n\n"

    lines = source.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("minimize(", "maximize(")):
            return "\n".join(lines[:index]) + insertion + "\n".join(lines[index:])

    return source + insertion


#: Backwards-compatible alias; the helper used to be private.
_append_constraints = append_constraints


def _measure_violation_rate(
    combined_source: str,
    constraints: list[dict[str, str]],
    *,
    samples: int,
    seed: int,
) -> tuple[float | None, float | None, float]:
    """Measure how strictly the new constraints bite on random assignments.

    Returns ``(violation_rate, baseline_violation_rate, baseline_feasible)``:

    - ``violation_rate`` — fraction of *all* random assignments that violate the
      new constraints (used for vacuity detection: 0.0 means "never fires").
    - ``baseline_violation_rate`` — fraction of random assignments that satisfy
      the model's *existing* constraints yet violate the new ones (used for
      over-constraint detection).
    - ``baseline_feasible`` — fraction of all samples that satisfied the
      existing constraints, so callers can tell when the random distribution is
      nowhere near feasible space (and the second number is meaningless).

    Anything can be ``None`` when the measurement cannot be made (no decision
    variables, or the constraint cannot be executed).
    """
    from large_neighborhood_search.lns import build_lns_context
    from large_neighborhood_search.problem_reader import read_problem_from_code
    from large_neighborhood_search._utils import set_decision_value

    try:
        problem = read_problem_from_code(combined_source, compile_runtime=True)
    except Exception:
        return None, None, 0.0

    context = build_lns_context(problem, random_seed=seed)
    decision_keys = context.extra["decision_keys"]
    if not decision_keys:
        return None, None, 0.0

    names = [constraint["name"] for constraint in constraints if constraint.get("name")]
    new_set = set(names)
    callables = [problem.parsed.runtime_constraints.get(name) for name in names]
    callables = [fn for fn in callables if callable(fn)]
    if not callables:
        return None, None, 0.0

    # Map each predicate's parameter names to the assignment keys it needs.
    parameter_names: list[list[str]] = []
    for name in names:
        node = problem.parsed.constraints.get(name)
        if node is None:
            continue
        parameter_names.append([arg.arg for arg in node.args.args])

    if not parameter_names:
        return None, None, 0.0

    # Baseline = every callable constraint in the combined model (original
    # predicates plus anything else already present) minus the new ones.
    all_runtime = problem.parsed.runtime_constraints
    baseline_names = [
        name
        for name in problem.parsed.constraints
        if name not in new_set and callable(all_runtime.get(name))
    ]
    baseline_callables = [all_runtime[name] for name in baseline_names]
    baseline_params = [
        [arg.arg for arg in problem.parsed.constraints[name].args.args]
        for name in baseline_names
    ]

    rng = random.Random(seed)
    domains = context.extra["decision_domains"]
    variables = problem.variables

    violated_all = 0
    violated_baseline = 0
    baseline_feasible = 0
    for _ in range(samples):
        assignment: dict[str, Any] = {}
        for variable_name, spec in variables.items():
            if spec.domain is None:
                continue
            assignment[variable_name] = _random_value(spec.domain, rng)

        for key in decision_keys:
            lower, upper = domains[key]
            set_decision_value(assignment, key, rng.randint(lower, upper))

        baseline_ok = not _violates(baseline_callables, baseline_params, assignment)
        new_violated = _violates(callables, parameter_names, assignment)
        if new_violated:
            violated_all += 1
        if baseline_ok:
            baseline_feasible += 1
            if new_violated:
                violated_baseline += 1

    baseline_ratio = (
        baseline_feasible / samples if baseline_feasible > 0 else 0.0
    )
    baseline_violation_rate = (
        violated_baseline / baseline_feasible if baseline_feasible > 0 else None
    )
    return violated_all / samples, baseline_violation_rate, baseline_ratio


def _random_value(domain: Any, rng: random.Random) -> Any:
    """Build a random value matching a ``VariableDomain`` or ``IntDomain``.

    ``VariableDomain.element_domain`` is a ``VariableDomain`` for nested lists
    but a bare ``IntDomain`` for a flat ``DSList(N, DSInt(lo, hi))``, so both
    shapes have to be handled.
    """
    if domain is None:
        return None

    if isinstance(domain, IntDomain):
        lower = domain.lower if domain.lower is not None else 0
        upper = domain.upper if domain.upper is not None else lower
        return rng.randint(lower, upper)

    if domain.kind == "int":
        return _random_value(domain.int_domain, rng)

    if domain.kind == "list":
        length = domain.length or 0
        return [_random_value(domain.element_domain, rng) for _ in range(length)]

    if domain.kind == "list_2d":
        length = domain.length or 0
        inner = domain.element_domain
        return [_random_value(inner, rng) for _ in range(length)]

    if domain.kind == "list_of_record":
        length = domain.length or 0
        fields = domain.record_fields or {}
        return [
            {field: _random_value(field_domain, rng) for field, field_domain in fields.items()}
            for _ in range(length)
        ]

    return None


def _violates(
    callables: list[Any],
    parameter_names: list[list[str]],
    assignment: dict[str, Any],
) -> bool:
    for function, parameters in zip(callables, parameter_names):
        if not all(name in assignment for name in parameters):
            continue
        try:
            function(*[assignment[name] for name in parameters])
        except AssertionError:
            return True
        except Exception:
            # A constraint that raises on a valid assignment is broken; treat
            # it as a violation so it surfaces rather than being ignored.
            return True
    return False
