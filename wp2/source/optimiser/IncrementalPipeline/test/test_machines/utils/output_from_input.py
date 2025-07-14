from gurobipy import Model, GRB
from IncrementalPipeline.Objects.board import BoardVars

def can_machine_produce_output_from_input(machine, input_list, output_list):
    """
    It tests whether status indicates if the machine can produce output from input.
    """
    
    model = Model()
    vars_input_boards = [BoardVars(model, board=board, id=f"board-{i}")
                        for i, board in enumerate(input_list)]
    _, output_pieces = machine.impose_conditions(model, vars_input_boards)
    
    for i, piece in enumerate(output_pieces):
        my_var = model.addVar(vtype=GRB.BINARY, name=f"my_var-{i}")
        model.addConstr(
            my_var == 1,
            name=f"my_var_{i}"
        )
        piece.conditional_equality(model, my_var, 1, output_list[i])
    
    model.optimize()
    return model.status
