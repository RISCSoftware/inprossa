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
from solver import MiniZincSolver

code = """
# --- Objects ---
Item = DSRecord({"width" : DSInt(lb=1, ub=10), "height" : DSInt(lb=1, ub=10)})
X_Y_Position = DSRecord({"x" : DSInt(lb=0, ub=12), "y" : DSInt(lb=0, ub=5)})



# --- Constants and Decision Variables ---
BOX_HEIGHT : int = 5
BOX_WIDTH : int = 12
ITEMS : DSList(length=9, elem_type=Item) = [{'name': 'item1', 'width': 4, 'height': 3}, {'name': 'item2', 'width': 1, 'height': 2}, {'name': 'item3', 'width': 5, 'height': 3}, {'name': 'item4', 'width': 4, 'height': 2}, {'name': 'item5', 'width': 1, 'height': 3}, {'name': 'item6', 'width': 5, 'height': 2}, {'name': 'item7', 'width': 9, 'height': 5}, {'name': 'item8', 'width': 3, 'height': 5}, {'name': 'item9', 'width': 5, 'height': 1}]
N_ITEMS : int = 9
nr_used_boxes : DSInt(lb=1, ub=9)
item_box_assignments : DSList(length=9, elem_type=DSInt(lb=1, ub=9))
N_ITEM_BOX_ASSIGNMENTS : int = 9
x_y_positions : DSList(length=9, elem_type=X_Y_Position)
N_X_Y_POSITIONS : int = 9
N_ITEM_BOX_ASSIGNMENTS : int = 9
N_X_Y_POSITIONS : int = 9


# --- objective ---
def calculate_objective(assignments: DSList(length=9, elem_type=DSInt(lb=1, ub=9))) -> int:
    max_box = 0
    for i in range(1, 10):
        if assignments[i] > max_box:
            max_box = assignments[i]
    return max_box

calculated_objective_value = calculate_objective(item_box_assignments)
objective = calculated_objective_value

# --- Constraints ---
def validate_all_constraints(
    items: DSList(length=9, elem_type=Item),
    assignments: DSList(length=9, elem_type=DSInt(lb=1, ub=9)),
    positions: DSList(length=9, elem_type=X_Y_Position),
    nr_used_boxes: DSInt(lb=1, ub=9)
) -> None:
    # Items fit in box constraint
    for i in range(1, 10):
        item : Item = items[i]
        pos : X_Y_Position = positions[i]
        assert pos.x + item.width <= BOX_WIDTH
        assert pos.y + item.height <= BOX_HEIGHT

        # Ensure item-box assignment validity
        assert assignments[i] >= 1
        assert assignments[i] <= nr_used_boxes

        # Non-negative positions
        assert pos.x >= 0
        assert pos.y >= 0

    # No overlap constraint
    for i in range(1, 10):
        for j in range(i + 1, 10):
            if assignments[i] == assignments[j]:
                item_i : Item = items[i]
                item_j : Item = items[j]
                pos_i : X_Y_Position = positions[i]
                pos_j : X_Y_Position = positions[j]
                assert (pos_i.x + item_i.width <= pos_j.x) or (pos_j.x + item_j.width <= pos_i.x) or (pos_i.y + item_i.height <= pos_j.y) or (pos_j.y + item_j.height <= pos_i.y)

validate_all_constraints(ITEMS, item_box_assignments, x_y_positions, nr_used_boxes)

nr_used_boxes = objective
"""

translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model))
