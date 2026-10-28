"""Static analysis and code generation for OptDSL formulations.

This package is the shared semantic layer used by:

* ``optdsl-lsp`` — the language server (diagnostics, completion, hover, ...)
* ``operator-synthesis`` — the LNS operator generation/validation harness
* the command line tools

It deliberately has **no** dependency on ``pygls`` or on any editor API, and it
never executes OptDSL source. Everything here is derived from ``ast`` alone, so
it is safe to run against a buffer that is mid-edit or untrusted.
"""

from .analysis import (
    ConstantSymbol,
    DecisionSymbol,
    ModuleIndex,
    PredicateSymbol,
    TypeAliasSymbol,
    VariableSymbol,
    analyze,
    analyze_file,
)
from .diagnostics import Diagnostic, Severity, check
from .fingerprint import ProblemFingerprint, fingerprint
from .positions import PositionMapper

__all__ = [
    "ConstantSymbol",
    "DecisionSymbol",
    "Diagnostic",
    "ModuleIndex",
    "PositionMapper",
    "PredicateSymbol",
    "ProblemFingerprint",
    "Severity",
    "TypeAliasSymbol",
    "VariableSymbol",
    "analyze",
    "analyze_file",
    "check",
    "fingerprint",
]
