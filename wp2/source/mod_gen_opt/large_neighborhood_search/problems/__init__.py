"""Problem-specific initializers and helpers for the LNS framework.

These components are opt-in: the generic LNS engine remains agnostic. Use a
problem-specific initializer when the structure of the DSL allows much
stronger feasibility-aware construction than generic randomized search.
"""

from .cvrp import CVRPRouteInitializer, detect_cvrp_problem, prepare_cvrp_assignment_for_evaluation

__all__ = [
    "CVRPRouteInitializer",
    "detect_cvrp_problem",
    "prepare_cvrp_assignment_for_evaluation",
]
