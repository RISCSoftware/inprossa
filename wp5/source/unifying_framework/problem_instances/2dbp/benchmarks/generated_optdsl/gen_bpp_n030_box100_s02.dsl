# Auto-generated 2D bin-packing instance via Tools/generate_2dbp_instances.py.
# Boxes are identical squares of size 100x100; item sizes are drawn
# uniformly in [20, 55].  NBOXES == NITEMS (one box slot per
# item, so a solution within one box per item always exists in this encoding).

NBOXES : int = 30
NITEMS : int = 30
MAX_BOX_WIDTH : int = 100
MAX_BOX_HEIGHT : int = 100

BOX_WIDTH_CAPACITIES : DSList(NBOXES, DSInt()) = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
BOX_HEIGHT_CAPACITIES : DSList(NBOXES, DSInt()) = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]

ITEM_WIDTHS : DSList(NITEMS, DSInt()) = [23, 25, 25, 43, 30, 39, 36, 33, 22, 30, 47, 45, 52, 43, 54, 48, 52, 37, 22, 21, 43, 49, 40, 44, 47, 53, 30, 55, 31, 35]
ITEM_HEIGHTS : DSList(NITEMS, DSInt()) = [34, 21, 31, 40, 31, 28, 52, 52, 43, 52, 55, 31, 48, 46, 53, 43, 42, 43, 48, 30, 45, 49, 53, 35, 51, 37, 51, 52, 52, 42]

assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))
x_positions: DSList(NITEMS, DSInt(0, MAX_BOX_WIDTH - 1))
y_positions: DSList(NITEMS, DSInt(0, MAX_BOX_HEIGHT - 1))

def all_assigned(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    assigned: DSList(NITEMS, DSInt()) = [0] * NITEMS
    for i in range(0, NBOXES):
        for j in range(0, NITEMS):
            if assignments[j] == i:
                assigned[j] = 1
    for k in range(0, NITEMS):
        assert assigned[k] != 0

def number_of_boxes(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    used: DSList(NBOXES, DSInt(0, 1)) = [0] * NBOXES
    obj = 0
    for i in range(0, NBOXES):
        used[i] = 0

        for j in range(0, NITEMS):
            if assignments[j] == i:
                used[i] = 1

        obj = obj + used[i]

    return obj


def no_overlap(
    assignments: DSList(NITEMS, DSInt(0, NBOXES - 1)),
    x_positions: DSList(NITEMS, DSInt(0, MAX_BOX_WIDTH - 1)),
    y_positions: DSList(NITEMS, DSInt(0, MAX_BOX_HEIGHT - 1)),
):
    # Item must fit into its selected box dimensions.
    for i in range(0, NITEMS):
        box_i = assignments[i]
        assert x_positions[i] + ITEM_WIDTHS[i] <= BOX_WIDTH_CAPACITIES[box_i]
        assert y_positions[i] + ITEM_HEIGHTS[i] <= BOX_HEIGHT_CAPACITIES[box_i]

    # Any two items in the same box must not overlap.
    for i in range(0, NITEMS):
        for j in range(i + 1, NITEMS):
            if assignments[i] == assignments[j]:
                assert (
                    x_positions[i] + ITEM_WIDTHS[i] <= x_positions[j]
                    or x_positions[j] + ITEM_WIDTHS[j] <= x_positions[i]
                    or y_positions[i] + ITEM_HEIGHTS[i] <= y_positions[j]
                    or y_positions[j] + ITEM_HEIGHTS[j] <= y_positions[i]
                )

all_assigned(assignments)
no_overlap(assignments, x_positions, y_positions)
objective: DSInt(0, NBOXES) = number_of_boxes(assignments)

minimize(objective)
