from gurobipy import GRB

def cut(model, input_board, n_cuts, n_intervals, id="cut"):
    """
    Adds constraints to the model for cutting boards based on the input lengths.
    
    Parameters:
    - model: The Gurobi model to which constraints will be added.
    - input_boards: a dictionary containing:
        - 'length': total board length (float)
        - 'intervals': list of (start, end) tuples where cuts must occur
    
    Returns:
    - None
    """
    # Check the number of intervals match
    if len(input_board['intervals']) != n_intervals:
        raise ValueError("Number of intervals does not match the input board's intervals.")
    
    input_length = input_board['length']
    
    # Create cutting variables
    cut_vars = model.addVars(
        range(n_cuts),
        lb=0, # lower bound
        ub=input_length, # upper bound
        vtype=GRB.CONTINUOUS,
        name="cut_vars"
    )

    # Cuts must be ordered
    for j in range(n_cuts - 1):
        model.addConstr(cut_vars[j] <= cut_vars[j + 1], name=f"cut_order_{j}")

    # Create binary variables to indicate if a cut is made in an interval
    cut_in_interval = model.addVars(n_intervals,
                                    n_cuts, vtype=GRB.BINARY,
                                    name="cut_in_interval")

    # Check that there is at least one cut in each interval
    for i in range(n_intervals):
        for j in range(n_cuts):
            # if cut_in_interval[i, j] is 1, then cut_vars[j] must be in the interval
            # otherwise these constraints are useless
            start, finish = input_board['intervals'][i]
            model.addConstr(
                cut_vars[j] >= start - input_length * (1 - cut_in_interval[i, j]),
                name=f"cut_in_interval_lower_{i}_{j}"
            )
            model.addConstr(
                cut_vars[j] <= finish + input_length * (1 - cut_in_interval[i, j]),
                name=f"cut_in_interval_upper_{i}_{j}"
            )
    
    # Ensure that at least one cut is made in each interval
    for i in range(n_intervals):
        model.addConstr(
            sum(cut_in_interval[i, j] for j in range(n_cuts)) >= 1,
            name=f"at_least_one_cut_in_interval_{i}"
        )

    # Create variables for output lengths
    output_lengths = model.addVars(n_cuts + 1, vtype=GRB.CONTINUOUS, name="output_lengths")

    # Set the first output length to the first cut variable
    model.addConstr(output_lengths[0] == cut_vars[0], name="first_output_length")
    # Set the last output length to the last cut variable
    model.addConstr(output_lengths[n_cuts] == input_board['length'] - cut_vars[n_cuts - 1], name="last_output_length")
    # Set the output lengths between cuts
    for j in range(1, n_cuts):
        model.addConstr(
            output_lengths[j] == cut_vars[j] - cut_vars[j - 1],
            name=f"output_length_{j}"
        )

    return output_lengths