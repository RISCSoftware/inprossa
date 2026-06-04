"""LNS uses the exact same OptDSL parser/reader implementation as tree search."""

from tree_search.problem_reader import (  # re-export for explicit dependency clarity
    ConstraintSpec,
    DecisionIndexSpec,
    IntDomain,
    ProblemDefinition,
    ProblemObjective,
    VariableDomain,
    VariableSpec,
    infer_assignment_variable_name,
    read_problem,
    read_problem_from_code,
)

__all__ = [
    "ConstraintSpec",
    "DecisionIndexSpec",
    "IntDomain",
    "ProblemDefinition",
    "ProblemObjective",
    "VariableDomain",
    "VariableSpec",
    "infer_assignment_variable_name",
    "read_problem",
    "read_problem_from_code",
]
