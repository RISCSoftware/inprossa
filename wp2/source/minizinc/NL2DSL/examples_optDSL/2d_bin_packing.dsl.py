"""
BOX_WIDTH = 10
BOX_HEIGHT = 6

MAX_ITEM_HEIGHT = 10
MAX_ITEM_WIDTH = 10
GIVEN_ITEMS = [
    Item(width=4,
        height=3
    ),
    Item(width=3,
        height=2
    ),
    Item(width=5,
        height=3
    ),
    Item(width=2,
        height=4
    ),
    Item(width=3,
        height=3
    ),
    Item(width=5,
        height=2
    )
]
Item = DSRecord({
    "width": DSInt(0, MAX_ITEM_WIDTH),
    "height": DSInt(0, MAX_ITEM_HEIGHT)
})
Position = DSRecord({
    "x": DSInt(0, BOX_WIDTH),
    "y": DSInt(0, BOX_LENGTH)
})

initial_items: list[Item] = GIVEN_ITEMS
N_ITEMS = len(initial_items)
item_positions: DSList(N_ITEMS, Position)

# For each item i: assign bin b_i in [0..m-1]
item_bin_assignments: DSList(N_ITEMS, DSInt)
assert all(
   0 <= item_bin_assignment and
   item_bin_assignment < N_ITEMS
   for item_bin_assignment in item_bin_assignments
)

# For each of the bin N_ITEMS: whether it is used
used_bins: DSList(N_ITEMS, bool)

def pack_items(initial_items: DSList(N_ITEMS, Item),
                item_positions: DSList(N_ITEMS, Position),
                used_bins: DSList(N_ITEMS, bool),
                N_ITEMS: int,
                BOX_WIDTH: int,
                BOX_HEIGHT: int):
    # If item i is assigned to bin j, then bin j is “used”
    for i in range(N_ITEMS):
        for j in range(N_ITEMS):
            if item_bin_assignments[i] == j:
                assert used_bins[j] == True

    # Non‐overlap: for each pair of items i<j, if they are in same bin then they must not overlap
    for i in range(N_ITEMS):
        assert item_positions[i].x >= 0
        assert item_positions[i].y >= 0
        assert item_positions[i].x + initial_items[i].width <= BOX_WIDTH
        assert item_positions[i].y + initial_items[i].height <= BOX_HEIGHT
        for j in range(i+1, N_ITEMS):
            wi, hi = initial_items[i]
            wj, hj = initial_items[j]
            if item_bin_assignments[i] == item_bin_assignments[j]: #then ( item i is left or right or above or below j )
                assert item_positions[i].x + initial_items[i].width <= item_positions[j].x,
                assert item_positions[j].x + initial_items[j].width <= item_positions[i].x,
                assert item_positions[i].y + initial_items[i].height <= item_positions[j].y,
                assert item_positions[j].y + initial_items[j].height <= item_positions[i].y

    # Link used_bins[j] to whether any item uses bin j:
    # (At least one item with b[i]==j) ⇒ used_bins[j]
    for j in range(m):
        # if used_bins[j] is false, then no item i can have used_bins[i]==j
        for i in range(n):
            if not used_bins[j]:
                assert item_bin_assignments[i] != j
    return used_bins

for i in range(N_ITEMS):
    if used_bins[i]:
        objective += 1

objective = sum( If(u[j], 1, 0) for j in range(m) )
"""