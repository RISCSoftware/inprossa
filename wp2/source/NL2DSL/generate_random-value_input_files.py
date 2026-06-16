import json
import random

from input_reader import InputReader

def generate_randomvalue_input_files_for_flex_shapes():
    """
    Generate 2d bin packing input files with random values for LLM-prompting Framework.
    Specifically, to input files for formulation generation with flexible shapes.
    """

    general_item_spec: dict[str, dict[str, list | dict[str, int | str | dict[str, int]]]] = {
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

    nr_items = 10
    for i in range(1, 21):
        width = random.randint(5, 25)
        height = random.randint(5, 20)
        target_path = "problem_descriptions/testset_paper_2D-BPP_CLASS/"
        general_item_spec["objects"]["Item"][0]["maximum"] = width
        general_item_spec["objects"]["Item"][1]["maximum"] = height
        general_item_spec["input_variables"]["BOX_WIDTH"]["value"] = width
        general_item_spec["input_variables"]["BOX_HEIGHT"]["value"] = height
        general_item_spec["input_variables"]["ITEMS"]["type"]["length"] = nr_items
        general_item_spec["input_variables"]["ITEMS"]["value"] = "random"
        items = InputReader.generate_data(general_item_spec)
        with open(target_path + f"test_n{nr_items}_{i}" + ".json", "w") as f:
            json.dump(items, f, indent=4)

def generate_randomvalue_input_files_for_fixed_shapes():
    """
    Generate 2d bin packing input files with random values for LLM-prompting Framework.
    Specifically, to input files for formulation generation with fixed shapes.
    """
    general_item_spec: dict[str, dict[str, list | dict[str, int | str | dict[str, int]]]]  = {
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
    width = random.randint(1, 20)
    height = random.randint(1, 20)
    nr_items = 20
    target_path = "problem_descriptions/testset_paper_2D-BPP_CLASS_fixed_shapes/"
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

def generate_randomvalue_input_files_for_fixed_shapes_woodcutter():
    """
    Generate 2d bin packing input files with random values for LLM-prompting Framework.
    Specifically, to input files for formulation generation with fixed shapes.
    """
    general_item_spec: dict[str, dict[str, list | dict[str, list | int | str | dict[str, int]]]]  = {
        "objects": {},
        "input_variables": {
            "NITEMS": {
                "type": "integer",
                "value": 9
            },
            "NBOXES": {
                "type": "integer",
                "value": 9
            },
            "ITEM_LENGTHS": {
                "type": {
                    "elem_type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "length": 8
                },
                "value": "random"
            },
            "BOX_CAPACITIES": {
                "type": {
                    "elem_type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "length": 8
                },
                "value": "random"
            },
            "MAX_ITEM_LENGTH": {
                "type": "integer",
                "value": 10
            },
        },
        "output_variables": {
            "assignments": {
                "type": {
                    "elem_type": "integer",
                    "minimum": 1,
                    "maximum": 9,
                    "length": 9
                }
            },
            "cut_positions": {
                "type": {
                    "elem_type": "integer",
                    "minimum": 0,
                    "maximum": 9,
                    "length": 9
                }
            },
            "cut_items": {
                "type": {
                    "elem_type": "integer",
                    "minimum": 0,
                    "maximum": 9,
                    "length": 9,
                }
            },
            "total_cost": {
                "type": "integer",
                "minimum": 0
            }
        }
    }
    max_item_length = random.randint(1, 20)
    nr_items = 6
    target_path = "problem_descriptions/testset_algopolish_woodcutter/"
    general_item_spec["input_variables"]["NITEMS"]["value"] = nr_items
    general_item_spec["input_variables"]["NBOXES"]["value"] = nr_items
    general_item_spec["input_variables"]["MAX_ITEM_LENGTH"]["value"] = max_item_length
    general_item_spec["input_variables"]["ITEM_LENGTHS"]["type"]["length"] = nr_items
    general_item_spec["input_variables"]["ITEM_LENGTHS"]["type"]["maximum"] = max_item_length
    general_item_spec["input_variables"]["BOX_CAPACITIES"]["type"]["length"] = nr_items
    general_item_spec["input_variables"]["BOX_CAPACITIES"]["type"]["maximum"] = max_item_length
    general_item_spec["output_variables"]["assignments"]["type"]["maximum"]= nr_items
    general_item_spec["output_variables"]["assignments"]["type"]["length"]= nr_items * 2
    general_item_spec["output_variables"]["cut_positions"]["type"]["maximum"]= max_item_length
    general_item_spec["output_variables"]["cut_positions"]["type"]["length"]= nr_items * 2
    general_item_spec["output_variables"]["cut_items"]["type"]["maximum"]= max_item_length
    general_item_spec["output_variables"]["cut_items"]["type"]["length"]= nr_items * 2

    for i in range(10):
        # super-simple capacities and lengths; tweak as needed
        box_capacities = []
        item_lengths = []
        for _ in range(nr_items):
            box_capacity = random.randint(1, max_item_length)
            box_capacities.append(box_capacity)
            item_lengths.append(random.randint(1, box_capacity))
        general_item_spec["input_variables"]["ITEM_LENGTHS"]["value"] = item_lengths
        general_item_spec["input_variables"]["BOX_CAPACITIES"]["value"] = box_capacities
        with open(target_path + f"test_inst_{i}" + ".json", "w") as f:
            json.dump(general_item_spec, f, indent=4)

# example usage
#if __name__ == "__main__":
    # generate_randomvalue_input_files_for_flex_shapes() # results saved in "problem_descriptions/testset_paper_2D-BPP_flex_shapes/"
    # generate_randomvalue_input_files_for_fixed_shapes() # results saved in "problem_descriptions/testset_paper_2D-BPP_fixed_shapes/"
    # generate_randomvalue_input_files_for_fixed_shapes_woodcutter() # results saved in "problem_descriptions/testset_algopolish_woodcutter/"
