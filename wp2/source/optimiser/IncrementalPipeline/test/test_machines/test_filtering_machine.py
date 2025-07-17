"""Contains tests for the filtering machine."""

from IncrementalPipeline.Machines.FilteringMachine import FilteringMachine
from IncrementalPipeline.test.test_machines.utils.output_from_input import can_machine_produce_output_from_input
from IncrementalPipeline.Objects.piece import Piece, PieceVars
from IncrementalPipeline.Objects.board import Board, BoardVars
import pytest

def test_filtering_machine_valid_identity():
    """
    Tests if the filtering machine can handle an identity case
    where the input is the same as the output.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100), Piece(length=200)]
    status = can_machine_produce_output_from_input(machine, input_list, input_list)
    assert status == 2  # GRB.OPTIMAL

def test_filtering_machine_valid_filtering_case_1():
    """
    Tests if the filtering machine can handle a valid filtering case
    where the output is a filtered version of the input.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100), Piece(length=200)]
    expected_output = [Piece(length=100), Piece(length=0)]
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 2  # GRB.OPTIMAL

def test_filtering_machine_valid_filtering_case_2():
    """
    Tests if the filtering machine can handle a valid filtering case
    where the output is a filtered version of the input.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100), Piece(length=200)]
    expected_output = [Piece(length=200), Piece(length=0)]
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 2  # GRB.OPTIMAL

def test_filtering_machine_invalid_filtering_case_1():
    """
    Tests if the filtering machine can handle an invalid filtering case
    where the output is a filtered version of the input, but the kept elements are not moved to the front.
    """
    # TODO In the future, we might want to change this behavior to keep pieces where they are and make them 0 if not kept.
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100), Piece(length=200)]
    expected_output = [Piece(length=0), Piece(length=200)]
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 3  # GRB.INFEASIBLE

def test_filtering_machine_invalid_reorder():
    """
    Tests if the filtering machine correctly identifies an invalid case
    where the output cannot be produced from the input.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100), Piece(length=200)]
    expected_output = [Piece(length=200), Piece(length=100)]  # Invalid output
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 3  # GRB.INFEASIBLE

def test_filtering_machine_invalid_change_2():
    """
    Tests if the filtering machine correctly identifies an invalid case
    where the output cannot be produced from the input.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100), Piece(length=200)]
    expected_output = [Piece(length=100), Piece(length=300)]  # Invalid output
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 3  # GRB.INFEASIBLE

def test_filtering_machine_invalid_change_1():
    """
    Tests if the filtering machine correctly identifies an invalid case
    where the output cannot be produced from the input.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100)]
    expected_output = [Piece(length=200)]  # Invalid output
    status = can_machine_produce_output_from_input(machine, input_list, expected_output)
    assert status == 3  # GRB.INFEASIBLE

def test_filtering_machine_invalid_increase_list():
    """
    Tests if the filtering machine correctly identifies an invalid case
    where the output cannot be produced from the input.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100)]
    expected_output = [Piece(length=100), Piece(length=100)]  # Invalid output
    with pytest.raises(ValueError, match="does not match the desired output list"):
        can_machine_produce_output_from_input(machine, input_list, expected_output)

def test_filtering_machine_invalid_decrease_list():
    """
    Tests if the filtering machine correctly identifies an invalid case
    where the output cannot be produced from the input.
    """
    machine = FilteringMachine(id="filtering_machine_test")
    input_list = [Piece(length=100), Piece(length=100)]
    expected_output = [Piece(length=100)]  # Invalid output
    with pytest.raises(ValueError, match="does not match the desired output list"):
        can_machine_produce_output_from_input(machine, input_list, expected_output)

# def test_filtering_machine_valid_board_identity():
#     """
#     Tests if the filtering machine can handle an identity case
#     where the input is the same as the output for boards.
#     """
#     machine = FilteringMachine(id="filtering_machine_test")
#     input_list = [Board(length=100), Board(length=200)]
#     status = can_machine_produce_output_from_input(machine, input_list, input_list)
#     assert status == 2  # GRB.OPTIMAL