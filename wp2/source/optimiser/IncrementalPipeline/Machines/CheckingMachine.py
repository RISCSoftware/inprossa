"""Defines a machine that checks a list of pieces."""

from IncrementalPipeline.Machines.GenericMachine import GenericMachine
from IncrementalPipeline.Objects.piece import Piece, PieceVars
from IncrementalPipeline.Tools.simple_computations import (
    compute_max_pieces_per_layer,
    layer_length,
    min_consecutive_distance,
    compute_forbidden_zones
)
from gurobipy import GRB, quicksum, Model
from IncrementalPipeline.Tools.or_functions import add_or_constraints


class CheckingMachine(GenericMachine):
    """
    A machine that checks that a list of pieces fits the purpose.

    This machine expects a list of Piece objects as input
    and does not produce any output.
    """

    def __init__(self, id: str, current_beam: int = 0):
        super().__init__(id=f"CheckingMachine-{id}",
                         input_type=PieceVars,
                         output_type=None)

    def impose_conditions(self, model, input_list: list) -> None:
        """
        Defines the constraints that the pieces must satisfy.
        All pieces must be good.

        They must form layers of a beam,
        """
        lengths_list = [piece.length for piece in input_list]
        input_length = len(lengths_list)
        max_pieces_per_layer = compute_max_pieces_per_layer()

        # break the input list into layers
        layers = [lengths_list[i:i + max_pieces_per_layer]
                  for i in range(0, input_length, max_pieces_per_layer)]

        # Layers never exceed layer_length.
        self.layers_below_length(model, layers)

        # If one layer is not complete, then the next layer is empty.
        self.layers_are_complete(model, layers)

        # Check that there are no two cuts too close to each other
        # in two consecutive layers.
        self.cuts_not_too_close(model, layers)

        # Check that there are no cuts in the global danger zones
        self.cuts_not_in_forbidden_zones(model, layers)

        return dict(), []

    def layers_below_length(self, model, layers: list):
        """
        Each layer must not exceed the layer length.
        """
        for i, layer in enumerate(layers):
            model.addConstr(
                quicksum(layer) <= layer_length,
                name=f"{self.id} layer_length[{i}]"
            )

    def layers_are_complete(self, model, layers: list):
        """
        If a layer is not complete the next layer must be empty.
        """
        n_layers = len(layers)
        for i in range(n_layers - 1):
            # Do the reverse, if a layer is not empty,
            # the previous one must be complete

            # Similarly, or if layer[i + 1] is empty,
            # or layer[i] is complete.

            upper_layer_empty = (quicksum(layers[i + 1]), '==', 0)
            lower_layer_complete = (quicksum(layers[i]), '==', layer_length)

            # Add OR constraints for the layers
            add_or_constraints(
                model,
                [
                    upper_layer_empty,
                    lower_layer_complete
                ],
                name_prefix=f"{self.id} layer_complete[{i}]"
            )

    def cuts_not_too_close(self, model, layers: list):
        """
        Check that there are no two cuts too close to each other
        in two consecutive layers.
        """
        for i in range(len(layers) - 1):
            # Check the cuts in layer[i] and layer[i + 1]
            for j in range(1, len(layers[i])):
                # j first pieces in layer[i]
                # at most all but the last piece
                # None and all are ignored
                for k in range(1, len(layers[i + 1])):
                    # k first pieces in layer[i + 1]
                    # at most all but the last piece

                    # If the cut in layer i + 1 is before the cut in layer i,
                    cut_lower_before = (quicksum(layers[i + 1][:k]) -
                                        quicksum(layers[i][:j]),
                                        '>=',
                                        min_consecutive_distance)
                    # If the cut in layer i + 1 is after the cut in layer i,
                    cut_upper_before = (quicksum(layers[i][:j]) -
                                        quicksum(layers[i + 1][:k]),
                                        '>=',
                                        min_consecutive_distance)
                    # one of these two conditions must hold
                    add_or_constraints(
                        model,
                        [
                            cut_lower_before,
                            cut_upper_before
                        ],
                        name_prefix=f"{self.id} cuts_[{i}]_{j}_{k}"
                    )

    def cuts_not_in_forbidden_zones(self, model, layers: list):
        """
        Check that there are no cuts in the global danger zones.
        """
        for i, layer in enumerate(layers):
            for j in range(1, len(layer) + 1):
                # Check if the piece is in a forbidden zone
                forbidden_zones = compute_forbidden_zones()
                for zone_index, zone in enumerate(forbidden_zones):
                    cut_before_forbidden_zone = (quicksum(layer[:j]),
                                                 '<=',
                                                 zone[0])
                    cut_after_forbidden_zone = (quicksum(layer[:j]),
                                                '>=',
                                                zone[1])

                    # Add OR constraints for the forbidden zones
                    add_or_constraints(
                        model,
                        [
                            cut_before_forbidden_zone,
                            cut_after_forbidden_zone
                        ],
                        name_prefix=f"{self.id} forbidden_zone_[{i}]_{j}_{zone_index}"
                    )
