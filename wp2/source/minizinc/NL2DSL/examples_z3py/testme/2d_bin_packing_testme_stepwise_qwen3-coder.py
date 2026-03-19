import json

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver
from structures_utils import initial_clean_up

code = """
# --- Objects ---
Item = DSRecord({"width": Annotated[int, Field(strict=True, ge=1, le=10)], "height": Annotated[int, Field(strict=True, ge=1, le=10)]})
X_Y_Position = DSRecord({"x": Annotated[int, Field(strict=True, ge=0, le=10)], "y": Annotated[int, Field(strict=True, ge=0, le=10)]})

# --- Constants ---
BOX_HEIGHT: int = 10
BOX_WIDTH: int = 10
N_ITEMS: int = 20
N_ITEM_BOX_ASSIGNMENTS: int = 20
N_X_Y_POSITIONS: int = 20

# --- Decision Variables ---
nr_used_boxes: Annotated[int, Field(strict=True, ge=1, le=20)]
item_box_assignments: Annotated[list[Annotated[int, Field(strict=True, ge=1, le=20)]], Len(20, 20)]
x_y_positions: Annotated[list[X_Y_Position], Len(20, 20)]

# --- Problem Data (Constants) ---
ITEMS: Annotated[list[Item], Len(20, 20)] = [{"width": 10, "height": 4}, {"width": 2, "height": 10}, {"width": 2, "height": 4}, {"width": 10, "height": 10}, {"width": 7, "height": 2}, {"width": 9, "height": 10}, {"width": 5, "height": 6}, {"width": 7, "height": 5}, {"width": 1, "height": 7}, {"width": 5, "height": 3}, {"width": 3, "height": 9}, {"width": 9, "height": 4}, {"width": 2, "height": 10}, {"width": 4, "height": 3}, {"width": 2, "height": 2}, {"width": 4, "height": 9}, {"width": 2, "height": 8}, {"width": 1, "height": 1}, {"width": 1, "height": 7}, {"width": 4, "height": 4}]

# --- Objective ---
def calculate_objective(item_box_assignments: Annotated[list[Annotated[int, Field(strict=True, ge=1, le=20)]], Len(20, 20)],
                       boxes_used: Annotated[list[Annotated[bool, Field()]], Len(20, 20)]) -> int:
    # Constraint: if any item is assigned to box b, then boxes_used[b] = True
    for b in range(1, 21):
        any_item_in_box: bool = False
        for i in range(1, N_ITEM_BOX_ASSIGNMENTS + 1):
            if item_box_assignments[i] == b:
                any_item_in_box = True
        if any_item_in_box:
            assert boxes_used[b] == True

    # Objective: minimize sum of boxes_used
    total_boxes_used: int = 0
    for b in range(1, 21):
        if boxes_used[b]:
            total_boxes_used = total_boxes_used + 1
    return total_boxes_used

boxes_used : Annotated[list[Annotated[bool, Field()]], Len(20, 20)]
objective = calculate_objective(item_box_assignments, boxes_used)
nr_used_boxes = objective
minimize(objective)
"""
translator = MiniZincTranslator(initial_clean_up(code))
model = translator.unroll_translation().replace("True", "true").replace("False", "false")
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model, last_in_progress=True))




