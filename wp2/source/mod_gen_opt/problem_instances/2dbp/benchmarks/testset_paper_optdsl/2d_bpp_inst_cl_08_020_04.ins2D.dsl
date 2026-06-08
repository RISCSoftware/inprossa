NBOXES : int = 20
NITEMS : int = 20
MAX_BOX_WIDTH : int = 100
MAX_BOX_HEIGHT : int = 100

BOX_WIDTH_CAPACITIES : DSList(NBOXES, DSInt()) = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
BOX_HEIGHT_CAPACITIES : DSList(NBOXES, DSInt()) = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]

ITEM_WIDTHS : DSList(NITEMS, DSInt()) = [11, 84, 18, 78, 27, 8, 40, 16, 54, 2, 24, 65, 45, 7, 79, 26, 47, 24, 76, 99]
ITEM_HEIGHTS : DSList(NITEMS, DSInt()) = [79, 31, 91, 55, 87, 88, 68, 74, 53, 98, 88, 82, 92, 80, 23, 74, 35, 71, 75, 55]

assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))
x_positions: DSList(NITEMS, DSInt(0, MAX_BOX_WIDTH - 1))
y_positions: DSList(NITEMS, DSInt(0, MAX_BOX_HEIGHT - 1))

def all_assigned(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    assigned: DSList(NITEMS, DSInt())
    for i in range(0, NBOXES):
        for j in range(0, NITEMS):
            if assignments[j] == i:
                assigned[j] = 1
    for k in range(0, NITEMS):
        assert assigned[k] != 0

def not_exceed_2d(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    used: DSList(NBOXES, DSInt(0, 1))
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
