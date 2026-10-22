#!/usr/bin/env python
"""Convert standard 2D Bin Packing benchmark files (.txt) to OptDSL format (.dsl).

Supports standard bin packing format (boxes, items with dimensions).

Usage:
  # Batch conversion
  python convert_2dbp.py --input-dir <dir> --output-dir <dir>
  
  # Single file conversion
  python convert_2dbp.py --input-file instance.txt --output-file instance.dsl

Input file format (examples from Hopper & Turton, etc.):
  # First line: n_boxes width height
  # Following lines: item_width item_height

Example:
  10 100 100
  50 50
  40 30
  ...

Output:
  Converts to OptDSL format with variables for item placement and objective to minimize boxes used.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_2dbp_file(filepath: str) -> dict:
    """Parse 2D bin packing file.
    
    Format:
      Line 1: n_boxes box_width box_height
      Lines 2+: item_width item_height
    """
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    result = {
        "n_boxes": 0,
        "box_width": 0,
        "box_height": 0,
        "items": [],
    }

    if not lines:
        raise ValueError("Empty file")

    # Parse header
    parts = lines[0].split()
    if len(parts) < 3:
        raise ValueError(f"First line must contain: n_boxes box_width box_height, got: {lines[0]}")

    result["n_boxes"] = int(parts[0])
    result["box_width"] = int(parts[1])
    result["box_height"] = int(parts[2])

    # Parse items
    for line in lines[1:]:
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                w = int(parts[0])
                h = int(parts[1])
                result["items"].append((w, h))
            except ValueError:
                pass

    if not result["items"]:
        raise ValueError("No items found in file")

    return result


def generate_optdsl(
    n_boxes: int,
    box_width: int,
    box_height: int,
    items: list[tuple[int, int]],
    name: str = "2dbp",
) -> str:
    """Generate OptDSL content for 2D bin packing instance.
    
    Args:
        n_boxes: Number of available boxes
        box_width: Width of each box
        box_height: Height of each box
        items: List of (width, height) tuples
        name: Instance name
    
    Returns:
        OptDSL content as string
    """
    n_items = len(items)
    box_area = box_width * box_height
    total_item_area = sum(w * h for w, h in items)

    items_w = [w for w, h in items]
    items_h = [h for w, h in items]

    problem_name = name.replace(" ", "_").replace("/", "_")

    template = f"""# 2D Bin Packing instance: {problem_name}
# Minimize the number of bins used to pack all items.

N_BOXES : int = {n_boxes}
BOX_WIDTH : int = {box_width}
BOX_HEIGHT : int = {box_height}
BOX_AREA : int = BOX_WIDTH * BOX_HEIGHT

N_ITEMS : int = {n_items}
TOTAL_AREA : int = {total_item_area}

ITEM_WIDTHS : DSList(N_ITEMS, DSInt()) = {items_w}
ITEM_HEIGHTS : DSList(N_ITEMS, DSInt()) = {items_h}

# Decision variables:
# x[i], y[i] = position of item i in its assigned box (0 <= x <= BOX_WIDTH - ITEM_WIDTHS[i])
# box[i] = which box item i is assigned to (0 <= box[i] < N_BOXES)
# box_used[b] = 1 if box b is used, 0 otherwise

x: DSList(N_ITEMS, DSInt(0, BOX_WIDTH))
y: DSList(N_ITEMS, DSInt(0, BOX_HEIGHT))
box: DSList(N_ITEMS, DSInt(0, N_BOXES - 1))
box_used: DSList(N_BOXES, DSInt(0, 1))


def item_bounds(x: DSList(N_ITEMS, DSInt(0, BOX_WIDTH)), y: DSList(N_ITEMS, DSInt(0, BOX_HEIGHT))):
    # Each item must fit within its box
    for i in range(N_ITEMS):
        assert x[i] + ITEM_WIDTHS[i] <= BOX_WIDTH
        assert y[i] + ITEM_HEIGHTS[i] <= BOX_HEIGHT


def no_overlaps(
    x: DSList(N_ITEMS, DSInt(0, BOX_WIDTH)),
    y: DSList(N_ITEMS, DSInt(0, BOX_HEIGHT)),
    box: DSList(N_ITEMS, DSInt(0, N_BOXES - 1))
):
    # Items in the same box must not overlap
    for i in range(N_ITEMS):
        for j in range(i + 1, N_ITEMS):
            if box[i] == box[j]:
                # i and j are in same box; they must not overlap
                no_overlap = 0
                # Check all 4 possible non-overlap conditions
                no_overlap = no_overlap + (x[i] + ITEM_WIDTHS[i] <= x[j])  # i left of j
                no_overlap = no_overlap + (x[j] + ITEM_WIDTHS[j] <= x[i])  # j left of i
                no_overlap = no_overlap + (y[i] + ITEM_HEIGHTS[i] <= y[j]) # i below j
                no_overlap = no_overlap + (y[j] + ITEM_HEIGHTS[j] <= y[i]) # j below i
                assert no_overlap >= 1


def track_box_usage(box: DSList(N_ITEMS, DSInt(0, N_BOXES - 1)), box_used: DSList(N_BOXES, DSInt(0, 1))):
    # box_used[b] = 1 iff at least one item is assigned to box b
    for b in range(N_BOXES):
        used = 0
        for i in range(N_ITEMS):
            if box[i] == b:
                used = 1
        assert box_used[b] == used


def boxes_needed(box_used: DSList(N_BOXES, DSInt(0, 1))):
    # Return number of boxes used
    count = 0
    for b in range(N_BOXES):
        count = count + box_used[b]
    return count


item_bounds(x, y)
no_overlaps(x, y, box)
track_box_usage(box, box_used)

objective: DSInt(0, N_BOXES) = boxes_needed(box_used)

minimize(objective)
"""

    return template


def convert_single(input_file: str, output_file: str) -> bool:
    """Convert a single 2DBP file.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        data = parse_2dbp_file(input_file)
        optdsl = generate_optdsl(
            n_boxes=data["n_boxes"],
            box_width=data["box_width"],
            box_height=data["box_height"],
            items=data["items"],
            name=Path(input_file).stem,
        )
        Path(output_file).write_text(optdsl, encoding="utf-8")
        n_items = len(data["items"])
        total_area = sum(w * h for w, h in data["items"])
        box_area = data["box_width"] * data["box_height"]
        area_ratio = total_area / (data["n_boxes"] * box_area)
        print(f"  ✓ {Path(input_file).name} → {Path(output_file).name}")
        print(f"    Items: {n_items}, Boxes: {data['n_boxes']}, Box size: {data['box_width']}×{data['box_height']}, Area ratio: {area_ratio:.2%}")
        return True
    except Exception as e:
        print(f"  ✗ {Path(input_file).name}: {e}")
        return False


def convert_batch(input_dir: str, output_dir: str) -> int:
    """Convert all .txt files in input_dir to output_dir.
    
    Returns:
        Number of files successfully converted
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    input_files = sorted(input_path.glob("*.txt"))
    if not input_files:
        print(f"No .txt files found in {input_dir}")
        return 0

    print(f"Converting {len(input_files)} 2D bin packing files...")
    success_count = 0

    for input_file in input_files:
        output_file = output_path / f"{input_file.stem}.dsl"
        if convert_single(str(input_file), str(output_file)):
            success_count += 1

    print(f"\nConversion complete: {success_count}/{len(input_files)} files converted to {output_dir}")
    return success_count


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert 2D bin packing benchmark files (.txt) to OptDSL format (.dsl)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--input-dir",
        help="Input directory containing .txt files (batch mode)",
    )
    mode_group.add_argument(
        "--input-file",
        help="Single input file (.txt) to convert",
    )
    
    parser.add_argument(
        "--output-dir",
        help="Output directory for batch conversion (required with --input-dir)",
    )
    parser.add_argument(
        "--output-file",
        help="Output file for single conversion (required with --input-file)",
    )
    
    args = parser.parse_args()
    
    # Batch mode
    if args.input_dir:
        if not args.output_dir:
            parser.error("--output-dir required with --input-dir")
        convert_batch(args.input_dir, args.output_dir)
    
    # Single file mode
    elif args.input_file:
        if not args.output_file:
            parser.error("--output-file required with --input-file")
        if not Path(args.input_file).exists():
            parser.error(f"Input file not found: {args.input_file}")
        success = convert_single(args.input_file, args.output_file)
        exit(0 if success else 1)


if __name__ == "__main__":
    main()
