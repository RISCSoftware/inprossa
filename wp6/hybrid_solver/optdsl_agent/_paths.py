"""Make the repository's sibling packages importable.

The repo is a flat collection of top-level packages rather than an installed
distribution: ``optdsl_tooling``, ``large_neighborhood_search`` and ``src`` live
at the root, while ``operator_synthesis`` and ``optdsl_lsp`` live in their own
subdirectories. The VS Code extension handles this by setting ``PYTHONPATH``
before spawning Python; a CLI invoked directly has no such help.

Importing this module first makes ``python -m optdsl_agent`` work from any
working directory, which matters because the CLI is meant to be runnable from a
notebook, a script, or a shell in a different folder.

Paths are appended rather than prepended: if the user has installed a real
package with the same name, theirs wins.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Directories that contain importable packages.
_SEARCH_PATHS = (
    REPO_ROOT,
    REPO_ROOT / "operator-synthesis",
    REPO_ROOT / "optdsl-lsp",
)


def ensure_import_paths() -> list[str]:
    """Add the repository's package roots to ``sys.path`` if missing.

    Returns the paths that were added, so a caller can report them.
    """
    added: list[str] = []
    for path in _SEARCH_PATHS:
        if not path.is_dir():
            continue
        text = str(path)
        if text not in sys.path:
            sys.path.append(text)
            added.append(text)
    return added


ensure_import_paths()
