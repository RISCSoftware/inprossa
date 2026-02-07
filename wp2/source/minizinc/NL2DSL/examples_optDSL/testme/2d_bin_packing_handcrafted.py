import json
import os

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver

directory = "../../problem_descriptions/testset_paper_2D-BPP/"
result = {}
for filename in os.listdir(directory):
    if filename.endswith(".json") and "_n30_" in filename: #
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

for i in range(1, NITEMS):
    assert 0 <= assignments_and_positions[i].x
    assert 0 <= assignments_and_positions[i].y
    assert assignments_and_positions[i].y + ITEMS[i].height <= BOX_HEIGHT
    assert assignments_and_positions[i].x + ITEMS[i].width <= BOX_WIDTH
    assert 0 < assignments_and_positions[i].box_id
    assert assignments_and_positions[i].box_id <= nr_boxes

    for j in range(i + 1, NITEMS):
        assert assignments_and_positions[i].box_id != assignments_and_positions[j].box_id or \\
            assignments_and_positions[i].x >= assignments_and_positions[j].x + ITEMS[j].width or \\
            assignments_and_positions[j].x >= assignments_and_positions[i].x + ITEMS[i].width or \\
            assignments_and_positions[i].y >= assignments_and_positions[j].y + ITEMS[j].height or \\
            assignments_and_positions[j].y >= assignments_and_positions[i].y + ITEMS[i].height

for i in range(1, NITEMS):
    if assignments_and_positions[i].box_id > nr_boxes:
        nr_boxes = assignments_and_positions[i].box_id
minimize(nr_boxes)
""".format(len(items), box_width, box_height, json.dumps(items))

        translator = MiniZincTranslator(code)
        model = translator.unroll_translation()
        #print(model)
        solver = MiniZincSolver()
        print(f"{filename}: {solver.solve_with_command_line_minizinc(model, last_in_progress=True)}")
