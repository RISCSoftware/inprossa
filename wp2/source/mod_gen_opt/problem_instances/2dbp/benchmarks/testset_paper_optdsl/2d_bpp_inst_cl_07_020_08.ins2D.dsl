NBOXES : int = 20
NITEMS : int = 20
MAX_BOX_WIDTH : int = 100
MAX_BOX_HEIGHT : int = 100

BOX_WIDTH_CAPACITIES : DSList(NBOXES, DSInt()) = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
BOX_HEIGHT_CAPACITIES : DSList(NBOXES, DSInt()) = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]

ITEM_WIDTHS : DSList(NITEMS, DSInt()) = [68, 72, 67, 84, 67, 81, 69, 97, 73, 98, 80, 84, 83, 34, 99, 19, 76, 88, 86, 23]
ITEM_HEIGHTS : DSList(NITEMS, DSInt()) = [43, 39, 42, 20, 19, 5, 23, 43, 6, 33, 17, 27, 55, 81, 22, 22, 17, 24, 89, 29]

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

def not_exceed_2d(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
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
objective: DSInt(0, NBOXES) = not_exceed_2d(assignments)

minimize(objective)
