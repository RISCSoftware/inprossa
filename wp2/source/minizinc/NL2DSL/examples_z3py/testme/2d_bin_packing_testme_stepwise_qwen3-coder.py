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
from Translator.Objects.MiniZincTranslator import MiniZincTranslator

code = """


Item = DSRecord({
    "width": DSInt(),
    "height": DSInt()
})

BoxAssignment = DSRecord({
    "box_id": DSInt(),
    "x": DSInt(),
    "y": DSInt()
})



# --- Constants ---
BOX_HEIGHT : int = 6
BOX_WIDTH : int = 10
ITEM1 : Item = {"width": 4, "height": 3}
ITEM2 : Item = {"width": 3, "height": 2}
ITEM3 : Item = {"width": 5, "height": 3}
ITEM4 : Item = {"width": 2, "height": 4}
ITEM5 : Item = {"width": 3, "height": 3}
ITEM6 : Item = {"width": 5, "height": 2}
ITEMS : DSList(length=6, elem_type=Item) = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N_ITEMS : int = 6
nr_used_boxes: DSInt()
item_box_assignment: DSList(length=N_ITEMS, elem_type=BoxAssignment)
x_y_positions: DSList(length=N_ITEMS, elem_type=BoxAssignment)


# -- Objective --


def calculate_objective(item_box_assignment: DSList(length=N_ITEMS, elem_type=BoxAssignment)) -> DSInt():
    max_box_id = 0
    for i in range(1, N_ITEMS + 1):
        box_id = item_box_assignment[i].box_id
        if box_id > max_box_id:
            max_box_id = box_id
    return max_box_id

temp_objective = calculate_objective(item_box_assignment)
assert objective == temp_objective

# -- Constraints --


# --- Auxiliary Variables ---
# Leave empty, if not required.

# --- Constraints ---
def place_items_in_bins(
    items: DSList(length=6, elem_type=Item),
    assignments: DSList(length=6, elem_type=BoxAssignment),
    box_width: int,
    box_height: int
):
    for i in range(1, 7):
        item = items[i]
        assignment = assignments[i]
        
        # Ensure item fits within the box dimensions
        assert assignment.x + item.width <= box_width
        assert assignment.y + item.height <= box_height
        
        # Ensure item is placed within positive coordinates
        assert assignment.x >= 0
        assert assignment.y >= 0

place_items_in_bins(ITEMS, item_box_assignment, BOX_WIDTH, BOX_HEIGHT)

# --- Auxiliary Variables ---
# Leave empty, if not required.

# --- Constraints ---
def no_overlap(
    assignments: DSList(length=6, elem_type=BoxAssignment),
    items: DSList(length=6, elem_type=Item)
):
    for i in range(1, 7):
        for j in range(i + 1, 7):
            assignment_i = assignments[i]
            assignment_j = assignments[j]
            item_i = items[i]
            item_j = items[j]
            
            # Check if both items are in the same box
            if assignment_i.box_id == assignment_j.box_id:
                # Check for non-overlapping on x-axis
                x_overlap = not (
                    assignment_i.x + item_i.width <= assignment_j.x or
                    assignment_j.x + item_j.width <= assignment_i.x
                )
                
                # Check for non-overlapping on y-axis
                y_overlap = not (
                    assignment_i.y + item_i.height <= assignment_j.y or
                    assignment_j.y + item_j.height <= assignment_i.y
                )
                
                # If both x and y overlap, then there is a conflict
                assert not (x_overlap and y_overlap)

no_overlap(item_box_assignment, ITEMS)

# --- Auxiliary Variables ---
# Leave empty, if not required.

# --- Constraints ---
def ensure_one_box_per_item(
    assignments: DSList(length=6, elem_type=BoxAssignment)
):
    assignment : BoxAssignment
    for i in range(1, 7):
        assignment = assignments[i]
        # Ensure each item is assigned to exactly one box (assuming box_id starts at 1)
        assert assignment.box_id >= 1

ensure_one_box_per_item(item_box_assignment)
"""
code = """
# -- Objects --
Item = DSRecord({
    "width": DSInt(lb=1, ub=10),
    "height": DSInt(lb=1, ub=6)
})

BoxAssignment = DSRecord({
    "box_id": DSInt(lb=1, ub=6),
    "x": DSInt(lb=0, ub=10),
    "y": DSInt(lb=0, ub=6)
})

Position = DSRecord({
    "x": DSInt(lb=0, ub=10),
    "y": DSInt(lb=0, ub=6)
})


# --- Constants ---
BOX_HEIGHT : int = 6
BOX_WIDTH : int = 10
ITEM1 : Item = {"width": 4, "height": 3}
ITEM2 : Item = {"width": 3, "height": 2}
ITEM3 : Item = {"width": 5, "height": 3}
ITEM4 : Item = {"width": 2, "height": 4}
ITEM5 : Item = {"width": 3, "height": 3}
ITEM6 : Item = {"width": 5, "height": 2}
ITEMS : DSList(length=6, elem_type=Item) = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
nr_used_boxes : DSInt(lb=1, ub=6)
item_box_assignment : DSList(length=6, elem_type=BoxAssignment)
x_y_positions : DSList(length=6, elem_type=Position)
N_ITEMS : int = 6
N_item_box_assignment : int = 6
N_x_y_positions : int = 6


# -- Objective --
def calculate_objective(assignments: DSList(length=6, elem_type=BoxAssignment)) -> DSInt(lb=1, ub=6):
    max_box_id: DSInt(lb=1, ub=6) = 0
    for i in range(1, N_ITEMS + 1):
        box_id : DSInt(lb=1, ub=6) = assignments[i].box_id
        if box_id > max_box_id:
            max_box_id = box_id
    return max_box_id

temp_objective : DSInt(lb=1, ub=6) = calculate_objective(item_box_assignment)
objective = temp_objective

# -- Constraints --


# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def ensure_items_fit_in_assigned_boxes(
    items: DSList(length=6, elem_type=Item),
    positions: DSList(length=6, elem_type=Position),
    assignments: DSList(length=6, elem_type=BoxAssignment)
):
    for i in range(1, N_ITEMS + 1):
        item : Item = items[i]
        pos : Position = positions[i]
        assign : BoxAssignment = assignments[i]
        
        # Ensure item fits within box boundaries
        assert pos.x + item.width <= BOX_WIDTH
        assert pos.y + item.height <= BOX_HEIGHT
        
        # Ensure item is placed within the assigned box
        assert assign.x == pos.x
        assert assign.y == pos.y

ensure_items_fit_in_assigned_boxes(ITEMS, x_y_positions, item_box_assignment)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def ensure_no_overlap(
    items: DSList(length=6, elem_type=Item),
    positions: DSList(length=6, elem_type=Position),
    assignments: DSList(length=6, elem_type=BoxAssignment)
):
    for i in range(1, N_ITEMS + 1):
        for j in range(i + 1, N_ITEMS + 1):
            # Only check overlap if both items are in the same box
            if assignments[i].box_id == assignments[j].box_id:
                item_i : Item = items[i]
                pos_i : Position = positions[i]
                item_j : Item = items[j]
                pos_j : Position = positions[j]
                
                # Check if rectangles overlap
                assert pos_i.x >= pos_j.x + item_j.width or pos_j.x >= pos_i.x + item_i.width or \
                       pos_i.y >= pos_j.y + item_j.height or pos_j.y >= pos_i.y + item_i.height

ensure_no_overlap(ITEMS, x_y_positions, item_box_assignment)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def ensure_item_in_one_box(
    assignments: DSList(length=6, elem_type=BoxAssignment)
):
    for i in range(1, N_ITEMS + 1):
        box_id : DSInt(lb=1, ub=6) = assignments[i].box_id
        assert box_id >= 1
        assert box_id <= 6

ensure_item_in_one_box(item_box_assignment)

assert nr_used_boxes == temp_objective"""
translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")