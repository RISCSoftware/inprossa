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
            "maximum": 9
          },
          {
            "name": "height",
            "type": "integer",
            "minimum": 1,
            "maximum": 9
          }
        ],
        "X_Y_Position": [
          {
            "name": "x",
            "type": "integer",
            "minimum": 0,
            "maximum": 9
          },
          {
            "name": "y",
            "type": "integer",
            "minimum": 0,
            "maximum": 9
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
      },
      "output_variables": {
        "nr_used_boxes": {
          "type": "integer",
          "minimum": 1,
          "maximum": 9
        },
        "item_box_assignments": {
          "type": {
            "elem_type": "integer",
            "minimum": 1,
            "maximum": 9,
            "length": 9
          }
        },
        "x_y_positions": {
          "type": {
            "elem_type": "X_Y_Position",
            "length": 9
          }
        }
      }
    }

width = 8
height = 15
nr_items = 10
target_path = "problem_descriptions/testset_paper_2D-BPP/"
general_item_spec["objects"]["Item"][0]["maximum"] = width
general_item_spec["objects"]["Item"][1]["maximum"] = height
general_item_spec["objects"]["X_Y_Position"][0]["maximum"] = width
general_item_spec["objects"]["X_Y_Position"][1]["maximum"] = height
general_item_spec["input_variables"]["BOX_WIDTH"]["value"] = width
general_item_spec["input_variables"]["BOX_HEIGHT"]["value"] = height
general_item_spec["input_variables"]["ITEMS"]["type"]["length"] = nr_items
general_item_spec["output_variables"]["nr_used_boxes"]["maximum"] = nr_items
general_item_spec["output_variables"]["item_box_assignments"]["type"]["maximum"]= nr_items
general_item_spec["output_variables"]["item_box_assignments"]["type"]["length"] = nr_items
general_item_spec["output_variables"]["x_y_positions"]["type"]["length"] = nr_items

for i in range(6,11):
    general_item_spec["input_variables"]["ITEMS"]["value"] = "random"
    items = InputReader.generate_data(general_item_spec)
    general_item_spec["input_variables"]["ITEMS"]["value"] = items["ITEMS"]
    with open(target_path + f"test_inst_{i}" + ".json", "w") as f:
        json.dump(general_item_spec, f, indent=4)
