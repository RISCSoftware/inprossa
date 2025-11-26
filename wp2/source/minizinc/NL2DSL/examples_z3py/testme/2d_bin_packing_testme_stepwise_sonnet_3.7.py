'''from z3 import *


if s.check() == sat:
    m = s.model()
    print("Satisfiable")
else:
    print("Unsatisfiable")
'''
from Translator.Objects.MiniZincTranslator import MiniZincTranslator

code = """
# -- Objects --


# Define object types for the bin packing problem
Item = DSRecord({
    "width": DSInt(),
    "height": DSInt()
})

Position = DSRecord({
    "x": DSInt(),
    "y": DSInt()
})

Assignment = DSRecord({
    "item_id": DSInt(),
    "box_id": DSInt(),
    "position": Position
})



# --- Constants ---
BOX_HEIGHT: int = 6
BOX_WIDTH: int = 10
ITEM1: Item = {"width": 4, "height": 3}
ITEM2: Item = {"width": 3, "height": 2}
ITEM3: Item = {"width": 5, "height": 3}
ITEM4: Item = {"width": 2, "height": 4}
ITEM5: Item = {"width": 3, "height": 3}
ITEM6: Item = {"width": 5, "height": 2}
ITEMS: DSList(length=6, elem_type=Item) = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N_ITEMS: int = 6
N_ITEMS : int = 6
nr_used_boxes: DSInt(lb=1, ub=N_ITEMS)
box_used: DSList(length=N_ITEMS, elem_type=DSBool())
assignments: DSList(length=N_ITEMS, elem_type=Assignment)
item_y_positions: DSList(length=N_ITEMS, elem_type=DSInt(lb=0, ub=BOX_HEIGHT-1))
item_box_assignment: DSList(length=N_ITEMS, elem_type=DSInt(lb=1, ub=N_ITEMS))


# -- Objective --


def calculate_objective(box_used: DSList(length=N_ITEMS, elem_type=DSBool())):
    # Count the number of boxes used
    box_count = 0
    for i in range(1, N_ITEMS + 1):
        if box_used[i]:
            box_count = box_count + 1
    return box_count

# Calculate the objective - minimize number of boxes used
used_boxes = calculate_objective(box_used)

# Set the objective to minimize the number of boxes used
assert objective == used_boxes

# -- Constraints --



item_x_positions: DSList(length=N_ITEMS, elem_type=DSInt(lb=0, ub=BOX_WIDTH-1))

def items_fit_in_boxes(
    items: DSList(length=N_ITEMS, elem_type=Item),
    item_box_assignment: DSList(length=N_ITEMS, elem_type=DSInt(lb=1, ub=N_ITEMS)),
    item_x_positions: DSList(length=N_ITEMS, elem_type=DSInt(lb=0, ub=BOX_WIDTH-1)),
    item_y_positions: DSList(length=N_ITEMS, elem_type=DSInt(lb=0, ub=BOX_HEIGHT-1)),
    box_used: DSList(length=N_ITEMS, elem_type=DSBool()),
    box_width: int,
    box_height: int
):
    # For each item, ensure it fits within its assigned box
    for i in range(1, N_ITEMS + 1):
        # The item must fit within the box width
        assert item_x_positions[i] + items[i].width <= box_width
        
        # The item must fit within the box height
        assert item_y_positions[i] + items[i].height <= box_height
        
        # Ensure the box is marked as used if an item is assigned to it
        assert box_used[item_box_assignment[i]] == True
        
        # Check for overlapping items within the same box
        for j in range(1, N_ITEMS + 1):
            if i != j:
                # If items are in the same box, they must not overlap
                assert not (item_box_assignment[i] == item_box_assignment[j] and 
                           item_x_positions[i] < item_x_positions[j] + items[j].width and
                           item_x_positions[i] + items[i].width > item_x_positions[j] and
                           item_y_positions[i] < item_y_positions[j] + items[j].height and
                           item_y_positions[i] + items[i].height > item_y_positions[j])

    # Update assignment records for output
    for i in range(1, N_ITEMS + 1):
        assignments[i].item_id = 1

items_fit_in_boxes(ITEMS, item_box_assignment, item_x_positions, item_y_positions, box_used, BOX_WIDTH, BOX_HEIGHT)
"""
translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")