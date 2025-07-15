"""Will convert a list of Board or Piece objects to a list of BoardVars or PieceVars objects."""

from IncrementalPipeline.Objects.board import Board, BoardVars
from IncrementalPipeline.Objects.piece import Piece, PieceVars

def to_vars(input_list: list, model, starting_machine_name: str) -> list:
    """
    Converts a list of Board or Piece objects to a list of BoardVars or PieceVars objects.

    Args:
        input_list (list): List of Board or Piece objects.
        model: Gurobi model to which the variables will be added.
        starting_machine_name (str): Name of the starting machine for variable naming.

    Returns:
        list: List of BoardVars or PieceVars objects.
    """
    if not input_list:
        return []

    if isinstance(input_list[0], Board) or isinstance(input_list[0], BoardVars):
        return [BoardVars(model, board=board, id=f"{starting_machine_name} board [{i}]")
                for i, board in enumerate(input_list)]
    elif isinstance(input_list[0], Piece) or isinstance(input_list[0], PieceVars):
        return [PieceVars(model, piece=piece, id=f"{starting_machine_name} piece [{i}]")
                for i, piece in enumerate(input_list)]
    else:
        raise TypeError("Input list must contain either Board or Piece objects.")