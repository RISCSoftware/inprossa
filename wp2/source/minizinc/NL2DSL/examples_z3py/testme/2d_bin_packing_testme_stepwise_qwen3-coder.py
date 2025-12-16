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




# --- Objects ---
Item = DSRecord({
    "width": DSInt(lb=1, ub=10),
    "height": DSInt(lb=1, ub=10)
})

BoxAssignment = DSRecord({
    "box_id": DSInt(lb=1, ub=100),
    "x": DSInt(lb=0, ub=100),
    "y": DSInt(lb=0, ub=100)
})

# --- Constants ---
BOX_HEIGHT : int = 5
BOX_WIDTH : int = 10
ITEM1 : Item = {"width": 10, "height": 5}
ITEM2 : Item = {"width": 2, "height": 2}
ITEMS : DSList(length=2, elem_type=Item) = [ITEM1, ITEM2]
N_ITEMS : int = 2
nr_used_boxes: DSInt(lb=1, ub=100)
item_box_assignments: DSList(length=2, elem_type=BoxAssignment)
x_y_positions: DSList(length=2, elem_type=BoxAssignment)


# -- Objective --

def calculate_objective(assignments: DSList(length=2, elem_type=BoxAssignment)) -> int:
    max_box_id = 0
    for i in range(1, N_ITEMS + 1):
        box_id = assignments[i].box_id
        if box_id > max_box_id:
            max_box_id = box_id
    return max_box_id

calculated_objective_value = calculate_objective(item_box_assignments)
objective = calculated_objective_value

def fit_items_in_boxes(
    items: DSList(length=2, elem_type=Item),
    assignments: DSList(length=2, elem_type=BoxAssignment)
) -> None:
    for i in range(1, 3):
        item : Item = items[i]
        pos : BoxAssignment = assignments[i]
        assert pos.x >= 0
        assert pos.y >= 0
        assert pos.x + item.width <= BOX_WIDTH
        assert pos.y + item.height <= BOX_HEIGHT

fit_items_in_boxes(ITEMS, x_y_positions)

def no_item_overlap(
    items: DSList(length=2, elem_type=Item),
    assignments: DSList(length=2, elem_type=BoxAssignment),
    box_width: int,
    box_height: int
):
    for i in range(1, 3):
        for j in range(i + 1, 3):
            if i != j:
                item_i: Item = items[i]
                item_j: Item = items[j]
                assignment_i: BoxAssignment = assignments[i]
                assignment_j: BoxAssignment = assignments[j]
                
                # Check if items are in the same box
                if assignment_i.box_id == assignment_j.box_id:
                    # Check for non-overlapping rectangles
                    assert not (
                        assignment_i.x < assignment_j.x + item_j.width and
                        assignment_j.x < assignment_i.x + item_i.width and
                        assignment_i.y < assignment_j.y + item_j.height and
                        assignment_j.y < assignment_i.y + item_i.height
                    )
no_item_overlap(ITEMS, item_box_assignments, BOX_WIDTH, BOX_HEIGHT)
"""

translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model))