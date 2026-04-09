import json

class UnsatisfiableProblemError(Exception):
    def __init__(self, dimension, message="Given the provided constants, the problem is unsatisfiable. At least one item's dimensions exceeds a box dimension."):
        super().__init__(message)
        self.dimension = dimension

    def __str__(self):
        return f"{self.dimension} -> {self.args[0]}"


def _extract_assignment_and_position(solver_solution: dict):
    """
    Extract item-box-assignments and x-y-positions from solver_solution
    Args:
        solver_solution (dict): solver solution
    """
    solution = []
    box_assigments = solver_solution["item_box_assignments"]
    # Initialize solution array
    for box_assigment in range(len(box_assigments[0])):
        solution.append({})
    # Extract solution from minizinc solution for validation
    for i, item_positions in enumerate(solver_solution["x_y_positions"][0]):
        if isinstance(item_positions, dict):
            for key in item_positions.keys():
                if "x" in key:
                    solution[i].update({"x": item_positions[key]})
                elif "y" in key:
                    solution[i].update({"y": item_positions[key]})
                elif "position" in key:
                    for position_key in item_positions[key]:
                        if "x" in position_key:
                            solution[i].update({"x": item_positions[key][position_key]})
                        elif "y" in position_key:
                            solution[i].update({"y": item_positions[key][position_key]})
                        else:
                            raise ValueError(
                                "Unreadable format of x_y_positions[\"position\"], no x or y position found.")
        else:
            raise ValueError("Unreadable format of x_y_positions of solver solution for validation.")
    for i, box_assigment in enumerate(box_assigments[0]):
        if isinstance(box_assigment, int):
            solution[i].update({"box_id": box_assigment})
        elif isinstance(box_assigment, dict):
            for key in box_assigment.keys():
                if "box" in key:
                    solution[i].update({"box_id": box_assigment[key]})
                elif "item" in key:
                    solution[i].update({"item_id": box_assigment[key]})
                elif "x" not in solution[i] or "y" not in solution[i]:
                    if "x" not in solution[i] and "x" in key:
                        solution[i].update({"x": box_assigment[key]})
                    elif "y" not in solution[i] and "y" in key:
                        solution[i].update({"y": box_assigment[key]})
                    elif "position" not in solution[i] and "position" in key:
                        for position_key in box_assigment[key]:
                            if "x" in position_key:
                                solution[i].update({"x": box_assigment[key][position_key]})
                            elif "y" in position_key:
                                solution[i].update({"y": box_assigment[key][position_key]})
                            else:
                                raise ValueError(
                                    "Unreadable format of item_box_assignments[\"position\"], no x or y position found.")
        else:
            raise ValueError(f"Unreadable format of item_box_assignments of solver solution for validation.")
    # check overlap to check if assignments contain valid positions
    overlap_detected = False
    for i, item_placement in enumerate(solution):
        for j in range(i + 1, len(solution)):
            if (solution[i]["box_id"] == solution[j]["box_id"] and
                solution[i]["x"] == 0 and
                solution[i]["y"] == 0 and
                solution[j]["x"] == 0 and
                solution[j]["y"] == 0):
                overlap_detected = True
    if overlap_detected:
        for i, box_assigment in enumerate(box_assigments[0]):
            if isinstance(box_assigment, dict):
                for key in box_assigment.keys():
                    if "x" in key and "box" not in key:
                        solution[i].update({"x": box_assigment[key]})
                    elif "y" in key:
                        solution[i].update({"y": box_assigment[key]})
                    elif "position" in key:
                        for position_key in box_assigment[key]:
                            if "x" in position_key:
                                solution[i].update({"x": box_assigment[key][position_key]})
                            elif "y" in position_key:
                                solution[i].update({"y": box_assigment[key][position_key]})

    if solution[0] == {}: raise ValueError("Unreadable format of solver solution for validation.")
    return solution

def validate_solution(solver_solution : dict, task : dict):
    """
    Validate a solver's solution given constants in task
    Args:
        solver_solution (dict): solver's solution
        task (dict): task, contains constants (input variables) to validate against
    """
    assert solver_solution is not None, "Solution is None."

    # Extract solution
    cut_positions = solver_solution["cut_positions"]
    cut_items: list[int] = solver_solution["cut_items"]
    assignments = solver_solution["assignments"]
    assert len(cut_positions) == task["NITEMS"], f"Invalid number of cuts: {len(cut_positions)}"
    assert len(cut_items) == len(assignments) == task["NITEMS"]*2, f"Incorrect number of assignments for {len(cut_items)} items"

    # Validate objective
    if "total_cost" not in solver_solution:
        objective_val = solver_solution["total_cost"]
    else:
        objective_val = solver_solution["objective"]
    assert objective_val > 0, f"Invalid value for objective: {objective_val}"
    assert objective_val == sum(1 for x in cut_items if x != 0) + len(set(assignments)) * 3, f"Invalid value for objective, number of cuts + number of used boxes do not accumulate to resulting cost: {sum(1 for x in cut_items if x != 0) + len(set(assignments)) * 3}"

    # Validate cut does not exceed item boundaries and cut items are valid after being cut
    for i, cut in enumerate(cut_positions):
        assert 0 <= cut < task["ITEM_LENGTHS"][i], f"Invalid cut position for item {i}: {cut}"

        assert 0 <= cut_positions[2 * i - 1] < task["ITEM_LENGTHS"][i], f"Invalid length of left part of cut item: {cut_items[2 * i - 1]}"
        assert 0 <= cut_positions[2 * i] < task["ITEM_LENGTHS"][i], f"Invalid length of right part of cut item: {cut_items[2 * i]}"
        assert cut_items[2 * i] == cut_positions[i], f"Invalid length of left part of cut item: {cut_items[2 * i - 1]}"
        assert cut_items[2 * i + 1] == task["ITEM_LENGTHS"][i] - cut_positions[i], f"Invalid length of right part of cut item: {cut_items[2 * i]}"

    capacities = [] * task["NBOXES"]
    for i, assignment in enumerate(assignments):
        capacities[assignment-1] += cut_items[i]
    for i, capacity in enumerate(capacities):
        assert 0 <= capacity <= task["BOX_CAPACITIES"][i]

def check_satisfiability_given(constants: list[dict]):
    """
    Check satisfiability of 2D bin packing problem instance given a set of constants.
    Args:
         constants (list[dict]): List of constants.
    """
    box_height = None
    box_width = None
    items = []
    for constant in constants:
        if "box_height" in constant["variable_name"].lower():
            box_height = constant["variable_instance"][0]
        if "box_width" in constant["variable_name"].lower():
            box_width = constant["variable_instance"][0]
        if "items" in constant["variable_name"].lower():
            items = constant["variable_instance"][1]
    if box_height is None or box_width is None or items is None or len(items) != len(items):
        raise ValueError("Could not find box_height or box_width or items.")
    if min([item["width"] for item in items]) < 0:
        raise ValueError(f"Invalid item width: {min([item["width"] for item in items])}")
    if min([item["height"] for item in items]) < 0:
        raise ValueError(f"Invalid item height: {min([item["height"] for item in items])}")
    if max([item["width"] for item in items]) > box_width:
        raise UnsatisfiableProblemError(max([item["width"] for item in items]))
    if max([item["height"] for item in items]) > box_height:
        raise UnsatisfiableProblemError(max([item["height"] for item in items]))
