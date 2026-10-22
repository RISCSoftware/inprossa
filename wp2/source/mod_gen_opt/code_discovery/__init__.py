"""Code discovery module: integrates LNS, MiniZinc lower-bound estimation, and LLM-generated operators."""

from .pipeline import CodeDiscoveryPipeline
from .iterative_pipeline import (
    InitPhaseResult,
    IterativeCodeDiscoveryPipeline,
    IterativeDiscoveryResult,
    RoundSummary,
)
from .lower_bound import estimate_lower_bound
from .operator_gen import generate_initializers_with_llm, generate_operators_with_llm

__all__ = [
    "CodeDiscoveryPipeline",
    "InitPhaseResult",
    "IterativeCodeDiscoveryPipeline",
    "IterativeDiscoveryResult",
    "RoundSummary",
    "estimate_lower_bound",
    "generate_initializers_with_llm",
    "generate_operators_with_llm",
]
