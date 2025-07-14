
"""
Tests for the CuttingMachine class using various input boards and expected outputs.
"""

from IncrementalPipeline.test.test_machines.utils.output_from_input import can_machine_produce_output_from_input
from IncrementalPipeline.test.test_machines.fixtures.fixtures import board1, board2, piece_list1, piece_list3, piece_list4
from IncrementalPipeline.Machines.CuttingMachine import CuttingMachine



def test_cutting_machine_valid_single_board(board1, piece_list1):
    machine = CuttingMachine(id="cutting_machine_test")
    status = can_machine_produce_output_from_input(machine, [board1], piece_list1)
    assert status == 2  # GRB.OPTIMAL


def test_cutting_machine_invalid_single_board(board2, piece_list1):
    machine = CuttingMachine(id="cutting_machine_test")
    status = can_machine_produce_output_from_input(machine, [board2], piece_list1)
    assert status == 3  # GRB.INFEASIBLE


def test_cutting_machine_invalid_multiple_boards(board1, board2, piece_list3):
    machine = CuttingMachine(id="cutting_machine_test")
    status = can_machine_produce_output_from_input(machine, [board1, board2], piece_list3)
    assert status == 3  # GRB.INFEASIBLE

def test_cutting_machine_valid_multiple_boards(board1, board2, piece_list4):
    machine = CuttingMachine(id="cutting_machine_test")
    status = can_machine_produce_output_from_input(machine, [board1, board2], piece_list4)
    assert status == 2  # GRB.OPTIMAL

