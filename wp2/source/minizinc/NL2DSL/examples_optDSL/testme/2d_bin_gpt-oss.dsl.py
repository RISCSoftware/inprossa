# z3 all at once: gpt-oss
'''
from z3 import *
import json

# constants
BOX_HEIGHT = IntVal(6)                     # height of each box
BOX_WIDTH = IntVal(10)                     # width of each box

# datatype for an item
Item = Datatype('Item')
Item.declare('mk', ('name', StringSort()), ('width', IntSort()), ('height', IntSort()))
Item = Item.create()

# items (constants)
# item1
ITEM_0 = Item.mk(StringVal("item1"), IntVal(4), IntVal(3))
# item2
ITEM_1 = Item.mk(StringVal("item2"), IntVal(3), IntVal(2))
# item3
ITEM_2 = Item.mk(StringVal("item3"), IntVal(5), IntVal(3))
# item4
ITEM_3 = Item.mk(StringVal("item4"), IntVal(2), IntVal(4))
# item5
ITEM_4 = Item.mk(StringVal("item5"), IntVal(3), IntVal(3))
# item6
ITEM_5 = Item.mk(StringVal("item6"), IntVal(5), IntVal(2))

ITEMS = [ITEM_0, ITEM_1, ITEM_2, ITEM_3, ITEM_4, ITEM_5]
ITEM_COUNT = len(ITEMS)

# decision variables
NR_USED_BOXES = Int('NR_USED_BOXES')                     # number of boxes used (objective)
ITEM_BOX = [Int(f'ITEM_{i}_BOX') for i in range(ITEM_COUNT)]   # box assignment per item
ITEM_X = [Int(f'ITEM_{i}_X') for i in range(ITEM_COUNT)]       # x‑position of item i
ITEM_Y = [Int(f'ITEM_{i}_Y') for i in range(ITEM_COUNT)]       # y‑position of item i

s = Optimize()

def add_fitting_constraints():
    for i, itm in enumerate(ITEMS):
        w = Item.width(itm)
        h = Item.height(itm)
        s.add(ITEM_X[i] >= 0,
              ITEM_Y[i] >= 0,
              ITEM_X[i] + w <= BOX_WIDTH,
              ITEM_Y[i] + h <= BOX_HEIGHT,
              ITEM_BOX[i] >= 1)                     # boxes are 1‑based
add_fitting_constraints()

def add_non_overlap_constraints():
    for i in range(ITEM_COUNT):
        for j in range(i + 1, ITEM_COUNT):
            wi = Item.width(ITEMS[i])
            hi = Item.height(ITEMS[i])
            wj = Item.width(ITEMS[j])
            hj = Item.height(ITEMS[j])
            no_overlap = Or(
                ITEM_X[i] + wi <= ITEM_X[j],
                ITEM_X[j] + wj <= ITEM_X[i],
                ITEM_Y[i] + hi <= ITEM_Y[j],
                ITEM_Y[j] + hj <= ITEM_Y[i]
            )
            # enforce only when items share the same box
            s.add(Implies(ITEM_BOX[i] == ITEM_BOX[j], no_overlap))
add_non_overlap_constraints()

def add_box_count_constraints():
    for i in range(ITEM_COUNT):
        s.add(NR_USED_BOXES >= ITEM_BOX[i])
    s.add(NR_USED_BOXES >= 0)
add_box_count_constraints()

# objective: minimise number of used boxes
s.minimize(NR_USED_BOXES)

# solve
if s.check() == sat:
    m = s.model()
    result = [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "mandatory_variable_name": "nr_used_boxes",
            "value": m.evaluate(NR_USED_BOXES).as_long()
        },
        {
            "description": "Which item is assigned to which box.",
            "mandatory_variable_name": "item_box_assignment",
            "value": [m.evaluate(v).as_long() for v in ITEM_BOX]
        },
        {
            "description": "Position x and y of each item within box",
            "mandatory_variable_name": "x_y_positions",
            "value": [
                {"x": m.evaluate(ITEM_X[i]).as_long(),
                 "y": m.evaluate(ITEM_Y[i]).as_long()}
                for i in range(ITEM_COUNT)
            ]
        }
    ]
    print(json.dumps(result, indent=2))
else:
    print("unsat")

'''
from Translator.Objects.MiniZincTranslator import MiniZincTranslator

# optdsl all at once: gpt-oss
code = """
# Height of each box
BOX_HEIGHT : int = 6
# Width of each box
BOX_WIDTH : int = 10
# Number of items
N_ITEMS : int = 6

# Item object type with width and height attributes
Item = DSRecord({
    "width": DSInt(0, BOX_WIDTH),
    "height": DSInt(0, BOX_HEIGHT)
})

# Definition of each item
ITEM1 : Item = {"width": 4, "height": 3}
ITEM2 : Item = {"width": 3, "height": 2}
ITEM3 : Item = {"width": 5, "height": 3}
ITEM4 : Item = {"width": 2, "height": 4}
ITEM5 : Item = {"width": 3, "height": 3}
ITEM6 : Item = {"width": 5, "height": 2}

# List of all items
Items = DSList(length = N_ITEMS, elem_type = Item)
ITEMS : Items = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]

# Decision variable: number of boxes used
nr_used_boxes : DSInt(0, N_ITEMS) = 0
# Decision variable: assignment of each item to a box (box indices start at 1)
item_box_assignment : DSList(N_ITEMS, DSInt(1, N_ITEMS)) = [1]*N_ITEMS
# Decision variable: x‑coordinate of each item inside its box
x_positions : DSList(N_ITEMS, DSInt(0, BOX_WIDTH)) = [0]*N_ITEMS
# Decision variable: y‑coordinate of each item inside its box
y_positions : DSList(N_ITEMS, DSInt(0, BOX_HEIGHT)) = [0]*N_ITEMS
# Objective variable (to be minimized)
objective : DSInt(0, N_ITEMS) = 0

# ----------------------------------------------------------------------
# Constraint: each item must lie completely inside its assigned box
def fit_inside_box(items: Items,
                   assignment: DSList(N_ITEMS, DSInt(1, N_ITEMS)),
                   xs: DSList(N_ITEMS, DSInt(0, BOX_WIDTH)),
                   ys: DSList(N_ITEMS, DSInt(0, BOX_HEIGHT)),
                   used_boxes: DSInt(0, N_ITEMS)):
    for i in range(1, N_ITEMS + 1):
        item = items[i]
        # x + width <= BOX_WIDTH
        assert xs[i] + item.width <= BOX_WIDTH
        # y + height <= BOX_HEIGHT
        assert ys[i] + item.height <= BOX_HEIGHT
        # box index must not exceed number of used boxes
        assert assignment[i] <= used_boxes
fit_inside_box(ITEMS, item_box_assignment, x_positions, y_positions, nr_used_boxes)

# ----------------------------------------------------------------------
# Constraint: items placed in the same box must not overlap
def non_overlap(items: Items,
                assignment: DSList(N_ITEMS, DSInt(1, N_ITEMS)),
                xs: DSList(N_ITEMS, DSInt(0, BOX_WIDTH)),
                ys: DSList(N_ITEMS, DSInt(0, BOX_HEIGHT))):
    for i in range(1, N_ITEMS):
        for j in range(i + 1, N_ITEMS + 1):
            # Only enforce non‑overlap when items share a box
            assert any([
                assignment[i] != assignment[j],
                xs[i] + items[i].width <= xs[j],
                xs[j] + items[j].width <= xs[i],
                ys[i] + items[i].height <= ys[j],
                ys[j] + items[j].height <= ys[i]
            ])
non_overlap(ITEMS, item_box_assignment, x_positions, y_positions)

# ----------------------------------------------------------------------
# Constraint: link objective to number of used boxes (minimization)
def set_objective(used_boxes: DSInt(0, N_ITEMS), obj: DSInt(0, N_ITEMS)):
    assert obj == used_boxes
set_objective(nr_used_boxes, objective)
"""
translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")