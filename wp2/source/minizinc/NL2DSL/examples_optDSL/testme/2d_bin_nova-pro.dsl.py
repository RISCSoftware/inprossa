# z3 all at once: gpt-oss
'''
from z3 import *
import json



# solve
if s.check() == sat:
    m = s.model()
    print("")
else:
    print("unsat")

'''
from Translator.Objects.MiniZincTranslator import MiniZincTranslator

# optdsl all at once: gpt-oss
code = """
# Objects
Item = DSRecord({
    "name": float,
    "width": DSInt(0, BOX_WIDTH),
    "height": DSInt(0, BOX_HEIGHT)
})

# Constants
# Box dimensions
BOX_HEIGHT : int = 6
BOX_WIDTH : int = 10
# Items
ITEM1 : Item = {"name": "item1", "width": 4, "height": 3}
ITEM2 : Item = {"name": "item2", "width": 3, "height": 2}
ITEM3 : Item
ITEM3.name = "item3"
ITEM3.width = 5
ITEM3.height = 3
ITEM4 : Item
ITEM4.name = "item4"
ITEM4.width = 2
ITEM4.height = 4
ITEM5 : Item
ITEM5.name = "item5"
ITEM5.width = 3
ITEM5.height = 3
ITEM6 : Item
ITEM6.name = "item6"
ITEM6.width = 5
ITEM6.height = 2
Items = DSList(length = 6, elem_type = Item)
ITEMS : Items = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N_ITEMS : int = 6

# Decision Variables
# Assignment of each item to a box
ItemBoxAssignment = DSList(N_ITEMS, DSInt(1, 100))  # Assuming max 100 boxes
item_box_assignment : ItemBoxAssignment
# Position (x, y) of each item within its assigned box
XYPosition = DSRecord({
    "x": DSInt(1, BOX_WIDTH),
    "y": DSInt(1, BOX_HEIGHT)
})
XYPositions = DSList(N_ITEMS, XYPosition)
x_y_positions : XYPositions
# Number of boxes used
nr_used_boxes : DSInt(1, 100)  # Assuming max 100 boxes

# Objective
objective = nr_used_boxes

# Constraints

def no_overlap(items: Items, item_box_assignment: ItemBoxAssignment, x_y_positions: XYPositions, box_width: int, box_height: int):
    for i in range(1, N_ITEMS + 1):
        for j in range(i + 1, N_ITEMS + 1):
            if item_box_assignment[i] == item_box_assignment[j]:
                item_i = items[i - 1]
                item_j = items[j - 1]
                pos_i = x_y_positions[i - 1]
                pos_j = x_y_positions[j - 1]
                assert not (pos_i.x < pos_j.x + item_j.width and pos_i.x + item_i.width > pos_j.x and pos_i.y < pos_j.y + item_j.height and pos_i.y + item_i.height > pos_j.y)

def one_item_one_box(item_box_assignment: ItemBoxAssignment):
    for i in range(1, N_ITEMS + 1):
        count = 0
        for j in range(1, N_ITEMS + 1):
            if item_box_assignment[j] == item_box_assignment[i]:
                count += 1
        assert count == 1

# Calling constraints
#fit_inside_box(ITEM1, x_y_positions[0].x, x_y_positions[0].y, BOX_WIDTH, BOX_HEIGHT)
no_overlap(ITEMS, item_box_assignment, x_y_positions, BOX_WIDTH, BOX_HEIGHT)
one_item_one_box(item_box_assignment)
"""

code = """
# --- Objects ---
Item = DSRecord({
    "name": int,
    "width": int,
    "height": int
})
Box = DSRecord({
    "width": int,
    "height": int
})

# --- Constants ---
# Number of items
N_ITEMS : int = 6
# Box dimensions
BOX_HEIGHT : int = 6
BOX_WIDTH : int = 10
# Items
ITEM1 : Item = {"name": 1, "width": 4, "height": 3}
ITEM2 : Item = {"name": 2, "width": 3, "height": 2}
ITEM3 : Item = {"name": 3, "width": 5, "height": 3}
ITEM4 : Item = {"name": 4, "width": 2, "height": 4}
ITEM5 : Item = {"name": 5, "width": 3, "height": 3}
ITEM6 : Item = {"name": 6, "width": 5, "height": 2}
Items = DSList(length = N_ITEMS, elem_type = Item)
ITEMS : Items = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]

# --- Decision variables ---
N_BOXES : int = 2  # Assuming a fixed number of boxes for simplicity
nr_used_boxes : DSInt(0, N_BOXES)
ItemBoxAssignment = DSList(length = N_ITEMS, elem_type = DSInt(1, N_BOXES))
item_box_assignment : ItemBoxAssignment
XPositions = DSList(length = N_ITEMS, elem_type = DSInt(0, BOX_WIDTH))
x_positions : XPositions
YPositions = DSList(length = N_ITEMS, elem_type = DSInt(0, BOX_HEIGHT))
y_positions : YPositions



# --- Constraints ---
def fit_inside_box(items: Items, item_box_assignment: ItemBoxAssignment, x_positions: XPositions, y_positions: YPositions, box_width: int, box_height: int):
    for i in range(1, N_ITEMS + 1):
        item = items[i]
        box_number = item_box_assignment[i]
        x_pos = x_positions[i]
        y_pos = y_positions[i]
        assert x_pos + item.width <= box_width
        assert y_pos + item.height <= box_height
fit_inside_box(ITEMS, item_box_assignment, x_positions, y_positions, BOX_WIDTH, BOX_HEIGHT)
# Objective: Minimize the number of boxes used
objective = nr_used_boxes

def no_overlap(items: Items, item_box_assignment: ItemBoxAssignment, x_positions: XPositions, y_positions: YPositions):
    for i in range(1, N_ITEMS):
        for j in range(i + 1, N_ITEMS + 1):
            if item_box_assignment[i] == item_box_assignment[j]:
                item_i = items[i]
                item_j = items[j]
                x_pos_i = x_positions[i]
                y_pos_i = y_positions[i]
                x_pos_j = x_positions[j]
                y_pos_j = y_positions[j]
                assert not (x_pos_i < x_pos_j + item_j.width and x_pos_i + item_i.width > x_pos_j and y_pos_i < y_pos_j + item_j.height and y_pos_i + item_i.height > y_pos_j)
no_overlap(ITEMS, item_box_assignment, x_positions, y_positions)"""
translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")