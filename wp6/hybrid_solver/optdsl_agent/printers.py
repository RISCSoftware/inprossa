"""Problem-specific solution printers.

A raw assignment is a dict of flat lists. For CVRP that is 256 zeros and ones;
for JSSP it is a completion-time matrix. Neither tells you anything at a glance,
and the interesting question — *which vehicle serves which customers, in what
order, at what load* — requires re-deriving structure the solver already had.

Each printer here reconstructs that structure for one problem class and renders
it as text. They are deliberately read-only and defensive: a printer that cannot
find the constants it needs returns ``None`` so the caller falls back to the
generic dump rather than raising in the middle of a report.

Printers are keyed by the same problem-class names as
:mod:`optdsl_tooling.fingerprint`, so detection and rendering agree.
"""

from __future__ import annotations

from typing import Any, Callable

#: A printer takes the assignment and constants and returns text, or ``None``
#: when the data does not match what it expects.
Printer = Callable[[dict[str, Any], dict[str, Any]], str | None]


def format_solution(
    assignment: dict[str, Any],
    constants: dict[str, Any],
    *,
    problem_class: str | None = None,
    objective_value: float | None = None,
    objective_sense: str = "minimize",
    feasible: bool | None = None,
    max_items: int = 40,
) -> str:
    """Render *assignment* using the printer for *problem_class*.

    Falls back to a generic variable dump when the class is unknown or the
    printer cannot interpret the data.
    """
    header = _header(objective_value, objective_sense, feasible)

    printer = PRINTERS.get(problem_class or "")
    if printer is not None:
        try:
            body = printer(assignment, constants)
        except Exception:  # noqa: BLE001 - a printer must never break a report
            body = None
        if body:
            return f"{header}\n\n{body}"

    return f"{header}\n\n{_generic(assignment, max_items=max_items)}"


def _header(
    objective_value: float | None,
    objective_sense: str,
    feasible: bool | None,
) -> str:
    """One-line summary.

    Infeasibility is stated explicitly: a degenerate assignment (every item at
    the origin, every decision zero) renders as a plausible-looking table, and
    without this line the reader would take it at face value.
    """
    if objective_value is None:
        head = "Solution (objective unknown)"
    else:
        head = f"Solution ({objective_sense} objective = {_num(objective_value)})"
    if feasible is False:
        head += " - INFEASIBLE, constraint violations present"
    return head


# ---------------------------------------------------------------------------
# CVRP
# ---------------------------------------------------------------------------


def _print_cvrp(assignment: dict[str, Any], constants: dict[str, Any]) -> str | None:
    """One line per vehicle: route, load, distance."""
    arcs = assignment.get("arcs")
    if not isinstance(arcs, list):
        return None

    try:
        n = int(constants["N_CITIES"])
        nv = int(constants["N_VEHICLES"])
        depot = int(constants.get("DEPOT", 0))
        demands = [int(v) for v in constants["DEMANDS"]]
        capacity = int(constants["VEHICLE_CAPACITY"])
        dist = constants.get("DISTANCE_MATRIX")
    except (KeyError, TypeError, ValueError):
        return None

    if len(arcs) < nv * n * n:
        return None

    lines: list[str] = []
    total_distance = 0
    total_customers = 0
    used = 0

    for v in range(nv):
        route = _cvrp_route(arcs, v, n, depot)
        if not route:
            continue
        used += 1
        total_customers += len(route)
        load = sum(demands[c] for c in route if c < len(demands))
        cost = _cvrp_route_cost(route, depot, dist)
        total_distance += cost

        path = " -> ".join(str(node) for node in [depot, *route, depot])
        flag = "" if load <= capacity else f"  OVER CAPACITY ({capacity})"
        lines.append(
            f"  vehicle {v}: {path}\n"
            f"      {len(route)} customers, load {load}/{capacity}, distance {cost}{flag}"
        )

    if not lines:
        return "  no vehicle is used"

    summary = (
        f"  {used}/{nv} vehicles, {total_customers} customers served, "
        f"total distance {total_distance}"
    )
    return summary + "\n\n" + "\n".join(lines)


def _cvrp_route(arcs: list[int], vehicle: int, n: int, depot: int) -> list[int]:
    """Trace one vehicle's route from the depot through the arc matrix."""
    route: list[int] = []
    current = depot
    visited: set[int] = set()
    offset = vehicle * n * n

    for _ in range(n):
        nxt = -1
        for j in range(n):
            if arcs[offset + current * n + j]:
                nxt = j
                break
        if nxt < 0 or nxt == depot or nxt in visited:
            break
        visited.add(nxt)
        route.append(nxt)
        current = nxt

    return route


def _cvrp_route_cost(route: list[int], depot: int, dist: Any) -> int:
    if not isinstance(dist, list) or not route:
        return 0
    path = [depot, *route, depot]
    total = 0
    for a, b in zip(path, path[1:]):
        try:
            total += int(dist[a][b])
        except (IndexError, TypeError, ValueError):
            return total
    return total


# ---------------------------------------------------------------------------
# JSSP
# ---------------------------------------------------------------------------


def _print_jssp(assignment: dict[str, Any], constants: dict[str, Any]) -> str | None:
    """A per-machine schedule table plus the makespan."""
    completion = assignment.get("completion")
    if not isinstance(completion, list):
        return None

    try:
        n_jobs = int(constants["N_JOBS"])
        n_machines = int(constants["N_MACHINES"])
        processing = constants["PROCESSING_TIMES"]
        sequence = constants["MACHINE_SEQUENCE"]
    except (KeyError, TypeError, ValueError):
        return None

    if len(completion) < n_jobs:
        return None

    # Collect (start, end, job, op) per machine.
    per_machine: list[list[tuple[int, int, int, int]]] = [[] for _ in range(n_machines)]
    makespan = 0

    for job in range(n_jobs):
        row = completion[job]
        if not isinstance(row, list):
            return None
        for op in range(n_machines):
            if op >= len(row):
                continue
            end = row[op]
            if not isinstance(end, (int, float)):
                continue
            end = int(end)
            makespan = max(makespan, end)
            try:
                machine = int(sequence[job][op])
                duration = int(processing[job][machine])
            except (IndexError, TypeError, ValueError):
                continue
            per_machine[machine].append((end - duration, end, job, op))

    lines = [f"  makespan {makespan}", ""]
    for machine in range(n_machines):
        ops = sorted(per_machine[machine])
        if not ops:
            lines.append(f"  machine {machine}: idle")
            continue
        rendered = "  ".join(
            f"J{job}.{op}[{start}-{end}]" for start, end, job, op in ops
        )
        lines.append(f"  machine {machine}: {rendered}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1D bin packing
# ---------------------------------------------------------------------------


def _print_1dbp(assignment: dict[str, Any], constants: dict[str, Any]) -> str | None:
    """One line per bin: which items it holds and how full it is."""
    assignments = assignment.get("assignments")
    if not isinstance(assignments, list):
        return None

    try:
        weights = [int(v) for v in constants["ITEM_WEIGHTS"]]
        capacities = [int(v) for v in constants["BOX_CAPACITIES"]]
    except (KeyError, TypeError, ValueError):
        return None

    bins: dict[int, list[int]] = {}
    for item, box in enumerate(assignments):
        if not isinstance(box, (int, float)) or box < 0:
            continue
        bins.setdefault(int(box), []).append(item)

    if not bins:
        return "  no item is assigned"

    lines: list[str] = []
    for box in sorted(bins):
        items = bins[box]
        load = sum(weights[i] for i in items if i < len(weights))
        capacity = capacities[box] if box < len(capacities) else None
        detail = ", ".join(f"item {i} (w={weights[i]})" for i in items if i < len(weights))
        cap_text = f"/{capacity}" if capacity is not None else ""
        flag = "" if capacity is None or load <= capacity else "  OVER CAPACITY"
        lines.append(f"  bin {box}: load {load}{cap_text}{flag}\n      {detail}")

    return f"  {len(bins)} bin(s) used\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 2D bin packing
# ---------------------------------------------------------------------------


def _print_2dbp(assignment: dict[str, Any], constants: dict[str, Any]) -> str | None:
    """One line per box: item placements and used area."""
    boxes = assignment.get("assignments")
    xs = assignment.get("x_positions")
    ys = assignment.get("y_positions")
    if not isinstance(boxes, list) or not isinstance(xs, list) or not isinstance(ys, list):
        return None

    try:
        widths = [int(v) for v in constants["ITEM_WIDTHS"]]
        heights = [int(v) for v in constants["ITEM_HEIGHTS"]]
        box_w = [int(v) for v in constants["BOX_WIDTH_CAPACITIES"]]
        box_h = [int(v) for v in constants["BOX_HEIGHT_CAPACITIES"]]
    except (KeyError, TypeError, ValueError):
        return None

    grouped: dict[int, list[int]] = {}
    for item, box in enumerate(boxes):
        if not isinstance(box, (int, float)) or box < 0:
            continue
        grouped.setdefault(int(box), []).append(item)

    if not grouped:
        return "  no item is placed"

    lines: list[str] = []
    for box in sorted(grouped):
        items = grouped[box]
        width = box_w[box] if box < len(box_w) else None
        height = box_h[box] if box < len(box_h) else None
        area = sum(
            widths[i] * heights[i]
            for i in items
            if i < len(widths) and i < len(heights)
        )
        capacity = (width * height) if width and height else None
        fill = f", fill {area / capacity:.0%}" if capacity else ""
        lines.append(f"  box {box} ({width}x{height}{fill}):")
        for item in items:
            if item >= len(widths) or item >= len(heights):
                continue
            x = xs[item] if item < len(xs) else "?"
            y = ys[item] if item < len(ys) else "?"
            lines.append(
                f"      item {item} at ({x},{y}) size {widths[item]}x{heights[item]}"
            )

    return f"  {len(grouped)} box(es) used\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Cutting and packing
# ---------------------------------------------------------------------------


def _print_cutting_packing(
    assignment: dict[str, Any], constants: dict[str, Any]
) -> str | None:
    """One line per layer: the cut positions and the resulting pieces."""
    cuts = assignment.get("cut_positions")
    if not isinstance(cuts, list):
        return None

    try:
        n_segments = int(constants["N_SEGMENTS"])
        n_cuts = int(constants["N_CUTS_PER_SEGMENT"])
        n_pieces = int(constants["N_PIECES_PER_SEGMENT"])
        lengths = [int(v) for v in constants["SEGMENT_LENGTHS"]]
    except (KeyError, TypeError, ValueError):
        return None

    lines: list[str] = []
    total_waste = 0

    for segment in range(n_segments):
        base = segment * n_cuts
        if base + n_cuts > len(cuts):
            break
        positions = [int(cuts[base + i]) for i in range(n_cuts)]
        length = lengths[segment] if segment < len(lengths) else None

        pieces: list[int] = []
        previous = 0
        for position in positions:
            pieces.append(position - previous)
            previous = position
        if length is not None:
            pieces.append(length - previous)

        waste = sum(p for p in pieces if p <= 0)
        total_waste += waste
        piece_text = ", ".join(str(p) for p in pieces)
        length_text = f"/{length}" if length is not None else ""
        lines.append(
            f"  segment {segment}: cuts {positions} -> pieces [{piece_text}] "
            f"(total {sum(pieces)}{length_text})"
        )

    if not lines:
        return None

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Woodcutting pipeline
# ---------------------------------------------------------------------------


def _print_woodcutting(
    assignment: dict[str, Any], constants: dict[str, Any]
) -> str | None:
    """One line per board: its cut positions and the pieces they produce."""
    cuts = assignment.get("cuts_list_list")
    if not isinstance(cuts, list):
        return None

    boards = constants.get("GIVEN_INITIAL_BOARDS")
    if not isinstance(boards, list):
        return None

    lines: list[str] = []
    for index, board_cuts in enumerate(cuts):
        # The DSL declares cuts_list_list as a list of records, so each entry
        # arrives as {"position_list": [...]} rather than a bare list.
        positions = _cut_positions(board_cuts)
        if positions is None:
            continue

        board = boards[index] if index < len(boards) else None
        length = _board_length(board)

        pieces: list[int] = []
        previous = 0
        for position in positions:
            pieces.append(position - previous)
            previous = position
        if length is not None:
            pieces.append(length - previous)

        length_text = f"/{length}" if length is not None else ""
        piece_text = ", ".join(str(p) for p in pieces) if pieces else "-"
        lines.append(
            f"  board {index}: cuts {positions} -> pieces [{piece_text}] "
            f"(total {sum(pieces)}{length_text})"
        )

    if not lines:
        return None

    kept = assignment.get("keep_decisions")
    if isinstance(kept, list):
        lines.append("")
        lines.append(f"  keep decisions: {_compact(kept)}")

    return "\n".join(lines)


def _cut_positions(value: Any) -> list[int] | None:
    """Extract cut positions from either a record or a bare list."""
    if isinstance(value, dict):
        value = value.get("position_list")
    if not isinstance(value, list):
        return None
    return [int(v) for v in value if isinstance(v, (int, float))]


def _board_length(board: Any) -> int | None:
    """Read a board's length from whichever shape the instance uses."""
    if isinstance(board, dict):
        for key in ("length", "board_length"):
            if isinstance(board.get(key), (int, float)):
                return int(board[key])
        return None
    if isinstance(board, (int, float)):
        return int(board)
    return None


# ---------------------------------------------------------------------------
# generic fallback
# ---------------------------------------------------------------------------


def _generic(assignment: dict[str, Any], *, max_items: int = 40) -> str:
    """Dump every variable, truncating long vectors."""
    if not assignment:
        return "  (empty assignment)"

    lines: list[str] = []
    for name in sorted(assignment):
        value = assignment[name]
        if isinstance(value, list):
            lines.append(f"  {name} ({len(value)} values): {_compact(value, max_items)}")
        else:
            lines.append(f"  {name} = {value}")
    return "\n".join(lines)


def _compact(value: list[Any], limit: int = 40) -> str:
    """Render a list on one line, eliding the middle when it is long."""
    if len(value) <= limit:
        return "[" + ", ".join(str(v) for v in value) + "]"
    head = ", ".join(str(v) for v in value[: limit // 2])
    tail = ", ".join(str(v) for v in value[-(limit // 2) :])
    return f"[{head}, ... {len(value) - limit} more ..., {tail}]"


def _num(value: float) -> str:
    """Render a number without a trailing ``.0``."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:g}" if isinstance(value, float) else str(value)


#: Problem class -> printer. Keys match :mod:`optdsl_tooling.fingerprint`.
PRINTERS: dict[str, Printer] = {
    "cvrp": _print_cvrp,
    "cvrp_tour": _print_cvrp,
    "jssp": _print_jssp,
    "1dbp": _print_1dbp,
    "2dbp": _print_2dbp,
    "cutting_packing": _print_cutting_packing,
    "woodcutting": _print_woodcutting,
}


def supported_classes() -> list[str]:
    """Problem classes that have a dedicated printer."""
    return sorted(PRINTERS)
