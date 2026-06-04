import argparse
import ast
import html
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ItemPlacement:
    item_index: int
    width: int
    height: int
    x: int
    y: int
    box_index: int


def _read_text_with_fallback(path: str) -> str:
    """Read text files written by different shells/editors (UTF-8/UTF-16/etc.)."""

    with open(path, "rb") as f:
        raw = f.read()

    # Try common encodings first. PowerShell often emits UTF-16 with BOM.
    tried: list[str] = []
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252"):
        tried.append(enc)
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "fallback-decode",
        raw,
        0,
        1,
        f"Could not decode file with tried encodings: {tried}",
    )


def _extract_braced_object(text: str, start_idx: int) -> str:
    depth = 0
    in_string = False
    quote_char = ""
    escaped = False

    for i in range(start_idx, len(text)):
        ch = text[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote_char:
                in_string = False
            continue

        if ch in ("'", '"'):
            in_string = True
            quote_char = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]

    raise ValueError("Could not find matching closing brace in result text.")


def extract_best_solution(result_text: str) -> Dict:
    key_pos = result_text.find("'best_solution'")
    if key_pos < 0:
        key_pos = result_text.find('"best_solution"')
    if key_pos < 0:
        raise ValueError("Could not find 'best_solution' in result text.")

    brace_start = result_text.find("{", key_pos)
    if brace_start < 0:
        raise ValueError("Could not locate opening brace for best_solution.")

    best_solution_text = _extract_braced_object(result_text, brace_start)

    best_solution_text = _remove_dict_field(best_solution_text, "check")

    try:
        return ast.literal_eval(best_solution_text)
    except Exception as exc:
        raise ValueError("Failed to parse best_solution as Python literal.") from exc


def extract_example_search_solution(result_text: str) -> Dict[str, Any]:
    """Parse tree-search/LNS output block under 'Variable assignment ...'."""

    markers = (
        "Variable assignment (best solution):",
        "Variable assignment (incumbent):",
    )
    marker_pos = -1
    marker = ""
    for candidate in markers:
        marker_pos = result_text.find(candidate)
        if marker_pos >= 0:
            marker = candidate
            break

    if marker_pos < 0:
        raise ValueError("Could not find variable assignment block in result text.")

    lines = result_text[marker_pos + len(marker) :].splitlines()
    data: Dict[str, Any] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if " = " not in line:
            # Stop when we leave the assignment section.
            if data:
                break
            continue

        name, raw_value = line.split(" = ", 1)
        name = name.strip()
        raw_value = raw_value.strip()
        try:
            value = ast.literal_eval(raw_value)
        except (ValueError, SyntaxError):
            value = raw_value
        data[name] = value

    if "assignments" not in data:
        raise ValueError("Example-search assignment block does not contain 'assignments'.")

    return data


def parse_solution_data(result_text: str) -> Dict[str, Any]:
    """Try supported formats in order and return a normalized solution dict."""

    try:
        return extract_best_solution(result_text)
    except ValueError:
        try:
            return extract_example_search_solution(result_text)
        except ValueError as exc:
            raise ValueError(
                "Could not parse solution from result file. "
                "Expected either a solver dict containing 'best_solution' or an output block starting with "
                "'Variable assignment (best solution):'. "
                "If this is LNS output, rerun with '--print-assignment'."
            ) from exc


def parse_warm_start_hints(dsl_text: str) -> Optional[Dict[str, Any]]:
    """Extract warm-start assignment hints from a @warm_start-decorated function in DSL source."""

    try:
        tree = ast.parse(dsl_text)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        for decorator in node.decorator_list:
            is_warm_start = (
                isinstance(decorator, ast.Name)
                and decorator.id == "warm_start"
            ) or (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "warm_start"
            )
            if not is_warm_start:
                continue

            bound_value: Optional[float] = None
            if isinstance(decorator, ast.Call):
                for kw in decorator.keywords:
                    if kw.arg in ("upper_bound", "ub", "lower_bound", "lb"):
                        try:
                            bound_value = float(ast.literal_eval(kw.value))
                        except (ValueError, SyntaxError, TypeError):
                            pass

            for stmt in node.body:
                if not isinstance(stmt, ast.Return) or stmt.value is None:
                    continue
                try:
                    hints = ast.literal_eval(stmt.value)
                except (ValueError, SyntaxError):
                    continue

                if not isinstance(hints, dict):
                    continue

                if "assignments" not in hints:
                    continue

                # Use bound as displayed objective value when available.
                if bound_value is not None and "objective" not in hints:
                    hints = dict(hints)
                    hints["objective"] = bound_value

                return hints

    return None


def _remove_dict_field(dict_text: str, field_name: str) -> str:
    key_token = f"'{field_name}'"
    key_pos = dict_text.find(key_token)
    if key_pos < 0:
        return dict_text

    colon_pos = dict_text.find(":", key_pos)
    if colon_pos < 0:
        return dict_text

    i = colon_pos + 1
    depth_curly = 0
    depth_square = 0
    depth_round = 0
    depth_angle = 0
    in_string = False
    quote_char = ""
    escaped = False

    while i < len(dict_text):
        ch = dict_text[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote_char:
                in_string = False
            i += 1
            continue

        if ch in ("'", '"'):
            in_string = True
            quote_char = ch
            i += 1
            continue

        if ch == "{":
            depth_curly += 1
        elif ch == "}":
            if depth_curly > 0:
                depth_curly -= 1
            elif depth_square == depth_round == depth_angle == 0:
                end = i
                return (dict_text[:key_pos] + dict_text[end:]).replace("{,", "{")
        elif ch == "[":
            depth_square += 1
        elif ch == "]":
            if depth_square > 0:
                depth_square -= 1
        elif ch == "(":
            depth_round += 1
        elif ch == ")":
            if depth_round > 0:
                depth_round -= 1
        elif ch == "<":
            depth_angle += 1
        elif ch == ">":
            if depth_angle > 0:
                depth_angle -= 1
        elif (
            ch == ","
            and depth_curly == 0
            and depth_square == 0
            and depth_round == 0
            and depth_angle == 0
        ):
            end = i + 1
            return dict_text[:key_pos] + dict_text[end:]

        i += 1

    return dict_text


def _parse_dsl_list(name: str, dsl_text: str) -> List[int]:
    pattern = rf"^{name}\s*:\s*DSList\(.*\)\s*=\s*(\[[^\]]*\])"
    match = re.search(pattern, dsl_text, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find list '{name}' in DSL file.")

    try:
        values = ast.literal_eval(match.group(1))
    except Exception as exc:
        raise ValueError(f"Could not parse list '{name}' values from DSL file.") from exc

    if not isinstance(values, list) or not all(isinstance(v, int) for v in values):
        raise ValueError(f"List '{name}' must be a list of integers.")

    return values


def parse_instance_data(dsl_text: str) -> Dict[str, List[int]]:
    return {
        "box_widths": _parse_dsl_list("BOX_WIDTH_CAPACITIES", dsl_text),
        "box_heights": _parse_dsl_list("BOX_HEIGHT_CAPACITIES", dsl_text),
        "item_widths": _parse_dsl_list("ITEM_WIDTHS", dsl_text),
        "item_heights": _parse_dsl_list("ITEM_HEIGHTS", dsl_text),
    }


def _normalize_assignments(assignments_obj) -> List[int]:
    if isinstance(assignments_obj, list) and assignments_obj and isinstance(assignments_obj[0], list):
        row = assignments_obj[0]
    elif isinstance(assignments_obj, list):
        row = assignments_obj
    else:
        raise ValueError("Unsupported assignments format in best_solution.")

    if not all(isinstance(v, int) for v in row):
        raise ValueError("Assignments must contain integer box indices.")

    return row


def _normalize_positions(positions_obj, expected_len: int, field_name: str) -> Optional[List[int]]:
    if positions_obj is None:
        return None

    if isinstance(positions_obj, list) and positions_obj and isinstance(positions_obj[0], list):
        row = positions_obj[0]
    elif isinstance(positions_obj, list):
        row = positions_obj
    else:
        raise ValueError(f"Unsupported {field_name} format in solution.")

    if len(row) != expected_len or not all(isinstance(v, int) for v in row):
        raise ValueError(f"{field_name} must be a list of {expected_len} integers.")

    return row


def build_layout(
    assignments: List[int],
    box_widths: List[int],
    box_heights: List[int],
    item_widths: List[int],
    item_heights: List[int],
) -> Tuple[List[ItemPlacement], List[int]]:
    placements: List[ItemPlacement] = []
    unplaced: List[int] = []

    items_by_box: Dict[int, List[int]] = {b: [] for b in range(len(box_widths))}
    for i, b in enumerate(assignments):
        if b in items_by_box:
            items_by_box[b].append(i)
        else:
            unplaced.append(i)

    for b in range(len(box_widths)):
        max_w = box_widths[b]
        max_h = box_heights[b]

        x = 0
        y = 0
        shelf_h = 0

        for i in items_by_box[b]:
            w = item_widths[i]
            h = item_heights[i]

            if w > max_w or h > max_h:
                unplaced.append(i)
                continue

            if x + w <= max_w and y + h <= max_h:
                placements.append(ItemPlacement(i, w, h, x, y, b))
                x += w
                shelf_h = max(shelf_h, h)
                continue

            y += shelf_h
            x = 0
            shelf_h = 0

            if x + w <= max_w and y + h <= max_h:
                placements.append(ItemPlacement(i, w, h, x, y, b))
                x += w
                shelf_h = max(shelf_h, h)
            else:
                unplaced.append(i)

    return placements, sorted(set(unplaced))


def build_layout_from_positions(
    assignments: List[int],
    x_positions: List[int],
    y_positions: List[int],
    box_widths: List[int],
    box_heights: List[int],
    item_widths: List[int],
    item_heights: List[int],
) -> Tuple[List[ItemPlacement], List[int]]:
    placements: List[ItemPlacement] = []
    unplaced: List[int] = []

    n_items = len(assignments)
    for i in range(n_items):
        box_idx = assignments[i]
        if box_idx < 0 or box_idx >= len(box_widths):
            unplaced.append(i)
            continue

        x = x_positions[i]
        y = y_positions[i]
        w = item_widths[i]
        h = item_heights[i]

        if x < 0 or y < 0:
            unplaced.append(i)
            continue

        if x + w > box_widths[box_idx] or y + h > box_heights[box_idx]:
            unplaced.append(i)
            continue

        placements.append(ItemPlacement(i, w, h, x, y, box_idx))

    # Validate no-overlap for plotted placements.
    by_box: Dict[int, List[ItemPlacement]] = {b: [] for b in range(len(box_widths))}
    for p in placements:
        by_box[p.box_index].append(p)

    to_remove: set[int] = set()
    for box_items in by_box.values():
        for i in range(len(box_items)):
            a = box_items[i]
            for j in range(i + 1, len(box_items)):
                b = box_items[j]
                separated = (
                    a.x + a.width <= b.x
                    or b.x + b.width <= a.x
                    or a.y + a.height <= b.y
                    or b.y + b.height <= a.y
                )
                if not separated:
                    to_remove.add(a.item_index)
                    to_remove.add(b.item_index)

    if to_remove:
        placements = [p for p in placements if p.item_index not in to_remove]
        unplaced.extend(sorted(to_remove))

    return placements, sorted(set(unplaced))


def _item_color(idx: int) -> str:
    palette = [
        "#ef476f",
        "#118ab2",
        "#06d6a0",
        "#ffd166",
        "#f78c6b",
        "#7b2cbf",
        "#90be6d",
        "#577590",
        "#ff006e",
        "#3a86ff",
    ]
    return palette[idx % len(palette)]


def render_html(
    best_solution: Dict[str, Any],
    data: Dict[str, List[int]],
    title: str,
) -> str:
    assignments = _normalize_assignments(best_solution.get("assignments", []))
    box_widths = data["box_widths"]
    box_heights = data["box_heights"]
    item_widths = data["item_widths"]
    item_heights = data["item_heights"]

    if len(assignments) != len(item_widths):
        raise ValueError("Assignments length does not match number of items.")

    x_positions = _normalize_positions(best_solution.get("x_positions"), len(assignments), "x_positions")
    y_positions = _normalize_positions(best_solution.get("y_positions"), len(assignments), "y_positions")

    used_direct_positions = x_positions is not None and y_positions is not None
    if used_direct_positions:
        placements, unplaced = build_layout_from_positions(
            assignments,
            x_positions,
            y_positions,
            box_widths,
            box_heights,
            item_widths,
            item_heights,
        )
    else:
        placements, unplaced = build_layout(assignments, box_widths, box_heights, item_widths, item_heights)

    scale = 18
    box_gap = 20
    box_blocks = []

    for b in range(len(box_widths)):
        w = box_widths[b]
        h = box_heights[b]
        svg_w = w * scale
        svg_h = h * scale

        rects = []
        for p in placements:
            if p.box_index != b:
                continue
            rx = p.x * scale
            ry = p.y * scale
            rw = p.width * scale
            rh = p.height * scale
            label = f"i{p.item_index} ({p.width}x{p.height})"
            rects.append(
                f"<g>"
                f"<rect x='{rx}' y='{ry}' width='{rw}' height='{rh}' fill='{_item_color(p.item_index)}' fill-opacity='0.85' stroke='#111' stroke-width='1'/>"
                f"<text x='{rx + 4}' y='{ry + 16}' font-size='12' fill='#111'>{html.escape(label)}</text>"
                f"</g>"
            )

        assigned_items = [i for i, bx in enumerate(assignments) if bx == b]
        box_blocks.append(
            f"<div class='box-card'>"
            f"<h3>Box {b}</h3>"
            f"<p class='meta'>Capacity: {w} x {h} | Assigned: {assigned_items}</p>"
            f"<svg width='{svg_w + 2}' height='{svg_h + 2}' viewBox='0 0 {svg_w + 2} {svg_h + 2}'>"
            f"<rect x='1' y='1' width='{svg_w}' height='{svg_h}' fill='#f8f9fa' stroke='#222' stroke-width='2'/>"
            f"{''.join(rects)}"
            f"</svg>"
            f"</div>"
        )

    obj_val = best_solution.get("objective", "n/a")
    placement_mode = "direct x/y positions" if used_direct_positions else "fallback shelf layout"

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 20px; background: #fafafa; color: #1f2937; }}
    h1 {{ margin-bottom: 4px; }}
    .subtitle {{ color: #4b5563; margin-top: 0; }}
    .summary {{ margin: 14px 0; padding: 10px 12px; background: #eef2ff; border-left: 4px solid #6366f1; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: {box_gap}px; }}
    .box-card {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
    .box-card h3 {{ margin: 0 0 6px 0; }}
    .meta {{ margin: 0 0 8px 0; color: #374151; font-size: 13px; }}
    .warn {{ margin-top: 14px; padding: 10px 12px; background: #fff7ed; border-left: 4px solid #f97316; }}
    code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class='subtitle'>2D Bin Packing solution visualization</p>
  <div class='summary'>
    Objective (used bins): <strong>{obj_val}</strong><br/>
        Assignments: <code>{html.escape(str(assignments))}</code><br/>
        Placement mode: <strong>{html.escape(placement_mode)}</strong>
  </div>
  <div class='grid'>
    {''.join(box_blocks)}
  </div>
  {"<div class='warn'>Could not place these items with simple shelf layout: " + html.escape(str(unplaced)) + "</div>" if unplaced else ""}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize OptDSL 2DBP solution output as HTML/SVG.")
    parser.add_argument(
        "--result-file",
        default=None,
        help=(
            "Path to text file containing solver output dict. "
            "Optional when --dsl-file contains @warm_start hints."
        ),
    )
    parser.add_argument("--dsl-file", required=True, help="Path to 2DBP OptDSL instance file.")
    parser.add_argument("--output", default="2dbp_solution_viz.html", help="Output HTML path.")
    parser.add_argument("--title", default="2DBP Solution", help="Title shown in HTML.")
    args = parser.parse_args()

    with open(args.dsl_file, "r", encoding="utf-8") as f:
        dsl_text = f.read()

    best_solution = parse_warm_start_hints(dsl_text)
    if best_solution is None:
        if not args.result_file:
            print(
                "Error: no warm-start hints found in DSL and no --result-file was provided."
            )
            raise SystemExit(2)
        result_text = _read_text_with_fallback(args.result_file)
        try:
            best_solution = parse_solution_data(result_text)
        except ValueError as exc:
            print(f"Error: {exc}")
            raise SystemExit(2) from exc

    data = parse_instance_data(dsl_text)
    html_text = render_html(best_solution, data, args.title)

    out_path = os.path.abspath(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    print(f"Wrote visualization to: {out_path}")


if __name__ == "__main__":
    main()
