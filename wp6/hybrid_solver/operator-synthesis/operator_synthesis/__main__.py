"""Entry point so ``python -m operator_synthesis`` works as documented.

``docs/tooling.md`` and the module docstrings advertise ``python -m
operator_synthesis``, but without this file Python has no ``__main__`` to run
and the command fails with "No module named operator_synthesis.__main__".
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
