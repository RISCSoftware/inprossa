r"""Convert Golden's CVRP benchmark files (.vrp) to OPTDSL format (.dsl).

Golden instances use the standard VRP file format:
  - NAME
  - TYPE CVRP
  - EDGE_WEIGHT_TYPE EUC_2D (or EUC_2D with rounding/truncating)
  - NODE_COORD_SECTION  (depot first, then customers)
  - DEMAND_SECTION
  - (optional) EDGE_WEIGHT_SECTION

The OPTDSL output follows the same structure as the existing random_euclidean_cvrp_*.dsl
files (arc-based formulation with MTZ subtour elimination).

Usage:
    python Tools/convert_golden_cvrp_to_optdsl.py input_dir output_dir
    python Tools/convert_golden_cvrp_to_optdsl.py problem_instances/cvrp/benchmark/golden problem_instances/cvrp/benchmark/golden_optdsl
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path


def parse_vrp_file(filepath: str) -> dict:
    """Parse VRP/CVRP file format (handles both standard and Golden format)."""
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    result = {
        "name": "",
        "type": "",
        "edge_weight_type": "EUC_2D",
        "depot": 1,
        "n_vehicles": 100,  # Will be computed if not specified
        "capacity": 1000,
        "nodes": [],  # (x, y) tuples
        "demands": [],
        "edge_weights": None,  # matrix if provided
    }

    section = None
    node_idx = 0
    customer_idx = 0

    for line in lines:
        if not line or line.startswith("*"):
            continue

        parts = line.split()

        # Header fields
        if parts[0] == "NAME":
            result["name"] = " ".join(parts[1:])
            section = None
        elif parts[0] == "TYPE":
            result["type"] = parts[1]
            section = None
        elif parts[0] == "EDGE_WEIGHT_TYPE":
            result["edge_weight_type"] = parts[1]
            section = None
        elif parts[0] == "DIMENSION" and len(parts) >= 2:
            # Golden format: DIMENSION : N
            pass  # Ignore, we count nodes
        elif parts[0] == "VEHICLES" and len(parts) >= 2:
            result["n_vehicles"] = int(parts[1])
            section = None
        elif parts[0] == "CAPACITY":
            # Handle both "CAPACITY : N" and "VEHICLES N CAPACITY M" format
            cap_val = int(float(parts[-1]))
            result["capacity"] = cap_val
            section = None
        elif parts[0] == "NODE_COORD_SECTION":
            section = "nodes"
            node_idx = 0
            customer_idx = 0
            continue
        elif parts[0] == "DEMAND_SECTION":
            section = "demands"
            continue
        elif parts[0] == "EDGE_WEIGHT_SECTION":
            section = "edge_weights"
            result["edge_weights"] = []
            continue
        elif parts[0] == "EOL_COMMENT":
            section = None
            continue

        if section == "nodes":
            # Format: id x y [demand] or id x y
            try:
                node_id = int(parts[0])
                x = int(float(parts[1]))
                y = int(float(parts[2]))
                if node_idx == 0:
                    result["depot"] = node_id
                result["nodes"].append((x, y))
                node_idx += 1
                if node_idx > 1:
                    customer_idx += 1
            except (ValueError, IndexError):
                pass
        elif section == "demands":
            # Format: id demand
            try:
                customer_id = int(parts[0])
                demand = int(float(parts[1]))
                result["demands"].append((customer_id, demand))
            except (ValueError, IndexError):
                pass
        elif section == "edge_weights":
            try:
                row = [int(x) for x in parts]
                result["edge_weights"].append(row)
            except ValueError:
                pass

    # Pad demands list to match node count (depot demand = 0)
    demand_dict = {d[0]: d[1] for d in result["demands"]}
    n_nodes = len(result["nodes"])
    full_demands = [0] * n_nodes
    for node_id, demand in demand_dict.items():
        if node_id <= n_nodes:
            full_demands[node_id - 1] = demand

    result["demands"] = full_demands

    return result


def euc_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    """Euclidean distance rounded to nearest integer."""
    return round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2))


def compute_distance_matrix(nodes: list[tuple[int, int]]) -> list[list[int]]:
    """Compute flattened Euclidean distance matrix."""
    n = len(nodes)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = euc_distance(nodes[i][0], nodes[i][1], nodes[j][0], nodes[j][1])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def generate_optdsl(data: dict) -> str:
    """Generate OPTDSL content from parsed VRP data.
    
    Matches the exact formulation of random_euclidean_cvrp_8.dsl:
    - All customers visited exactly once (incoming + outgoing per customer)
    - Depot start/end constraints (departures/returns per vehicle)
    - Flow conservation (incoming == outgoing per customer)
    - Capacity constraints (load per vehicle)
    - No self-loops
    - MTZ subtour elimination (aggregated arcs across all vehicles)
    - Objective = total distance (minimize)
    """
    n_cities = len(data["nodes"])
    depot = 0  # 0-indexed (depot is always first node)
    capacity = data["capacity"]
    n_vehicles = data["n_vehicles"]
    
    # If no vehicle count specified, compute from total demand / capacity (upper bound)
    total_demand = sum(data["demands"])
    if n_vehicles > total_demand / capacity * 2:  # Heuristic: if too large, compute reasonable upper bound
        n_vehicles = max(1, (total_demand + capacity - 1) // capacity + 2)
    
    n_arcs = n_vehicles * n_cities * n_cities
    max_route_cost = 100000  # Large upper bound

    demands_str = str(data["demands"])

    # Coordinates (integers from .vrp, rounded)
    x_coords = [n[0] for n in data["nodes"]]
    y_coords = [n[1] for n in data["nodes"]]
    x_coords_str = str(x_coords)
    y_coords_str = str(y_coords)

    # Distance matrix
    dist_matrix = compute_distance_matrix(data["nodes"])
    dist_matrix_lines = []
    for row in dist_matrix:
        dist_matrix_lines.append(f"\t{row}")
    dist_matrix_str = "[\n" + ",\n".join(dist_matrix_lines) + "\n]"

    problem_name = data.get("name", "cvrp").replace(" ", "_")

    template = f"""# Golden CVRP instance: {problem_name}
# City 0 is the depot.
# Converted from standard VRP file format.

N_CITIES : int = {n_cities}
DEPOT : int = {depot}
N_VEHICLES : int = {n_vehicles}
VEHICLE_CAPACITY : int = {capacity}
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = {max_route_cost}

X_COORDS : DSList(N_CITIES, DSInt()) = {x_coords_str}
Y_COORDS : DSList(N_CITIES, DSInt()) = {y_coords_str}

# Depot demand is 0.
DEMANDS : DSList(N_CITIES, DSInt()) = {demands_str}

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = {dist_matrix_str}

# Flattened binary arc variables: arcs[v, i, j] in {{0, 1}}
arcs: DSList(N_ARCS, DSInt(0, 1))
vehicle_used: DSList(N_VEHICLES, DSInt(0, 1))
# MTZ/load variable to eliminate customer-only subtours.
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

    return template


def convert_directory(input_dir: str, output_dir: str) -> None:
    """Convert all .vrp files in input_dir to .dsl files in output_dir."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    vrp_files = sorted(input_path.glob("*.vrp"))
    print(f"Found {len(vrp_files)} VRP files in {input_dir}")

    for vrp_file in vrp_files:
        print(f"  Converting {vrp_file.name}...")
        try:
            data = parse_vrp_file(str(vrp_file))
            optdsl = generate_optdsl(data)
            outfile = output_path / f"{vrp_file.stem}.dsl"
            outfile.write_text(optdsl, encoding="utf-8")
            print(f"    -> {outfile} (cities={len(data['nodes'])}, demands={sum(data['demands'])})")
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\nDone. Files written to: {output_dir}")


def main() -> None:
    import sys
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_vrp_dir> <output_optdsl_dir>")
        sys.exit(1)

    convert_directory(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
