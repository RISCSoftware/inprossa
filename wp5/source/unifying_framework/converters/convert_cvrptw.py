"""Convert CVRPTW Solomon benchmark files (.txt) to OptDSL format (.dsl).

Solomon CVRPTW format:
  INSTANCE_NAME

  VEHICLE
  NUMBER     CAPACITY
    25         200

  CUSTOMER
  CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE TIME

      0      40         50          0          0       1236          0
      1      45          68         10        912        967         90
      ...

The depot is customer 0.

Model
-----
Arc-based formulation with explicit time propagation:

  arc[i * NUM_NODES * K + j * K + k]   = 1 if vehicle k travels i -> j
  arrival_time[(c - 1) * K + k]        = arrival time of vehicle k at customer c
  departure_time[(c - 1) * K + k]      = departure time of vehicle k from customer c
  load[(c - 1) * K + k]                = load of vehicle k when leaving customer c
  route_start[k] / route_end[k]        = depot departure / return time of vehicle k

Every constraint is emitted as a top-level ``def`` function.  This is required by
the LNS backend: ``OptDSLImporter`` only collects ``ast.FunctionDef`` nodes as
constraints, so a model written as bare top-level ``for``/``assert`` statements
is invisible to the evaluator and every candidate is scored as infeasible.

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

    All constraints are emitted as ``def`` functions so the LNS importer can
    collect them (see the module docstring).
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

    dist_flat = [dist[i][j] for i in range(num_nodes) for j in range(num_nodes)]

    lines: list[str] = []
    lines.append(f"# CVRPTW instance: {inst.name}")
    lines.append(f"# {n} customers, {K} vehicles, capacity {inst.capacity}")
    lines.append(f"# Horizon: {horizon}, Max total dist: {max_total_dist}")
    lines.append("")

    # Constants
    lines.append(f"N_CUSTOMERS : int = {n}")
    lines.append(f"N_VEHICLES : int = {K}")
    lines.append("NUM_NODES : int = N_CUSTOMERS + 1")
    lines.append(f"CAPACITY : int = {inst.capacity}")
    lines.append(f"HORIZON : int = {horizon}")
    lines.append(f"MAX_TOTAL_DIST : int = {max_total_dist}")
    lines.append("N_ARCS : int = NUM_NODES * NUM_NODES * N_VEHICLES")
    lines.append("N_CUSTOMER_SLOTS : int = N_CUSTOMERS * N_VEHICLES")
    lines.append("")

    # Instance data
    lines.append(f"DIST : DSList(NUM_NODES * NUM_NODES, DSInt()) = [{', '.join(str(v) for v in dist_flat)}]")
    lines.append(f"DEMAND : DSList(NUM_NODES, DSInt()) = [{', '.join(str(v) for v in inst.demand)}]")
    lines.append(f"READY_TIME : DSList(NUM_NODES, DSInt()) = [{', '.join(str(v) for v in inst.ready_time)}]")
    lines.append(f"DUE_DATE : DSList(NUM_NODES, DSInt()) = [{', '.join(str(v) for v in inst.due_date)}]")
    lines.append(f"SERVICE_TIME : DSList(NUM_NODES, DSInt()) = [{', '.join(str(v) for v in inst.service_time)}]")
    lines.append("")

    # Decision variables
    lines.append("# arc[i * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k] = 1 if vehicle k travels i -> j")
    lines.append("arc : DSList(N_ARCS, DSInt(0, 1))")
    lines.append("# Customer-indexed slots: (customer - 1) * N_VEHICLES + k")
    lines.append("arrival_time : DSList(N_CUSTOMER_SLOTS, DSInt(0, HORIZON))")
    lines.append("departure_time : DSList(N_CUSTOMER_SLOTS, DSInt(0, HORIZON))")
    lines.append("load : DSList(N_CUSTOMER_SLOTS, DSInt(0, CAPACITY))")
    lines.append("# Depot departure / return time per vehicle")
    lines.append("route_start : DSList(N_VEHICLES, DSInt(0, HORIZON))")
    lines.append("route_end : DSList(N_VEHICLES, DSInt(0, HORIZON))")
    lines.append("")

    # --- Constraints -------------------------------------------------------
    lines.append("")
    lines.append("def all_customers_visited(arc: DSList(N_ARCS, DSInt(0, 1))):")
    lines.append("    # Every customer is entered exactly once across all vehicles.")
    lines.append("    for c in range(1, NUM_NODES):")
    lines.append("        visits = 0")
    lines.append("        for k in range(N_VEHICLES):")
    lines.append("            for i in range(NUM_NODES):")
    lines.append("                if i != c:")
    lines.append("                    visits = visits + arc[i * NUM_NODES * N_VEHICLES + c * N_VEHICLES + k]")
    lines.append("        assert visits == 1")
    lines.append("")
    lines.append("")
    lines.append("def flow_conservation(arc: DSList(N_ARCS, DSInt(0, 1))):")
    lines.append("    # A vehicle entering a customer must also leave it.")
    lines.append("    for k in range(N_VEHICLES):")
    lines.append("        for c in range(1, NUM_NODES):")
    lines.append("            incoming = 0")
    lines.append("            outgoing = 0")
    lines.append("            for i in range(NUM_NODES):")
    lines.append("                if i != c:")
    lines.append("                    incoming = incoming + arc[i * NUM_NODES * N_VEHICLES + c * N_VEHICLES + k]")
    lines.append("                    outgoing = outgoing + arc[c * NUM_NODES * N_VEHICLES + i * N_VEHICLES + k]")
    lines.append("            assert incoming == outgoing")
    lines.append("")
    lines.append("")
    lines.append("def no_self_loops(arc: DSList(N_ARCS, DSInt(0, 1))):")
    lines.append("    for k in range(N_VEHICLES):")
    lines.append("        for i in range(NUM_NODES):")
    lines.append("            assert arc[i * NUM_NODES * N_VEHICLES + i * N_VEHICLES + k] == 0")
    lines.append("")
    lines.append("")
    lines.append("def depot_balance(arc: DSList(N_ARCS, DSInt(0, 1))):")
    lines.append("    # Each vehicle leaves the depot at most once and must return.")
    lines.append("    for k in range(N_VEHICLES):")
    lines.append("        departures = 0")
    lines.append("        returns = 0")
    lines.append("        for j in range(1, NUM_NODES):")
    lines.append("            departures = departures + arc[0 * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k]")
    lines.append("            returns = returns + arc[j * NUM_NODES * N_VEHICLES + 0 * N_VEHICLES + k]")
    lines.append("        assert departures <= 1")
    lines.append("        assert returns == departures")
    lines.append("")
    lines.append("")
    lines.append("def capacity_constraints(")
    lines.append("    arc: DSList(N_ARCS, DSInt(0, 1)),")
    lines.append("    load: DSList(N_CUSTOMER_SLOTS, DSInt(0, CAPACITY))")
    lines.append("):")
    lines.append("    # Cumulative load along each route never exceeds the vehicle capacity.")
    lines.append("    for k in range(N_VEHICLES):")
    lines.append("        for j in range(1, NUM_NODES):")
    lines.append("            slot_j = (j - 1) * N_VEHICLES + k")
    lines.append("            if arc[0 * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k] == 1:")
    lines.append("                assert load[slot_j] >= DEMAND[j]")
    lines.append("            for i in range(1, NUM_NODES):")
    lines.append("                if i != j:")
    lines.append("                    if arc[i * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k] == 1:")
    lines.append("                        assert load[slot_j] >= load[(i - 1) * N_VEHICLES + k] + DEMAND[j]")
    lines.append("            assert load[slot_j] <= CAPACITY")
    lines.append("")
    lines.append("")
    lines.append("def time_windows(")
    lines.append("    arc: DSList(N_ARCS, DSInt(0, 1)),")
    lines.append("    arrival_time: DSList(N_CUSTOMER_SLOTS, DSInt(0, HORIZON)),")
    lines.append("    departure_time: DSList(N_CUSTOMER_SLOTS, DSInt(0, HORIZON)),")
    lines.append("    route_start: DSList(N_VEHICLES, DSInt(0, HORIZON)),")
    lines.append("    route_end: DSList(N_VEHICLES, DSInt(0, HORIZON))")
    lines.append("):")
    lines.append("    # Arrival/departure propagation plus the depot return leg.")
    lines.append("    # Time-window bounds only apply to customers actually served by the")
    lines.append("    # vehicle: an unused slot keeps its default value and must not be")
    lines.append("    # forced into the customer's window.")
    lines.append("    for k in range(N_VEHICLES):")
    lines.append("        assert route_start[k] >= READY_TIME[0]")
    lines.append("        assert route_start[k] <= DUE_DATE[0]")
    lines.append("        assert route_end[k] >= route_start[k]")
    lines.append("        assert route_end[k] <= DUE_DATE[0]")
    lines.append("        for j in range(1, NUM_NODES):")
    lines.append("            slot_j = (j - 1) * N_VEHICLES + k")
    lines.append("            visited = 0")
    lines.append("            for i in range(NUM_NODES):")
    lines.append("                if i != j:")
    lines.append("                    visited = visited + arc[i * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k]")
    lines.append("            if visited == 1:")
    lines.append("                assert arrival_time[slot_j] >= READY_TIME[j]")
    lines.append("                assert arrival_time[slot_j] <= DUE_DATE[j]")
    lines.append("                assert departure_time[slot_j] >= arrival_time[slot_j] + SERVICE_TIME[j]")
    lines.append("                assert departure_time[slot_j] <= DUE_DATE[j] + SERVICE_TIME[j]")
    lines.append("                if arc[0 * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k] == 1:")
    lines.append("                    assert arrival_time[slot_j] >= route_start[k] + DIST[0 * NUM_NODES + j]")
    lines.append("                for i in range(1, NUM_NODES):")
    lines.append("                    if i != j:")
    lines.append("                        if arc[i * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k] == 1:")
    lines.append("                            assert arrival_time[slot_j] >= departure_time[(i - 1) * N_VEHICLES + k] + DIST[i * NUM_NODES + j]")
    lines.append("                if arc[j * NUM_NODES * N_VEHICLES + 0 * N_VEHICLES + k] == 1:")
    lines.append("                    assert route_end[k] >= departure_time[slot_j] + DIST[j * NUM_NODES + 0]")
    lines.append("")
    lines.append("")
    lines.append("def total_distance(arc: DSList(N_ARCS, DSInt(0, 1))):")
    lines.append("    dist = 0")
    lines.append("    for k in range(N_VEHICLES):")
    lines.append("        for i in range(NUM_NODES):")
    lines.append("            for j in range(NUM_NODES):")
    lines.append("                if i != j:")
    lines.append("                    dist = dist + DIST[i * NUM_NODES + j] * arc[i * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k]")
    lines.append("    return dist")
    lines.append("")
    lines.append("")
    lines.append("all_customers_visited(arc)")
    lines.append("flow_conservation(arc)")
    lines.append("no_self_loops(arc)")
    lines.append("depot_balance(arc)")
    lines.append("capacity_constraints(arc, load)")
    lines.append("time_windows(arc, arrival_time, departure_time, route_start, route_end)")
    lines.append("")
    lines.append("objective: DSInt(0, MAX_TOTAL_DIST) = total_distance(arc)")
    lines.append("")
    lines.append("minimize(objective)")
    lines.append("")

    return "\n".join(lines)


def convert_single(input_file: Path, output_file: Path) -> bool:
    """Convert a single Solomon CVRPTW file to OptDSL. Returns True on success."""
    try:
        inst = parse_solomon_file(input_file)
        dsl = generate_optdsl(inst)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(dsl, encoding="utf-8")
        print(f"  [OK] {input_file.name} -> {output_file.name}")
        print(f"    Customers: {inst.n_customers}, Vehicles: {inst.n_vehicles}, Capacity: {inst.capacity}")
        return True
    except Exception as exc:
        print(f"  [FAIL] {input_file.name}: {exc}")
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
