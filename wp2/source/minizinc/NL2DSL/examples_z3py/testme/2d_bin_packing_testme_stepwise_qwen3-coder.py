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
from minizinc_solver import MiniZincSolver

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


# -- Objective --


# --- objective ---
def calculate_objective(assignments: DSList(length=6, elem_type=BoxAssignment)) -> DSInt(lb=1, ub=6):
    max_box_id : DSInt(lb=1, ub=6) = 1
    for i in range(1, N_ITEMS + 1):
        box_id : DSInt(lb=1, ub=6) = assignments[i].box_id
        if box_id > max_box_id:
            max_box_id = box_id
    return max_box_id

nr_used_boxes = calculate_objective(item_box_assignment)
objective = nr_used_boxes

# -- Constraints --


# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def items_fit_exactly_in_boxes(items: DSList(length=6, elem_type=Item), assignments: DSList(length=6, elem_type=BoxAssignment)):
    for i in range(1, N_ITEMS + 1):
        item : Item = items[i]
        assignment : BoxAssignment = assignments[i]
        assert assignment.x + item.width <= BOX_WIDTH
        assert assignment.y + item.height <= BOX_HEIGHT

items_fit_exactly_in_boxes(ITEMS, item_box_assignment)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def no_overlap(assignments: DSList(length=6, elem_type=BoxAssignment), items: DSList(length=6, elem_type=Item)):
    for i in range(1, N_ITEMS + 1):
        for j in range(i + 1, N_ITEMS + 1):
            assignment_i : BoxAssignment = assignments[i]
            assignment_j : BoxAssignment = assignments[j]
            item_i : Item = items[i]
            item_j : Item = items[j]
            
            # Check if items are in the same box
            same_box : bool = assignment_i.box_id == assignment_j.box_id
            
            # Check for non-overlapping in x-axis
            no_overlap_x : bool = (assignment_i.x + item_i.width <= assignment_j.x) or (assignment_j.x + item_j.width <= assignment_i.x)
            
            # Check for non-overlapping in y-axis
            no_overlap_y : bool = (assignment_i.y + item_i.height <= assignment_j.y) or (assignment_j.y + item_j.height <= assignment_i.y)
            
            # If in the same box, ensure they don't overlap
            assert not same_box or (no_overlap_x or no_overlap_y)

no_overlap(item_box_assignment, ITEMS)

# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def assign_item_positions(assignments: DSList(length=6, elem_type=BoxAssignment), positions: DSList(length=6, elem_type=Position)):
    for i in range(1, N_ITEMS + 1):
        assignment : BoxAssignment = assignments[i]
        position : Position = positions[i]
        assert position.x == assignment.x
        assert position.y == assignment.y

assign_item_positions(item_box_assignment, x_y_positions)"""
'''
minizinc solution:
objective = [0, 0, 3, 3, 3, 3];
nr_used_boxes = [3];
item_box_assignment = [[(box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
x_y_positions = [[(x: 0, y: 0), (x: 0, y: 0), (x: 0, y: 2), (x: 8, y: 0), (x: 5, y: 0), (x: 0, y: 0)]];
assignments__calculate_objective__1 = [[(box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
box_id__calculate_objective__1 = [2, 3, 1, 1, 1, 1];
max_box_id__calculate_objective__1 = [1, 2, 3, 3, 3, 3, 3];
objective__calculate_objective__1 = [0];
assignment__items_fit_exactly_in_boxes__1 = [(box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)];
assignments__items_fit_exactly_in_boxes__1 = [[(box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
item__items_fit_exactly_in_boxes__1 = [(height: 3, width: 4), (height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5)];
items__items_fit_exactly_in_boxes__1 = [[(height: 3, width: 4), (height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5)]];
objective__items_fit_exactly_in_boxes__1 = [0];
assignment_i__no_overlap__1 = [(box_id: 2, x: 0, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0)];
assignment_j__no_overlap__1 = [(box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 0, y: 0)];
assignments__no_overlap__1 = [[(box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
item_i__no_overlap__1 = [(height: 3, width: 4), (height: 3, width: 4), (height: 3, width: 4), (height: 3, width: 4), (height: 3, width: 4), (height: 2, width: 3), (height: 2, width: 3), (height: 2, width: 3), (height: 2, width: 3), (height: 3, width: 5), (height: 3, width: 5), (height: 3, width: 5), (height: 4, width: 2), (height: 4, width: 2), (height: 3, width: 3)];
item_j__no_overlap__1 = [(height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5), (height: 3, width: 3), (height: 2, width: 5), (height: 2, width: 5)];
items__no_overlap__1 = [[(height: 3, width: 4), (height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5)]];
no_overlap_x__no_overlap__1 = [false, false, true, true, false, false, true, true, false, true, true, false, true, true, true];
no_overlap_y__no_overlap__1 = [false, false, false, false, false, true, false, false, false, false, false, true, false, false, false];
objective__no_overlap__1 = [0];
same_box__no_overlap__1 = [false, false, false, false, false, false, false, false, false, true, true, true, true, true, true];
assignment__assign_item_positions__1 = [(box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)];
assignments__assign_item_positions__1 = [[(box_id: 2, x: 0, y: 0), (box_id: 3, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
objective__assign_item_positions__1 = [0];
position__assign_item_positions__1 = [(x: 0, y: 0), (x: 0, y: 0), (x: 0, y: 2), (x: 8, y: 0), (x: 5, y: 0), (x: 0, y: 0)];
positions__assign_item_positions__1 = [[(x: 0, y: 0), (x: 0, y: 0), (x: 0, y: 2), (x: 8, y: 0), (x: 5, y: 0), (x: 0, y: 0)]];
_objective = 3;
----------
objective = [0, 0, 2, 2, 2, 2];
nr_used_boxes = [2];
item_box_assignment = [[(box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
x_y_positions = [[(x: 3, y: 0), (x: 0, y: 0), (x: 0, y: 2), (x: 8, y: 0), (x: 5, y: 0), (x: 0, y: 0)]];
assignments__calculate_objective__1 = [[(box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
box_id__calculate_objective__1 = [2, 2, 1, 1, 1, 1];
max_box_id__calculate_objective__1 = [1, 2, 2, 2, 2, 2, 2];
objective__calculate_objective__1 = [0];
assignment__items_fit_exactly_in_boxes__1 = [(box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)];
assignments__items_fit_exactly_in_boxes__1 = [[(box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
item__items_fit_exactly_in_boxes__1 = [(height: 3, width: 4), (height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5)];
items__items_fit_exactly_in_boxes__1 = [[(height: 3, width: 4), (height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5)]];
objective__items_fit_exactly_in_boxes__1 = [0];
assignment_i__no_overlap__1 = [(box_id: 2, x: 3, y: 0), (box_id: 2, x: 3, y: 0), (box_id: 2, x: 3, y: 0), (box_id: 2, x: 3, y: 0), (box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0)];
assignment_j__no_overlap__1 = [(box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0), (box_id: 1, x: 0, y: 0)];
assignments__no_overlap__1 = [[(box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
item_i__no_overlap__1 = [(height: 3, width: 4), (height: 3, width: 4), (height: 3, width: 4), (height: 3, width: 4), (height: 3, width: 4), (height: 2, width: 3), (height: 2, width: 3), (height: 2, width: 3), (height: 2, width: 3), (height: 3, width: 5), (height: 3, width: 5), (height: 3, width: 5), (height: 4, width: 2), (height: 4, width: 2), (height: 3, width: 3)];
item_j__no_overlap__1 = [(height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5), (height: 3, width: 3), (height: 2, width: 5), (height: 2, width: 5)];
items__no_overlap__1 = [[(height: 3, width: 4), (height: 2, width: 3), (height: 3, width: 5), (height: 4, width: 2), (height: 3, width: 3), (height: 2, width: 5)]];
no_overlap_x__no_overlap__1 = [true, false, true, false, false, false, true, true, false, true, true, false, true, true, true];
no_overlap_y__no_overlap__1 = [false, false, false, false, false, true, false, false, false, false, false, true, false, false, false];
objective__no_overlap__1 = [0];
same_box__no_overlap__1 = [true, false, false, false, false, false, false, false, false, true, true, true, true, true, true];
assignment__assign_item_positions__1 = [(box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)];
assignments__assign_item_positions__1 = [[(box_id: 2, x: 3, y: 0), (box_id: 2, x: 0, y: 0), (box_id: 1, x: 0, y: 2), (box_id: 1, x: 8, y: 0), (box_id: 1, x: 5, y: 0), (box_id: 1, x: 0, y: 0)]];
objective__assign_item_positions__1 = [0];
position__assign_item_positions__1 = [(x: 3, y: 0), (x: 0, y: 0), (x: 0, y: 2), (x: 8, y: 0), (x: 5, y: 0), (x: 0, y: 0)];
positions__assign_item_positions__1 = [[(x: 3, y: 0), (x: 0, y: 0), (x: 0, y: 2), (x: 8, y: 0), (x: 5, y: 0), (x: 0, y: 0)]];
_objective = 2;
'''
code = """# -- Objects --


# --- Objects ---
Item = DSRecord({
    "width": DSInt(lb=1, ub=10),
    "height": DSInt(lb=1, ub=6)
})

BoxAssignment = DSRecord({
    "box_id": DSInt(lb=1, ub=6),
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
N_ITEMS : int = 6
nr_used_boxes : DSInt(lb=1, ub=6)
item_box_assignment : DSList(length=6, elem_type=BoxAssignment)
x_y_positions : DSList(length=6, elem_type=BoxAssignment)
N_ITEMS : int = 6
N_ITEM_BOX_ASSIGNMENT : int = 6
N_X_Y_POSITIONS : int = 6


# -- Objective --


# --- objective ---
def calculate_objective(assignments: DSList(length=6, elem_type=BoxAssignment)) -> int:
    max_box_id = 0
    for i in range(1, N_ITEMS + 1):
        box_id = assignments[i].box_id
        if box_id > max_box_id:
            max_box_id = box_id
    return max_box_id

calculated_objective_value = calculate_objective(item_box_assignment)
objective = calculated_objective_value

# -- Constraints --


# --- Auxiliary Variables ---
# Leave empty, if not required.
# --- constraints ---
def fit_items_in_box(
    items: DSList(length=6, elem_type=Item),
    assignments: DSList(length=6, elem_type=BoxAssignment),
    box_width: int,
    box_height: int
):
    for i in range(1, N_ITEMS + 1):
        item: Item = items[i]
        assignment: BoxAssignment = assignments[i]
        assert assignment.x + item.width <= box_width
        assert assignment.y + item.height <= box_height

fit_items_in_box(ITEMS, item_box_assignment, BOX_WIDTH, BOX_HEIGHT)

# --- Auxiliary Variables ---
asdf : DSList(length=36, elem_type=DSBool())
# --- constraints ---
def no_overlap(
    assignments: DSList(length=6, elem_type=BoxAssignment),
    items: DSList(length=6, elem_type=Item),
    no_overlap_check: DSList(length=36, elem_type=DSBool())
):
    index: int = 1
    for i in range(1, N_ITEMS + 1):
        item_i: Item = items[i]
        assign_i: BoxAssignment = assignments[i]
        for j in range(1, N_ITEMS + 1):
            item_j: Item = items[j]
            assign_j: BoxAssignment = assignments[j]

            # Skip if same item
            if i == j:
                no_overlap_check[index] = True
            else:
                # Check if in same box
                if assign_i.box_id != assign_j.box_id:
                    no_overlap_check[index] = True
                else:
                    # Check for non-overlapping intervals on x-axis
                    x_overlap: bool = not (
                        assign_i.x + item_i.width <= assign_j.x or
                        assign_j.x + item_j.width <= assign_i.x
                    )

                    # Check for non-overlapping intervals on y-axis
                    y_overlap: bool = not (
                        assign_i.y + item_i.height <= assign_j.y or
                        assign_j.y + item_j.height <= assign_i.y
                    )

                    # Overlap occurs if both axes overlap
                    overlap: bool = x_overlap and y_overlap
                    no_overlap_check[index] = not overlap
            index = index + 1

    assert all(no_overlap_check[i] for i in range(1, 36 + 1))

no_overlap(item_box_assignment, ITEMS, asdf)
"""

translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
solver.solve_with_command_line_minizinc(model)