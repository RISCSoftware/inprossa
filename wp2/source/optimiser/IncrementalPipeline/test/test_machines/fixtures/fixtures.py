from IncrementalPipeline.Objects.board import Board, BoardVars
from IncrementalPipeline.Objects.piece import Piece, PieceVars
import pytest
from IncrementalPipeline.Tools.simple_computations import max_pieces_per_board
from IncrementalPipeline.test.test_machines.utils.empty_piece_filler import empty_piece_filler

# ----------------------------
# Fixtures: Sample Boards and Outputs
# ----------------------------

@pytest.fixture
def board1():
    return Board(length=500, bad_parts=[(90, 100)], curved_parts=[])

@pytest.fixture
def board2():
    return Board(length=500, bad_parts=[(100, 150)], curved_parts=[])

@pytest.fixture
def piece_list4():
    output_board_1 = empty_piece_filler([
        Piece(length=40, good=0),
        Piece(length=50, good=1),
        Piece(length=20, good=0),
        Piece(length=100, good=1),
        Piece(length=290, good=1)],
        max_pieces_per_board)
    output_board_2 = empty_piece_filler([
        Piece(length=50, good=1),
        Piece(length=100, good=0),
        Piece(length=350, good=1),
    ], max_pieces_per_board)

    return output_board_1 + output_board_2

@pytest.fixture
def piece_list1():
    return empty_piece_filler([
        Piece(length=90, good=1),
        Piece(length=10, good=0),
        Piece(length=400, good=1)
    ], max_pieces_per_board)

@pytest.fixture
def piece_list2():
    output_board_1 = empty_piece_filler([
        Piece(length=130, good=1),
        Piece(length=200, good=1),
        Piece(length=20, good=1),
        Piece(length=100, good=1),
        Piece(length=50, good=1)],
        max_pieces_per_board)
    output_board_2 = empty_piece_filler([
        Piece(length=500, good=1)
    ], max_pieces_per_board)

    return output_board_1 + output_board_2

@pytest.fixture
def piece_list3():
    output_board_1 = empty_piece_filler([
        Piece(length=90, good=1),
        Piece(length=410, good=1),
    ], max_pieces_per_board)
    output_board_2 = empty_piece_filler([
        Piece(length=50, good=1),
        Piece(length=50, good=1),
        Piece(length=50, good=1),
        Piece(length=250, good=1),
        Piece(length=40, good=1),
        Piece(length=60, good=1),
    ], max_pieces_per_board)

    return output_board_1 + output_board_2