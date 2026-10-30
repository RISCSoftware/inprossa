"""Generate size-scaled 2D bin-packing DSL instances for the computational study.

Writes OptDSL files in the same format as the existing paper test set under
``problem_instances/2dbp/benchmarks/testset_paper_optdsl`` (identical model
body, only the data header differs), so the same MiniZinc translation and LNS
backend consume them without changes.

The existing set is fixed at NITEMS=20 and boxes 10..300; this generator adds
larger sizes (n=30, 40, 50) to obtain a true *size*-scaled medium set.

Examples:
    python Tools/generate_2dbp_instances.py \
        --items 30 40 50 --box-size 100 --min-item 20 --max-item 55 \
        --outdir problem_instances/2dbp/benchmarks/generated_optdsl
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

_MODEL_HEADER = """# Auto-generated 2D bin-packing instance via {tool}.
# Boxes are identical squares of size {box}x{box}; item sizes are drawn
# uniformly in [{min_item}, {max_item}].  NBOXES == NITEMS (one box slot per
# item, so a solution within one box per item always exists in this encoding).

NBOXES : int = {nboxes}
NITEMS : int = {nitems}
MAX_BOX_WIDTH : int = {box}
MAX_BOX_HEIGHT : int = {box}

BOX_WIDTH_CAPACITIES : DSList(NBOXES, DSInt()) = {boxes_w}
BOX_HEIGHT_CAPACITIES : DSList(NBOXES, DSInt()) = {boxes_h}

ITEM_WIDTHS : DSList(NITEMS, DSInt()) = {item_w}
ITEM_HEIGHTS : DSList(NITEMS, DSInt()) = {item_h}

assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))
x_positions: DSList(NITEMS, DSInt(0, MAX_BOX_WIDTH - 1))
y_positions: DSList(NITEMS, DSInt(0, MAX_BOX_HEIGHT - 1))

def all_assigned(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    assigned: DSList(NITEMS, DSInt()) = [0] * NITEMS
    for i in range(0, NBOXES):
        for j in range(0, NITEMS):
            if assignments[j] == i:
                assigned[j] = 1
    for k in range(0, NITEMS):
        assert assigned[k] != 0

def number_of_boxes(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    used: DSList(NBOXES, DSInt(0, 1)) = [0] * NBOXES
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
objective: DSInt(0, NBOXES) = number_of_boxes(assignments)

minimize(objective)
"""


def _fmt_int_list(values: list[int]) -> str:
    return "[" + ", ".join(str(v) for v in values) + "]"


def generate_instance(
    nitems: int,
    box_size: int,
    min_item: int,
    max_item: int,
    seed: int,
) -> str:
    rng = random.Random(seed)
    item_w = [rng.randint(min_item, max_item) for _ in range(nitems)]
    item_h = [rng.randint(min_item, max_item) for _ in range(nitems)]
    nboxes = nitems  # one slot per item keeps the encoding's feasibility simple

    boxes_w = [box_size] * nboxes
    boxes_h = [box_size] * nboxes

    return _MODEL_HEADER.format(
        tool="Tools/generate_2dbp_instances.py",
        box=box_size,
        min_item=min_item,
        max_item=max_item,
        nboxes=nboxes,
        nitems=nitems,
        boxes_w=_fmt_int_list(boxes_w),
        boxes_h=_fmt_int_list(boxes_h),
        item_w=_fmt_int_list(item_w),
        item_h=_fmt_int_list(item_h),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", nargs="+", type=int, default=[30, 40, 50],
                        help="Number of items (and boxes) per generated instance")
    parser.add_argument("--box-size", type=int, default=100)
    parser.add_argument("--min-item", type=int, default=20)
    parser.add_argument("--max-item", type=int, default=55)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1],
                        help="Random seeds; one instance per seed per size")
    parser.add_argument("--outdir", type=Path,
                        default=Path("problem_instances/2dbp/benchmarks/generated_optdsl"))
    args = parser.parse_args()

    if args.min_item > args.max_item:
        raise SystemExit("--min-item must be <= --max-item")
    if args.min_item < 1 or args.max_item > args.box_size:
        raise SystemExit("Item sizes must lie in [1, box-size].")

    args.outdir.mkdir(parents=True, exist_ok=True)
    written = 0
    for nitems in args.items:
        for seed in args.seeds:
            instance = generate_instance(
                nitems=nitems,
                box_size=args.box_size,
                min_item=args.min_item,
                max_item=args.max_item,
                seed=seed,
            )
            name = f"gen_bpp_n{nitems:03d}_box{args.box_size:03d}_s{seed:02d}.dsl"
            out_path = args.outdir / name
            out_path.write_text(instance, encoding="utf-8")
            written += 1
            print(f"wrote {out_path}")
    print(f"Generated {written} instance(s) in {args.outdir}")


if __name__ == "__main__":
    main()
