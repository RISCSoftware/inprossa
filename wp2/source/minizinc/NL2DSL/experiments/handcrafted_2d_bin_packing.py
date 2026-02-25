import json
import os

from BinPackingValidator import validate_solution
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver

def apply_handcrafted(directory: str, object_types_are_fixed: bool):
    objective_values = []
    solve_times = []
    for filename in os.listdir(directory):
        if (filename.endswith(".json")): # and "02_020_10" in filename
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if object_types_are_fixed:
                box_width = data["input_variables"]["BOX_WIDTH"]["value"]
                box_height = data["input_variables"]["BOX_HEIGHT"]["value"]
                items = data["input_variables"]["ITEMS"]["value"]
                data = {
                    "BOX_WIDTH": data["input_variables"]["BOX_WIDTH"]["value"],
                    "BOX_HEIGHT": data["input_variables"]["BOX_HEIGHT"]["value"],
                    "ITEMS": data["input_variables"]["ITEMS"]["value"]
                }
            else:
                box_width = data["BOX_WIDTH"]
                box_height = data["BOX_HEIGHT"]
                items = data["ITEMS"]

            code = """
NITEMS : int = {}
Item = DSRecord({{
    \"width\" : DSInt(lb=1),
    \"height\" : DSInt(lb=1)
}})
BoxAssignment = DSRecord({{
    \"x\" : DSInt(lb=0),
    \"y\" : DSInt(lb=0),
    \"box_id\" : DSInt(1, NITEMS)
}})

BOX_WIDTH : int = {}
BOX_HEIGHT : int = {}
ITEMS: DSList(NITEMS, Item) = {}
item_box_assignments: DSList(NITEMS, BoxAssignment)
x_y_positions : DSList(NITEMS, BoxAssignment)
nr_used_boxes : DSInt(1, NITEMS)

for i in range(1, NITEMS + 1):
    assignment_i : BoxAssignment = item_box_assignments[i]
    #item_i : Item = ITEMS[i]
    assert 0 <= assignment_i.x
    assert 0 <= assignment_i.y
    assert assignment_i.y + ITEMS[i].height <= BOX_HEIGHT
    assert assignment_i.x + ITEMS[i].width <= BOX_WIDTH
    assert 0 < assignment_i.box_id

    for j in range(i + 1, NITEMS + 1):
        assignment_j : BoxAssignment = item_box_assignments[j]
        #item_j : Item = ITEMS[j]
        assert (
            (assignment_i.box_id != assignment_j.box_id) or
            (assignment_i.x + ITEMS[i].width <= assignment_j.x) or
            (assignment_j.x + ITEMS[j].width <= assignment_i.x) or
            (assignment_i.y + ITEMS[i].height <= assignment_j.y) or
            (assignment_j.y + ITEMS[j].height <= assignment_i.y)
        )
for i in range(1, NITEMS + 1):
    if item_box_assignments[i].box_id > nr_used_boxes:
        nr_used_boxes = item_box_assignments[i].box_id
minimize(nr_used_boxes)
x_y_positions = item_box_assignments
    """.format(len(items), box_width, box_height, json.dumps(items))


            translator = MiniZincTranslator(code)
            model = translator.unroll_translation()
            solver = MiniZincSolver()
            solution, solve_time = solver.solve_with_command_line_minizinc(model, last_in_progress=True)
            print(f"{filename}")

            try:
                validate_solution(solution, {"input": data})
            except AssertionError as e:
                validation_res = f"Failed to validate solution: {e}"
                objective_values.append(-1)
                solve_times.append(-1)
            except Exception as e:
                validation_res = f"Evaluation failed: {e}"
                objective_values.append(-1)
                solve_times.append(-1)
            else:
                validation_res = f"Successfully validated solution."
                objective_values.append(solution["nr_used_boxes"][0])
                solve_times.append(solve_time)
            print(validation_res)
    print(f"""
*************************************
objective_values : {objective_values}
solve_times : {solve_times}
*************************************
""")
    return objective_values, solve_times

# apply_handcrafted("../problem_descriptions/testset_paper_2D-BPP_CLASS/", object_types_are_fixed=False)
# apply_handcrafted("../../problem_descriptions/testset_fixed_objects_2D-BPP_CLASS/", object_types_are_fixed=True)
