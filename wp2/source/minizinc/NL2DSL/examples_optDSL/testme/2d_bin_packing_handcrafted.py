import json
import os

from BinPackingValidator import validate_solution
from Translator_.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver

directory = "../../problem_descriptions/testset_paper_2D-BPP_CLASS/"
result = {}
for filename in os.listdir(directory):
    if filename.endswith(".json"): #
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result[filename] = data
        box_width = data["BOX_WIDTH"]
        box_height = data["BOX_HEIGHT"]
        """items = [
                {
                  "width": 4,
                  "height": 3
                },
                {
                  "width": 1,
                  "height": 2
                },
                {
                  "width": 5,
                  "height": 3
                },
                {
                  "width": 4,
                  "height": 2
                },
                {
                  "width": 1,
                  "height": 3
                },
                {
                  "width": 5,
                  "height": 2
                },
                {
                  "width": 9,
                  "height": 5
                },
                {
                  "width": 3,
                  "height": 5
                },
                {
                  "width": 5,
                  "height": 1
                }
              ]"""
        items = data["ITEMS"]

        code = """
NITEMS : int = {}
Item = DSRecord({{
    \"width\" : DSInt(lb=0),
    \"height\" : DSInt(lb=0)
}})
BoxAssignment = DSRecord({{
    \"x\" : DSInt(lb=0),
    \"y\" : DSInt(lb=0),
    \"box_id\" : DSInt(1, NITEMS)
}})

BOX_WIDTH : int = {}
BOX_HEIGHT : int = {}
ITEMS: DSList(NITEMS, Item) = {}
assignments_and_positions: DSList(NITEMS, BoxAssignment)
nr_boxes : DSInt(1, NITEMS)

for i in range(1, NITEMS + 1):
    assign_i : BoxAssignment = assignments_and_positions[i]
    assert 0 <= assign_i.x
    assert 0 <= assign_i.y
    assert assign_i.y + ITEMS[i].height <= BOX_HEIGHT
    assert assign_i.x + ITEMS[i].width <= BOX_WIDTH
    assert 0 < assign_i.box_id
    assert assign_i.box_id <= nr_boxes

    for j in range(i + 1, NITEMS + 1):
        assign_j : BoxAssignment = assignments_and_positions[j]
        assert assignments_and_positions[i].box_id != assignments_and_positions[j].box_id or \\
            (assign_i.x >= assign_j.x + ITEMS[j].width or \\
            assign_j.x >= assign_i.x + ITEMS[i].width or \\
            assign_i.y >= assign_j.y + ITEMS[j].height or \\
            assign_j.y >= assign_i.y + ITEMS[i].height)

for i in range(1, NITEMS):
    if assignments_and_positions[i].box_id > nr_boxes:
        nr_boxes = assignments_and_positions[i].box_id
minimize(nr_boxes)
""".format(len(items), box_width, box_height, json.dumps(items))
        code = """
NITEMS : int = {}
Item = DSRecord({{
    \"width\" : DSInt(lb=1),
    \"height\" : DSInt(lb=1)
}})
BoxAssignment = DSRecord({{
    \"x\" : DSInt(lb=0),
    \"y\" : DSInt(lb=0),
    \"box_id\" : DSInt()
}})

BOX_WIDTH : int = {}
BOX_HEIGHT : int = {}
ITEMS: DSList(NITEMS, Item) = {}
item_box_assignments: DSList(NITEMS, BoxAssignment)
x_y_positions: DSList(NITEMS, BoxAssignment)
nr_used_boxes : DSInt(1,NITEMS)

for i in range(1, NITEMS + 1):
    assignment_i : BoxAssignment = item_box_assignments[i]
    item_i : Item = ITEMS[i]
    assert 0 <= assignment_i.x
    assert 0 <= assignment_i.y
    assert assignment_i.y + item_i.height <= BOX_HEIGHT
    assert assignment_i.x + item_i.width <= BOX_WIDTH
    assert 0 < assignment_i.box_id
    assert assignment_i.box_id <= nr_used_boxes

    for j in range(i + 1, NITEMS + 1):
        assignment_j : BoxAssignment = item_box_assignments[j]
        item_j : Item = ITEMS[j]
        assert assignment_i.box_id != assignment_j.box_id or \\
            assignment_i.x >= assignment_j.x + item_j.width or \\
            assignment_j.x >= assignment_i.x + item_i.width or \\
            assignment_i.y >= assignment_j.y + item_j.height or \\
            assignment_j.y >= assignment_i.y + item_i.height

for i in range(1, NITEMS):
    if item_box_assignments[i].box_id > nr_used_boxes:
        nr_used_boxes = item_box_assignments[i].box_id
minimize(nr_used_boxes)
x_y_positions = item_box_assignments
        """.format(len(items), box_width, box_height, json.dumps(items))

        translator = MiniZincTranslator(code)
        model = translator.unroll_translation()
        #print(model)
        solver = MiniZincSolver()
        solution = solver.solve_with_command_line_minizinc(model, last_in_progress=True)
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
