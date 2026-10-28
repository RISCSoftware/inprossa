"""Operator synthesis package."""

from .harness import (
    ALLOWED_IMPORTS,
    AcceptancePolicy,
    RunMetrics,
    StaticCheckResult,
    Verdict,
    evaluate_candidate,
    run_candidate,
    static_check,
)
from .prompts import OperatorSpec, build_system_prompt, build_user_prompt, contract_reference
from .synthesize import (
    Attempt,
    SynthesisResult,
    extract_code,
    synthesize,
    write_operator,
    write_report,
)

__all__ = [
    "ALLOWED_IMPORTS",
    "AcceptancePolicy",
    "Attempt",
    "OperatorSpec",
    "RunMetrics",
    "StaticCheckResult",
    "SynthesisResult",
    "Verdict",
    "build_system_prompt",
    "build_user_prompt",
    "contract_reference",
    "evaluate_candidate",
    "extract_code",
    "run_candidate",
    "static_check",
    "synthesize",
    "write_operator",
    "write_report",
]
