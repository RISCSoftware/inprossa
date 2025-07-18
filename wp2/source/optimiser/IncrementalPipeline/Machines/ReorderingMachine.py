"""Defines a reorder machine."""

from IncrementalPipeline.Machines.GenericMachine import GenericMachine
from gurobipy import GRB, quicksum
from IncrementalPipeline.Objects.board import BoardVars, Board, create_board_var_list
from IncrementalPipeline.Objects.piece import Piece, PieceVars, create_piece_var_list


class ReorderMachine(GenericMachine):
    """
    A machine that reorders a list of items of a given type.
    """

    def __init__(self, id: str, input_type: type = None):
        super().__init__(id=f"ReorderMachine{id}",
                         input_type=input_type,
                         output_type=input_type)

    def output_length(self,
                      input_length: int,
                      existing_output_length: int
                      ) -> int:
        """
        Returns the length of the output list based on the input length,
        and the existing output length.

        In this case, it simply returns the input length,
        plus the existing output length.
        """
        return input_length + existing_output_length

    def impose_conditions(self, model, input_list: list) -> list:
        """
        Defines the possible reorderings of the input list.
        """

        # Create binary variable to indicate if input piece i goes to output j
        # If reorder_vars[i, j] is 1, then input piece i goes to output j
        self.n = len(input_list)

        self.define_swap_not_swap_decisions(model)

        self.define_reorder_vars(model)

        self.one_to_one_reordering(model)

        self.generate_output_list(model, input_list)
        
        # Keep the last output in the "buffer" and add it to the objective function
        # with a penalisation coefficient (e.g. 0.3)
        # other idea would be to penalise less the future
        # if self.input_type == Board or self.input_type == BoardVars:
        #     model.setObjective(model.getObjective() + 0.1 * output_list[-1].length, GRB.MINIMIZE)

        # if self.input_type == Piece or self.input_type == PieceVars:
        #     # Add a buffer penalisation for the last output
        #     self.buffer_penalisation(model, self.output_list[-1])
        #     return self.swap_decisions, self.output_list[:-1]

        return self.swap_decisions, self.output_list
    
    def buffer_penalisation(self, model, buffer_item):
        """
        Penalise the last output in the buffer.
        """
        # if the piece is good spare some of the penalisation
        # if the piece is bad, then penalise the whole length
        buffer_penalisation = model.addVar(
            name=f"{self.id} buffer_penalisation",
            vtype=GRB.CONTINUOUS
        )
        model.addGenConstrIndicator(
            buffer_item.good,
            1,
            buffer_penalisation == 0.3 * buffer_item.length,
            name=f"{self.id} last_output_good"
        )
        model.addGenConstrIndicator(
            buffer_item.good,
            0,
            buffer_penalisation == buffer_item.length,
            name=f"{self.id} last_output_bad"
        )
        model.setObjective(model.getObjective() + buffer_penalisation, GRB.MINIMIZE)

    def generate_output_list(self, model, input_list: list) -> list:
        self.output_list = []
        # Create a list of output objects based on the input type.
        if self.input_type == Board or self.input_type == BoardVars:
            self.output_list = create_board_var_list(model, self.n, id_prefix=f"{self.id} output")
        elif self.input_type == Piece or self.input_type == PieceVars:
            self.output_list = create_piece_var_list(model, self.n, id_prefix=f"{self.id} output")

        for j in range(self.n):
            for i in range(self.n):
                # If input piece i goes to output j,
                # then output[j] = input_list[i]
                # Use create_conditional_copy to impose this condition
                self.output_list[j].conditional_equality(
                    model,
                    self.reorder_vars[i, j],
                    1,
                    input_list[i],
                    name=f"{self.id} input[{i}] output[{j}]"
                    )
    
    def define_swap_not_swap_decisions(self, model):
        self.swap_decisions = model.addVars(self.n - 1,
                                       vtype=GRB.BINARY,
                                       name=f"{self.id} swap_decisions")
        self.not_swap_decisions = model.addVars(self.n - 1,
                                           vtype=GRB.BINARY,
                                           name=f"{self.id} not_swap_decisions")

        # Impose swap and not swap to be different
        for i in range(self.n - 1):
            model.addConstr(
                self.not_swap_decisions[i] == 1 - self.swap_decisions[i],
                name=f"{self.id} not_swap_decisions_[{i}]_constraint"
            )

    def define_reorder_vars(self, model):
        self.reorder_vars = model.addVars(self.n, self.n,
                                          vtype=GRB.BINARY,
                                          name=f"{self.id} reorder_vars")

        # Define reordering decision variables
        # If reorder_decision[i] == 1,
        # then there is a swap between input[i+1] and input[i]

        # Move a piece backwards whenever swap_decision[i] == 1
        # if swap_decisions[i] == 1, then reorder_vars[i + 1, i] = 1
        for i in range(self.n - 1):
            model.addConstr(
                self.swap_decisions[i] == self.reorder_vars[i + 1, i],
                name=f"{self.id} one_backwards_[{i}]"
            )


        # For every input piece i, if:
        # swap_decision[i-1] == 0, (out of range if i == 0)
        # swap_decision[i] == 1,
        # swap_decision[i] == 1,
        # ...
        # swap_decision[i+r-1] == 1, (none if r == 0)
        # swap_decision[i+r] == 0. (out of range if i == n-r)
        # Then reorder_vars[i, i+r] = 1
        for i in range(self.n):
            for r in range(self.n - i - 1):
                # Check if input i goes to output i + r
                self.necessary_swaps = []
                for k in range(r):
                    # intermediate swaps
                    self.necessary_swaps.append(self.swap_decisions[i + k])
                if i > 0:
                    # previous swap
                    self.necessary_swaps.append(self.not_swap_decisions[i - 1])
                if i + r < self.n - 1:
                    # next swap
                    self.necessary_swaps.append(self.not_swap_decisions[i + r])
                model.addGenConstrAnd(
                    self.reorder_vars[i, i + r],
                    self.necessary_swaps,
                    name=f"{self.id} force_reorder_vars_[{i}]_[{i + r}]"
                )

    def one_to_one_reordering(self, model):
                
        # Each input piece must go to exactly one output
        for i in range(self.n):
            model.addConstr(
                quicksum(self.reorder_vars[i, j] for j in range(self.n)) == 1,
                name=f"{self.id} input_piece_[{i}]_goes_to_one_output"
            )
        for j in range(self.n):
            model.addConstr(
                quicksum(self.reorder_vars[i, j] for i in range(self.n)) == 1,
                name=f"{self.id} output_piece_[{j}]_comes_from_one_input"
            )
