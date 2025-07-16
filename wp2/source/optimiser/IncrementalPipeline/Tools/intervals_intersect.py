"""We define a variable that checks if a piece between two cuts intersects any bad part of a board."""

# First define for each bad interval a binary variable

# if this binary variable is 1 (intersects) then endbadpart > startpiece and startbadpart < endpiece
from gurobipy import Model, GRB
from IncrementalPipeline.Objects.board import Board

def intersect_intervals(model: Model, start_cut:int, end_cut, bad_intervals, name_prefix: str = ""):
    """
    Adds constraints to the model to ensure that no piece intersects with any bad part of the board.

    This function could always return intersection to be True,
    but can only return False if there is no intersection.

    This is not a big issue here as the 'bad' option here is
    to have an intersection with a bad part of the board.
    In the sense that it is what makes the objective function grow.
    """
    # create a list of binary variables for each bad interval
    # that indicates whether the piece intersects with the bad part
    possible_intersections = []
    for i, interval in enumerate(bad_intervals):
        start_bad_interval, end_bad_interval = interval
        intersect = model.addVar(vtype=GRB.BINARY, name=f"{name_prefix} intersect_bad_part_{i}")
        end_possibly_overlaps = model.addVar(vtype=GRB.BINARY, name=f"{name_prefix} end_overlaps_bad_part_{i}")
        start_possibly_overlaps = model.addVar(vtype=GRB.BINARY, name=f"{name_prefix} start_overlaps_bad_part_{i}")
        # If the interval intersects with the piece defined by start_cut and end_cut,
        # then both starts must be less than the end of the other

        # If the start of the bad part cannot possibly overlap with the end of the piece,
        # then the start of the bad part must be greater than or equal to the end of the piece
        model.addGenConstrIndicator(
            start_possibly_overlaps,
            0,
            start_bad_interval >= end_cut,
            name=f"{name_prefix} intersect_bad_part_{i}_start_overlaps"
        )
        # If end cannot possibly overlap with the start of the bad part,
        # then the start of the piece must be greater than or equal to the end of the bad part
        model.addGenConstrIndicator(
            end_possibly_overlaps,
            0,
            start_cut >= end_bad_interval,
            name=f"{name_prefix} intersect_bad_part_{i}_end_overlaps"
        )
        # Only if both overlap possibilities are preserved, the intervals intersect
        model.addGenConstrAnd(
            intersect,
            [end_possibly_overlaps, start_possibly_overlaps],
            name=f"{name_prefix} intersect_bad_part_{i}_indicator"
        )
        possible_intersections.append(intersect)
    
    # Add a variable to check if any intersection occurs
    any_intersection = model.addVar(vtype=GRB.BINARY, name=f"{name_prefix} any_intersection")
    model.addGenConstrOr(
        any_intersection,
        possible_intersections,
        name=f"{name_prefix} any_intersection_indicator"
    )

    return any_intersection


def process_intersect_intervals(start_cut, end_cut, bad_intervals):
    """
    Returns True if the piece defined by start_cut and end_cut intersects with any bad part of the board.
    """
    for interval in bad_intervals:
        if start_cut < interval[1] and end_cut > interval[0]:
            return True
    return False