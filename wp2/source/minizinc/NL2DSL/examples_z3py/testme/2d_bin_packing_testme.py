from z3 import *

# ======================================================
# === 1. Define datatypes
# ======================================================

# Define datatype for Item
Item = Datatype('Item')
Item.declare('mkItem', ('name', StringSort()), ('width', IntSort()), ('height', IntSort()))
Item = Item.create()

# Define datatype for BoxAssignment
BoxAssignment = Datatype('BoxAssignment')
BoxAssignment.declare('mkBoxAssignment', ('item', Item), ('box_id', IntSort()), ('x', IntSort()), ('y', IntSort()))
BoxAssignment = BoxAssignment.create()

# Constructors/accessors
mkItem = Item.mkItem
get_name = Item.name
get_width = Item.width
get_height = Item.height

mkBoxAssignment = BoxAssignment.mkBoxAssignment
get_item = BoxAssignment.item
get_box_id = BoxAssignment.box_id
get_x = BoxAssignment.x
get_y = BoxAssignment.y

# ======================================================
# === 2. Define parameters as Z3 constants
# ======================================================

BOX_HEIGHT = IntVal(6)
BOX_WIDTH  = IntVal(10)

ITEM1 = mkItem(StringVal("item1"), IntVal(4), IntVal(3))
ITEM2 = mkItem(StringVal("item2"), IntVal(3), IntVal(2))
ITEM3 = mkItem(StringVal("item3"), IntVal(5), IntVal(3))
ITEM4 = mkItem(StringVal("item4"), IntVal(2), IntVal(4))
ITEM5 = mkItem(StringVal("item5"), IntVal(3), IntVal(3))
ITEM6 = mkItem(StringVal("item6"), IntVal(5), IntVal(2))

ITEMS = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N = len(ITEMS)

# ======================================================
# === 3. Define decision variables
# ======================================================

# Each item gets a box id and position (x,y)
box_ids = [Int(f"box_id_{i}") for i in range(N)]
xs = [Int(f"x_{i}") for i in range(N)]
ys = [Int(f"y_{i}") for i in range(N)]

# ======================================================
# === 4. Create the solver
# ======================================================

s = Optimize()

# ======================================================
# === 5. Constraints: items must fit inside their boxes
# ======================================================

for i, item in enumerate(ITEMS):
    width_i  = get_width(item)
    height_i = get_height(item)
    # Non-negative coordinates
    s.add(xs[i] >= 0)
    s.add(ys[i] >= 0)
    # Must fit inside box dimensions
    s.add(xs[i] + width_i <= BOX_WIDTH)
    s.add(ys[i] + height_i <= BOX_HEIGHT)

# ======================================================
# === 6. Constraints: no overlap for items in the same box
# ======================================================

for i in range(N):
    for j in range(i + 1, N):
        same_box = box_ids[i] == box_ids[j]

        # Overlap condition — at least one of these must hold to prevent overlap
        no_overlap = Or(
            xs[i] + get_width(ITEMS[i]) <= xs[j],
            xs[j] + get_width(ITEMS[j]) <= xs[i],
            ys[i] + get_height(ITEMS[i]) <= ys[j],
            ys[j] + get_height(ITEMS[j]) <= ys[i]
        )

        # If in the same box, then they cannot overlap
        s.add(Implies(same_box, no_overlap))

# ======================================================
# === 7. Minimize the number of boxes used
# ======================================================

# The number of distinct box IDs = max(box_ids) + 1
MAX_BOX_ID = Int("MAX_BOX_ID")
for i in range(N):
    s.add(box_ids[i] <= MAX_BOX_ID)
    s.add(box_ids[i] >= 0)

# Objective: minimize MAX_BOX_ID
s.minimize(MAX_BOX_ID)

# ======================================================
# === 8. Solve and print results
# ======================================================

if s.check() == sat:
    m = s.model()
    print("=== Solution ===")
    print(f"Minimal number of boxes used: {m[MAX_BOX_ID].as_long() + 1}")
    for i, item in enumerate(ITEMS):
        print(f"{get_name(item)}: box {m[box_ids[i]]}, position = ({m[xs[i]]}, {m[ys[i]]})")
else:
    print("No solution found.")
