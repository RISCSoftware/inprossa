import argparse
import ast
import html
import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class RouteInfo:
    vehicle: int
    used: int
    route: list[int]
    load: int
    distance: int
    notes: list[str]


def _read_text_with_fallback(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()

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


def _extract_best_solution_dict(result_text: str) -> dict[str, Any]:
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
        parsed = ast.literal_eval(best_solution_text)
    except (ValueError, SyntaxError) as exc:
        raise ValueError("Failed to parse best_solution as Python literal.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Parsed best_solution is not a dict.")
    return parsed


def _extract_assignment_block(result_text: str) -> dict[str, Any]:
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
    data: dict[str, Any] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if " = " not in line:
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

    if "arcs" not in data:
        raise ValueError("Variable assignment block does not contain 'arcs'.")
    return data


def parse_warm_start_hints(dsl_text: str) -> dict[str, Any] | None:
    """Extract arcs/vehicle_used and objective bound from a @warm_start decorated function in DSL source."""
    try:
        tree = ast.parse(dsl_text)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            is_ws = (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "warm_start"
            ) or (
                isinstance(decorator, ast.Name)
                and decorator.id == "warm_start"
            )
            if not is_ws:
                continue

            # Extract bound from decorator keyword args
            bound_value: float | None = None
            bound_key: str | None = None
            if isinstance(decorator, ast.Call):
                for kw in decorator.keywords:
                    if kw.arg in ("upper_bound", "ub", "lower_bound", "lb"):
                        try:
                            bound_value = float(ast.literal_eval(kw.value))
                            bound_key = kw.arg
                        except (ValueError, TypeError):
                            pass

            # Extract return dict from function body
            for stmt in node.body:
                if isinstance(stmt, ast.Return) and stmt.value is not None:
                    try:
                        hints = ast.literal_eval(stmt.value)
                    except (ValueError, SyntaxError):
                        continue
                    if not isinstance(hints, dict):
                        continue
                    result: dict[str, Any] = dict(hints)
                    if bound_value is not None:
                        result["objective"] = bound_value
                        result["_bound_key"] = bound_key
                    return result

    return None


def parse_solution_data(result_text: str) -> dict[str, Any]:
    try:
        return _extract_best_solution_dict(result_text)
    except ValueError:
        try:
            return _extract_assignment_block(result_text)
        except ValueError as exc:
            raise ValueError(
                "Could not parse solution from result file. Expected either a solver dict containing "
                "'best_solution' or an assignment block starting with 'Variable assignment (best solution):'. "
                "If this is LNS output, rerun with '--print-assignment'."
            ) from exc


def _parse_int_constant(name: str, dsl_text: str) -> int:
    match = re.search(rf"^\s*{name}\s*:\s*int\s*=\s*(-?\d+)\s*$", dsl_text, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find int constant '{name}' in DSL file.")
    return int(match.group(1))


def _extract_list_literal(name: str, dsl_text: str) -> str:
    anchor_re = re.compile(rf"^\s*{name}\s*:\s*DSList\(.*?\)\s*=\s*", flags=re.MULTILINE)
    m = anchor_re.search(dsl_text)
    if not m:
        raise ValueError(f"Could not find list constant '{name}' in DSL file.")

    i = m.end()
    while i < len(dsl_text) and dsl_text[i].isspace():
        i += 1
    if i >= len(dsl_text) or dsl_text[i] != "[":
        raise ValueError(f"Could not find list literal start for '{name}'.")

    depth = 0
    in_string = False
    quote = ""
    escaped = False

    for j in range(i, len(dsl_text)):
        ch = dsl_text[j]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                in_string = False
            continue

        if ch in ("'", '"'):
            in_string = True
            quote = ch
            continue

        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return dsl_text[i : j + 1]

    raise ValueError(f"Could not find matching closing bracket for '{name}'.")


def _parse_int_list(name: str, dsl_text: str) -> list[int]:
    literal = _extract_list_literal(name, dsl_text)
    try:
        values = ast.literal_eval(literal)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"Could not parse list '{name}'.") from exc

    if not isinstance(values, list) or not all(isinstance(v, int) for v in values):
        raise ValueError(f"List '{name}' must be a list of integers.")

    return values


def _parse_nested_int_list(name: str, dsl_text: str) -> list[list[int]]:
    literal = _extract_list_literal(name, dsl_text)
    try:
        values = ast.literal_eval(literal)
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"Could not parse nested list '{name}'.") from exc

    if not isinstance(values, list):
        raise ValueError(f"Nested list '{name}' is not a list.")

    for row in values:
        if not isinstance(row, list) or not all(isinstance(v, int) for v in row):
            raise ValueError(f"Nested list '{name}' must contain integer rows.")

    return values


def parse_instance_data(dsl_text: str) -> dict[str, Any]:
    return {
        "n_cities": _parse_int_constant("N_CITIES", dsl_text),
        "n_vehicles": _parse_int_constant("N_VEHICLES", dsl_text),
        "depot": _parse_int_constant("DEPOT", dsl_text),
        "demands": _parse_int_list("DEMANDS", dsl_text),
        "x_coords": _parse_int_list("X_COORDS", dsl_text),
        "y_coords": _parse_int_list("Y_COORDS", dsl_text),
        "distance_matrix": _parse_nested_int_list("DISTANCE_MATRIX", dsl_text),
    }


def _normalize_1d_int_list(value: Any, field_name: str) -> list[int]:
    if isinstance(value, list) and value and isinstance(value[0], list):
        row = value[0]
    elif isinstance(value, list):
        row = value
    else:
        raise ValueError(f"Unsupported {field_name} format in solution.")

    if not all(isinstance(v, int) for v in row):
        raise ValueError(f"{field_name} must contain only integers.")

    return row


def _decode_arcs(arcs_flat: list[int], n_vehicles: int, n_cities: int) -> list[list[tuple[int, int]]]:
    expected = n_vehicles * n_cities * n_cities
    if len(arcs_flat) != expected:
        raise ValueError(f"arcs length {len(arcs_flat)} does not match expected {expected}.")

    edges_by_vehicle: list[list[tuple[int, int]]] = [[] for _ in range(n_vehicles)]
    for v in range(n_vehicles):
        base = v * n_cities * n_cities
        for i in range(n_cities):
            row_base = base + i * n_cities
            for j in range(n_cities):
                val = arcs_flat[row_base + j]
                if val == 1:
                    edges_by_vehicle[v].append((i, j))
    return edges_by_vehicle


def _extract_routes(
    edges_by_vehicle: list[list[tuple[int, int]]],
    vehicle_used: list[int],
    depot: int,
    demands: list[int],
    distance: list[list[int]],
) -> list[RouteInfo]:
    routes: list[RouteInfo] = []

    for v, edges in enumerate(edges_by_vehicle):
        notes: list[str] = []
        outgoing: dict[int, list[int]] = {}
        for i, j in edges:
            outgoing.setdefault(i, []).append(j)

        route: list[int] = [depot]
        seen_edges: set[tuple[int, int]] = set()
        curr = depot

        while True:
            nxts = outgoing.get(curr, [])
            if not nxts:
                if curr != depot and vehicle_used[v] == 1:
                    notes.append("route does not return to depot")
                break
            if len(nxts) > 1:
                notes.append(f"multiple outgoing arcs from node {curr}")

            nxt = nxts[0]
            edge = (curr, nxt)
            if edge in seen_edges:
                notes.append("cycle detected while tracing route")
                break

            seen_edges.add(edge)
            route.append(nxt)
            curr = nxt
            if curr == depot:
                break

            if len(route) > 2 * max(1, len(demands)):
                notes.append("route tracing aborted due to excessive length")
                break

        customers = [c for c in route if c != depot]
        load = sum(demands[c] for c in customers if 0 <= c < len(demands))
        dist = 0
        for i in range(len(route) - 1):
            a, b = route[i], route[i + 1]
            if 0 <= a < len(distance) and 0 <= b < len(distance[a]):
                dist += int(distance[a][b])

        if vehicle_used[v] == 0 and edges:
            notes.append("vehicle has arcs but vehicle_used=0")
        if vehicle_used[v] == 1 and not edges:
            notes.append("vehicle_used=1 but no arcs selected")

        routes.append(RouteInfo(vehicle=v, used=vehicle_used[v], route=route, load=load, distance=dist, notes=notes))

    return routes


def _validate_global(
    edges_by_vehicle: list[list[tuple[int, int]]],
    n_cities: int,
    depot: int,
) -> tuple[list[str], list[int]]:
    incoming = [0] * n_cities
    outgoing = [0] * n_cities

    for edges in edges_by_vehicle:
        for i, j in edges:
            if 0 <= i < n_cities and 0 <= j < n_cities:
                outgoing[i] += 1
                incoming[j] += 1

    notes: list[str] = []
    unserved: list[int] = []
    for c in range(n_cities):
        if c == depot:
            continue
        if incoming[c] != 1 or outgoing[c] != 1:
            unserved.append(c)

    if unserved:
        notes.append(f"Customers violating visit/flow requirements: {unserved}")

    return notes, unserved


def _palette(idx: int) -> str:
    colors = [
        "#2563eb",
        "#dc2626",
        "#16a34a",
        "#ca8a04",
        "#7c3aed",
        "#0891b2",
        "#ea580c",
        "#be123c",
    ]
    return colors[idx % len(colors)]


def render_html(solution: dict[str, Any], instance: dict[str, Any], title: str) -> str:
    n_cities = int(instance["n_cities"])
    n_vehicles = int(instance["n_vehicles"])
    depot = int(instance["depot"])
    demands = instance["demands"]
    x_coords = instance["x_coords"]
    y_coords = instance["y_coords"]
    distance = instance["distance_matrix"]

    arcs = _normalize_1d_int_list(solution.get("arcs", []), "arcs")
    raw_vehicle_used = solution.get("vehicle_used", [0] * n_vehicles)
    vehicle_used = _normalize_1d_int_list(raw_vehicle_used, "vehicle_used")
    objective = solution.get("objective", "n/a")

    if len(vehicle_used) != n_vehicles:
        raise ValueError(f"vehicle_used length {len(vehicle_used)} does not match N_VEHICLES {n_vehicles}.")

    edges_by_vehicle = _decode_arcs(arcs, n_vehicles, n_cities)
    routes = _extract_routes(edges_by_vehicle, vehicle_used, depot, demands, distance)
    global_notes, unserved = _validate_global(edges_by_vehicle, n_cities, depot)

    width = 900
    height = 620
    pad = 50
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    dx = max(1, x_max - x_min)
    dy = max(1, y_max - y_min)

    def sx(x: int) -> float:
        return pad + (x - x_min) * (width - 2 * pad) / dx

    def sy(y: int) -> float:
        return height - pad - (y - y_min) * (height - 2 * pad) / dy

    edge_svg: list[str] = []
    for r in routes:
        color = _palette(r.vehicle)
        for i, j in edges_by_vehicle[r.vehicle]:
            if 0 <= i < n_cities and 0 <= j < n_cities:
                edge_svg.append(
                    f"<line x1='{sx(x_coords[i]):.2f}' y1='{sy(y_coords[i]):.2f}' "
                    f"x2='{sx(x_coords[j]):.2f}' y2='{sy(y_coords[j]):.2f}' "
                    f"stroke='{color}' stroke-width='2.5' marker-end='url(#arrow-{r.vehicle})' opacity='0.9'/>"
                )

    node_svg: list[str] = []
    for c in range(n_cities):
        fill = "#111827" if c == depot else "#f9fafb"
        stroke = "#111827"
        text_color = "#f9fafb" if c == depot else "#111827"
        radius = 11 if c == depot else 9
        node_svg.append(
            f"<g>"
            f"<circle cx='{sx(x_coords[c]):.2f}' cy='{sy(y_coords[c]):.2f}' r='{radius}' fill='{fill}' stroke='{stroke}' stroke-width='2'/>"
            f"<text x='{sx(x_coords[c]):.2f}' y='{sy(y_coords[c]) + 4:.2f}' text-anchor='middle' font-size='10' fill='{text_color}'>{c}</text>"
            f"</g>"
        )

    route_rows: list[str] = []
    for r in routes:
        note_text = "; ".join(r.notes) if r.notes else "ok"
        route_text = " -> ".join(str(x) for x in r.route) if r.route else "<none>"
        route_rows.append(
            f"<tr>"
            f"<td><span class='swatch' style='background:{_palette(r.vehicle)}'></span>v{r.vehicle}</td>"
            f"<td>{r.used}</td>"
            f"<td>{html.escape(route_text)}</td>"
            f"<td>{r.load}</td>"
            f"<td>{r.distance}</td>"
            f"<td>{html.escape(note_text)}</td>"
            f"</tr>"
        )

    marker_defs = "".join(
        f"<marker id='arrow-{v}' markerWidth='8' markerHeight='8' refX='7' refY='3' orient='auto'>"
        f"<path d='M0,0 L8,3 L0,6 z' fill='{_palette(v)}'/></marker>"
        for v in range(n_vehicles)
    )

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 20px; background: #f8fafc; color: #111827; }}
    h1 {{ margin-bottom: 4px; }}
    .subtitle {{ color: #4b5563; margin-top: 0; }}
    .summary {{ margin: 12px 0 16px 0; padding: 10px 12px; background: #e0f2fe; border-left: 4px solid #0284c7; }}
    .warn {{ margin-top: 12px; padding: 10px 12px; background: #fff7ed; border-left: 4px solid #f97316; }}
    .layout {{ display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px; align-items: start; }}
    .panel {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }}
    svg {{ width: 100%; height: auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 6px; text-align: left; vertical-align: top; }}
    th {{ background: #f9fafb; }}
    .swatch {{ display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }}
    code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class='subtitle'>CVRP route visualization from OptDSL solver/LNS output</p>
  <div class='summary'>
    Objective: <strong>{html.escape(str(objective))}</strong><br/>
    Cities: <strong>{n_cities}</strong>, Vehicles: <strong>{n_vehicles}</strong>, Depot: <strong>{depot}</strong><br/>
    Unserved/invalid customers: <code>{html.escape(str(unserved))}</code>
  </div>
  <div class='layout'>
    <div class='panel'>
      <svg viewBox='0 0 {width} {height}'>
        <defs>{marker_defs}</defs>
        {''.join(edge_svg)}
        {''.join(node_svg)}
      </svg>
    </div>
    <div class='panel'>
      <table>
        <thead>
          <tr><th>Vehicle</th><th>Used</th><th>Route</th><th>Load</th><th>Dist</th><th>Notes</th></tr>
        </thead>
        <tbody>
          {''.join(route_rows)}
        </tbody>
      </table>
    </div>
  </div>
  {"<div class='warn'>" + html.escape("; ".join(global_notes)) + "</div>" if global_notes else ""}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize CVRP OptDSL solution output as HTML/SVG.")
    parser.add_argument("--result-file", default=None, help="Path to text file containing solver output. If omitted, warm start hints in --dsl-file are used.")
    parser.add_argument("--dsl-file", required=True, help="Path to CVRP OptDSL instance file.")
    parser.add_argument("--output", default="cvrp_solution_viz.html", help="Output HTML path.")
    parser.add_argument("--title", default="CVRP Solution", help="Title shown in HTML.")
    args = parser.parse_args()

    with open(args.dsl_file, "r", encoding="utf-8") as f:
        dsl_text = f.read()

    solution: dict[str, Any] | None = None

    if args.result_file:
        result_text = _read_text_with_fallback(args.result_file)
        try:
            solution = parse_solution_data(result_text)
        except ValueError as exc:
            print(f"Error parsing result file: {exc}")
            raise SystemExit(2) from exc
    else:
        solution = parse_warm_start_hints(dsl_text)
        if solution is None:
            print(
                "Error: no --result-file given and no @warm_start decorator found in the DSL file.\n"
                "Either provide --result-file or use an LNS snapshot DSL that contains a @warm_start hint."
            )
            raise SystemExit(2)
        bound_key = solution.pop("_bound_key", None)
        if args.title == "CVRP Solution" and bound_key:
            args.title = f"CVRP LNS Warm Start ({bound_key}={solution.get('objective', 'n/a')})"

    instance = parse_instance_data(dsl_text)
    html_text = render_html(solution, instance, args.title)

    out_path = os.path.abspath(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    print(f"Wrote visualization to: {out_path}")


if __name__ == "__main__":
    main()
