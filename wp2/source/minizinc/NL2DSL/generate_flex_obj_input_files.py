import copy
import json

from input_reader import InputReader
general_item_spec = {
      "objects": {
        "Item": [
          {
            "name": "width",
            "type": "integer",
            "minimum": 1,
            "maximum": 6
          },
          {
            "name": "height",
            "type": "integer",
            "minimum": 1,
            "maximum": 7
          }
        ]
      },
      "input_variables": {
        "BOX_HEIGHT": {
          "type": "integer",
          "value": 9
        },
        "BOX_WIDTH": {
          "type": "integer",
          "value": 9
        },
        "ITEMS": {
          "type": {
            "elem_type": "Item",
            "length": 8
          },
          "value": "random"
        }
      }
    }

width = 16
height = 11
nr_items = 30
target_path = "problem_descriptions/testset_paper_2D-BPP/"
general_item_spec["objects"]["Item"][0]["maximum"] = width
general_item_spec["objects"]["Item"][1]["maximum"] = height
general_item_spec["input_variables"]["BOX_WIDTH"]["value"] = width
general_item_spec["input_variables"]["BOX_HEIGHT"]["value"] = height
general_item_spec["input_variables"]["ITEMS"]["type"]["length"] = nr_items

for i in range(1,100):
    general_item_spec["input_variables"]["ITEMS"]["value"] = "random"
    items = InputReader.generate_data(general_item_spec)
    with open(target_path + f"test_n{nr_items}_{i}" + ".json", "w") as f:
        json.dump(items, f, indent=4)
