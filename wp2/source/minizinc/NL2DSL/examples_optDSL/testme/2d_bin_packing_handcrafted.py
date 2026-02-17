import json
import os

from BinPackingValidator import validate_solution
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver

directory = "../../problem_descriptions/testset_paper_2D-BPP_CLASS/"
result = {}
for filename in os.listdir(directory):
    if (filename.endswith(".json")): # and "02_020_10" in filename
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result[filename] = data
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
        solution = solver.solve_with_command_line_minizinc(model, last_in_progress=True)
        #if solution[0]["solver_result_is"] == "unknown":
        #    print(f"--------\n{model}\n----------")
        print(f"{filename}")

        try:
            validate_solution(solution[0], {"input": data})
        except AssertionError as e:
            validation_res = f"Failed to validate solution: {e}"
        except Exception as e:
            validation_res = f"Evaluation failed: {e}"
        else:
            validation_res = f"Successfully validated solution."
        print(validation_res)
