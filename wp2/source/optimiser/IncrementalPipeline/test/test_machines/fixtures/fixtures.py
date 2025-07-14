from IncrementalPipeline.Objects.board import Board, BoardVars
from IncrementalPipeline.Objects.piece import Piece, PieceVars
import pytest

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
def desired_output1():
    return [
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

@pytest.fixture
def desired_output2():
    return [
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

@pytest.fixture
def desired_output3():
    return [
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