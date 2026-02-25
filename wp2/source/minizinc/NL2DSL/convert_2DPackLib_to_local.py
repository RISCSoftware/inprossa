import json
import os
import random

def convert_2DPackLib_to_local_flex_objects():
    general_item_spec = {
        "BOX_HEIGHT": 9,
        "BOX_WIDTH": 9,
        "ITEMS": []
    }

    directory = "problem_descriptions/2DPackLib/CLASS/CLASS"
    files = [filename for filename in os.listdir(directory) if "01_020_" in filename or "02_020_" in filename or "03_020_" in filename or "04_020_" in filename or "05_020_" in filename or "06_020_" in filename or "07_020_" in filename or "08_020_" in filename]
    files = random.sample(files, 20)
    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()

        nr_items = int(lines[0])

        second_line_parts = lines[1].split()
        bin_width = int(second_line_parts[0])
        bin_height = int(second_line_parts[1])

        # extract 2nd and 3rd numbers from remaining lines
        items = []
        for line in lines[2:]:
            parts = line.split()
            second_num = int(parts[1])
            third_num = int(parts[2])
            items.append({"width": second_num, "height": third_num})

        target_path = "problem_descriptions/testset_paper_2D-BPP_CLASS/"
        general_item_spec["BOX_WIDTH"] = bin_width
        general_item_spec["BOX_HEIGHT"] = bin_height
        general_item_spec["ITEMS"] = items
        with open(target_path + f"2d_bpp_inst_{filename}" + ".json", "w") as f:
            json.dump(general_item_spec, f, indent=4)


def convert_2DPackLib_to_local_fixed_objects():
    general_item_spec = {
        "objects": {
            "Item": [
                {
                    "name": "width",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1
                },
                {
                    "name": "height",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1
                }
            ],
            "X_Y_Position": [
                {
                    "name": "x",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 0
                },
                {
                    "name": "y",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 0
                }
            ]
        },
        "input_variables": {
            "BOX_HEIGHT": {
                "type": "integer",
                "value": 0
            },
            "BOX_WIDTH": {
                "type": "integer",
                "value": 0
            },
            "ITEMS": {
                "type": {
                    "elem_type": "Item",
                    "length": 0
                },
                "value": []
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

    directory = "problem_descriptions/2DPackLib/CLASS/CLASS"
    files = [filename for filename in os.listdir(directory) if
             "01_020_" in filename or "02_020_" in filename or "03_020_" in filename or "04_020_" in filename or "05_020_" in filename or "06_020_" in filename or "07_020_" in filename or "08_020_" in filename or "09_020_" in filename or "10_020_" in filename]
    files = random.sample(files, 20)
    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()

        nr_items = int(lines[0])

        second_line_parts = lines[1].split()
        width = int(second_line_parts[0])
        height = int(second_line_parts[1])

        # extract 2nd and 3rd numbers from remaining lines
        items = []
        for line in lines[2:]:
            parts = line.split()
            second_num = int(parts[1])
            third_num = int(parts[2])
            items.append({"width": second_num, "height": third_num})

        target_path = "problem_descriptions/testset_fixed_objects_2D-BPP_CLASS/"
        general_item_spec["objects"]["Item"][0]["maximum"] = width
        general_item_spec["objects"]["Item"][1]["maximum"] = height
        general_item_spec["objects"]["X_Y_Position"][0]["maximum"] = width
        general_item_spec["objects"]["X_Y_Position"][1]["maximum"] = height
        general_item_spec["input_variables"]["BOX_WIDTH"]["value"] = width
        general_item_spec["input_variables"]["BOX_HEIGHT"]["value"] = height
        general_item_spec["input_variables"]["ITEMS"]["type"]["length"] = nr_items
        general_item_spec["input_variables"]["ITEMS"]["value"] = items
        general_item_spec["output_variables"]["nr_used_boxes"]["maximum"] = nr_items
        general_item_spec["output_variables"]["item_box_assignments"]["type"]["maximum"] = nr_items
        general_item_spec["output_variables"]["item_box_assignments"]["type"]["length"] = nr_items
        general_item_spec["output_variables"]["x_y_positions"]["type"]["length"] = nr_items
        with open(target_path + f"2d_bpp_inst_{filename}" + ".json", "w") as f:
            json.dump(general_item_spec, f, indent=4)

if __name__ == "__main__":
    convert_2DPackLib_to_local_fixed_objects()
