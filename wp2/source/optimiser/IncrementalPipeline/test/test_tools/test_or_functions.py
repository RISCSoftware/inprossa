"""Contains tests for the OR functions."""

from gurobipy import Model, GRB
from IncrementalPipeline.Tools.or_functions import add_or_constraints

def test_add_or_constraints():
    """
    Tests the add_or_constraints function.
    """
    model = Model("test_model")
    x1 = model.addVar(vtype=GRB.BINARY, name="x1")
    model.addConstr(x1 == 1, name="c1")
    x1_before = (x1,
                 '<=',
                 0)
    x1_after = (x1,
                 '>=',
                 2)
    #  I want x1 to be before 0 or after 2
    add_or_constraints(model, [x1_before, x1_after])
    model.optimize()
    assert model.status == 3, f"Model should be unfeasible but got {model.status}"   # GRB.INFEASIBLE