"""Shared utility functions for LNS framework."""

from __future__ import annotations

from typing import Any

from .models import LNSContext


def _list_get(value: list, idx: int | tuple) -> object:
    """Safely index into a list for 1-D, 2-D, and record-field decision indices.

    ``idx`` shapes: ``int`` (1-D), ``(i, j)`` ints (2-D), ``(i, field)`` with a
    string field name (record-list scalar field), or ``(i, field, j)`` (record
    -list field that is itself a list).
    """
    if isinstance(idx, tuple):
        if len(idx) == 3:
            i, field, j = idx
            return value[i][field][j]
        i, second = idx
        return value[i][second]
    return value[idx]


def _list_set(value: list, idx: int | tuple, v: object) -> None:
    """Safely set a list element for 1-D, 2-D, and record-field decision indices."""
    if isinstance(idx, tuple):
        if len(idx) == 3:
            i, field, j = idx
            value[i][field][j] = v
            return
        i, second = idx
        value[i][second] = v
        return
    value[idx] = v


def get_decision_value(assignment: dict[str, object], key: tuple[str, int | tuple[int, int] | None]) -> Any:
    """Get a decision value from assignment, handling scalar/list/2D correctly."""
    var_name, idx = key
    value = assignment.get(var_name)
    if value is None:
        return None
    if idx is None:
        return value
    if isinstance(value, list):
        return _list_get(value, idx)
    return None


def set_decision_value(
    assignment: dict[str, object], 
    key: tuple[str, int | tuple[int, int] | None], 
    value: int | None
) -> None:
    """Set a decision value in assignment, handling scalar/list/2D correctly."""
    var_name, idx = key
    if idx is None:
        assignment[var_name] = value
        return
    var_value = assignment.get(var_name)
    if isinstance(var_value, list):
        _list_set(var_value, idx, value)


def is_better_score(candidate: float, best: float, objective_sense: str) -> bool:
    """Compare two scores under given optimization sense."""
    if objective_sense == "maximize":
        return candidate > best
    return candidate < best


def is_better_feasibility_lex(
    cand_failed: int,
    cand_objective: float,
    best_failed: int,
    best_objective: float,
    objective_sense: str,
) -> bool:
    """Lexicographic comparison: feasibility first, then objective.
    
    Returns True if candidate is better than best under:
    1. Fewer violations (feasibility)
    2. Better objective value (if equally feasible)
    """
    if cand_failed != best_failed:
        return cand_failed < best_failed
    if objective_sense == "maximize":
        return cand_objective > best_objective
    return cand_objective < best_objective


def is_penalty_score(score: float, context: LNSContext) -> bool:
    """Check if score represents an infeasible solution (penalty-based)."""
    penalty_base = context.extra.get("penalty_base")
    if not isinstance(penalty_base, (int, float)):
        return False
    if context.objective_sense == "maximize":
        return score <= -float(penalty_base)
    return score >= float(penalty_base)


def has_unassigned(assignment: dict[str, object]) -> bool:
    """Check if assignment has any unassigned (None) decision variables.

    Recurses into nested lists and dicts (record-shaped decision variables)
    generically. Negative numeric values also count as unassigned/invalid
    since they violate ``DSInt(0, ...)`` lower bounds.
    """
    return any(_value_has_unassigned(value) for value in assignment.values())


def _value_has_unassigned(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value < 0
    if isinstance(value, list):
        return any(_value_has_unassigned(item) for item in value)
    if isinstance(value, dict):
        return any(_value_has_unassigned(item) for item in value.values())
    return False


def clone_assignment(assignment: dict[str, object]) -> dict[str, object]:
    """Deep-copy an assignment, preserving nested list/dict (record) structure."""
    return {key: _deep_copy_value(value) for key, value in assignment.items()}


def _deep_copy_value(value: object) -> object:
    """Recursively deep-copy a value (handles nested lists and dict/record values)."""
    if isinstance(value, list):
        return [_deep_copy_value(item) for item in value]
    if isinstance(value, dict):
        return type(value)({key: _deep_copy_value(item) for key, item in value.items()})
    return value


# Backward-compatible alias (previously only handled nested lists).
_deep_copy_list = _deep_copy_value
