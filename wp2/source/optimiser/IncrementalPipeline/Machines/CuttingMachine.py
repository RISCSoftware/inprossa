"""Defines a cutting machine."""

from IncrementalPipeline.Machines.GenericMachine import GenericMachine
from IncrementalPipeline.Objects.board import Board, BoardVars
from IncrementalPipeline.Objects.piece import Piece, PieceVars, create_piece_var_list
from IncrementalPipeline.config_loader import get_config
from IncrementalPipeline.Tools.simple_computations import (
    max_pieces_per_board,
    min_piece_length
)
from IncrementalPipeline.Tools.intervals_intersect import intersect_intervals, process_intersect_intervals
from gurobipy import Model, GRB, quicksum


class CuttingMachine(GenericMachine):
    """
    A machine that cuts a list of boards into pieces.

    This machine expects a list of Board objects as input
    and produces a list of Piece objects as output.
    """

    def __init__(self, id: str):
        super().__init__(id=f"CuttingMachine-{id}",
                         input_type=BoardVars,
                         output_type=PieceVars)
        self.max_pieces_per_board = max_pieces_per_board

    def output_length(self,
                      input_length: int,
                      existing_output_length: int
                      ) -> int:
        """
        Returns the length of the output list based on the input length,
        and the existing output length.

        In this case, we look for the maximum length of a board,
        and the minimum length of each piece, with this we can get
        a maximum number of pieces that will be generated from a single board,
        which is given by the formula:
        2 * floor( max_board_length / min_piece_length) + 1.

        The output length is then the input length multiplied by this value,
        plus the existing output length.
        """

        return (input_length * self.max_pieces_per_board +
                existing_output_length)

    def impose_conditions(self, model, input_list):


        # create a list to store all pieces
        all_pieces = []

        for board_index, board in enumerate(input_list):
            # create self.max_pieces_per_board - 1 variables for the cuts
            cuts = model.addVars(self.max_pieces_per_board - 1, vtype=GRB.CONTINUOUS, name=f"{self.id} cuts")

            # Force cuts to be incremental
            model.addConstrs((cuts[i] >= cuts[i - 1] for i in range(1, self.max_pieces_per_board - 1)), name=f"{self.id} incremental_cuts")

            # create variables for the pieces
            pieces = create_piece_var_list(
                model,
                self.max_pieces_per_board,
                id_prefix=f"{self.id} output ",
                start_index=board_index * self.max_pieces_per_board
                )

            # make their length equal to the difference of two cuts
            model.addConstr(pieces[0].length == cuts[0], name=f"{self.id} first_piece_length")
            model.addConstrs((pieces[i].length == cuts[i] - cuts[i - 1] for i in range(1, self.max_pieces_per_board - 1)), name=f"{self.id} piece_lengths")
            model.addConstr(pieces[self.max_pieces_per_board - 1].length == board.length - cuts[self.max_pieces_per_board - 2], name=f"{self.id} last_piece_length")

            # determine their quality: bad if (0<len and len<35)
            # if positive_length[i] is 0 then pieces[i].length is 0
            positive_length = model.addVars(self.max_pieces_per_board, vtype=GRB.BINARY, name=f"{self.id} positive_length")
            for i in range(self.max_pieces_per_board):
                piece_index = board_index * self.max_pieces_per_board + i
                model.addGenConstrIndicator(
                    positive_length[i],
                    0,
                    pieces[i].length == 0,
                    name=f"{self.id} piece_[{piece_index}]_positive_length"
                )

            below_min_length = model.addVars(self.max_pieces_per_board, vtype=GRB.BINARY, name=f"{self.id} below_min_length")
            for i in range(self.max_pieces_per_board):
                piece_index = board_index * self.max_pieces_per_board + i
                model.addGenConstrIndicator(
                    below_min_length[i],
                    0,
                    pieces[i].length >= min_piece_length,
                    name=f"{self.id} piece_[{piece_index}]_below_min_length"
                )
            bad_size = model.addVars(self.max_pieces_per_board, vtype=GRB.BINARY, name=f"{self.id} bad_size")
            for i in range(self.max_pieces_per_board):
                piece_index = board_index * self.max_pieces_per_board + i
                model.addGenConstrAnd(
                    bad_size[i],
                    [positive_length[i], below_min_length[i]],
                    name=f"{self.id} piece_[{piece_index}]_bad_size"
                )

            # Check if any piece intersects with a bad part
            bad_quality = []
            if self.max_pieces_per_board > 1:
                piece_index = board_index * self.max_pieces_per_board
                # Intersect the first piece with the bad parts?
                bad_quality.append(
                    intersect_intervals(model,
                                        0,
                                        cuts[0],
                                        board.bad_parts,
                                        name_prefix=f"{self.id} input [{board_index}] output [{piece_index}] bad_quality"
                                        )
                )
                for i in range(self.max_pieces_per_board - 2):
                    piece_index = board_index * self.max_pieces_per_board + i + 1
                    # Intersect the pieces with the bad parts?
                    bad_quality.append(
                        intersect_intervals(model,
                                            cuts[i],
                                            cuts[i + 1],
                                            board.bad_parts,
                                            name_prefix=f"{self.id} input [{board_index}] output [{piece_index}] bad_quality"
                                            )
                    )
                piece_index = board_index * self.max_pieces_per_board + self.max_pieces_per_board - 1
                bad_quality.append(
                    intersect_intervals(model,
                                        cuts[self.max_pieces_per_board - 2],
                                        board.length,
                                        board.bad_parts,
                                        name_prefix=f"{self.id} input [{board_index}] output [{piece_index}] bad_quality"
                                        )
                )
            else:
                piece_index = board_index * self.max_pieces_per_board
                bad_quality.append(
                    intersect_intervals(model,
                                        0,
                                        board.length,
                                        board.bad_parts,
                                        name_prefix=f"{self.id} input [{board_index}] output [{piece_index}] bad_quality"
                                        )
                )

            for i in range(self.max_pieces_per_board):
                piece_index = board_index * self.max_pieces_per_board + i
                pieces[i].good = model.addVar(vtype=GRB.BINARY,
                                              name=f"{self.id} output [{piece_index}] good_quality")
                model.addGenConstrIndicator(
                    pieces[i].good,
                    1,
                    bad_size[i] == 0,
                    name=f"{self.id} output [{piece_index}] good_size_indicator"
                )

                model.addGenConstrIndicator(
                    pieces[i].good,
                    1,
                    bad_quality[i] == 0,
                    name=f"{self.id} output [{piece_index}] good_quality_indicator"
                )
            
            # Add the pieces to the list of all pieces
            all_pieces.extend(pieces)
        return [], all_pieces

    def process(self,
                decisions_list,
                n_input_to_process,
                input_list):
        """
        Processes the elements in the input list specified by n_input_to_process based on the decisions
        """
        output_pieces = []
        for i in n_input_to_process:
            # Get the board from the input list
            board = input_list[i]
            # Get the decisions for this board
            decisions = decisions_list[i]
            # Cut the board based on the decisions
            pieces = self.cut_board(board, decisions)
            # Add the pieces to the output list
            output_pieces.extend(pieces)

        return output_pieces
    
    def cut_board(self,
                  board,
                  decisions):
        # TODO self not used here, maybe move to board or to Tools?
        """
        Cuts the board based on the decisions.

        Decisions are expected to be a list of cuts,
        where each cut is a float representing the position of the cut.

        it is necessary to determine whether the piece is good or bad,
        it will be bad if its length is less than the minimum length
        or if it intersects with a bad part of the board.
        """
        pieces = []
        previous_cut = 0
        for cut in decisions:
            piece_length = cut - previous_cut
            # Check if the piece is good or bad
            if (piece_length < min_piece_length or
                process_intersect_intervals(previous_cut, cut, board.bad_parts)):
                piece_good = False
            else:
                piece_good = True
            pieces.append(Piece(length=piece_length, good=piece_good))
        return pieces
