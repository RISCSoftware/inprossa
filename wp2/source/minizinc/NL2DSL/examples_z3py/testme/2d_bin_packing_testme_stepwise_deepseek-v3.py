from z3 import *

# Box height constant
BOX_HEIGHT = 6
# Box width constant
BOX_WIDTH = 10

# Item datatype
Item = Datatype('Item')
Item.declare('item', ('name', StringSort()), ('width', IntSort()), ('height', IntSort()))
Item = Item.create()

# List of items
ITEMS = [
    Item.item(StringVal("item1"), IntVal(4), IntVal(3)),
    Item.item(StringVal("item2"), IntVal(3), IntVal(2)),
    Item.item(StringVal("item3"), IntVal(5), IntVal(3)),
    Item.item(StringVal("item4"), IntVal(2), IntVal(4)),
    Item.item(StringVal("item5"), IntVal(3), IntVal(3)),
    Item.item(StringVal("item6"), IntVal(5), IntVal(2))
]

# Number of boxes used in the end to pack all items. Minimizing it is the objective.
nr_used_boxes = Int('nr_used_boxes')

# Which item is assigned to which box.
item_box_assignment = [Int(f'item_box_assignment_{i}') for i in range(len(ITEMS))]

# Position x and y of each item within box
x_positions = [Int(f'x_positions_{i}') for i in range(len(ITEMS))]
y_positions = [Int(f'y_positions_{i}') for i in range(len(ITEMS))]

s = Optimize()

def define_constraints():
    constraints = []
    # Each item must be assigned to a box
    for i in range(len(ITEMS)):
        constraints.append(And(item_box_assignment[i] >= 0, item_box_assignment[i] < nr_used_boxes))
    # Items must fit within their box boundaries
    for i in range(len(ITEMS)):
        constraints.append(And(x_positions[i] >= 0, x_positions[i] + Item.width(ITEMS[i]) <= BOX_WIDTH))
        constraints.append(And(y_positions[i] >= 0, y_positions[i] + Item.height(ITEMS[i]) <= BOX_HEIGHT))
    # Items in the same box must not overlap
    for i in range(len(ITEMS)):
        for j in range(i+1, len(ITEMS)):
            same_box = (item_box_assignment[i] == item_box_assignment[j])
            no_overlap_x = Or(x_positions[i] + Item.width(ITEMS[i]) <= x_positions[j], x_positions[j] + Item.width(ITEMS[j]) <= x_positions[i])
            no_overlap_y = Or(y_positions[i] + Item.height(ITEMS[i]) <= y_positions[j], y_positions[j] + Item.height(ITEMS[j]) <= y_positions[i])
            constraints.append(Implies(same_box, Or(no_overlap_x, no_overlap_y)))
    return constraints

for c in define_constraints():
    s.add(c)

s.minimize(nr_used_boxes)


if s.check() == sat:
    m = s.model()
    print("Satisfiable")
else:
    print("Unsatisfiable")