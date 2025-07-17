"""Defines a filtering machine."""

from IncrementalPipeline.Machines.GenericMachine import GenericMachine
from IncrementalPipeline.Objects.piece import Piece, PieceVars, create_piece_var_list
from gurobipy import GRB, quicksum


class FilteringMachine(GenericMachine):
    """
    A machine that filters a list of pieces.

    This machine expects a list of Piece objects as input
    and produces a list of Piece objects as output.
    """

    def __init__(self, id: str):
        super().__init__(id=f"FilteringMachine-{id}",
                         input_type=PieceVars,
                         output_type=PieceVars)

    def impose_conditions(self, model, input_list: list) -> list:
        """
        Filters the input list of pieces based on some conditions.
        For example, it can filter out pieces that are too short or too long.
        """

        n = len(input_list)  # Number of inputs

        # define one boolean decision variable for each input
        # if the input is used, keep[i] = 1, if it's dropped keep[i] = 0
        keep = model.addVars(n, vtype=GRB.BINARY, name=f"{self.id} keep piece")

        # if piece quality is bad, then keep[i] must be 0
        for i in range(n):
            model.addGenConstrIndicator(
                input_list[i].good,
                0,
                keep[i] == 0,
                name=f"{self.id} good_constraint_{i}"
            )

        # define the output variables
        output_list = create_piece_var_list(model, n, id_prefix=f"{self.id} output ")

        # create variables to link input and output
        input_to_output = model.addVars(n, n, vtype=GRB.BINARY, name=f"{self.id} input_to_output")

        # if this variable is one then input[i] goes to output[j]
        for i in range(n):
            for j in range(n):
                output_list[j].conditional_equality(model,
                                                    input_to_output[i, j],
                                                    1,
                                                    input_list[i])

        # if the sum of this variables for one output is cero
        # then the piece has length 0

        is_output_filled = model.addVars(
            n,
            vtype=GRB.BINARY,
            name=f"{self.id} is_output_filled",
            lb=0
        )
        for j in range(n):
            model.addConstr(
                is_output_filled[j] == quicksum(
                    input_to_output[i, j] for i in range(n)
                ),
                name=f"{self.id} output_filled_{j}"
            )
            output_list[j].conditional_equality(
                model,
                is_output_filled[j],
                0,
                Piece(length=0, good=True)
            )

        # input[i] goes to output[j] if input_to_output[i, j] == 1
        # we want this to happen when we keep j pieces before the ith input
        for i in range(n):
            for j in range(n):
                model.addGenConstrIndicator(
                    input_to_output[i, j],
                    1,
                    quicksum(keep[k] for k in range(i)) == j,
                    name=f"{self.id} input_to_output_indicator_{i}_{j}"
                )

        # Only one output variable can be assigned to each input if we keep it
        for i in range(n):
            model.addConstr(
                quicksum(input_to_output[i, j] for j in range(n)) == keep[i],
                name=f"{self.id} at most one output per input constraint [{i}]"
            )

        # At most one input variable can be assigned to each output
        for j in range(n):
            model.addConstr(
                quicksum(input_to_output[i, j] for i in range(n)) <= 1,
                name=f"{self.id} at most one input per output constraint [{j}]")

        # If keep[i] == 0, then add length to objective function
        waste_added = model.addVars(n, vtype=GRB.CONTINUOUS, name=f"{self.id} waste_added")
        for i in range(n):
            model.addGenConstrIndicator(
                keep[i],
                0,
                waste_added[i] == input_list[i].length,
                name=f"{self.id} waste_added_{i}"
            )

        # Define objective function as the sum of the waste
        model.setObjective(quicksum(waste_added[i] for i in range(n)), GRB.MINIMIZE)

        return keep, output_list
