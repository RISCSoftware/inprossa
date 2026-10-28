"""Formatting helpers for OptDSL ``@warm_start`` blocks.

The MiniZinc translator discovers warm-start hints by parsing a
``@warm_start``-decorated function from the DSL source.  These helpers render
such a block from a *warm-start spec* so callers (the LNS CLI, the MiniZinc
CLI, the Python bridge) can attach hints to a problem file without editing the
file on disk.

A warm-start spec is a plain dict::

    {
        "hints": { "<dsl-var>": <literal>, ... },
        "lower_bound": float | None,   # from a feasible max. objective
        "upper_bound": float | None,   # from a feasible min. objective
    }

which is exactly what ``MiniZincTranslator`` reads back out of the parsed
decorator.
"""
from __future__ import annotations

from typing import Any, Mapping


def normalise_hints(assignment: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only hints the MiniZinc backend can consume.

    - ``None`` values are dropped (unassigned variables).
    - Per-row helper keys such as ``completion_0`` have no top-level DSL
      variable and are dropped.
    - Nested (2-D) list values are dropped because MiniZinc's ``warm_start``
      annotation only accepts 1-D arrays.
    """
    hints: dict[str, Any] = {}
    for var_name, value in assignment.items():
        if value is None:
            continue
        # Skip per-row helper keys written by e.g. JSSPScheduleInitializer.
        if "_" in var_name:
            _, suffix = var_name.rsplit("_", 1)
            if suffix.isdigit():
                continue
        if isinstance(value, list):
            if value and isinstance(value[0], list):
                continue
        hints[var_name] = value
    return hints


def _dsl_literal(value: Any) -> str:
    """Render *value* as a Python literal parseable by the DSL translator.

    ``MiniZincTranslator._parse_warm_start_function`` uses
    ``ast.literal_eval`` on the ``@warm_start`` return value, so the rendered
    text must be valid literal syntax.
    """
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_dsl_literal(item) for item in value) + "]"
    return repr(value)


def warm_start_block(spec: Mapping[str, Any]) -> str:
    """Render a ``@warm_start``-decorated function from *spec*.

    If *spec* carries ``lower_bound``/``upper_bound`` these are passed to the
    decorator so the translator emits objective bound constraints; otherwise a
    bare ``@warm_start`` is used.
    """
    hints = normalise_hints(spec.get("hints") or {})

    decorator_args: list[str] = []
    lower_bound = spec.get("lower_bound")
    upper_bound = spec.get("upper_bound")
    if lower_bound is not None:
        decorator_args.append(f"lower_bound={lower_bound!r}")
    if upper_bound is not None:
        decorator_args.append(f"upper_bound={upper_bound!r}")

    lines = [
        f"@warm_start({', '.join(decorator_args)})" if decorator_args else "@warm_start",
        "def _warm_start_hints():",
        "    return {",
    ]
    for var_name in sorted(hints):
        lines.append(f'        "{var_name}": {_dsl_literal(hints[var_name])},')
    lines.append("    }")
    return "\n".join(lines)


def inject_warm_start(dsl_text: str, spec: Mapping[str, Any] | None) -> str:
    """Return *dsl_text* with the warm-start block of *spec* appended.

    Returns *dsl_text* unchanged when *spec* is empty or carries no hints, so
    callers can hand the result straight to the translator.
    """
    if not spec:
        return dsl_text
    if not normalise_hints(spec.get("hints") or {}):
        return dsl_text

    block = warm_start_block(spec)
    if not dsl_text.endswith("\n"):
        dsl_text += "\n"
    return dsl_text + "\n" + block + "\n"
