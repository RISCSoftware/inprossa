from gurobipy import GRB, quicksum


def reorder(model, input_pieces, max_length, id="reorder"):
    """
    Allow reordering of input pieces
    """

    # Create binary variable to indicate if input piece i goes to output j
    n = len(input_pieces)
    reorder_vars = model.addVars(n, n, vtype=GRB.BINARY, name="reorder_vars")

    # Each input piece can only go to one output
    for i in range(n):
        model.addConstr(
            quicksum(reorder_vars[i, j] for j in range(n)) == 1,
            name=f"one_output_per_input_{i}"
        )
    # Each output can only have one input piece assigned to it
    for j in range(n):
        model.addConstr(
            quicksum(reorder_vars[i, j] for i in range(n)) == 1,
            name=f"one_input_per_output_{j}"
        )

    # Define the output variables
    output = model.addVars(n, vtype=GRB.CONTINUOUS, name="output_"+id, lb=0)

    for i in range(n):
        for j in range(n):
            # if reorder_vars[i, j] is 1, then output[j] = input_pieces[i]
            model.addConstr(
                output[j] >= input_pieces[i] - (1 - reorder_vars[i, j]) * max_length,
                name=f"output_lower_{i}_{j}"
            )
            model.addConstr(
                output[j] <= input_pieces[i] + (1 - reorder_vars[i, j]) * max_length,
                name=f"output_upper_{i}_{j}"
            )

    # Define reordering decsision variables
    # If reorder_decision[i] == 1, then there is a swap between input[i+1] and input[i]
    reorder_decision = model.addVars(n - 1, vtype=GRB.BINARY, name="reorder_decision", lb=0)

    # If reorder_decision[i] == 1 then reorder_vars[i, i-1] = 1
    # Same if its 0
    for i in range(n - 1):
        model.addConstr(
            reorder_decision[i] == reorder_vars[i + 1, i],
            name=f"reorder_decision_{i}"
        )

    # An input i can only end up in output j if all reorder_decision in the middle are 1
    for i in range(n - 1):
        for j in range(i + 1, n):
            for k in range(i, j):
                model.addConstr(
                    reorder_vars[i, j] <= reorder_decision[k],
                    name=f"reorder_decision_constraint_{i}_{j}_{k}"
                )

    return output
