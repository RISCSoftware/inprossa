from gurobipy import Model, GRB
from IncrementalPipeline.Objects.board import Board, BoardVars
from IncrementalPipeline.Objects.piece import Piece, PieceVars

def can_machine_produce_output_from_input(machine, input_list, desired_output_list):
    """
    It tests whether status indicates if the machine can produce output from input.
    """
    
    model = Model()
    if type(input_list[0]) is BoardVars or type(input_list[0]) is Board:
        vars_input = [BoardVars(model, board=board, id=f"board-{i}")
                            for i, board in enumerate(input_list)]
    if type(input_list[0]) is PieceVars or type(input_list[0]) is Piece:
        vars_input = [PieceVars(model, piece=piece, id=f"piece-{i}")
                            for i, piece in enumerate(input_list)]
    _, obtained_output_list = machine.impose_conditions(model, vars_input)

    if len(obtained_output_list) != len(desired_output_list):
        raise ValueError("The length of the obtained output list does not match the desired output list.")

    for i, output in enumerate(obtained_output_list):
        my_var = model.addVar(vtype=GRB.BINARY, name=f"my_var-{i}")
        model.addConstr(
            my_var == 1,
            name=f"my_var_{i}"
        )
        output.conditional_equality(model, my_var, 1, desired_output_list[i])
    
    model.optimize()
    return model.status
