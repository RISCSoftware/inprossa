"""
This file contains tests for the CuttingMachine class.

Given an input list of boards, it checks if the CuttingMachine
can produce a given output list of pieces.
"""
from gurobipy import Model, GRB
import pytest

from IncrementalPipeline.Machines.CuttingMachine import CuttingMachine
from IncrementalPipeline.Objects.board import Board, BoardVars
from IncrementalPipeline.Objects.piece import Piece, PieceVars

board1 = Board(length=500, bad_parts=[(90, 100)], curved_parts=[])
board2 = Board(length=500, bad_parts=[(100, 150)], curved_parts=[])

desired_pieces1 = [
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=90, good=1, id="piece-0-board-0"),
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=0, good=0, id="piece-1-board-0"),
    Piece(length=10, good=0, id="piece-2-board-0"),
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=400, good=1, id="piece-0-board-0"),
    Piece(length=0, good=1, id="piece-0-board-0"),
]

desired_pieces2 = [
    Piece(length=130, good=1, id="piece-0-board-1"),
    Piece(length=200, good=1, id="piece-1-board-1"),
    Piece(length=20, good=1, id="piece-2-board-1"),
    Piece(length=0, good=1, id="piece-3-board-1"),
    Piece(length=100, good=1, id="piece-4-board-1"),
    Piece(length=0, good=1, id="piece-5-board-1"),
    Piece(length=50, good=1, id="piece-6-board-1"),
    Piece(length=0, good=1, id="piece-7-board-1"),
    Piece(length=0, good=1, id="piece-8-board-1"),
    Piece(length=0, good=1, id="piece-9-board-1"),
    Piece(length=0, good=1, id="piece-10-board-1"),
    Piece(length=0, good=1, id="piece-11-board-1"),
    Piece(length=0, good=1, id="piece-0-board-1"),
    Piece(length=0, good=1, id="piece-1-board-1"),
    Piece(length=0, good=1, id="piece-2-board-1"),
    Piece(length=0, good=1, id="piece-3-board-1"),
    Piece(length=0, good=1, id="piece-4-board-1"),
    Piece(length=0, good=1, id="piece-5-board-1"),
    Piece(length=0, good=1, id="piece-6-board-1"),
    Piece(length=0, good=1, id="piece-7-board-1"),
    Piece(length=0, good=1, id="piece-8-board-1"),
    Piece(length=500, good=1, id="piece-9-board-1"),
    Piece(length=0, good=1, id="piece-10-board-1"),
    Piece(length=0, good=1, id="piece-11-board-1"),
]

desired_pieces3 = [
    Piece(length=0, good=1, id="piece-0-board-0"),
    Piece(length=0, good=1, id="piece-1-board-0"),
    Piece(length=90, good=1, id="piece-2-board-0"),
    Piece(length=0, good=1, id="piece-3-board-0"),
    Piece(length=0, good=1, id="piece-4-board-0"),
    Piece(length=0, good=1, id="piece-5-board-0"),
    Piece(length=0, good=1, id="piece-6-board-0"),
    Piece(length=0, good=1, id="piece-7-board-0"),
    Piece(length=0, good=1, id="piece-8-board-0"),
    Piece(length=0, good=1, id="piece-9-board-0"),
    Piece(length=0, good=1, id="piece-10-board-0"),
    Piece(length=410, good=1, id="piece-11-board-0"),
    Piece(length=0, good=1, id="piece-0-board-1"),
    Piece(length=0, good=1, id="piece-1-board-1"),
    Piece(length=50, good=1, id="piece-2-board-1"),
    Piece(length=0, good=1, id="piece-3-board-1"),
    Piece(length=0, good=1, id="piece-4-board-1"),
    Piece(length=0, good=1, id="piece-5-board-1"),
    Piece(length=50, good=1, id="piece-6-board-1"),
    Piece(length=0, good=1, id="piece-7-board-1"),
    Piece(length=50, good=1, id="piece-8-board-1"),
    Piece(length=250, good=1, id="piece-9-board-1"),
    Piece(length=40, good=1, id="piece-10-board-1"),
    Piece(length=60, good=1, id="piece-11-board-1"),
]

def test_cutting_machine():
    cutting_machine = CuttingMachine(id="test_cutting_machine")
    list_input_boards = [
        [board1],
        [board2],
        [board1, board2],
    ]
    list_desired_pieces = [
        desired_pieces1,
        desired_pieces1,
        desired_pieces3,
    ]
    list_results = [
        GRB.OPTIMAL,
        GRB.INFEASIBLE,
        GRB.OPTIMAL
    ]
    for input_boards, expected_status, desired_pieces in zip(list_input_boards, list_results, list_desired_pieces):

        model = Model()
        vars_input_boards = [BoardVars(model, board=board, id=f"board-{i}")
                            for i, board in enumerate(input_boards)]
        decisions, output_pieces = cutting_machine.impose_conditions(model, vars_input_boards)
        
        for i, piece in enumerate(output_pieces):
            my_var = model.addVar(vtype=GRB.BINARY, name=f"my_var-{i}")
            model.addConstr(
                my_var == 1,
                name=f"my_var_{i}"
            )
            piece.conditional_equality(model, my_var, 1, desired_pieces[i])
        
        model.optimize()
        assert model.status == expected_status, f"Model should be {expected_status} but is {model.status}"
