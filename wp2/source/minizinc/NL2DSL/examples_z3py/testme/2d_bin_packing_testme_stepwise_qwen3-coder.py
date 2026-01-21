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
# -- Objects --




# --- Objects ---
Item = DSRecord({
    "width": DSInt(lb=1, ub=10),
    "height": DSInt(lb=1, ub=10)
})
BOX_HEIGHT : int = 3
BOX_WIDTH : int = 3
#ITEMS : DSList(length = 6, elem_type = Item) = [{'width': 4, 'height': 3}, {'width': 3, 'height': 2}, {'width': 5, 'height': 3}, {'width': 2, 'height': 4}, {'width': 3, 'height': 3}, {'width': 5, 'height': 2}]
# --- Objects ---
Item = DSRecord({
    "value": DSInt(lb=1, ub=80),
    "weight": DSInt(lb=1, ub=100)
})

BoxAssignment = DSRecord({
    "box_id": DSInt(lb=1, ub=1000),
    "x": DSFloat(lb=0, ub=10000),
    "y": DSFloat(lb=0, ub=10000)
})



BOX_HEIGHT : int = 2
BOX_WIDTH : int = 6
ITEMS : DSList(length = 6, elem_type = Item) = [{'width': 4, 'height': 3}, {'width': 3, 'height': 2}, {'width': 5, 'height': 3}, {'width': 2, 'height': 4}, {'width': 3, 'height': 3}, {'width': 5, 'height': 2}]
"""

translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model))