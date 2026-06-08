"""Convert 2D-bin-packing benchmark JSON instances to OPTDSL format.

Reads ``*.ins2D.json`` files (uniform-box 2D-BPP instances) and produces
equivalent OPTDSL formulations (``*.dsl``) compatible with the LNS / direct-
approach frameworks.

Usage:
    python Tools/convert_2dbp_to_optdsl.py \\
        problem_instances/2dbp/benchmarks/testset_paper_2D-BPP_CLASS \\
        -o problem_instances/2dbp/benchmarks/testset_paper_optdsl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# OPTDSL template (filled by the converter)
# ---------------------------------------------------------------------------
OPTDSL_TEMPLATE = """\
NBOXES : int = {nboxes}
NITEMS : int = {nitems}
MAX_BOX_WIDTH : int = {max_width}
MAX_BOX_HEIGHT : int = {max_height}

BOX_WIDTH_CAPACITIES : DSList(NBOXES, DSInt()) = {box_widths}
BOX_HEIGHT_CAPACITIES : DSList(NBOXES, DSInt()) = {box_heights}

ITEM_WIDTHS : DSList(NITEMS, DSInt()) = {item_widths}
ITEM_HEIGHTS : DSList(NITEMS, DSInt()) = {item_heights}

assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))
x_positions: DSList(NITEMS, DSInt(0, MAX_BOX_WIDTH - 1))
y_positions: DSList(NITEMS, DSInt(0, MAX_BOX_HEIGHT - 1))

def all_assigned(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    assigned: DSList(NITEMS, DSInt())
    for i in range(0, NBOXES):
        for j in range(0, NITEMS):
            if assignments[j] == i:
                assigned[j] = 1
    for k in range(0, NITEMS):
        assert assigned[k] != 0

def not_exceed_2d(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    used: DSList(NBOXES, DSInt(0, 1))
    obj = 0
    for i in range(0, NBOXES):
        used[i] = 0

        for j in range(0, NITEMS):
            if assignments[j] == i:
                used[i] = 1

        obj = obj + used[i]

    return obj


def no_overlap(
    assignments: DSList(NITEMS, DSInt(0, NBOXES - 1)),
    x_positions: DSList(NITEMS, DSInt(0, MAX_BOX_WIDTH - 1)),
    y_positions: DSList(NITEMS, DSInt(0, MAX_BOX_HEIGHT - 1)),
):
    # Item must fit into its selected box dimensions.
    for i in range(0, NITEMS):
        box_i = assignments[i]
        assert x_positions[i] + ITEM_WIDTHS[i] <= BOX_WIDTH_CAPACITIES[box_i]
        assert y_positions[i] + ITEM_HEIGHTS[i] <= BOX_HEIGHT_CAPACITIES[box_i]

    # Any two items in the same box must not overlap.
    for i in range(0, NITEMS):
        for j in range(i + 1, NITEMS):
            if assignments[i] == assignments[j]:
                assert (
                    x_positions[i] + ITEM_WIDTHS[i] <= x_positions[j]
                    or x_positions[j] + ITEM_WIDTHS[j] <= x_positions[i]
                    or y_positions[i] + ITEM_HEIGHTS[i] <= y_positions[j]
                    or y_positions[j] + ITEM_HEIGHTS[j] <= y_positions[i]
                )

all_assigned(assignments)
no_overlap(assignments, x_positions, y_positions)
objective: DSInt(0, NBOXES) = not_exceed_2d(assignments)

minimize(objective)
"""


def read_json_instance(path: Path) -> dict:
    """Read and return the parsed JSON data from an ins2D file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_optdsl(data: dict) -> str:
    """Generate the OPTDSL text from a parsed JSON instance dictionary."""
    box_width = int(data["BOX_WIDTH"])
    box_height = int(data["BOX_HEIGHT"])
    items = data["ITEMS"]
    nitems = len(items)

    # NBOXES = NITEMS (worst-case upper bound, always feasible)
    nboxes = nitems

    item_widths = [int(it["width"]) for it in items]
    item_heights = [int(it["height"]) for it in items]

    # All boxes are identical (uniform box 2D-BPP)
    box_widths = [box_width] * nboxes
    box_heights = [box_height] * nboxes

    return OPTDSL_TEMPLATE.format(
        nboxes=nboxes,
        nitems=nitems,
        max_width=box_width,
        max_height=box_height,
        box_widths=box_widths,
        box_heights=box_heights,
        item_widths=item_widths,
        item_heights=item_heights,
    )


def convert_directory(input_dir: str, output_dir: str) -> None:
    """Convert all .ins2D.json files in input_dir to .dsl files in output_dir."""
    src = Path(input_dir)
    dst = Path(output_dir)
    dst.mkdir(parents=True, exist_ok=True)

    json_files = sorted(src.glob("*.ins2D.json"))
    if not json_files:
        print(f"No *.ins2D.json files found in {src}")
        return

    converted = 0
    for json_path in json_files:
        print(f"Reading {json_path.name} ...", end=" ")
        data = read_json_instance(json_path)
        dsl_text = generate_optdsl(data)

        # Same base name, extension to .dsl
        dsl_name = json_path.stem + ".dsl"
        dsl_path = dst / dsl_name
        dsl_path.write_text(dsl_text, encoding="utf-8")
        converted += 1
        print(f"-> {dsl_path.name}")

    print(f"\nConverted {converted} instances to {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert 2D-BPP JSON benchmark instances to OPTDSL format."
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing *.ins2D.json files.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="Output directory for *.dsl files (default: <input>_optdsl).",
    )
    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = str(Path(args.input_dir).parent / (Path(args.input_dir).name + "_optdsl"))

    convert_directory(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()