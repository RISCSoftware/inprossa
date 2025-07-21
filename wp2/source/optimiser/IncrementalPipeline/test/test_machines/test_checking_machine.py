"""Contains tests for the checking machine."""

from IncrementalPipeline.Machines.CheckingMachine import CheckingMachine
from IncrementalPipeline.test.test_machines.utils.output_from_input import (
    can_machine_produce_output_from_input
)
from IncrementalPipeline.Objects.piece import Piece
from IncrementalPipeline.Tools.simple_computations import (
    layer_length,
    my_forbidden_zones,
    min_consecutive_distance,
    max_pieces_per_layer
)

#####
# 
#####


def test_checking_machine_complete_first_layer():
    """
    Tests if the checking machine can handle a complete first layer of pieces.
    """
    machine = CheckingMachine(id="checking_machine_test")
    input_list = [Piece(length=layer_length)]
    status = can_machine_produce_output_from_input(machine, input_list, [])
    assert status == 2  # GRB.OPTIMAL


def test_checking_machine_complete_second_layer():
    """
    Tests if the checking machine can handle a complete second layer of pieces.
    """
    machine = CheckingMachine(id="checking_machine_test")
    input_list = (
        [Piece(length=layer_length)] +
        [Piece(length=0)] * (max_pieces_per_layer - 1) +  # First layer completed
        [Piece(length=layer_length)]
    )
    status = can_machine_produce_output_from_input(machine, input_list, [])
    assert status == 2  # GRB.OPTIMAL


def test_checking_machine_forbidden_zones():
    """
    Tests if the checking machine correctly identifies pieces in forbidden zones.
    """
    machine = CheckingMachine(id="checking_machine_test")
    for forbidden_zone in my_forbidden_zones:
        input_list = [Piece(length=(forbidden_zone[0] + forbidden_zone[1]) / 2)]
        status = can_machine_produce_output_from_input(machine, input_list, [])
        assert status == 3  # GRB.INFEASIBLE


def test_checking_machine_consecutive_distance():
    """
    Tests if the checking machine correctly identifies pieces that are too close together.
    """
    machine = CheckingMachine(id="checking_machine_test")
    input_list = (
        [Piece(length=my_forbidden_zones[0][0]), 
         Piece(length=layer_length - my_forbidden_zones[0][0])] + # First layer length completed
        [Piece(length=0)] * (max_pieces_per_layer - 2) +  # Fill the rest of the first layer
        [Piece(length=my_forbidden_zones[0][0] - min_consecutive_distance/2), Piece(length=0)]#
        # A piece is necessary at the end because the last piece is not checked in consecutive distance
    )
    status = can_machine_produce_output_from_input(machine, input_list, [])
    # Pieces 1 and 3 would be too close together and in different layers
    # so the model should be infeasible.
    assert status == 3  # GRB.INFEASIBLE

def test_layers_start_with_zeros():
    """
    Tests if the checking machine correctly handles layers that start with zeros.
    """
    machine = CheckingMachine(id="checking_machine_test")
    input_list = (
        [Piece(length=0)] * (max_pieces_per_layer - 1) +  # First layer starts with zeros
        [Piece(length=layer_length)] +  # Complete the first layer
        [Piece(length=0)] * (max_pieces_per_layer - 1) +  # Second layer starts with zeros
        [Piece(length=layer_length)]  # Complete the second layer
    )
    status = can_machine_produce_output_from_input(machine, input_list, [])
    assert status == 2  # GRB.OPTIMAL
