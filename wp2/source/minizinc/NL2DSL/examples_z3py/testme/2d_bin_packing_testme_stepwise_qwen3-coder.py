import json

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver
from structures_utils import initial_clean_up

code = """
# --- Objects ---


# Object type for items with width and height
Item = DSRecord({
    "width": DSInt(lb=1, ub=300),
    "height": DSInt(lb=1, ub=300)
})

# Object type for position (x, y) of an item within a box
Position = DSRecord({
    "x": DSInt(lb=0, ub=300),
    "y": DSInt(lb=0, ub=300)
})

# Object type for assignment of an item to a box with its position
Assignment = DSRecord({
    "box_id": DSInt(lb=1, ub=20),
    "position": Position
})



# --- Constants and Decision Variables ---
BOX_HEIGHT : int = 300
BOX_WIDTH : int = 300
ITEMS : DSList(length=20, elem_type=Item) = [{
                        "width": 77,
                        "height": 95
                    },
                    {
                        "width": 53,
                        "height": 50
                    },
                    {
                        "width": 30,
                        "height": 11
                    },
                    {
                        "width": 95,
                        "height": 100
                    },
                    {
                        "width": 73,
                        "height": 73
                    },
                    {
                        "width": 18,
                        "height": 19
                    },
                    {
                        "width": 19,
                        "height": 60
                    },
                    {
                        "width": 99,
                        "height": 52
                    },
                    {
                        "width": 12,
                        "height": 83
                    },
                    {
                        "width": 49,
                        "height": 76
                    },
                    {
                        "width": 30,
                        "height": 87
                    },
                    {
                        "width": 13,
                        "height": 3
                    },
                    {
                        "width": 84,
                        "height": 48
                    },
                    {
                        "width": 68,
                        "height": 77
                    },
                    {
                        "width": 19,
                        "height": 79
                    },
                    {
                        "width": 26,
                        "height": 76
                    },
                    {
                        "width": 11,
                        "height": 24
                    },
                    {
                        "width": 31,
                        "height": 11
                    },
                    {
                        "width": 73,
                        "height": 60
                    },
                    {
                        "width": 60,
                        "height": 26
                    }
]
nr_used_boxes : DSInt(lb=1, ub=20)
item_box_assignments : DSList(length=20, elem_type=Assignment)
x_y_positions : DSList(length=20, elem_type=Position)
N_ITEMS : int = 20
N_ITEM_BOX_ASSIGNMENTS : int = 20
N_X_Y_POSITIONS : int = 20


# --- objective ---
def calculate_objective(assignments: DSList(length=20, elem_type=Assignment)) -> DSInt(lb=1, ub=20):
    max_box_id: int = 0
    for i in range(1, N_ITEM_BOX_ASSIGNMENTS + 1):
        box_id: int = assignments[i].box_id
        if box_id > max_box_id:
            max_box_id = box_id
    return max_box_id

objective = calculate_objective(item_box_assignments)
nr_used_boxes = objective
minimize(objective)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def ensure_items_fit_in_boxes(
    items: DSList(length=20, elem_type=Item),
    assignments: DSList(length=20, elem_type=Assignment),
    positions: DSList(length=20, elem_type=Position),
    box_width: int,
    box_height: int
):
    for i in range(1, N_ITEMS + 1):
        item: Item = items[i]
        pos: Position = positions[i]
        assignment: Assignment = assignments[i]

        # Ensure position is within box boundaries
        assert pos.x >= 0
        assert pos.y >= 0
        assert pos.x + item.width <= box_width
        assert pos.y + item.height <= box_height

        # Link position objects
        assert assignment.position.x == pos.x
        assert assignment.position.y == pos.y

ensure_items_fit_in_boxes(ITEMS, item_box_assignments, x_y_positions, BOX_WIDTH, BOX_HEIGHT)

# Ensure box_id assignments are linked correctly
for i in range(1, N_ITEMS + 1):
    assert item_box_assignments[i].box_id >= 1
    assert item_box_assignments[i].box_id <= 20

# --- constraints ---
def ensure_no_item_overlap(
    items: DSList(length=20, elem_type=Item),
    positions: DSList(length=20, elem_type=Position),
    assignments: DSList(length=20, elem_type=Assignment)
):
    for i in range(1, N_ITEMS + 1):
        for j in range(i + 1, N_ITEMS + 1):
            # Only check overlap if both items are in the same box
            if assignments[i].box_id == assignments[j].box_id:
                # Assert that rectangles do not overlap
                # They do not overlap if one is completely to the left, right, above, or below the other
                assert (positions[i].x + items[i].width <= positions[j].x) or \
                       (positions[j].x + items[j].width <= positions[i].x) or \
                       (positions[i].y + items[i].height <= positions[j].y) or \
                       (positions[j].y + items[j].height <= positions[i].y)

ensure_no_item_overlap(ITEMS, x_y_positions, item_box_assignments)

# Ensure all position objects between assignments and standalone positions are synchronized
for i in range(1, N_ITEMS + 1):
    assert item_box_assignments[i].position.x == x_y_positions[i].x
    assert item_box_assignments[i].position.y == x_y_positions[i].y

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def ensure_item_box_assignment_uniqueness(
    assignments: DSList(length=20, elem_type=Assignment),
    n_items: int
):
    # Each item is assigned to exactly one box (injective mapping from items to boxes)
    # This is implicitly ensured by having one assignment per item
    # We just need to ensure the box_id is valid
    for i in range(1, N_ITEMS + 1):
        assert assignments[i].box_id >= 1
        assert assignments[i].box_id <= 20

ensure_item_box_assignment_uniqueness(item_box_assignments, N_ITEMS)

# Synchronize position objects between assignments and standalone positions
for i in range(1, N_ITEMS + 1):
    assert item_box_assignments[i].position.x == x_y_positions[i].x
    assert item_box_assignments[i].position.y == x_y_positions[i].y
"""
translator = MiniZincTranslator(initial_clean_up(code))
model = translator.unroll_translation().replace("True", "true").replace("False", "false")
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model, last_in_progress=True))




