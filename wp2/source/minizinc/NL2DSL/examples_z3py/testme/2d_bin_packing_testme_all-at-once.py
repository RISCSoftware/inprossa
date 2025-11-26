
from z3 import *

# Box dimensions
BOX_HEIGHT = 6
BOX_WIDTH = 10

# Item datatype
Item = Datatype('Item')
Item.declare('item', ('name', StringSort()), ('width', IntSort()), ('height', IntSort()))
Item = Item.create()

# Items
ITEMS = [
    Item.item(StringVal("item1"), IntVal(4), IntVal(3)),
    Item.item(StringVal("item2"), IntVal(3), IntVal(2)),
    Item.item(StringVal("item3"), IntVal(5), IntVal(3)),
    Item.item(StringVal("item4"), IntVal(2), IntVal(4)),
    Item.item(StringVal("item5"), IntVal(3), IntVal(3)),
    Item.item(StringVal("item6"), IntVal(5), IntVal(2))
]

NUM_ITEMS = len(ITEMS)

# Maximum number of boxes we might need (worst case, each item in separate box)
MAX_BOXES = NUM_ITEMS

# Decision variables

# Which box each item is assigned to
item_box_assignment = [Int(f'item_box_assignment_{i}') for i in range(NUM_ITEMS)]

# Position of each item within its box
x_positions = [Int(f'x_position_{i}') for i in range(NUM_ITEMS)]
y_positions = [Int(f'y_position_{i}') for i in range(NUM_ITEMS)]

# Binary variable indicating if a box is used
box_used = [Bool(f'box_used_{b}') for b in range(MAX_BOXES)]

# Number of boxes used
nr_used_boxes = Int('nr_used_boxes')

s = Optimize()

# Constraints

# Each item must be assigned to exactly one box
for i in range(NUM_ITEMS):
    s.add(And(item_box_assignment[i] >= 0, item_box_assignment[i] < MAX_BOXES))

# Items must fit within the box dimensions
for i in range(NUM_ITEMS):
    s.add(And(
        x_positions[i] >= 0,
        y_positions[i] >= 0,
        x_positions[i] + Item.width(ITEMS[i]) <= BOX_WIDTH,
        y_positions[i] + Item.height(ITEMS[i]) <= BOX_HEIGHT
    ))


# No overlapping items in the same box
def add_no_overlap_constraints():
    for i in range(NUM_ITEMS):
        for j in range(i + 1, NUM_ITEMS):
            # If items i and j are in the same box, they must not overlap
            same_box = item_box_assignment[i] == item_box_assignment[j]

            # Non-overlapping constraints
            no_overlap_x = Or(
                x_positions[i] + Item.width(ITEMS[i]) <= x_positions[j],
                x_positions[j] + Item.width(ITEMS[j]) <= x_positions[i]
            )

            no_overlap_y = Or(
                y_positions[i] + Item.height(ITEMS[i]) <= y_positions[j],
                y_positions[j] + Item.height(ITEMS[j]) <= y_positions[i]
            )

            s.add(Implies(same_box, Or(no_overlap_x, no_overlap_y)))


add_no_overlap_constraints()

# Link box_used variables to item assignments
for b in range(MAX_BOXES):
    # If any item is assigned to box b, then box_used[b] must be True
    items_in_box_b = [item_box_assignment[i] == b for i in range(NUM_ITEMS)]
    if items_in_box_b:
        s.add(Implies(Or(items_in_box_b), box_used[b]))
        # If no item is assigned to box b, then box_used[b] must be False
        s.add(Implies(Not(Or(items_in_box_b)), Not(box_used[b])))
    else:
        s.add(Not(box_used[b]))

# nr_used_boxes is the number of boxes that are used
s.add(nr_used_boxes == Sum([If(box_used[b], 1, 0) for b in range(MAX_BOXES)]))

# Objective: minimize the number of boxes used
s.minimize(nr_used_boxes)

# Check satisfiability
if s.check() == sat:
    model = s.model()

    # Prepare results
    result_item_box_assignment = []
    result_x_y_positions = []

    for i in range(NUM_ITEMS):
        box = model.evaluate(item_box_assignment[i]).as_long()
        x = model.evaluate(x_positions[i]).as_long()
        y = model.evaluate(y_positions[i]).as_long()

        result_item_box_assignment.append({
            "item": ITEMS[i],
            "box": box
        })

        result_x_y_positions.append({
            "item": ITEMS[i],
            "x": x,
            "y": y
        })

    nr_boxes = model