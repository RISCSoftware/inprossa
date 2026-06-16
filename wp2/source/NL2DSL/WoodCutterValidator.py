import json

class UnsatisfiableProblemError(Exception):
    def __init__(self, dimension, message="Given the provided constants, the problem is unsatisfiable. At least one item's dimensions exceeds a box dimension."):
        super().__init__(message)
        self.dimension = dimension

    def __str__(self):
        return f"{self.dimension} -> {self.args[0]}"

def validate_solution(solver_solution : dict, task : dict, model = None):
    """
    Validate a solver's solution given constants in task
    Args:
        solver_solution (dict): solver's solution
        task (dict): task, contains constants (input variables) to validate against
    """
    assert solver_solution is not None, "Solution is None."

    # Extract solution
    task = task["input"]
    cut_positions = solver_solution["cut_positions"][len(solver_solution["cut_positions"])-1]
    cut_items: list[int] = solver_solution["cut_items"][len(solver_solution["cut_items"])-1]
    assignments = solver_solution["assignments"][len(solver_solution["assignments"])-1]
    assert len(cut_positions) == int(task["NITEMS"]), f"Invalid number of cut_positions: {len(cut_positions)}"
    assert len(cut_items) == int(task["NITEMS"])*2, f"Incorrect number of cut_items for {len(cut_items)} items"
    assert len(assignments) == int(task["NITEMS"])*2, f"Incorrect number of assignments for {len(cut_items)} items"

    # Validate objective
    if "total_cost" in solver_solution:
        objective_val = solver_solution["total_cost"][len(solver_solution["total_cost"])-1]
    else:
        objective_val = solver_solution["objective"][len(solver_solution["objective"])-1]
    if model is not None: model.objective_val = objective_val
    used_boxes = len(set([(assignment) for (item, assignment) in zip(cut_items, assignments) if item != 0]))
    assert objective_val > 0, f"Invalid value for objective: {objective_val}"
    assert objective_val == sum(1 for x in cut_positions if x != 0) + used_boxes * 3, f"Invalid value for objective, number of cuts + number of used boxes do not accumulate to resulting cost: {sum(1 for x in cut_items if x != 0) + len(set(assignments)) * 3}"

    # Validate cut does not exceed item boundaries and cut items are valid after being cut
    for i in range(len(cut_positions)//2):
        cut = cut_positions[i]
        item_length = json.loads(task["ITEM_LENGTHS"])[i]
        assert 0 <= cut < item_length, f"Invalid cut position for item {i}: {cut}"

        assert 0 <= cut_positions[2 * i - 1] < item_length, f"Invalid length of left part of cut item: {cut_items[2 * i - 1]}"
        assert 0 <= cut_positions[2 * i] < item_length, f"Invalid length of right part of cut item: {cut_items[2 * i]}"
        assert cut_items[2 * i] == cut_positions[i], f"Invalid length of left part of cut item: {cut_items[2 * i]}"
        assert cut_items[2 * i + 1] == item_length - cut_positions[i], f"Invalid length of right part of cut item: {cut_items[2 * i - 1]}"

    capacities = [0] * int(task["NBOXES"])
    for i, assignment in enumerate([(assignment if item != 0 else 0) for (item, assignment) in zip(cut_items, assignments)]):
        # Box indices of assignments start at 0
        if 0 in assignments:
            capacities[assignment] = capacities[assignment] + cut_items[i]
        # Box indices of assignments start at 1
        else:
            capacities[assignment - 1] = capacities[assignment - 1] + cut_items[i]
    actual_box_capacities = json.loads(task["BOX_CAPACITIES"])
    for i, capacity in enumerate(capacities):
        assert 0 <= capacity <= actual_box_capacities[i], f"assigned items with length of {capacity}, exceed capacity of box {i}: {actual_box_capacities[i]}. Assigned box indices must start at 1."

def main():
    solution = {'assignments': [[6, 2, 2, 2, 2, 5, 5, 2, 2, 2, 2, 5]], 'assignments__packing_machine__1': [[6, 2, 2, 2, 2, 5, 5, 2, 2, 2, 2, 5]], 'box_load__packing_machine__1': [[0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 0, 18, 15, 15, 30], [0, 4, 32, 32, 28, 27], [0, 4, 15, 32, 28, 17], [0, 15, 31, 25, 31, 32], [0, 15, 32, 27, 22, 1], [0, 15, 32, 27, 22, 1], [0, 15, 32, 27, 22, 1], [0, 29, 31, 26, 32, 27], [0, 29, 32, 32, 32, 23], [0, 31, 28, 32, 10, 32], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 0, 20], [0, 31, 0, 0, 9, 19], [0, 31, 0, 0, 9, 6], [0, 31, 0, 0, 9, 6], [0, 31, 0, 0, 9, 6], [0, 31, 0, 0, 9, 6], [0, 31, 0, 0, 9, 6], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0], [0, 31, 0, 0, 30, 0]], 'cut_items': [[0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21]], 'cut_items__cutting_machine__1': [[18, 32, 12, 17, 20, 32, 27, 25, 21, 27, 3, 0], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21], [0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21]], 'cut_items__packing_machine__1': [[0, 4, 0, 11, 0, 9, 0, 14, 0, 2, 0, 21]], 'cut_positions': [[0, 0, 0, 0, 0, 0]], 'cut_positions__cutting_machine__1': [[0, 0, 0, 0, 0, 0]], 'cutting_cost': [0], 'cutting_cost__cutting_machine__1': [0, 0, 0, 0, 0, 0, 0], 'solver_result_is': 'optimal', 'total_cost': [6], 'use_cost': [6], 'use_cost__packing_machine__1': [0, 0, 3, 3, 3, 6, 6]}
    task = {'input': {'BOX_CAPACITIES': '[21,31,5,2,32,4,23,12,22,7]', 'ITEM_LENGTHS': '[4,11,9,14,2,21,7,18,3,3]', 'MAX_ITEM_LENGTH': '32', 'NBOXES': '6', 'NITEMS': '6'}}
    validate_solution(solution, task)


