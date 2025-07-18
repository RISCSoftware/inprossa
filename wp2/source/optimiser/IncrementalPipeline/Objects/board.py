"""Define a board of wood"""
from gurobipy import GRB, Model
from IncrementalPipeline.config_loader import get_config

from typing import List, Tuple

# Load configuration for maximum number of curved and bad parts
config = get_config()
general_info = config["BeamConfiguration"]
max_n_curved_parts = general_info["MaxNumberOfBadPartsInBoard"]
max_n_bad_parts = general_info["MaxNumberOfCurvedPartsInBoard"]


class Board:
    """
    A board of wood with:
    - length: float
    # Length of the board
    - curved parts: List[(float, float)]
    # List of tuples representing start and end of curved parts
    - bad parts: List[(float, float)]
    # List of tuples representing start and end of bad parts
    """

    def __init__(self,
                 length: float,
                 curved_parts: List[Tuple[float, float]] = None,
                 bad_parts: List[Tuple[float, float]] = None):
        self.length = length
        self.curved_parts = curved_parts
        self.bad_parts = bad_parts


class BoardVars:
    """
    A class to hold the Gurobi variables for a board.
    - length: Gurobi variable for the length of the board
    - curved_parts: List of Gurobi variables for the start
    and end of curved parts
    - bad_parts: List of Gurobi variables for the start
    and end of bad parts
    """
    def __init__(self, model, board: Board = None, id: str = ""):
        self.length = model.addVar(
            vtype=GRB.CONTINUOUS,
            name=f"{id} board_length"
        )
        self.curved_parts = [
            (
                model.addVar(
                    vtype=GRB.CONTINUOUS,
                    name=f"{id} curved_part_start-{i}"
                    ),
                model.addVar(
                    vtype=GRB.CONTINUOUS,
                    name=f"{id} curved_part_end-{i}"
                    )
            )
            for i in range(max_n_curved_parts)
        ]
        self.bad_parts = [
            (
                model.addVar(
                    vtype=GRB.CONTINUOUS,
                    name=f"{id} bad_part_start-{i}"
                    ),
                model.addVar(
                    vtype=GRB.CONTINUOUS,
                    name=f"{id} bad_part_end-{i}"
                )
            )
            for i in range(max_n_bad_parts)
        ]
        self.id = id
        # # Bad part starts shuold be less than their ends
        # for i in range(max_n_bad_parts):
        #     start_var, end_var = self.bad_parts[i]
        #     model.addConstr(start_var <= end_var, name=f"{id} bad_part_start_end_constraint-{i}")
        # # Curved part starts should be less than their ends
        # for i in range(max_n_curved_parts):
        #     start_var, end_var = self.curved_parts[i]
        #     model.addConstr(start_var <= end_var, name=f"{id} curved_part_start_end_constraint-{i}")

        # If board is provided, set the initial values
        if board is not None:
            my_var = model.addVar(vtype=GRB.BINARY, name=f"{id} board_activate")
            model.addConstr(my_var == 1)
            self.conditional_equality(model, my_var, 1, board)

    def conditional_equality(self,
                             model,
                             my_var,
                             value,
                             board: Board,
                             name: str = ""):
        """
        If my_var == 1, then the Gurobi variables
        will be equal to the board's attributes.
        """
        model.addGenConstrIndicator(my_var, value, self.length == board.length)

        for i, curved_interval in enumerate(board.curved_parts):
            start_var, end_var = self.curved_parts[i]
            start, end = curved_interval
            model.addGenConstrIndicator(my_var, value, start_var == start, name=f"{name}_curved_start_{i}")
            model.addGenConstrIndicator(my_var, value, end_var == end, name=f"{name}_curved_end_{i}")

        for i, bad_interval in enumerate(board.bad_parts):
            start_var, end_var = self.bad_parts[i]
            start, end = bad_interval
            model.addGenConstrIndicator(my_var, value, start_var == start, name=f"{name}_bad_start_{i}")
            model.addGenConstrIndicator(my_var, value, end_var == end, name=f"{name}_bad_end_{i}")



def create_board_var_list(model: Model, n, id_prefix: str, start_index: int = 0) -> List[BoardVars]:
    """
    Create a list of BoardVars of length n.
    """
    return [BoardVars(model, id=f"{id_prefix}-[{i}]") for i in range(start_index, start_index + n)]

def create_board_list_from_board_vars(model: Model, board_vars_list: List[BoardVars]) -> List[Board]:
    """
    Create a list of Board objects from a list of BoardVars.
    """
    boards = []
    for board_vars in board_vars_list:
        curved_parts = [(board_vars.curved_parts[i][0].X, board_vars.curved_parts[i][1].X)
                        for i in range(max_n_curved_parts)]
        bad_parts = [(board_vars.bad_parts[i][0].X, board_vars.bad_parts[i][1].X)
                     for i in range(max_n_bad_parts)]
        boards.append(Board(length=board_vars.length.X,
                            curved_parts=curved_parts,
                            bad_parts=bad_parts))
    return boards