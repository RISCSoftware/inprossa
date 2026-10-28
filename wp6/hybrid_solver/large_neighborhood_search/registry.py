"""Registry for LNS destroy/repair operators.

Before this module, operators were reachable only through long ``if/elif``
chains and ``choices=[...]`` lists in ``example_lns.py``. That made a new
operator invisible until three separate places were edited, which in turn made
generated operators impractical.

The registry is a plain name -> factory mapping. Registration is explicit
(``@register_destroy("Name")``) rather than import-time magic, so importing the
package stays cheap and the language server can start without pulling in every
problem adapter.

Factories take keyword arguments so the CLI can pass hyperparameters uniformly::

    @register_destroy("CVRPShawDestroy")
    def _make_shaw(**kwargs):
        return CVRPShawDestroy(**kwargs)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .components import DestroyOperator, RepairOperator

DestroyFactory = Callable[..., DestroyOperator]
RepairFactory = Callable[..., RepairOperator]


@dataclass(frozen=True)
class OperatorInfo:
    """Metadata about a registered operator."""

    name: str
    kind: str  # "destroy" | "repair"
    factory: Callable[..., Any]
    problem: str | None = None
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    generated: bool = False


_DESTROYS: dict[str, OperatorInfo] = {}
_REPAIRS: dict[str, OperatorInfo] = {}


def register_destroy(
    name: str,
    *,
    problem: str | None = None,
    description: str = "",
    parameters: dict[str, Any] | None = None,
    generated: bool = False,
) -> Callable[[DestroyFactory], DestroyFactory]:
    """Register a destroy-operator factory under ``name``."""

    def decorator(factory: DestroyFactory) -> DestroyFactory:
        _register(_DESTROYS, name, "destroy", factory, problem, description, parameters, generated)
        return factory

    return decorator


def register_repair(
    name: str,
    *,
    problem: str | None = None,
    description: str = "",
    parameters: dict[str, Any] | None = None,
    generated: bool = False,
) -> Callable[[RepairFactory], RepairFactory]:
    """Register a repair-operator factory under ``name``."""

    def decorator(factory: RepairFactory) -> RepairFactory:
        _register(_REPAIRS, name, "repair", factory, problem, description, parameters, generated)
        return factory

    return decorator


def _register(
    registry: dict[str, OperatorInfo],
    name: str,
    kind: str,
    factory: Callable[..., Any],
    problem: str | None,
    description: str,
    parameters: dict[str, Any] | None,
    generated: bool,
) -> None:
    if name in registry:
        raise ValueError(f"{kind} operator '{name}' is already registered")
    registry[name] = OperatorInfo(
        name=name,
        kind=kind,
        factory=factory,
        problem=problem,
        description=description,
        parameters=dict(parameters or {}),
        generated=generated,
    )


def available_destroys(problem: str | None = None) -> list[str]:
    """Registered destroy names, optionally filtered by problem class."""
    return sorted(
        name for name, info in _DESTROYS.items() if problem is None or info.problem in (None, problem)
    )


def available_repairs(problem: str | None = None) -> list[str]:
    """Registered repair names, optionally filtered by problem class."""
    return sorted(
        name for name, info in _REPAIRS.items() if problem is None or info.problem in (None, problem)
    )


def describe(name: str) -> OperatorInfo | None:
    return _DESTROYS.get(name) or _REPAIRS.get(name)


def all_operators() -> list[OperatorInfo]:
    return sorted(list(_DESTROYS.values()) + list(_REPAIRS.values()), key=lambda info: (info.kind, info.name))


def create_destroy(name: str, **kwargs: Any) -> DestroyOperator:
    """Instantiate a registered destroy operator."""
    info = _DESTROYS.get(name)
    if info is None:
        raise KeyError(f"unknown destroy operator '{name}'; available: {', '.join(available_destroys())}")
    return info.factory(**kwargs)


def create_repair(name: str, **kwargs: Any) -> RepairOperator:
    """Instantiate a registered repair operator."""
    info = _REPAIRS.get(name)
    if info is None:
        raise KeyError(f"unknown repair operator '{name}'; available: {', '.join(available_repairs())}")
    return info.factory(**kwargs)


def clear_generated() -> None:
    """Drop every generated operator. Used by the synthesis harness between runs."""
    for registry in (_DESTROYS, _REPAIRS):
        for name in [n for n, info in registry.items() if info.generated]:
            del registry[name]


def load_generated_directory(directory: str | Path | None = None) -> list[str]:
    """Import every ``*.py`` module in *directory* so its registrations apply.

    Generated operators are written as plain modules that call
    ``@register_destroy``/``@register_repair`` at import time. Nothing imports
    them automatically, so a freshly synthesized operator is invisible to
    ``create_destroy`` until this runs.

    A module that fails to import is skipped rather than aborting the load: one
    broken generated file must not make every other operator unreachable.

    Returns the names of the operators that became available, sorted.
    """
    import importlib.util
    import sys

    target = Path(directory) if directory is not None else _default_generated_dir()
    if not target.is_dir():
        return []

    before = {info.name for info in all_operators()}

    for path in sorted(target.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"large_neighborhood_search.problems.generated.{path.stem}"
        if module_name in sys.modules:
            continue
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception:  # noqa: BLE001 - a bad generated file must not break the rest
            sys.modules.pop(module_name, None)
            continue

    after = {info.name for info in all_operators()}
    return sorted(after - before)


def _default_generated_dir() -> Path:
    return Path(__file__).resolve().parent / "problems" / "generated"
