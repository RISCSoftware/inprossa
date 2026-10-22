"""Convert CVRPTW Solomon benchmark files (.txt) to OptDSL format (.dsl).

Solomon CVRPTW format:
  INSTANCE_NAME

  VEHICLE
  NUMBER     CAPACITY
    25         200

  CUSTOMER
  CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE TIME

      0      40         50          0          0       1236          0
      1      45         68         10        912        967         90
      ...

The depot is customer 0.

Usage:
  # Batch conversion
  python convert_cvrptw.py --input-dir <dir> --output-dir <dir>

  # Single file
  python convert_cvrptw.py --input-file C101.txt --output-file C101.dsl
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SolomonInstance:
    name: str
    n_vehicles: int
    capacity: int
    # Per-node: index 0 = depot
    x: list[float]
    y: list[float]
    demand: list[int]
    ready_time: list[int]
    due_date: list[int]
    service_time: list[int]

    @property
    def n_customers(self) -> int:
        return len(self.x) - 1  # exclude depot


def _euc_distance(x1: float, y1: float, x2: float, y2: float) -> int:
    """Euclidean distance rounded to nearest integer (Solomon convention)."""
    return round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))


def parse_solomon_file(filepath: Path) -> SolomonInstance:
    """Parse a Solomon-format CVRPTW instance file."""
    lines = filepath.read_text(encoding="utf-8").splitlines()

    # Strip empty lines and comments for robust parsing
    nonempty = [line.strip() for line in lines if line.strip()]

    name = nonempty[0]

    # Find VEHICLE section
    vehicle_idx = next(i for i, l in enumerate(nonempty) if l.upper().startswith("VEHICLE"))
    # Skip "NUMBER  CAPACITY" header
    n_vehicles, capacity = (int(v) for v in nonempty[vehicle_idx + 2].split())

    # Find CUSTOMER section
    customer_idx = next(i for i, l in enumerate(nonempty) if l.upper().startswith("CUSTOMER"))
    # Skip "CUST NO.  XCOORD. ..." header line
    data_start = customer_idx + 2

    x_coords: list[float] = []
    y_coords: list[float] = []
    demands: list[int] = []
    ready_times: list[int] = []
    due_dates: list[int] = []
    service_times: list[int] = []

    for line in nonempty[data_start:]:
        parts = line.split()
        if not parts:
            continue
        # cust_no x y demand ready_time due_date service_time
        x_coords.append(float(parts[1]))
        y_coords.append(float(parts[2]))
        demands.append(int(parts[3]))
        ready_times.append(int(parts[4]))
        due_dates.append(int(parts[5]))
        service_times.append(int(parts[6]))

    return SolomonInstance(
        name=name,
        n_vehicles=n_vehicles,
        capacity=capacity,
        x=x_coords,
        y=y_coords,
        demand=demands,
        ready_time=ready_times,
        due_date=due_dates,
        service_time=service_times,
    )


def generate_optdsl(inst: SolomonInstance) -> str:
    """Generate OptDSL code for a CVRPTW instance.

    Uses an arc-based formulation:
    - x[i,j,k] = 1 if vehicle k travels directly from node i to node j
    - t[i,k] = arrival time of vehicle k at node i
    - Constraints: time windows, capacity, subtour elimination via time
    - Objective: minimize total travel distance
    """
    n = inst.n_customers
    num_nodes = n + 1  # depot (0) + customers (1..n)
    K = inst.n_vehicles

    # Precompute integer distance matrix
    dist: list[list[int]] = [
        [_euc_distance(inst.x[i], inst.y[i], inst.x[j], inst.y[j]) for j in range(num_nodes)]
        for i in range(num_nodes)
    ]

    max_dist = max(max(row) for row in dist) + 1
    horizon = max(inst.due_date) + max(inst.service_time) + max_dist + 1
    max_total_dist = sum(max(row) for row in dist) * K + 1

    lines: list[str] = []
    lines.append(f"# CVRPTW instance: {inst.name}")
    lines.append(f"# {n} customers, {K} vehicles, capacity {inst.capacity}")
    lines.append(f"# Horizon: {horizon}, Max total dist: {max_total_dist}")
    lines.append("")

    # Constants
    lines.append(f"N_CUSTOMERS : int = {n}")
    lines.append(f"N_VEHICLES : int = {K}")
    lines.append(f"CAPACITY : int = {inst.capacity}")
    lines.append(f"HORIZON : int = {horizon}")
    lines.append("")

    # Distance matrix (flattened: dist[i * num_nodes + j])
    dist_flat = [dist[i][j] for i in range(num_nodes) for j in range(num_nodes)]
    dist_str = ", ".join(str(v) for v in dist_flat)
    lines.append(f"DIST : DSList({num_nodes * num_nodes}, int) = [{dist_str}]")
    lines.append("")

    # Demand array (customers 1..n, 0 = depot demand = 0)
    demand_str = ", ".join(str(inst.demand[i]) for i in range(num_nodes))
    lines.append(f"DEMAND : DSList({num_nodes}, int) = [{demand_str}]")
    lines.append("")

    # Time window arrays
    ready_str = ", ".join(str(inst.ready_time[i]) for i in range(num_nodes))
    due_str = ", ".join(str(inst.due_date[i]) for i in range(num_nodes))
    service_str = ", ".join(str(inst.service_time[i]) for i in range(num_nodes))
    lines.append(f"READY_TIME : DSList({num_nodes}, int) = [{ready_str}]")
    lines.append(f"DUE_DATE : DSList({num_nodes}, int) = [{due_str}]")
    lines.append(f"SERVICE_TIME : DSList({num_nodes}, int) = [{service_str}]")
    lines.append("")

    # Decision variables
    lines.append("# arc[i * num_nodes * K + j * K + k] = 1 if vehicle k travels i→j")
    lines.append(f"arc : DSList({num_nodes * num_nodes * K}, DSInt(0, 1))")
    lines.append("# arrival_time[i * K + k] = time vehicle k arrives at node i")
    lines.append(f"arrival_time : DSList({num_nodes * K}, DSInt(0, {horizon}))")
    lines.append("# load[i * K + k] = cumulative load of vehicle k after visiting node i")
    lines.append(f"load : DSList({num_nodes * K}, DSInt(0, {inst.capacity}))")
    lines.append("")

    # Objective: minimize total distance
    lines.append(f"total_dist : DSInt(0, {max_total_dist}) = 0")
    lines.append("")
    lines.append("# Compute total distance")
    lines.append(f"for i in range(0, {num_nodes}):")
    lines.append(f"    for j in range(0, {num_nodes}):")
    lines.append(f"        for k in range(0, {K}):")
    lines.append("            if i != j:")
    lines.append(f"                total_dist = total_dist + arc[i * {num_nodes * K} + j * {K} + k] * DIST[i * {num_nodes} + j]")
    lines.append("")

    # Each customer visited exactly once
    lines.append("# Each customer visited exactly once across all vehicles")
    lines.append(f"for j in range(1, {num_nodes}):")
    lines.append(f"    visits_j : DSInt(0, {K}) = 0")
    lines.append(f"    for k in range(0, {K}):")
    lines.append(f"        for i in range(0, {num_nodes}):")
    lines.append("            if i != j:")
    lines.append(f"                visits_j = visits_j + arc[i * {num_nodes * K} + j * {K} + k]")
    lines.append("    assert visits_j == 1")
    lines.append("")

    # Flow conservation
    lines.append("# Flow conservation: in-flow = out-flow for each vehicle at each node")
    lines.append(f"for k in range(0, {K}):")
    lines.append(f"    for node in range(0, {num_nodes}):")
    lines.append(f"        flow_in : DSInt(0, {num_nodes}) = 0")
    lines.append(f"        flow_out : DSInt(0, {num_nodes}) = 0")
    lines.append(f"        for j in range(0, {num_nodes}):")
    lines.append("            if j != node:")
    lines.append(f"                flow_in = flow_in + arc[j * {num_nodes * K} + node * {K} + k]")
    lines.append(f"                flow_out = flow_out + arc[node * {num_nodes * K} + j * {K} + k]")
    lines.append("        assert flow_in == flow_out")
    lines.append("")

    # No self-loops
    lines.append("# Prevent self-loops")
    lines.append(f"for i in range(0, {num_nodes}):")
    lines.append(f"    for k in range(0, {K}):")
    lines.append(f"        assert arc[i * {num_nodes * K} + i * {K} + k] == 0")
    lines.append("")

    # Capacity constraints (via load variable)
    lines.append("# Capacity and time window constraints via load tracking")
    lines.append(f"for k in range(0, {K}):")
    lines.append(f"    for j in range(1, {num_nodes}):")
    lines.append(f"        for i in range(0, {num_nodes}):")
    lines.append("            if i != j:")
    lines.append(f"                if arc[i * {num_nodes * K} + j * {K} + k] == 1:")
    lines.append(f"                    assert load[j * {K} + k] >= load[i * {K} + k] + DEMAND[j]")
    lines.append(f"                    assert load[j * {K} + k] <= {inst.capacity}")
    lines.append("")

    # Time window constraints (arrival time propagation)
    lines.append("# Time window propagation and enforcement")
    lines.append(f"for k in range(0, {K}):")
    lines.append(f"    for j in range(1, {num_nodes}):")
    lines.append(f"        for i in range(0, {num_nodes}):")
    lines.append("            if i != j:")
    lines.append(f"                if arc[i * {num_nodes * K} + j * {K} + k] == 1:")
    lines.append(f"                    depart_i : DSInt(0, {horizon}) = arrival_time[i * {K} + k] + SERVICE_TIME[i]")
    lines.append(f"                    earliest_j : DSInt(0, {horizon}) = depart_i + DIST[i * {num_nodes} + j]")
    lines.append(f"                    assert arrival_time[j * {K} + k] >= READY_TIME[j]")
    lines.append(f"                    assert arrival_time[j * {K} + k] <= DUE_DATE[j]")
    lines.append(f"                    assert arrival_time[j * {K} + k] >= earliest_j")
    lines.append("")

    # Depot time window
    lines.append("# Depot time windows for all vehicles")
    lines.append(f"for k in range(0, {K}):")
    lines.append(f"    assert arrival_time[0 * {K} + k] >= READY_TIME[0]")
    lines.append(f"    assert arrival_time[0 * {K} + k] <= DUE_DATE[0]")
    lines.append("")

    lines.append("minimize(total_dist)")
    lines.append("")

    return "\n".join(lines)


def convert_single(input_file: Path, output_file: Path) -> bool:
    """Convert a single Solomon CVRPTW file to OptDSL. Returns True on success."""
    try:
        inst = parse_solomon_file(input_file)
        dsl = generate_optdsl(inst)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(dsl, encoding="utf-8")
        print(f"  ✓ {input_file.name} → {output_file.name}")
        print(f"    Customers: {inst.n_customers}, Vehicles: {inst.n_vehicles}, Capacity: {inst.capacity}")
        return True
    except Exception as exc:
        print(f"  ✗ {input_file.name}: {exc}")
        return False


def convert_batch(input_dir: Path, output_dir: Path) -> None:
    """Convert all .txt files in input_dir to OptDSL in output_dir."""
    files = sorted(input_dir.glob("*.txt"))
    if not files:
        print(f"No .txt files found in {input_dir}")
        return
    print(f"Converting {len(files)} Solomon CVRPTW files...")
    ok = sum(convert_single(f, output_dir / f.with_suffix(".dsl").name) for f in files)
    print(f"\nDone: {ok}/{len(files)} converted successfully.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Solomon CVRPTW benchmark files (.txt) to OptDSL format (.dsl)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input-dir", type=Path, help="Input directory containing .txt files (batch mode)")
    group.add_argument("--input-file", type=Path, help="Single input file (.txt) to convert")
    parser.add_argument("--output-dir", type=Path, help="Output directory for batch conversion (required with --input-dir)")
    parser.add_argument("--output-file", type=Path, help="Output file for single conversion (required with --input-file)")

    args = parser.parse_args()

    if args.input_dir:
        if not args.output_dir:
            parser.error("--output-dir is required with --input-dir")
        if not args.input_dir.exists():
            parser.error(f"Input directory does not exist: {args.input_dir}")
        convert_batch(args.input_dir, args.output_dir)
    else:
        if not args.output_file:
            parser.error("--output-file is required with --input-file")
        if not args.input_file.exists():
            parser.error(f"Input file does not exist: {args.input_file}")
        convert_single(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
