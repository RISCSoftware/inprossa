import json

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from solver import MiniZincSolver

box_width = 12
box_height = 5
items = [
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
      ]

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
    item_i : Item = ITEMS[i]
    ass_i : BoxAssignment = assignments_and_positions[i]
    assert 0 <= ass_i.x and ass_i.x + item_i.width <= BOX_WIDTH
    assert 0 <= ass_i.y and ass_i.y + item_i.height <= BOX_HEIGHT
    assert 0 < ass_i.box_id and ass_i.box_id < NITEMS
    for j in range(i + 1, NITEMS):
        item_j : Item = ITEMS[j]
        ass_j : BoxAssignment = assignments_and_positions[j]
        assert ass_i.box_id != ass_j.box_id or \\
            ass_i.x >= ass_j.x + item_j.width or \\
            ass_j.x >= ass_i.x + item_i.width or \\
            ass_i.y >= ass_j.y + item_j.height or \\
            ass_j.y >= ass_i.y + item_i.height

max: int = 0
for i in range(1, NITEMS):
    if assignments_and_positions[i].box_id > max:
        max = assignments_and_positions[i].box_id
objective = max
""".format(len(items), box_width, box_height, json.dumps(items))

translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")
solver = MiniZincSolver()
print(solver.solve_with_command_line_minizinc(model))
