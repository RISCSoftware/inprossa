'''from z3 import *

# Define the Item datatype
Item = Datatype('Item')
Item.declare('mk_item', ('name', StringSort()), ('width', IntSort()), ('height', IntSort()))
Item = Item.create()
# Define the Box datatype
Box = Datatype('Box')
Box.declare('mk_box', ('id', IntSort()))
Box = Box.create()
# Define the Position datatype
Position = Datatype('Position')
Position.declare('mk_position', ('x', IntSort()), ('y', IntSort()))
Position = Position.create()
BOX_HEIGHT = 6
BOX_WIDTH = 10
ITEM1 = Item.mk_item(StringVal("item1"), 4, 3)
ITEM2 = Item.mk_item(StringVal("item2"), 3, 2)
ITEM3 = Item.mk_item(StringVal("item3"), 5, 3)
ITEM4 = Item.mk_item(StringVal("item4"), 2, 4)
ITEM5 = Item.mk_item(StringVal("item5"), 3, 3)
ITEM6 = Item.mk_item(StringVal("item6"), 5, 2)
ITEMS = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
NUM_ITEMS = 6
nr_used_boxes = Int('nr_used_boxes')
item_box_assignment = [Const(f'item_box_assignment_{i}', Box) for i in range(NUM_ITEMS)]
x_y_positions = [Const(f'position_{i}', Position) for i in range(NUM_ITEMS)]

s = Optimize()
s.minimize(nr_used_boxes)
# Constraint: All items must fit within their assigned box dimensions
for i in range(NUM_ITEMS):
    item_width = Item.width(ITEMS[i])
    item_height = Item.height(ITEMS[i])
    pos_x = Position.x(x_y_positions[i])
    pos_y = Position.y(x_y_positions[i])

    # Ensure the item fits within the box boundaries
    s.add(pos_x >= 0)
    s.add(pos_y >= 0)
    s.add(pos_x + item_width <= BOX_WIDTH)
    s.add(pos_y + item_height <= BOX_HEIGHT)

    # Constraint: Each item's box assignment must be valid (box id >= 0)
    box_id = Box.id(item_box_assignment[i])
    s.add(box_id >= 0)
    s.add(box_id < NUM_ITEMS)  # Bounding box IDs for practical purposes
    # Minimize the number of used boxes# Constraint: Items must not overlap within the same box
    # Ensure item i fits within the box dimensions
    s.add(Position.x(x_y_positions[i]) >= 0)
    s.add(Position.y(x_y_positions[i]) >= 0)
    s.add(Position.x(x_y_positions[i]) + Item.width(ITEMS[i]) <= BOX_WIDTH)
    s.add(Position.y(x_y_positions[i]) + Item.height(ITEMS[i]) <= BOX_HEIGHT)
    # Assign valid box IDs
    s.add(Box.id(item_box_assignment[i]) >= 0)
    s.add(Box.id(item_box_assignment[i]) < nr_used_boxes)
    for j in range(i + 1, NUM_ITEMS):
        # Only check overlap if both items are in the same box
        same_box = Box.id(item_box_assignment[i]) == Box.id(item_box_assignment[j])

        # No overlap condition
        no_overlap = Or(
            Position.x(x_y_positions[i]) + Item.width(ITEMS[i]) <= Position.x(x_y_positions[j]),
            Position.x(x_y_positions[j]) + Item.width(ITEMS[j]) <= Position.x(x_y_positions[i]),
            Position.y(x_y_positions[i]) + Item.height(ITEMS[i]) <= Position.y(x_y_positions[j]),
            Position.y(x_y_positions[j]) + Item.height(ITEMS[j]) <= Position.y(x_y_positions[i])
        )

        s.add(
            Implies(same_box, no_overlap))  # Constraint: Each item must be placed in exactly one box with valid box ID
    s.add(box_id < NUM_ITEMS)
    # Constraint: Items must fit within their assigned box dimensions
    # Box ID must be less than the number of used boxes
    s.add(box_id < nr_used_boxes)
    # Constraint: No overlapping items within the same box
    for j in range(i + 1, NUM_ITEMS):
        Position.x(x_y_positions[j])


if s.check() == sat:
    m = s.model()
    print("Satisfiable")
else:
    print("Unsatisfiable")
'''
import json

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver
from structures_utils import initial_clean_up

# old, valid, optimal
code = """
# -- Objects --
Item = DSRecord({
    "width": DSInt(lb=1, ub=9),
    "height": DSInt(lb=1, ub=5)
})

BoxAssignment = DSRecord({
    "box_id": DSInt(lb=1, ub=9),
    "x": DSInt(lb=0, ub=12),
    "y": DSInt(lb=0, ub=5)
})




# --- Constants ---
BOX_HEIGHT : int = 5
BOX_WIDTH : int = 12
ITEM1 : Item = {"width": 4, "height": 3}
ITEM2 : Item = {"width": 1, "height": 2}
ITEM3 : Item = {"width": 5, "height": 3}
ITEM4 : Item = {"width": 4, "height": 2}
ITEM5 : Item = {"width": 1, "height": 3}
ITEM6 : Item = {"width": 5, "height": 2}
ITEM7 : Item = {"width": 9, "height": 5}
ITEM8 : Item = {"width": 3, "height": 5}
ITEM9 : Item = {"width": 5, "height": 1}
ITEMS : DSList(length=9, elem_type=Item) = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6, ITEM7, ITEM8, ITEM9]
N_ITEMS : int = 9
nr_used_boxes : DSInt(lb=1, ub=9)
item_box_assignments : DSList(length=9, elem_type=BoxAssignment)
x_y_positions : DSList(length=9, elem_type=BoxAssignment)
N_ITEMS : int = 9
N_ITEM_BOX_ASSIGNMENTS : int = 9
N_X_Y_POSITIONS : int = 9


# --- Objective ---
def calculate_objective(assignments: DSList(length=9, elem_type=BoxAssignment)) -> int:
    max_box_id = 0
    for i in range(1, N_ITEMS + 1):
        box_id = assignments[i].box_id
        if box_id > max_box_id:
            max_box_id = box_id
    return max_box_id

calculated_objective_value = calculate_objective(item_box_assignments)
objective = calculated_objective_value
minimize(objective)

# -- Constraints --


# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def fit_items_in_boxes(
    items: DSList(length=9, elem_type=Item),
    assignments: DSList(length=9, elem_type=BoxAssignment),
    box_width: int,
    box_height: int
):
    for i in range(1, N_ITEMS + 1):
        item: Item = items[i]
        assignment: BoxAssignment = assignments[i]
        assert assignment.x + item.width <= box_width
        assert assignment.y + item.height <= box_height

fit_items_in_boxes(ITEMS, item_box_assignments, BOX_WIDTH, BOX_HEIGHT)

# --- constraints ---
def no_overlap(
    assignments: DSList(length=9, elem_type=BoxAssignment),
    items: DSList(length=9, elem_type=Item),
    box_width: int,
    box_height: int
):
    for i in range(1, N_ITEMS + 1):
        for j in range(i + 1, N_ITEMS + 1):
            # Assert that there is no overlap if items are in the same box
            assert (assignments[i].box_id != assignments[j].box_id) or \
                   (assignments[i].x + items[i].width <= assignments[j].x) or \
                   (assignments[j].x + items[j].width <= assignments[i].x) or \
                   (assignments[i].y + items[i].height <= assignments[j].y) or \
                   (assignments[j].y + items[j].height <= assignments[i].y)

no_overlap(item_box_assignments, ITEMS, BOX_WIDTH, BOX_HEIGHT)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def ensure_item_box_assignment_validity(
    assignments: DSList(length=9, elem_type=BoxAssignment),
    nr_used_boxes: DSInt(lb=1, ub=9)
):
    for i in range(1, N_ITEMS + 1):
        assignment: BoxAssignment = assignments[i]
        assert assignment.box_id >= 1
        assert assignment.box_id <= nr_used_boxes

ensure_item_box_assignment_validity(item_box_assignments, nr_used_boxes)

def ensure_positions_are_non_negative(
    assignments: DSList(length=9, elem_type=BoxAssignment)
):
    for i in range(1, N_ITEMS + 1):
        assignment: BoxAssignment = assignments[i]
        assert assignment.x >= 0
        assert assignment.y >= 0

ensure_positions_are_non_negative(item_box_assignments)

nr_used_boxes = objective
"""

# new, valid, 5
code = """
Full formulation:
# --- Objects ---


# Define the Item record type
Item = DSRecord({
    "width": DSInt(lb=1, ub=9),
    "height": DSInt(lb=1, ub=5)
})

# Define the Position record type for x, y coordinates
Position = DSRecord({
    "x": DSInt(lb=0, ub=1000),
    "y": DSInt(lb=0, ub=1000)
})

# Define the Assignment record type for item to box assignment
Assignment = DSRecord({
    "box_id": DSInt(lb=1, ub=100),
    "position": Position
})



# --- Constants and Decision Variables ---
BOX_HEIGHT : int = 5
BOX_WIDTH : int = 12
ITEMS : DSList(length=9, elem_type=Item) = [
    {"width": 4, "height": 3},
    {"width": 1, "height": 2},
    {"width": 5, "height": 3},
    {"width": 4, "height": 2},
    {"width": 1, "height": 3},
    {"width": 9, "height": 2},
    {"width": 9, "height": 5},
    {"width": 3, "height": 5},
    {"width": 5, "height": 1}
]
nr_used_boxes : DSInt(lb=1, ub=100)
item_box_assignments : DSList(length=9, elem_type=Assignment)
x_y_positions : DSList(length=9, elem_type=Position)
N_ITEMS : int = 9
N_ITEM_BOX_ASSIGNMENTS : int = 9
N_X_Y_POSITIONS : int = 9


# --- objective ---
def calculate_objective(item_assignments: DSList(length=9, elem_type=Assignment),
                       nr_boxes: int):
    # Objective is to minimize the number of boxes used
    # Calculate the actual number of boxes used based on assignments
    max_box_id = 0
    for i in range(1, N_ITEM_BOX_ASSIGNMENTS + 1):
        if item_assignments[i].box_id > max_box_id:
            max_box_id = item_assignments[i].box_id
    return max_box_id

# Calculate objective value
objective = calculate_objective(item_box_assignments, nr_used_boxes)

# Minimize the number of boxes used
minimize(objective)

# --- Auxiliary Variables ---
# None needed
# --- constraints ---
def place_items_in_boxes(items: DSList(length=9, elem_type=Item),
                        assignments: DSList(length=9, elem_type=Assignment),
                        positions: DSList(length=9, elem_type=Position),
                        nr_boxes: int):
    # Each item must fit within the box dimensions
    for i in range(1, N_ITEMS + 1):
        # Check that item fits within box dimensions
        assert items[i].width <= BOX_WIDTH
        assert items[i].height <= BOX_HEIGHT

        # Check that position is within box boundaries
        assert positions[i].x >= 0
        assert positions[i].y >= 0
        assert positions[i].x + items[i].width <= BOX_WIDTH
        assert positions[i].y + items[i].height <= BOX_HEIGHT

        # Assignment constraints: box_id must be valid and within used range
        assert assignments[i].box_id >= 1
        assert assignments[i].box_id <= nr_boxes

        # Position constraints: ensure item doesn't overlap with others in same box
        for j in range(1, N_ITEMS + 1):
            if i != j and assignments[i].box_id == assignments[j].box_id:
                # Non-overlapping constraint
                assert positions[i].x + items[i].width <= positions[j].x or \
                       positions[j].x + items[j].width <= positions[i].x or \
                       positions[i].y + items[i].height <= positions[j].y or \
                       positions[j].y + items[j].height <= positions[i].y

place_items_in_boxes(ITEMS, item_box_assignments, x_y_positions, nr_used_boxes)

# --- Auxiliary Variables ---
# None needed
# --- constraints ---
def enforce_non_overlapping_placement(items: DSList(length=9, elem_type=Item),
                                     assignments: DSList(length=9, elem_type=Assignment),
                                     positions: DSList(length=9, elem_type=Position),
                                     nr_boxes: int):
    # Each item must fit within box dimensions
    for i in range(1, N_ITEMS + 1):
        # Check that item fits within box dimensions
        assert items[i].width <= BOX_WIDTH
        assert items[i].height <= BOX_HEIGHT

        # Check that position is within box boundaries
        assert positions[i].x >= 0
        assert positions[i].y >= 0
        assert positions[i].x + items[i].width <= BOX_WIDTH
        assert positions[i].y + items[i].height <= BOX_HEIGHT

        # Assignment constraints: box_id must be valid and within used range
        assert assignments[i].box_id >= 1
        assert assignments[i].box_id <= nr_boxes

        # Position constraints: ensure item doesn't overlap with others in same box
        for j in range(1, N_ITEMS + 1):
            if i != j and assignments[i].box_id == assignments[j].box_id:
                # Non-overlapping constraint using logical combinations
                assert (positions[i].x + items[i].width <= positions[j].x) or \
                       (positions[j].x + items[j].width <= positions[i].x) or \
                       (positions[i].y + items[i].height <= positions[j].y) or \
                       (positions[j].y + items[j].height <= positions[i].y)

enforce_non_overlapping_placement(ITEMS, item_box_assignments, x_y_positions, nr_used_boxes)

# --- Auxiliary Variables ---
# None needed
# --- constraints ---
def validate_box_placement(items: DSList(length=9, elem_type=Item),
                          assignments: DSList(length=9, elem_type=Assignment),
                          positions: DSList(length=9, elem_type=Position),
                          nr_boxes: int):
    # Each item must fit within box dimensions
    for i in range(1, N_ITEMS + 1):
        # Item must fit within box
        assert items[i].width <= BOX_WIDTH
        assert items[i].height <= BOX_HEIGHT

        # Position must be within box boundaries
        assert positions[i].x >= 0
        assert positions[i].y >= 0
        assert positions[i].x + items[i].width <= BOX_WIDTH
        assert positions[i].y + items[i].height <= BOX_HEIGHT

        # Box ID must be valid
        assert assignments[i].box_id >= 1
        assert assignments[i].box_id <= nr_boxes

        # Non-overlapping constraint within same box
        for j in range(1, N_ITEMS + 1):
            if i != j and assignments[i].box_id == assignments[j].box_id:
                # Check for overlap using logical combinations
                assert (positions[i].x + items[i].width <= positions[j].x) or \
                       (positions[j].x + items[j].width <= positions[i].x) or \
                       (positions[i].y + items[i].height <= positions[j].y) or \
                       (positions[j].y + items[j].height <= positions[i].y)

validate_box_placement(ITEMS, item_box_assignments, x_y_positions, nr_used_boxes)
"""

# new, valid, optimal
code = """# --- Objects ---


Item = DSRecord({
    "width": DSInt(lb=1, ub=12),
    "height": DSInt(lb=1, ub=5)
})

BoxAssignment = DSRecord({
    "box_id": DSInt(lb=1, ub=9),
    "x": DSInt(lb=0, ub=12),
    "y": DSInt(lb=0, ub=5)
})



# --- Constants and Decision Variables ---
BOX_HEIGHT : int = 5
BOX_WIDTH : int = 12
ITEM1 : Item = {"width": 4, "height": 3}
ITEM2 : Item = {"width": 1, "height": 2}
ITEM3 : Item = {"width": 5, "height": 3}
ITEM4 : Item = {"width": 4, "height": 2}
ITEM5 : Item = {"width": 1, "height": 3}
ITEM6 : Item = {"width": 9, "height": 2}
ITEM7 : Item = {"width": 9, "height": 5}
ITEM8 : Item = {"width": 3, "height": 5}
ITEM9 : Item = {"width": 5, "height": 1}
ITEMS : DSList(length=9, elem_type=Item) = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6, ITEM7, ITEM8, ITEM9]
N_ITEMS : int = 9
nr_used_boxes : DSInt(lb=1, ub=9)
item_box_assignments : DSList(length=9, elem_type=BoxAssignment)
x_y_positions : DSList(length=9, elem_type=BoxAssignment)
N_ITEMS : int = 9
N_ITEM_BOX_ASSIGNMENTS : int = 9
N_X_Y_POSITIONS : int = 9


# --- objective ---
def calculate_objective(item_box_assignments: DSList(length=9, elem_type=BoxAssignment)) -> int:
    max_box_id: int = 0
    for i in range(1, N_ITEMS + 1):
        if item_box_assignments[i].box_id > max_box_id:
            max_box_id = item_box_assignments[i].box_id
    return max_box_id

objective = calculate_objective(item_box_assignments)
minimize(objective)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def items_fit_exactly_in_boxes(
    items: DSList(length=9, elem_type=Item),
    assignments: DSList(length=9, elem_type=BoxAssignment),
    box_width: int,
    box_height: int
):
    for i in range(1, N_ITEMS + 1):
        # Ensure item fits within box dimensions
        assert assignments[i].x + items[i].width <= box_width
        assert assignments[i].y + items[i].height <= box_height

items_fit_exactly_in_boxes(ITEMS, item_box_assignments, BOX_WIDTH, BOX_HEIGHT)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def no_overlap_between_items(
    items: DSList(length=9, elem_type=Item),
    assignments: DSList(length=9, elem_type=BoxAssignment)
):
    for i in range(1, N_ITEMS + 1):
        for j in range(i + 1, N_ITEMS + 1):
            # Only check overlap if both items are in the same box
            if assignments[i].box_id == assignments[j].box_id:
                # Check if rectangles (items) overlap
                assert (
                    assignments[i].x + items[i].width <= assignments[j].x or
                    assignments[j].x + items[j].width <= assignments[i].x or
                    assignments[i].y + items[i].height <= assignments[j].y or
                    assignments[j].y + items[j].height <= assignments[i].y
                )

no_overlap_between_items(ITEMS, item_box_assignments)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def ensure_item_box_assignment_validity(
    items: DSList(length=9, elem_type=Item),
    assignments: DSList(length=9, elem_type=BoxAssignment),
    nr_used_boxes: DSInt(lb=1, ub=9)
):
    for i in range(1, N_ITEMS + 1):
        # Ensure each item is assigned to a valid box
        assert assignments[i].box_id >= 1
        assert assignments[i].box_id <= nr_used_boxes
        # Ensure position coordinates are within valid bounds
        assert assignments[i].x >= 0
        assert assignments[i].x <= BOX_WIDTH - items[i].width
        assert assignments[i].y >= 0
        assert assignments[i].y <= BOX_HEIGHT - items[i].height

ensure_item_box_assignment_validity(ITEMS, item_box_assignments, nr_used_boxes)
"""
code = """# --- Objects ---
Item = DSRecord({"width" : DSInt(lb=1), "height" : DSInt(lb=1)})
X_Y_Position = DSRecord({"x" : DSInt(lb=0), "y" : DSInt(lb=0)})



# --- Constants and Decision Variables ---
BOX_HEIGHT : int = 5
BOX_WIDTH : int = 12
ITEMS : DSList(length=9, elem_type=Item) = [{'width': 4, 'height': 3}, {'width': 1, 'height': 2}, {'width': 5, 'height': 3}, {'width': 4, 'height': 2}, {'width': 1, 'height': 3}, {'width': 9, 'height': 2}, {'width': 9, 'height': 5}, {'width': 3, 'height': 5}, {'width': 5, 'height': 1}]
N_ITEMS : int = 9
nr_used_boxes : DSInt(lb=1, ub=9)
item_box_assignments : DSList(length=9, elem_type=DSInt(lb=1, ub=9))
N_ITEM_BOX_ASSIGNMENTS : int = 9
x_y_positions : DSList(length=9, elem_type=X_Y_Position)
N_X_Y_POSITIONS : int = 9


# --- objective ---
def calculate_objective(item_box_assignments: DSList(length=9, elem_type=DSInt(lb=1, ub=9))) -> int:
    max_box_used: int = 0
    for i in range(1, N_ITEMS + 1):
        box_nr: int = item_box_assignments[i]
        if box_nr > max_box_used:
            max_box_used = box_nr
    return max_box_used

objective = calculate_objective(item_box_assignments)
nr_used_boxes = objective
minimize(objective)


# --- Auxiliary Variables ---
# Leave empty, if not required.

# --- Constraints ---
def ensure_items_in_box_bounds(
    items: DSList(length=9, elem_type=Item),
    x_y_positions: DSList(length=9, elem_type=X_Y_Position)
):
    for i in range(1, N_ITEMS + 1):
        pos: X_Y_Position = x_y_positions[i]
        x: int = x_y_positions[i].x
        assert x_y_positions[i].x + items[i].width <= BOX_WIDTH
        assert x_y_positions[i].y + items[i].height <= BOX_HEIGHT
        assert x_y_positions[i].x >= 0
        assert x_y_positions[i].y >= 0

ensure_items_in_box_bounds(ITEMS, x_y_positions)

def ensure_no_item_overlap(
    items: DSList(length=9, elem_type=Item),
    item_box_assignments: DSList(length=9, elem_type=DSInt(lb=1, ub=9)),
    x_y_positions: DSList(length=9, elem_type=X_Y_Position)
):
    for i in range(1, N_ITEMS):
        for j in range(i + 1, N_ITEMS + 1):
            if item_box_assignments[i] == item_box_assignments[j]:
                assert (
                    x_y_positions[i].x + items[i].width <= x_y_positions[j].x or
                    x_y_positions[j].x + items[j].width <= x_y_positions[i].x or
                    x_y_positions[i].y + items[i].height <= x_y_positions[j].y or
                    x_y_positions[j].y + items[j].height <= x_y_positions[i].y
                )

ensure_no_item_overlap(ITEMS, item_box_assignments, x_y_positions)

# --- Auxiliary Variables ---
# Leave empty, if not required.

# --- Constraints ---
def ensure_item_box_assignment_validity(
    item_box_assignments: DSList(length=9, elem_type=DSInt(lb=1, ub=9))
):
    # Ensure each item is assigned to exactly one box
    for i in range(1, N_ITEMS + 1):
        assert item_box_assignments[i] >= 1
        assert item_box_assignments[i] <= nr_used_boxes

ensure_item_box_assignment_validity(item_box_assignments)
"""

code = """
# --- Objects ---
Item = DSRecord({
    "value": DSInt(lb=1, ub=80),
    "weight": DSInt(lb=1, ub=100)
})

# --- Constants ---
ITEM1 : Item = {\"value": 15, \"weight": 12}
ITEM2 : Item = {\"value": 50, \"weight": 70}
ITEM3 : Item
ITEM3.value = 80
ITEM3.weight = 100
ITEM4 : Item
ITEM4.value = 80
ITEM4.weight = 20
ITEM5 : Item
ITEM5.value = 20
ITEM5.weight = 12
ITEM6 : Item
ITEM6.value = 25
ITEM6.weight = 5
ITEMS : DSList(length=6, elem_type=Item) = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N_ITEMS : int = 6
MAX_WEIGHT : int = 110

# --- Decision Variables ---
chosen_items : DSList(length=6, elem_type=DSBool())
accumulated_value : DSInt(lb=0)
accumulated_weight : DSInt(lb=0, ub=MAX_WEIGHT)

# --- Constraints ---
def pack_item(items: DSList(length=6, elem_type=Item),
                chosen_items: DSList(length=6, elem_type=DSBool())):
    accumulated_weight: int = 0
    accumulated_value: int = 0
    for i in range(1, N_ITEMS + 1):
        if chosen_items[i]:
            item : Item = items[i]
            accumulated_weight = accumulated_weight + items[i].weight
            accumulated_value = accumulated_value + items[i].value
    return accumulated_value, accumulated_weight

accumulated_value, accumulated_weight = pack_item(ITEMS, chosen_items)
assert accumulated_weight >= 0
assert accumulated_weight < MAX_WEIGHT
assert accumulated_value >= 0
maximize(accumulated_value)
"""
translator = MiniZincTranslator(code)
model = translator.unroll_translation().replace("true", "True")
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model, last_in_progress=True))




