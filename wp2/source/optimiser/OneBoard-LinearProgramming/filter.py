from gurobipy import GRB, quicksum

def filter(model, input_pieces, min_length, max_length, id="filter"):
    n = len(input_pieces)  # Number of inputs
    
    # define one boolean decision variable for each input
    # if the input is used, keep[i] = 1, if it's dropped keep[i] = 0
    keep = model.addVars(n, vtype=GRB.BINARY, name="b")

    # define variables to check if the input is larger than 0
    input_positive = model.addVars(n, vtype=GRB.BINARY, name="input_positive")
    for i in range(n):
        # if the input is larger than 0, then input_positive[i] must be 1
        # input_positive[i] can only be 0 if input[i] is 0
        model.addConstr(
            input_pieces[i] - input_positive[i] * max_length <= 0,
            name=f"input_positive_{i}"
        )
    
    # define varibales to check if the input is smaller than min_length
    input_smaller = model.addVars(n, vtype=GRB.BINARY, name="input_negative")
    for i in range(n):
        # if the input is smaller than min_length, then input_smaller[i] must be 1
        # input_smaller[i] can only be 0 if input[i] is larger than min_length
        model.addConstr(
            min_length * (1- input_smaller[i]) - input_pieces[i] <= 0,
            name=f"input_smaller_{i}"
        )
    
    # if both input_positive[i] and input_smaller[i] are 1, then keep[i] must be 0
    # (i.e., keep[i] = 1 ⇨ input is either 0, or ≥ min_length)  
    for i in range(n):
        model.addConstr(
            keep[i] + input_positive[i] + input_smaller[i] <= 2,
            name=f"keep_{i}"
        )

    # define the output variables
    # we want output_j to be the jth not dropped input
    output = model.addVars(n, vtype=GRB.CONTINUOUS, name="output_"+id, lb=0)

    # binary auxiliary variables to match the inputs to the outputs
    aux_vars = model.addVars(n, n, vtype=GRB.BINARY, name="aux")
    # aux_vars[i, j] = 1 if input[i] is assigned to output[j], 0 otherwise

    # Only one output variable can be assigned to each input
    # and we only assign it if we keep the input
    for i in range(n):
        model.addConstr(
            sum(aux_vars[i, j] for j in range(n)) == keep[i],
            name=f"one_output_per_input_{i}"
        )

    # At most one input variable can be assigned to each output
    for j in range(n):
        model.addConstr(
            sum(aux_vars[i, j] for i in range(n)) <= 1,
            name=f"one_input_per_output_{i}"
        )
    # Each output[j] must be assigned to a smaller i for input[i] than output[j+1]
    # 1 * aux_vars[1,j] + 2 * aux_vars[2,j] + ... + n * aux_vars[n,j]
    # <=
    # 1 * aux_vars[1,j+1] + 2 * aux_vars[2,j+1] + ... + n * aux_vars[n,j+1]
    for j in range(n - 1):
        model.addConstr(
            quicksum(i * aux_vars[i, j] for i in range(n)) <=
            quicksum(i * aux_vars[i, j + 1] for i in range(n)),
            name=f"output_order_{j}"
        )

    # continuous variables to see how much the input i gives to output j
    cont_vars = model.addVars(n, n, vtype=GRB.CONTINUOUS, name="cont_aux", lb=0)
    for i in range(n):
        for j in range(n):
            # in any case cont_vars[i, j] <= input[i]
            model.addConstr(
                cont_vars[i, j] <= input_pieces[i]
            )
            # if aux_vars[i, j] is 1, then cont_vars[i, j] >= input[i]
            model.addConstr(
                cont_vars[i, j] >= input_pieces[i] - (1 - aux_vars[i, j]) * max_length
            )
            # if aux_vars[i, j] is 0, then cont_vars[i, j] must be equal to 0
            model.addConstr(
                cont_vars[i, j] <= aux_vars[i, j] * max_length
            )
    
    # output[j] must be the sum of all cont_vars[i, j] for i
    for j in range(n):
        model.addConstr(
            output[j] == sum(cont_vars[i, j] for i in range(n)),
            name=f"output_sum_{j}"
        )

    # Compute the cost as initial length minus the sum of outputs
    model.setObjective(
        sum(input_pieces[i] for i in range(n)) - sum(output[j] for j in range(n)),
        GRB.MINIMIZE
    )

    return output
