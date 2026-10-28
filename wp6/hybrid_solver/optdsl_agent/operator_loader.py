"""Make generated operator modules reachable from the registry.

``operator-synthesis`` and the VS Code extension both write accepted operators
into ``large_neighborhood_search/problems/generated/``, but nothing imports that
directory, so a freshly synthesized operator is invisible to
``create_destroy("MyDestroy")``. This module closes that gap.

The heavy lifting lives in :func:`large_neighborhood_search.registry.load_generated_directory`
so the CLI and the LSP can use it without depending on this package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from large_neighborhood_search.registry import (
    all_operators,
    clear_generated,
    load_generated_directory,
)


def load_generated_operators(directory: str | Path | None = None) -> list[str]:
    """Import every generated operator module and return the new names."""
    return load_generated_directory(directory)


def unload_generated_operators() -> None:
    """Drop generated operators from the registry.

    The modules stay in ``sys.modules``; only the registry entries are removed.
    That is enough for the tuning loop, which re-registers a fresh candidate
    under a new name each attempt.
    """
    clear_generated()


def list_operators(problem: str | None = None) -> list[dict[str, Any]]:
    """Describe every registered operator, optionally filtered by problem class.

    ``problem=None`` entries are generic operators that apply to any model, so
    they are included in every filtered listing.
    """
    # Importing this module is what populates the registry with the built-ins.
    import large_neighborhood_search.builtin_operators  # noqa: F401

    operators = []
    for info in all_operators():
        if problem is not None and info.problem not in (None, problem):
            continue
        operators.append(
            {
                "name": info.name,
                "kind": info.kind,
                "problem": info.problem,
                "description": info.description,
                "parameters": info.parameters,
                "generated": info.generated,
            }
        )
    return operators
