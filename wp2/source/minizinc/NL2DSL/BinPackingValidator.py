import ast
import json
import re

from structures_utils import remove_programming_environment


def _extract_assignment_and_position(solver_solution: dict):
    solution = []
    box_assigments = solver_solution["item_box_assignments"]
    # Initialize solution array
    for box_assigment in range(len(box_assigments[0])):
        solution.append({})
    # Extract solution from minizinc solution for validation
    for i, box_assigment in enumerate(box_assigments[0]):
        if isinstance(box_assigment, int):
            solution[i].update({"box_id": box_assigment})
        elif isinstance(box_assigment, dict):
            for key in box_assigment.keys():
                if "box" in key:
                    solution[i].update({"box_id": box_assigment[key]})
                elif "item" in key:
                    solution[i].update({"item_id": box_assigment[key]})
                elif "x" in key:
                    solution[i].update({"x": box_assigment[key]})
                elif "y" in key:
                    solution[i].update({"y": box_assigment[key]})
                elif "position" in key:
                    for position_key in box_assigment[key]:
                        if "x" in position_key:
                            solution[i].update({"x": box_assigment[key][position_key]})
                        elif "y" in position_key:
                            solution[i].update({"y": box_assigment[key][position_key]})
                        else:
                            raise ValueError(
                                "Unreadable format of item_box_assignments[\"position\"], no x or y position found.")
                else:
                    raise ValueError("Unreadable format of item_box_assignments, no item_id or x or y key could be found.")
        else:
            raise ValueError(f"Unreadable format of item_box_assignments of solver solution for validation.")
    if "x" not in solution[0]:
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
                        raise ValueError("Unreadable format of x_y_positions of x,y from solver solution for validation.")
            else:
                raise ValueError("Unreadable format of x_y_positions of solver solution for validation.")
    return solution

def validate_solution(solver_solution : dict, task : dict):
    assert solver_solution is not None, "Solution is None."

    # Extract assigments to an array of dicts: box_id, x, y
    solution : list[dict] = _extract_assignment_and_position(solver_solution)
    given_items = task["input"]["ITEMS"]
    box_height = task["input"]["BOX_HEIGHT"]
    box_width = task["input"]["BOX_WIDTH"]
    assert len(solution) == len(given_items), f"Incorrect number of assignments of items: {len(solution)}"

    # Validate objective
    objective_val = solver_solution["objective"][len(solver_solution["objective"])-1]
    assert objective_val > 0, f"Invalid value for objective: {objective_val}"
    assert (objective_val <= len(task["input"]["ITEMS"])), f"Invalid value for objective, more boxes than items: {objective_val}"
    max_box_id = max([solution_comp["box_id"] for solution_comp in solution])
    assert objective_val == max_box_id or objective_val == max_box_id-1, "Invalid value for objective, max_box_id and said value do not match."

    for i, item_placement in enumerate(solution):
        if "item_id" in item_placement:
            item = given_items[item_placement["item_id"]]
        else:
            item = given_items[i]

        # Validate items do not exceed box boundaries
        assert item_placement["x"] + item["width"] <= box_width, f"Item placement {item_placement["x"] + item["width"]} exceeds box width {box_width}"
        assert item_placement["y"] + item["height"] <= box_height, f"Item placement {item_placement["y"] + item["height"]} exceeds box width {box_height}"
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
                        assign_j["y"] + item_j["height"] <= assign_i["y"]), f"Items {i} and {j} overlap."


d2_bin_packing_formalized_problem_description = [
# Input
"""
´´´ json
{
    "BOX_HEIGHT": 6,
    "BOX_WIDTH": 10,
    "ITEMS": [
        {
            "name": "item1",
            "width": 4,
            "height": 3
        },
        {
            "name": "item2",
            "width": 3,
            "height": 2
        },
        {
            "name": "item3",
            "width": 5,
            "height": 3
        },
        {
            "name": "item4",
            "width": 2,
            "height": 4
        },
        {
            "name": "item5",
            "width": 3,
            "height": 3
        },
        {
            "name": "item6",
            "width": 5,
            "height": 2
        }
    ]
}
´´´
""",
# Output
"""
´´´json
[
    {
        "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
        "is_objective": true,
        "mandatory_variable_name": "nr_used_boxes",
        "suggested_shape": "integer"
    },
    {
        "description": "Which item is assigned to which box.",
        "is_objective": false,
        "mandatory_variable_name": "item_box_assignments",
        "suggested_shape": "array"
    },
    {
        "description": "Position x and y of each item within box",
        "is_objective": false,
        "mandatory_variable_name": "x_y_positions",
        "suggested_shape": "array"
    }
]
´´´
"""
]
d2_bin_packing_formalized_problem_description_inst2 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 5,
        "BOX_WIDTH": 12,
        "ITEMS": [
            {
                "name": "item1",
                "width": 4,
                "height": 3
            },
            {
                "name": "item2",
                "width": 1,
                "height": 2
            },
            {
                "name": "item3",
                "width": 5,
                "height": 3
            },
            {
                "name": "item4",
                "width": 4,
                "height": 2
            },
            {
                "name": "item5",
                "width": 1,
                "height": 3
            },
            {
                "name": "item6",
                "width": 5,
                "height": 2
            },
            {
                "name": "item7",
                "width": 9,
                "height": 5
            },
            {
                "name": "item8",
                "width": 3,
                "height": 5
            },
            {
                "name": "item9",
                "width": 5,
                "height": 1
            }
        ]
    }
    ´´´
    """,
    # Output
    """
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "is_objective": true,
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "is_objective": false,
            "mandatory_variable_name": "item_box_assignments",
            "suggested_shape": "array"
        },
        {
            "description": "Position x and y of each item within box",
            "is_objective": false,
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array"
        }
    ]
    ´´´
    """,
    # Global description
    """
    Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box 
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.
    """,
    # Subproblem description - part 1
    """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 2
    """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 3
    """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """
    ]

"""
# Example of calling from another function:
if __name__ == "__main__":
    task = {
        "input": json.loads(remove_programming_environment(d2_bin_packing_formalized_problem_description_inst2[0])),
        "output": json.loads(remove_programming_environment(d2_bin_packing_formalized_problem_description_inst2[1]))
    }

    # Extract minizinc solver solutions

    file_content = ""
    with open("experiments/run_20_single_pipeline_optdsl_pydantic_11.10._inst2.txt", "r", encoding="utf-8") as f:
        f.read()
    pattern = re.compile(r"Solution model:\s*({.+})")
    matches = pattern.findall(file_content)
    solver_solutions = []
    for m in matches:
        try:
            obj = ast.literal_eval(m)
            solver_solutions.append((obj, m))
        except (SyntaxError, ValueError):
            # fallback or skip invalid dict-literal
            pass


    # Validate solver solutions
    validate_solution(json.loads("{\"objective\": [0, 0, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8], \"nr_used_boxes\": [8], \"item_box_assignments\": [[3, 1, 8, 5, 7, 2, 6, 1, 4]], \"x_y_positions\": [[{\"x\": 0, \"y\": 0}, {\"x\": 3, \"y\": 0}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}]]}"), task)

    for i, (solver_solution, m) in enumerate(solver_solutions):
        try:
            validate_solution(solver_solution, task)
        except AssertionError as e:
            print(f"Failed to validate solution {i}: {e}")
        else:
            print(f"Successfully validated solution {i}.")
        print(f"Solution: {m}")
"""