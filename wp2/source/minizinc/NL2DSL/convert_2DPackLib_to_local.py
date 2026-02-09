import json

general_item_spec = {
    "BOX_HEIGHT": 9,
    "BOX_WIDTH": 9,
    "ITEMS": []
}

with open("problem_descriptions/2DPackLib/BENG/BENG/BENG05.ins2D", "r") as f:
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

target_path = "problem_descriptions/testset_paper_2D-BPP/"
general_item_spec["BOX_WIDTH"] = bin_width
general_item_spec["BOX_HEIGHT"] = bin_height
general_item_spec["ITEMS"] = items
with open(target_path + f"2d_bpp_inst_n{nr_items}" + ".json", "w") as f:
    json.dump(general_item_spec, f, indent=4)
