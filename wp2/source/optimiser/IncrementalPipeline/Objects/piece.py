"""Define a piece of wood"""
from gurobipy import GRB
from gurobipy import Model
from typing import List

class Piece:
    """
    A piece of wood with:
    - length: float
      Length of the piece
    - good: bool
      Whether the piece is good or not
    """
    def __init__(self, length: float, good: bool = True, id: str = ""):
        self.length = length
        self.good = good
        self.id = id


class PieceVars:
    """
    A class to hold the Gurobi variables for a piece of wood.
    - length: Gurobi variable for the length of the piece
    - good: Gurobi binary variable indicating if the piece is good
    """
    def __init__(self, model: Model,
                 piece: Piece = None,
                 id: str = ""):
        self.length = model.addVar(
            vtype=GRB.CONTINUOUS,
            name=f"{id} piece_length"
        )
        self.good = model.addVar(
            vtype=GRB.BINARY,
            name=f"{id} piece_good"
        )

        # If a piece object is provided, enforce conditional equality
        if piece is not None:
            self.conditional_equality(model, 1, 1, piece)

    def conditional_equality(self, model: Model, my_var, value, piece: Piece, name: str = ""):
        """
        If my_var == 1, enforce that this piece's variables
        match the attributes of the given piece.
        """
        expression = self.length - piece.length
        model.addGenConstrIndicator(my_var, value, expression == 0, name=f"{name}_length")
        model.addGenConstrIndicator(my_var, value, self.good == piece.good, name=f"{name}_good")


def create_piece_var_list(model: Model, n, id_prefix: str, start_index: int=0) -> List[PieceVars]:
    """
    Create a list of PieceVars of length n.
    """
    return [PieceVars(model, id=f"{id_prefix}[{i}]") for i in range(start_index, start_index + n)]
