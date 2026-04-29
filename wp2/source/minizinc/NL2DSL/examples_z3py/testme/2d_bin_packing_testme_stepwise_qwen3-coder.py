import json

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver
from structures_utils import initial_clean_up

code = """
# --- Objects ---


# --- Constants and Decision Variables ---
NITEMS : int = 10
NBOXES : int = 10
BOX_CAPACITIES : DSList(length=NBOXES, elem_type=DSInt()) = [21,31,5,2,32,4,23,12,22,7]
ITEM_LENGTHS : DSList(length=NITEMS, elem_type=DSInt()) = [4,11,9,14,2,21,7,18,3,3]
MAX_ITEM_LENGTH : int = 21
assignments: DSList(length=NITEMS * 2, elem_type=DSInt(1, NBOXES))
cut_positions: DSList(length=NITEMS, elem_type=DSInt(0, MAX_ITEM_LENGTH))
cut_items: DSList(length=NITEMS * 2, elem_type=DSInt(0, MAX_ITEM_LENGTH))
total_cost: DSInt(lb=0)


#--- Objective ---
# Approach 4: Decision-Based Cost Tracking
def calculate_total_cost(cut_positions: Annotated[list[Annotated[int, Field(strict=True, ge=0, le=21)]], Len(10, 10)],
                         assignments: Annotated[list[Annotated[int, Field(strict=True, ge=1, le=10)]], Len(20, 20)],
                         cut_items: Annotated[list[Annotated[int, Field(strict=True, ge=0, le=21)]], Len(20, 20)]) -> int:
    cutting_cost: int = 0
    use_cost: int = 0

    # Calculate cutting cost
    for i in range(1, NITEMS + 1):
        if cut_positions[i] != 0:
            cutting_cost = cutting_cost + 1

    # Calculate box usage cost
    box_used: Annotated[list[Annotated[bool, Field()]], Len(10, 10)]
    for b in range(1, NBOXES + 1):
        box_used[b] = False
        for j in range(1, NITEMS * 2 + 1):
            if assignments[j] == b:
                box_used[b] = True
        if box_used[b]:
            use_cost = use_cost + 3

    total_cost: int = cutting_cost + use_cost
    return total_cost

objective = calculate_total_cost(cut_positions, assignments, cut_items)
minimize(objective)

#--- Constraints ---
def cutting_machine(
    cut_positions: Annotated[list[Annotated[int, Field(strict=True, ge=0, le=21)]], Len(10, 10)]
    ):
    cutting_cost: int = 0
    cut_items: Annotated[list[Annotated[int, Field(strict=True, ge=0, le=21)]], Len(20, 20)]
    for n_item in range(1, NITEMS + 1):
        cut_items[2 * n_item] = ITEM_LENGTHS[n_item] - cut_positions[n_item]
        cut_items[2 * n_item - 1] = cut_positions[n_item]
        if cut_positions[n_item] != 0:
            # A cut is made
            cutting_cost = cutting_cost + 1

    return cut_items, cutting_cost

def packing_machine(
    assignments: Annotated[list[Annotated[int, Field(strict=True, ge=1, le=10)]], Len(20, 20)],
    cut_items: Annotated[list[Annotated[int, Field(strict=True, ge=0, le=21)]], Len(20, 20)]
    ):
    use_cost: int = 0
    cap: Annotated[list[Annotated[int, Field(strict=True, ge=0)]], Len(10, 10)]
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS * 2 + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + cut_items[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            use_cost = use_cost + 3
    return use_cost

cut_items, cutting_cost = cutting_machine(cut_positions)
use_cost = packing_machine(assignments, cut_items)
assert total_cost == cutting_cost + use_cost
"""
translator = MiniZincTranslator(initial_clean_up(code))
model = translator.unroll_translation().replace("True", "true").replace("False", "false")
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model, last_in_progress=True))




