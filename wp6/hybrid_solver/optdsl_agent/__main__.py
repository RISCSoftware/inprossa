"""Entry point for ``python -m optdsl_agent``."""

from __future__ import annotations

from . import _paths  # noqa: F401  (must run before the sibling-package imports)
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
