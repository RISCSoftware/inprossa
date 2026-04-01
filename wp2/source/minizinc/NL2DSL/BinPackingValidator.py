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

    # Extract assigments to an array of dicts: box_id, x, y
    solution : list[dict] = _extract_assignment_and_position(solver_solution)
    given_items = task["input"]["ITEMS"]
    box_height = task["input"]["BOX_HEIGHT"]
    box_width = task["input"]["BOX_WIDTH"]
    if isinstance(given_items, str):
        given_items = json.loads(given_items.replace("'", "\""))
        box_height = int(box_height)
        box_width = int(box_width)
    assert len(solution) == len(given_items), f"Incorrect number of assignments of items: {len(solution)}"

    # Validate objective
    if "objective" in solver_solution:
        objective_val = solver_solution["objective"][len(solver_solution["objective"])-1]
    else:
        objective_val = solver_solution["nr_used_boxes"][len(solver_solution["nr_used_boxes"])-1]
    try:
        assert objective_val > 0, f"Invalid value for objective: {objective_val}"
        assert (objective_val <= len(task["input"]["ITEMS"])), f"Invalid value for objective, more boxes than items: {objective_val}"
        number_of_used_boxes = len(set([solution_comp["box_id"] for solution_comp in solution]))
        assert objective_val == number_of_used_boxes, "Invalid value for objective, max_box_id and said value do not match."
    except AssertionError as e:
        print(e)

    # Validate constraints for specific problem
    for i, item_placement in enumerate(solution):
        if "item_id" in item_placement:
            if len([sol for sol in solution if sol["item_id"] == 0]) != 0:
                item = given_items[item_placement["item_id"]]
            else:
                item = given_items[item_placement["item_id"] - 1]
        else:
            item = given_items[i]

        # Validate items do not exceed box boundaries
        assert item_placement["x"] + item["width"] <= box_width, f"Placement of Item {i} at {item_placement["x"] + item["width"]} exceeds box width {box_width}"
        assert item_placement["y"] + item["height"] <= box_height, f"Placement of Item {i} at {item_placement["y"] + item["height"]} exceeds box height {box_height}"
        if "item_id" in item_placement:
            assert item_placement["item_id"] >= 0, f"Invalid value for item_id: {item_placement["item_id"]}"
            assert item_placement["item_id"] <= len(given_items), f"Invalid value for item_id: {item_placement["item_id"]}"
        if "box_id" in item_placement:
            assert item_placement["box_id"] >= 0, f"Invalid value for box_id: {item_placement["box_id"]}"
            assert item_placement["box_id"] <= len(given_items), f"Invalid value for box_id, more boxes than items: {item_placement["box_id"]}"

        # Validate items do not overlap
        for j in range(i + 1, len(solution)):
            item_i: dict = given_items[i]
            item_j: dict = given_items[j]
            assign_i: dict = item_placement
            assign_j: dict = solution[j]

            # Check if items are in the same box
            if assign_i["box_id"] == assign_j["box_id"]:

                # Check for non-overlapping
                        # item j is on the right-hand-side of item i
                assert (assign_i["x"] + item_i["width"] <= assign_j["x"] or
                        # item i is on the right-hand-side of item j
                        assign_j["x"] + item_j["width"] <= assign_i["x"] or
                        # item j is on the above of item i
                        assign_i["y"] + item_i["height"] <= assign_j["y"] or
                        # item i is on the above of item j
                        assign_j["y"] + item_j["height"] <= assign_i["y"]), f"Items {i+1} and {j+1} overlap."

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
