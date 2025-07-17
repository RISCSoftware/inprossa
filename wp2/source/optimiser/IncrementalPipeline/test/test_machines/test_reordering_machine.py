"""Contains tests for the reordering machine."""

from IncrementalPipeline.Machines.ReorderingMachine import ReorderMachine
from IncrementalPipeline.test.test_machines.utils.output_from_input import can_machine_produce_output_from_input
from IncrementalPipeline.Objects.piece import Piece, PieceVars
from IncrementalPipeline.Objects.board import Board, BoardVars


def test_reordering_machine_valid_identity():
    """
    Tests if the reordering machine can handle an identity case
    where the input is the same as the output.
    """
    machine = ReorderMachine(id="reorder_machine_test", input_type=PieceVars)
    input_list = [Piece(length=100), Piece(length=200)]
    status = can_machine_produce_output_from_input(machine, input_list, input_list)
    assert status == 2  # GRB.OPTIMAL

def test_reordering_machine_valid_2_reorder():
    """
    Tests if the reordering machine can handle a valid reordering case with two pieces.
    """
    machine = ReorderMachine(id="reorder_machine_test", input_type=PieceVars)
    input_list = [Piece(length=100), Piece(length=200)]
    expected_output = [Piece(length=200), Piece(length=100)]
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 2  # GRB.OPTIMAL

def test_reordering_machine_valid_3_reorder():
    """
    Tests if the reordering machine can handle a valid reordering case.
    """
    machine = ReorderMachine(id="reorder_machine_test", input_type=PieceVars)
    input_list = [Piece(length=100), Piece(length=200), Piece(length=300)]
    expected_output = [Piece(length=200), Piece(length=300), Piece(length=100)]
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 2  # GRB.OPTIMAL

def test_reordering_machine_invalid_3_reorder():
    """
    Tests if the reordering machine correctly identifies an invalid case
    with three pieces where the output cannot be produced from the input.
    The last element goes 2 places to the front, which is not allowed.
    """
    machine = ReorderMachine(id="reorder_machine_test", input_type=PieceVars)
    input_list = [Piece(length=100), Piece(length=200), Piece(length=300)]
    expected_output = [Piece(length=300), Piece(length=100), Piece(length=200)]  # Invalid output
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 3  # GRB.INFEASIBLE

def test_reordering_machine_invalid():
    """
    Tests if the reordering machine correctly identifies an invalid case
    where the output cannot be produced from the input.
    """
    machine = ReorderMachine(id="reorder_machine_test", input_type=PieceVars)
    input_list = [Piece(length=100), Piece(length=200)]
    expected_output = [Piece(length=300), Piece(length=400)]  # Invalid output
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 3  # GRB.INFEASIBLE