from gurobipy import GRB
from gurobipy import quicksum


def ensure_correct_beam(input_pieces, n_layers, n_layers_per_beam, pieces_per_layer, beam_length, model, global_danger):
    """
    Check if the input pieces can be arranged into beams with the given constraints.

    Parameters:
    - input_pieces: list of lengths of the input pieces (floats)
    - n_layers: total number of layers to be formed completely (int)
    - n_layers_per_beam: number of layers each beam must have (int)
    - max_pieces_per_layer: maximum number of pieces in each layer (int)

    Returns:
    - bool: True if the arrangement is possible, False otherwise
    """
    
    for i in range(n_layers):
        # Check if we can form a complete beam with the pieces
        start_index = i * pieces_per_layer
        end_index = start_index + pieces_per_layer
        # Sum of pieces must be equal to the beam length
        model.addConstr(
            quicksum(input_pieces[j] for j in range(start_index, end_index)) == beam_length,
            name=f"beam_length_{i}"
        )

    n_danger_intervals = len(global_danger)
    # Define a dictionary to hold binary variables used to ensure sums are outside global danger intervals
    danger_vars = model.addVars(n_layers, n_danger_intervals, pieces_per_layer, vtype=GRB.BINARY, name="danger_vars")
    for i in range(n_layers):
        # None of the sums should end up in a global danger interval
        start_index = i * pieces_per_layer
        end_index = start_index + pieces_per_layer
        for k, (start, end) in enumerate(global_danger):
            for partial_end_index in range(start_index + 1, end_index):
                # If the associated sum is below the start of danger interval, danger_vars[i, interval, j] must be 1
                # if it is above the end of the danger interval, it must be 0
                partial_sum = quicksum(input_pieces[j] for j in range(start_index, partial_end_index))
                model.addConstr(
                    partial_sum
                    <=
                    start + (1 - danger_vars[i, k, partial_end_index - start_index]) * beam_length,
                    name=f"danger_check_{i}_{k}_{partial_end_index}"
                )
                model.addConstr(
                    partial_sum
                    >=
                    end - danger_vars[i, k, partial_end_index - start_index] * beam_length,
                    name=f"danger_check_{i}_{k}_{partial_end_index}_upper"
                )
