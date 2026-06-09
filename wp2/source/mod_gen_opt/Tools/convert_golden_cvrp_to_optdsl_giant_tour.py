r"""Convert Golden's CVRP benchmark files (.vrp) to OPTDSL giant-tour format (.dsl).

Giant-tour representation:
  - tour: DSList(N_CUSTOMERS, DSInt(1, N_CITIES-1)) — permutation of customers
  - cut_after: DSList(N_CUSTOMERS, DSInt(0, 1))     — 1 = route break after position

This representation is designed for LNS with --operator-profile permutation.
MiniZinc (main.py) is NOT supported because the formulation uses conditional
logic and double variable-indexed array access inside constraint functions.

Usage:
    python Tools/convert_golden_cvrp_to_optdsl_giant_tour.py input_dir output_dir
    python Tools/convert_golden_cvrp_to_optdsl_giant_tour.py \
        problem_instances/cvrp/benchmarks/golden \
        problem_instances/cvrp/benchmarks/golden_optdsl_giant_tour
"""

from __future__ import annotations

import math
from pathlib import Path


def parse_vrp_file(filepath: str) -> dict:
    """Parse VRP/CVRP file format (handles Golden format with float coords)."""
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    result = {
        "name": "",
        "n_vehicles": 100,
        "capacity": 1000,
        "nodes": [],    # (x, y) float tuples
        "demands": [],  # int list indexed by node (0 = depot)
    }

    section = None

    for line in lines:
        if not line or line.startswith("*"):
            continue

        parts = line.split()

        if parts[0] == "NAME":
            result["name"] = " ".join(parts[1:]).lstrip(": ").strip()
            section = None
        elif parts[0] == "VEHICLES":
            try:
                result["n_vehicles"] = int(parts[1])
            except (ValueError, IndexError):
                pass
            section = None
        elif parts[0] == "CAPACITY":
            result["capacity"] = int(float(parts[-1]))
            section = None
        elif parts[0] == "NODE_COORD_SECTION":
            section = "nodes"
        elif parts[0] == "DEMAND_SECTION":
            section = "demands"
        elif parts[0] in ("EOF", "DEPOT_SECTION"):
            section = None
        elif section == "nodes":
            try:
                x = float(parts[1])
                y = float(parts[2])
                result["nodes"].append((x, y))
            except (ValueError, IndexError):
                pass
        elif section == "demands":
            try:
                demand = int(float(parts[1]))
                result["demands"].append(demand)
            except (ValueError, IndexError):
                pass

    # If n_vehicles was not in the file, infer a sufficient upper bound
    if result["n_vehicles"] >= 100:
        total_demand = sum(result["demands"])
        result["n_vehicles"] = max(1, (total_demand + result["capacity"] - 1) // result["capacity"] + 2)

    return result


def euc_distance(x1: float, y1: float, x2: float, y2: float) -> int:
    """Euclidean distance rounded to nearest integer (standard VRP rounding)."""
    return round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2))


def compute_distance_matrix(nodes: list[tuple[float, float]]) -> list[list[int]]:
    n = len(nodes)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = euc_distance(nodes[i][0], nodes[i][1], nodes[j][0], nodes[j][1])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def generate_optdsl_giant_tour(data: dict) -> str:
    """Generate OPTDSL giant-tour content from parsed VRP data.

    Key variables:
      tour[pos]      = customer ID (1..N_CITIES-1) at tour position pos
      cut_after[pos] = 1 if a route ends after position pos (depot return inserted)

    Constraint functions use Python-style conditional logic and double
    variable-indexed array access, which the LNS evaluator handles natively.
    MiniZinc is NOT supported for this formulation.
    """
    n_cities = len(data["nodes"])
    n_customers = n_cities - 1
    depot = 0
    n_vehicles = data["n_vehicles"]
    capacity = data["capacity"]
    max_route_cost = 1_000_000

    demands_str = str(data["demands"])

    x_coords = [round(n[0]) for n in data["nodes"]]
    y_coords = [round(n[1]) for n in data["nodes"]]
    x_coords_str = str(x_coords)
    y_coords_str = str(y_coords)

    dist_matrix = compute_distance_matrix(data["nodes"])
    dist_matrix_str = "[\n" + ",\n".join(f"\t{row}" for row in dist_matrix) + "\n]"

    problem_name = data.get("name", "cvrp").replace(" ", "_")

    template = f"""# Golden CVRP instance (giant-tour representation): {problem_name}
# City 0 is the depot. Customers are 1..{n_customers}.
#
# Giant-tour representation:
#   tour[pos]      = customer ID at tour position pos (permutation of 1..{n_customers})
#   cut_after[pos] = 1 if route break occurs after position pos
#
# NOTE: This formulation is designed for LNS (example_lns.py) with
#   --operator-profile permutation
# It is NOT compatible with MiniZinc (main.py).

N_CITIES : int = {n_cities}
N_CUSTOMERS : int = N_CITIES - 1
DEPOT : int = {depot}
N_VEHICLES : int = {n_vehicles}
VEHICLE_CAPACITY : int = {capacity}
MAX_ROUTE_COST : int = {max_route_cost}

X_COORDS : DSList(N_CITIES, DSInt()) = {x_coords_str}
Y_COORDS : DSList(N_CITIES, DSInt()) = {y_coords_str}

# Depot demand is 0.
DEMANDS : DSList(N_CITIES, DSInt()) = {demands_str}

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = {dist_matrix_str}

# Giant tour: permutation of customer IDs 1..N_CUSTOMERS
tour: DSList(N_CUSTOMERS, DSInt(1, N_CUSTOMERS))

# Route cuts: cut_after[pos] = 1 inserts a depot return after position pos
cut_after: DSList(N_CUSTOMERS, DSInt(0, 1))


def all_customers_visited(tour: DSList(N_CUSTOMERS, DSInt(1, N_CUSTOMERS))):
\t# Each customer must appear exactly once in the tour.
\tfor c in range(1, N_CITIES):
\t\tcount = 0
\t\tfor pos in range(N_CUSTOMERS):
\t\t\tif tour[pos] == c:
\t\t\t\tcount = count + 1
\t\tassert count == 1


def route_count(cut_after: DSList(N_CUSTOMERS, DSInt(0, 1))):
\t# Number of routes = cuts + 1; must not exceed N_VEHICLES.
\troutes = 0
\tfor pos in range(N_CUSTOMERS):
\t\troutes = routes + cut_after[pos]
\tassert routes + 1 <= N_VEHICLES
\t# No explicit cut needed at the last position (implicit depot return).
\tassert cut_after[N_CUSTOMERS - 1] == 0


def capacity_constraints(
\ttour: DSList(N_CUSTOMERS, DSInt(1, N_CUSTOMERS)),
\tcut_after: DSList(N_CUSTOMERS, DSInt(0, 1))
):
\t# Cumulative demand within each route must not exceed vehicle capacity.
\tload = 0
\tfor pos in range(N_CUSTOMERS):
\t\tload = load + DEMANDS[tour[pos]]
\t\tassert load <= VEHICLE_CAPACITY
\t\tif cut_after[pos] == 1:
\t\t\tload = 0


def total_distance(
\ttour: DSList(N_CUSTOMERS, DSInt(1, N_CUSTOMERS)),
\tcut_after: DSList(N_CUSTOMERS, DSInt(0, 1))
):
\tdist = 0
\t# Depot to first customer.
\tdist = dist + DISTANCE_MATRIX[DEPOT][tour[0]]
\t# Traverse the tour; insert depot detours at cut positions.
\tfor pos in range(N_CUSTOMERS - 1):
\t\tif cut_after[pos] == 1:
\t\t\tdist = dist + DISTANCE_MATRIX[tour[pos]][DEPOT] + DISTANCE_MATRIX[DEPOT][tour[pos + 1]]
\t\telse:
\t\t\tdist = dist + DISTANCE_MATRIX[tour[pos]][tour[pos + 1]]
\t# Last customer back to depot.
\tdist = dist + DISTANCE_MATRIX[tour[N_CUSTOMERS - 1]][DEPOT]
\treturn dist


all_customers_visited(tour)
route_count(cut_after)
capacity_constraints(tour, cut_after)

objective: DSInt(0, MAX_ROUTE_COST) = total_distance(tour, cut_after)

minimize(objective)
"""
    return template


def convert_directory(input_dir: str, output_dir: str) -> None:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    vrp_files = sorted(input_path.glob("*.vrp"))
    print(f"Found {len(vrp_files)} VRP files in {input_dir}")

    for vrp_file in vrp_files:
        print(f"  Converting {vrp_file.name}...")
        try:
            data = parse_vrp_file(str(vrp_file))
            optdsl = generate_optdsl_giant_tour(data)
            outfile = output_path / f"{vrp_file.stem}.dsl"
            outfile.write_text(optdsl, encoding="utf-8")
            n = len(data["nodes"])
            print(f"    -> {outfile} (cities={n}, customers={n-1}, vehicles={data['n_vehicles']}, capacity={data['capacity']})")
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
