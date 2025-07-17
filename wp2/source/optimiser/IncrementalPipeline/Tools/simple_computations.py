"""This file will contain simple computations that can be used
in various parts of the codebase."""
from IncrementalPipeline.config_loader import get_config

config = get_config()
general_info = config["BeamConfiguration"]
max_board_length = general_info["BoardMaxLength"]
min_piece_length = general_info["MinLengthOfBoardInLayer"]
layer_length = general_info["BeamLength"]
min_consecutive_distance = general_info["GapToBoardAbutInConsecutiveLayers"]
forbidden_zones = general_info["StaticForbiddenZones"]


def compute_max_pieces_per_board() -> int:
    """
    Computes the maximum number of pieces that can be cut from a board.

    The formula used is:
    2 * floor(max_board_length / min_piece_length) + 1
    """

    return (max_board_length // min_piece_length)  # * 2 + 1  # Commented out for efficiency


max_pieces_per_board = compute_max_pieces_per_board()


def compute_max_pieces_per_layer() -> int:
    """
    Computes the maximum number of pieces that can be in a layer.

    The formula used is:
    ceil(layer_length / min_piece_length)
    """

    return layer_length // min_piece_length + 1

max_pieces_per_layer = compute_max_pieces_per_layer()


def compute_min_distance_in_consecutive_layers() -> int:
    """
    Computes the minimum distance between cuts in consecutive layers.
    """
    return min_consecutive_distance


def compute_forbidden_zones() -> list:
    """
    Returns the list of forbidden zones.
    """
    my_forbidden_zones = []
    for zone in forbidden_zones:
        my_forbidden_zones.append([zone["Begin"], zone["End"]])
    return my_forbidden_zones

my_forbidden_zones = compute_forbidden_zones()