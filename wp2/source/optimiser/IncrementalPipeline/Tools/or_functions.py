from gurobipy import GRB


def add_or_constraints(model, constraints, name_prefix="or_constraints"):
    """
    Adds a constraint of the form: (C1) OR (C2) OR ... OR (Cn)

    Parameters:
    - model: Gurobi model
    - constraints: list of tuples [(expr, sense, rhs), ...]
      where `sense` is one of '<=', '>=', '=='
    - name_prefix: base name for the binary vars and constraints
    """
    binary_vars = []

    for idx, (expr, sense, rhs) in enumerate(constraints):
        indicator = model.addVar(vtype=GRB.BINARY, name=f"{name_prefix}_indicator{idx}")
        binary_vars.append(indicator)

        if sense == '<=':
            model.addGenConstrIndicator(indicator, True, expr <= rhs,
                                        name=f"{name_prefix}_cond{idx}")
        elif sense == '>=':
            model.addGenConstrIndicator(indicator, True, expr >= rhs,
                                        name=f"{name_prefix}_cond{idx}")
        elif sense == '==':
            model.addGenConstrIndicator(indicator, True, expr == rhs,
                                        name=f"{name_prefix}_cond{idx}")
        else:
            raise ValueError(f"Unsupported sense: {sense}")

    res = model.addVar(vtype=GRB.BINARY, name=f"{name_prefix}_res_or")
    model.addConstr(
        res == 1, name=f"{name_prefix}_or_True"
    )
    model.addGenConstrOr(res, binary_vars, name=f"{name_prefix}_or_logic")
