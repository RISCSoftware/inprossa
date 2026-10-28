#!/usr/bin/env python
"""Convert CVRP benchmark files (.vrp) to OptDSL format (.dsl).

This unified converter supports both common CVRP Library files and
Christofides/Eilon instances:

1. EUC_2D with NODE_COORD_SECTION
2. EXPLICIT with EDGE_WEIGHT_FORMAT LOWER_ROW and EDGE_WEIGHT_SECTION

Vehicle count resolution can use:
- a fixed integer override
- VEHICLES header
- filename pattern E-n*-k*
- automatic fallback heuristic
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path


def parse_vrp_file(filepath: str) -> dict:
    """Parse a CVRP .vrp file into a normalized dictionary.

    Supports TSPLIB variants using either "KEY : VALUE" or "KEY: VALUE".
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]

    result: dict = {
        "name": "",
        "type": "",
        "edge_weight_type": "EUC_2D",
        "edge_weight_format": "",
        "dimension": 0,
        "depot": 1,
        "n_vehicles": 0,
        "capacity": 1000,
        "nodes": [],
        "demands": [],
        "edge_weights": None,
    }

    section: str | None = None

    for line in lines:
        if not line or line.startswith("*"):
            continue

        parts = line.split()
        if not parts:
            continue

        key = parts[0].rstrip(":")
        vals = parts[1:]
        if vals and vals[0] == ":":
            vals = vals[1:]

        # Section markers
        if key == "NODE_COORD_SECTION":
            section = "nodes"
            continue
        if key == "DEMAND_SECTION":
            section = "demands"
            continue
        if key == "EDGE_WEIGHT_SECTION":
            section = "edge_weights"
            result["edge_weights"] = []
            continue
        if key == "DEPOT_SECTION":
            section = None
            continue
        if key in ("EOF", "END"):
            section = None
            break

        # Header fields
        if key == "NAME":
            result["name"] = " ".join(vals)
            section = None
            continue
        if key == "TYPE":
            result["type"] = vals[0] if vals else ""
            section = None
            continue
        if key == "EDGE_WEIGHT_TYPE":
            result["edge_weight_type"] = vals[0] if vals else ""
            section = None
            continue
        if key == "EDGE_WEIGHT_FORMAT":
            result["edge_weight_format"] = vals[0] if vals else ""
            section = None
            continue
        if key == "DIMENSION" and vals:
            result["dimension"] = int(float(vals[-1]))
            section = None
            continue
        if key == "VEHICLES" and vals:
            result["n_vehicles"] = int(float(vals[0]))
            section = None
            continue
        if key == "CAPACITY" and vals:
            result["capacity"] = int(float(vals[-1]))
            section = None
            continue

        # Section content
        if section == "nodes":
            try:
                _node_id = int(parts[0])
                # Coordinates are kept as floats: Golden instances use fractional
                # coordinates and truncating them changes the distance matrix.
                x = float(parts[1])
                y = float(parts[2])
                result["nodes"].append((x, y))
            except (ValueError, IndexError):
                pass
        elif section == "demands":
            try:
                node_id = int(parts[0])
                demand = int(float(parts[1]))
                result["demands"].append((node_id, demand))
            except (ValueError, IndexError):
                pass
        elif section == "edge_weights":
            try:
                row = [int(float(x)) for x in parts]
                result["edge_weights"].append(row)
            except ValueError:
                pass

    n_nodes = result["dimension"] or len(result["nodes"])
    demand_map = {node_id: demand for node_id, demand in result["demands"]}
    full_demands = [0] * n_nodes
    for node_id, demand in demand_map.items():
        if 1 <= node_id <= n_nodes:
            full_demands[node_id - 1] = demand
    result["demands"] = full_demands

    return result


def extract_n_vehicles_from_filename(filename: str) -> int:
    """Extract k from E-n*-k* names. Returns 0 when unavailable."""
    stem = Path(filename).stem
    match = re.search(r"-k(\d+)$", stem, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def extract_n_vehicles_from_solution(input_file: str) -> int:
    """Count the routes in a sibling ``.sol`` file. Returns 0 when unavailable.

    CVRPLIB solution files list one ``Route #n:`` line per vehicle.  Using the
    published route count keeps the fleet tight; the demand/capacity heuristic
    over-provisions and turns the benchmark into a relaxation.
    """
    solution_path = Path(input_file).with_suffix(".sol")
    if not solution_path.exists():
        return 0
    try:
        text = solution_path.read_text(encoding="utf-8")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if line.strip().startswith("Route #"))


def euc_distance(x1: float, y1: float, x2: float, y2: float) -> int:
    """Euclidean distance rounded to nearest integer."""
    return round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2))


def compute_distance_matrix_from_coords(nodes: list[tuple[float, float]]) -> list[list[int]]:
    """Compute full symmetric distance matrix from coordinates."""
    n = len(nodes)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = euc_distance(nodes[i][0], nodes[i][1], nodes[j][0], nodes[j][1])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def lower_row_to_full_matrix(rows: list[list[int]], n: int) -> list[list[int]]:
    """Expand TSPLIB LOWER_ROW data into a full symmetric matrix."""
    matrix = [[0] * n for _ in range(n)]
    flat: list[int] = []
    for row in rows:
        flat.extend(row)

    idx = 0
    for i in range(1, n):
        for j in range(i):
            if idx < len(flat):
                matrix[i][j] = flat[idx]
                matrix[j][i] = flat[idx]
                idx += 1
    return matrix


def build_distance_matrix(data: dict, edge_weight_type: str = "auto") -> list[list[int]]:
    """Build full distance matrix based on per-instance format detection."""
    n = data["dimension"] or len(data["nodes"])

    inferred_type = data.get("edge_weight_type", "EUC_2D").upper()
    inferred_format = data.get("edge_weight_format", "").upper()

    if edge_weight_type == "EXPLICIT":
        if not data["edge_weights"]:
            raise ValueError("EXPLICIT requested but EDGE_WEIGHT_SECTION is missing")
        return lower_row_to_full_matrix(data["edge_weights"], n)

    if edge_weight_type == "EUC_2D":
        if not data["nodes"]:
            raise ValueError("EUC_2D requested but NODE_COORD_SECTION is missing")
        return compute_distance_matrix_from_coords(data["nodes"])

    # auto mode
    if inferred_type == "EXPLICIT" or inferred_format == "LOWER_ROW":
        if not data["edge_weights"]:
            raise ValueError("Detected EXPLICIT/LOWER_ROW but EDGE_WEIGHT_SECTION is missing")
        return lower_row_to_full_matrix(data["edge_weights"], n)

    if not data["nodes"]:
        raise ValueError("Cannot auto-detect EUC_2D because NODE_COORD_SECTION is missing")
    return compute_distance_matrix_from_coords(data["nodes"])


def resolve_vehicle_count(data: dict, input_file: str, vehicles_mode: str | int) -> int:
    """Resolve the fleet size.

    Precedence: explicit integer override > ``VEHICLES`` header > filename
    ``E-n*-k*`` > published route count in a sibling ``.sol`` > demand/capacity
    heuristic (last resort).

    The heuristic is only a fallback: it adds two spare vehicles on top of the
    capacity lower bound, which relaxes the instance and makes the objective
    incomparable to the published optimum.
    """
    if isinstance(vehicles_mode, int) and vehicles_mode > 0:
        return vehicles_mode

    header_value = int(data.get("n_vehicles") or 0)
    filename_value = extract_n_vehicles_from_filename(input_file)

    if vehicles_mode == "header":
        if header_value > 0:
            return header_value
        raise ValueError("--vehicles header selected but VEHICLES field is missing")

    if vehicles_mode == "filename":
        if filename_value > 0:
            return filename_value
        raise ValueError("--vehicles filename selected but filename does not match E-n*-k*")

    # auto: prefer header, then filename, then the published solution
    if header_value > 0:
        return header_value
    if filename_value > 0:
        return filename_value

    solution_value = extract_n_vehicles_from_solution(input_file)
    if solution_value > 0:
        return solution_value

    total_demand = sum(data["demands"])
    capacity = int(data["capacity"])
    heuristic = max(1, (total_demand + capacity - 1) // capacity + 2)
    print(
        f"  [WARN] {Path(input_file).name}: no VEHICLES header, no -k suffix and no "
        f".sol file; falling back to the demand/capacity heuristic ({heuristic} vehicles). "
        "The objective will not be comparable to the published optimum."
    )
    return heuristic


def generate_optdsl(
    data: dict,
    n_vehicles: int,
    distance_matrix: list[list[int]],
) -> str:
    """Generate OptDSL text for one CVRP instance."""
    n_cities = data["dimension"] or len(data["nodes"])
    depot = 0
    capacity = data["capacity"]

    demands = data["demands"]
    if data["nodes"]:
        # Coordinates are only informational (the distance matrix is authoritative)
        # and X_COORDS/Y_COORDS are DSInt lists, so round them for display.
        x_coords = [round(n[0]) for n in data["nodes"]]
        y_coords = [round(n[1]) for n in data["nodes"]]
    else:
        x_coords = [0] * n_cities
        y_coords = [0] * n_cities

    dist_matrix_lines = [f"\t{row}" for row in distance_matrix]
    dist_matrix_str = "[\n" + ",\n".join(dist_matrix_lines) + "\n]"

    problem_name = data.get("name", "cvrp").replace(" ", "_").replace("/", "_")
    return f"""# CVRP instance: {problem_name}
# City 0 is the depot.

N_CITIES : int = {n_cities}
DEPOT : int = {depot}
N_VEHICLES : int = {n_vehicles}
VEHICLE_CAPACITY : int = {capacity}
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = 100000

X_COORDS : DSList(N_CITIES, DSInt()) = {x_coords}
Y_COORDS : DSList(N_CITIES, DSInt()) = {y_coords}

DEMANDS : DSList(N_CITIES, DSInt()) = {demands}

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = {dist_matrix_str}

arcs: DSList(N_ARCS, DSInt(0, 1))
vehicle_used: DSList(N_VEHICLES, DSInt(0, 1))
u: DSList(N_CITIES, DSInt(0, VEHICLE_CAPACITY))


def all_customers_visited(arcs: DSList(N_ARCS, DSInt(0, 1))):
\tfor c in range(N_CITIES):
\t\tif c != DEPOT:
\t\t\tincoming = 0
\t\t\toutgoing = 0
\t\t\tfor v in range(N_VEHICLES):
\t\t\t\tfor i in range(N_CITIES):
\t\t\t\t\tincoming = incoming + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + c]
\t\t\t\tfor j in range(N_CITIES):
\t\t\t\t\toutgoing = outgoing + arcs[v * N_CITIES * N_CITIES + c * N_CITIES + j]
\t\t\tassert incoming == 1
\t\t\tassert outgoing == 1


def depot_start_end(
\tarcs: DSList(N_ARCS, DSInt(0, 1)),
\tvehicle_used: DSList(N_VEHICLES, DSInt(0, 1))
):
\tfor v in range(N_VEHICLES):
\t\tdepartures = 0
\t\treturns = 0
\t\tfor j in range(N_CITIES):
\t\t\tdepartures = departures + arcs[v * N_CITIES * N_CITIES + DEPOT * N_CITIES + j]
\t\tfor i in range(N_CITIES):
\t\t\treturns = returns + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + DEPOT]
\t\tassert departures == vehicle_used[v]
\t\tassert returns == vehicle_used[v]


def flow_conservation(arcs: DSList(N_ARCS, DSInt(0, 1))):
\tfor v in range(N_VEHICLES):
\t\tfor c in range(N_CITIES):
\t\t\tif c != DEPOT:
\t\t\t\tincoming = 0
\t\t\t\toutgoing = 0
\t\t\t\tfor i in range(N_CITIES):
\t\t\t\t\tincoming = incoming + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + c]
\t\t\t\tfor j in range(N_CITIES):
\t\t\t\t\toutgoing = outgoing + arcs[v * N_CITIES * N_CITIES + c * N_CITIES + j]
\t\t\t\tassert incoming == outgoing


def capacity_constraints(arcs: DSList(N_ARCS, DSInt(0, 1))):
\tfor v in range(N_VEHICLES):
\t\tvehicle_load = 0
\t\tfor c in range(N_CITIES):
\t\t\tif c != DEPOT:
\t\t\t\tserved_by_v = 0
\t\t\t\tfor j in range(N_CITIES):
\t\t\t\t\tserved_by_v = served_by_v + arcs[v * N_CITIES * N_CITIES + c * N_CITIES + j]
\t\t\t\tvehicle_load = vehicle_load + DEMANDS[c] * served_by_v
\t\tassert vehicle_load <= VEHICLE_CAPACITY


def no_self_loops(arcs: DSList(N_ARCS, DSInt(0, 1))):
\tfor v in range(N_VEHICLES):
\t\tfor i in range(N_CITIES):
\t\t\tassert arcs[v * N_CITIES * N_CITIES + i * N_CITIES + i] == 0


def subtour_elimination(
\tarcs: DSList(N_ARCS, DSInt(0, 1)),
\tu: DSList(N_CITIES, DSInt(0, VEHICLE_CAPACITY))
):
\tassert u[DEPOT] == 0

\tfor c in range(N_CITIES):
\t\tif c != DEPOT:
\t\t\tassert u[c] >= DEMANDS[c]
\t\t\tassert u[c] <= VEHICLE_CAPACITY

\tfor i in range(N_CITIES):
\t\tif i != DEPOT:
\t\t\tfor j in range(N_CITIES):
\t\t\t\tif j != DEPOT and i != j:
\t\t\t\t\tarc_ij = 0
\t\t\t\t\tfor v in range(N_VEHICLES):
\t\t\t\t\t\tarc_ij = arc_ij + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + j]
\t\t\t\t\tassert u[i] - u[j] + VEHICLE_CAPACITY * arc_ij <= VEHICLE_CAPACITY - DEMANDS[j]


def total_distance(arcs: DSList(N_ARCS, DSInt(0, 1))):
\tdist = 0
\tfor v in range(N_VEHICLES):
\t\tfor i in range(N_CITIES):
\t\t\tfor j in range(N_CITIES):
\t\t\t\tdist = dist + DISTANCE_MATRIX[i][j] * arcs[v * N_CITIES * N_CITIES + i * N_CITIES + j]
\treturn dist


all_customers_visited(arcs)
depot_start_end(arcs, vehicle_used)
flow_conservation(arcs)
capacity_constraints(arcs)
no_self_loops(arcs)
subtour_elimination(arcs, u)

objective: DSInt(0, MAX_ROUTE_COST) = total_distance(arcs)

minimize(objective)
"""


def convert_single(
    input_file: str,
    output_file: str,
    vehicles_mode: str | int = "auto",
    edge_weight_type: str = "auto",
    capacity_override: int | None = None,
) -> bool:
    """Convert one .vrp file to one .dsl file."""
    input_path = Path(input_file)
    try:
        data = parse_vrp_file(input_file)

        if capacity_override is not None and capacity_override > 0:
            data["capacity"] = capacity_override

        n_vehicles = resolve_vehicle_count(data, input_file, vehicles_mode)
        dist_matrix = build_distance_matrix(data, edge_weight_type=edge_weight_type)

        optdsl = generate_optdsl(data, n_vehicles, dist_matrix)
        Path(output_file).write_text(optdsl, encoding="utf-8")

        n_cities = data["dimension"] or len(data["nodes"])
        total_demand = sum(data["demands"])
        ew_type = data.get("edge_weight_type", "")
        ew_format = data.get("edge_weight_format", "")

        print(
            f"  [OK] {input_path.name} -> {Path(output_file).name} "
            f"| cities={n_cities}, vehicles={n_vehicles}, "
            f"capacity={data['capacity']}, total_demand={total_demand}, "
            f"edge_weight_type={ew_type}, edge_weight_format={ew_format}"
        )
        return True

    except (ValueError, OSError, RuntimeError) as e:
        print(f"  [FAIL] {input_path.name}: {e}")
        return False


def convert_batch(
    input_dir: str,
    output_dir: str,
    file_pattern: str = "*.vrp",
    vehicles_mode: str | int = "auto",
    edge_weight_type: str = "auto",
    capacity_override: int | None = None,
) -> int:
    """Convert all matching files in input_dir to output_dir."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    input_files = sorted(input_path.glob(file_pattern))
    if not input_files:
        print(f"No files matching '{file_pattern}' found in {input_dir}")
        return 0

    print(f"Converting {len(input_files)} CVRP files...")
    success_count = 0

    for input_file in input_files:
        output_file = output_path / f"{input_file.stem}.dsl"
        if convert_single(
            input_file=str(input_file),
            output_file=str(output_file),
            vehicles_mode=vehicles_mode,
            edge_weight_type=edge_weight_type,
            capacity_override=capacity_override,
        ):
            success_count += 1

    print(f"\nConversion complete: {success_count}/{len(input_files)} files converted to {output_dir}")
    return success_count


def parse_vehicles_arg(value: str) -> str | int:
    """Parse --vehicles argument into one of {auto, header, filename} or int."""
    lower = value.lower()
    if lower in {"auto", "header", "filename"}:
        return lower
    try:
        parsed = int(value)
        if parsed <= 0:
            raise ValueError
        return parsed
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--vehicles must be one of: auto, header, filename, or a positive integer"
        ) from exc


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert CVRP benchmark files (.vrp) to OptDSL format (.dsl)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--input-dir", help="Input directory containing .vrp files (batch mode)")
    mode_group.add_argument("--input-file", help="Single input file (.vrp) to convert")

    parser.add_argument("--output-dir", help="Output directory for batch conversion (required with --input-dir)")
    parser.add_argument("--output-file", help="Output file for single conversion (required with --input-file)")
    parser.add_argument(
        "--format",
        default="vrp",
        choices=["vrp", "tsp"],
        help="Input extension for batch mode (default: vrp)",
    )
    parser.add_argument(
        "--vehicles",
        type=parse_vehicles_arg,
        default="auto",
        help="Vehicle strategy: auto|header|filename|<positive int> (default: auto)",
    )
    parser.add_argument(
        "--edge-weight-type",
        default="auto",
        choices=["auto", "EUC_2D", "EXPLICIT"],
        help="Distance mode: auto (per file), EUC_2D, or EXPLICIT",
    )
    parser.add_argument(
        "--capacity",
        type=int,
        help="Override vehicle capacity",
    )

    args = parser.parse_args()

    if args.input_dir:
        if not args.output_dir:
            parser.error("--output-dir required with --input-dir")
        file_pattern = f"*.{args.format}"
        convert_batch(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            file_pattern=file_pattern,
            vehicles_mode=args.vehicles,
            edge_weight_type=args.edge_weight_type,
            capacity_override=args.capacity,
        )
        return

    if not args.output_file:
        parser.error("--output-file required with --input-file")
    if not Path(args.input_file).exists():
        parser.error(f"Input file not found: {args.input_file}")

    success = convert_single(
        input_file=args.input_file,
        output_file=args.output_file,
        vehicles_mode=args.vehicles,
        edge_weight_type=args.edge_weight_type,
        capacity_override=args.capacity,
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
