#!/usr/bin/env python
"""Convert standard JSSP benchmark files (.txt) to OptDSL format (.dsl).

Usage:
  # Batch conversion
  python convert_jssp.py --input-dir <dir> --output-dir <dir> --format txt
  
  # Single file conversion
  python convert_jssp.py --input-file instance.txt --output-file instance.dsl --format txt

Standard JSSP .txt format (e.g., Fisher-Thompson, Taillard):
  # Line 1: n_jobs n_machines
  # Lines 2+: For each job: machine_1 time_1 machine_2 time_2 ...
  
Example (3x3 JSSP):
  3 3
  0 3 1 2 2 4
  1 4 2 3 0 5
  2 2 0 3 1 6

This defines:
  Job 0: Op1(M0,3), Op2(M1,2), Op3(M2,4)
  Job 1: Op1(M1,4), Op2(M2,3), Op3(M0,5)
  Job 2: Op1(M2,2), Op2(M0,3), Op3(M1,6)

Indexing convention
--------------------
``PROCESSING_TIMES[job][machine]`` is indexed by MACHINE ID, not by operation
position.  ``MACHINE_SEQUENCE[job][op]`` gives the machine used by operation
``op``, so the processing time of that operation is
``PROCESSING_TIMES[job][MACHINE_SEQUENCE[job][op]]``.

This matches the hand-written instances (``jssp_2x2.dsl``, ``jssp_5x4.dsl``,
``jssp_10x5.dsl``) and the LNS operators in
``large_neighborhood_search/problems/jssp.py`` and ``jssp_optdsl.py``, which all
read ``pt_matrix[job][machine]``.  Emitting operation-position-indexed times
would silently permute the processing times for every instance whose machine
sequence is not the identity, producing a different (easier) problem.

Because the encoding stores one processing time per (job, machine) pair, each
job's machine sequence must be a permutation of ``0..n_machines-1``.  Instances
that visit a machine twice are rejected.

Objective: Minimize total makespan (time to complete all jobs).
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_jssp_txt(filepath: str) -> dict:
    """Parse standard JSSP .txt file format.
    
    Returns:
        Dict with 'n_jobs', 'n_machines', 'operations' (list of jobs, each a list of (machine, time) tuples)
    """
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    # First line: n_jobs n_machines
    if not lines:
        raise ValueError("Empty file")

    parts = lines[0].split()
    if len(parts) < 2:
        raise ValueError(f"First line must be: n_jobs n_machines, got: {lines[0]}")

    n_jobs = int(parts[0])
    n_machines = int(parts[1])

    operations = []
    for job_idx in range(1, len(lines)):
        if not lines[job_idx] or lines[job_idx].startswith("#"):
            continue

        parts = lines[job_idx].split()
        if len(parts) < 2 * n_machines:
            raise ValueError(f"Job {job_idx - 1}: expected {2 * n_machines} values, got {len(parts)}")

        job_ops = []
        for i in range(0, len(parts), 2):
            machine = int(parts[i])
            time = int(parts[i + 1])
            job_ops.append((machine, time))

        operations.append(job_ops)

    if len(operations) != n_jobs:
        raise ValueError(f"Expected {n_jobs} jobs, found {len(operations)}")

    # The machine-indexed encoding needs exactly one processing time per
    # (job, machine) pair, so every job must visit each machine exactly once.
    expected_machines = set(range(n_machines))
    for job_idx, job_ops in enumerate(operations):
        machines = [machine for machine, _ in job_ops]
        if len(machines) != n_machines:
            raise ValueError(
                f"Job {job_idx}: expected {n_machines} operations, got {len(machines)}"
            )
        if set(machines) != expected_machines:
            duplicates = sorted({m for m in machines if machines.count(m) > 1})
            raise ValueError(
                f"Job {job_idx}: machine sequence {machines} is not a permutation of "
                f"0..{n_machines - 1} (repeated machines: {duplicates}); "
                "machine-indexed PROCESSING_TIMES cannot represent this instance"
            )

    return {
        "n_jobs": n_jobs,
        "n_machines": n_machines,
        "operations": operations,
    }


def generate_optdsl(
    n_jobs: int,
    n_machines: int,
    operations: list[list[tuple[int, int]]],
    name: str = "jssp",
) -> str:
    """Generate OptDSL content for JSSP instance.
    
    Args:
        n_jobs: Number of jobs
        n_machines: Number of machines
        operations: List of jobs; each job is a list of (machine, processing_time) tuples
        name: Instance name
    
    Returns:
        OptDSL content as string
    """
    max_time = sum(t for job in operations for _, t in job) if operations else 100

    # Matrix representation expected by the existing JSSP LNS operators:
    # PROCESSING_TIMES[job][machine] (machine-indexed) and
    # MACHINE_SEQUENCE[job][op] (operation-position indexed).
    processing_times = [[0] * n_machines for _ in range(n_jobs)]
    for job_idx, job_ops in enumerate(operations):
        for machine, time in job_ops:
            processing_times[job_idx][machine] = time
    machine_sequence = [[machine for machine, _ in job] for job in operations]

    problem_name = name.replace(" ", "_").replace("/", "_")

    template = f"""# Job Shop Scheduling instance: {problem_name}
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = {n_jobs}
N_MACHINES : int = {n_machines}
MAX_TIME : int = {max_time}

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = {processing_times}
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = {machine_sequence}

# Decision variable: completion time of operation op for each job.
completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))


def precedence_constraint(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))):
    # Each job's operations must respect sequence order with processing times.
    for j in range(N_JOBS):
        assert completion[j][0] >= PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][0]]
        for op in range(1, N_MACHINES):
            assert completion[j][op] >= completion[j][op - 1] + PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]


def no_overlap_constraint(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))):
    # No two jobs can use the same machine at overlapping times.
    for m in range(N_MACHINES):
        for j1 in range(N_JOBS):
            for op1 in range(N_MACHINES):
                if MACHINE_SEQUENCE[j1][op1] == m:
                    for j2 in range(j1 + 1, N_JOBS):
                        for op2 in range(N_MACHINES):
                            if MACHINE_SEQUENCE[j2][op2] == m:
                                assert (
                                    completion[j1][op1] >= completion[j2][op2] + PROCESSING_TIMES[j1][m]
                                    or completion[j2][op2] >= completion[j1][op1] + PROCESSING_TIMES[j2][m]
                                )


def makespan(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))):
    ms: DSInt() = 0
    for j in range(N_JOBS):
        if completion[j][N_MACHINES - 1] > ms:
            ms = completion[j][N_MACHINES - 1]
    return ms


precedence_constraint(completion)
no_overlap_constraint(completion)

objective: DSInt(0, MAX_TIME) = makespan(completion)

minimize(objective)
"""

    return template


def convert_single(input_file: str, output_file: str, format: str = "txt") -> bool:
    """Convert a single JSSP file.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if format == "txt":
            data = parse_jssp_txt(input_file)
        else:
            raise ValueError(f"Unsupported format: {format}")

        optdsl = generate_optdsl(
            n_jobs=data["n_jobs"],
            n_machines=data["n_machines"],
            operations=data["operations"],
            name=Path(input_file).stem,
        )
        Path(output_file).write_text(optdsl, encoding="utf-8")
        total_time = sum(t for job_ops in data["operations"] for _, t in job_ops)
        print(f"  ✓ {Path(input_file).name} → {Path(output_file).name}")
        print(f"    Jobs: {data['n_jobs']}, Machines: {data['n_machines']}, Total processing time: {total_time}")
        return True
    except Exception as e:
        print(f"  ✗ {Path(input_file).name}: {e}")
        return False


def convert_batch(input_dir: str, output_dir: str, format: str = "txt") -> int:
    """Convert all matching files in input_dir to output_dir.
    
    Returns:
        Number of files successfully converted
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_pattern = f"*.{format}"
    input_files = sorted(input_path.glob(file_pattern))
    if not input_files:
        print(f"No {file_pattern} files found in {input_dir}")
        return 0

    print(f"Converting {len(input_files)} JSSP files...")
    success_count = 0

    for input_file in input_files:
        output_file = output_path / f"{input_file.stem}.dsl"
        if convert_single(str(input_file), str(output_file), format=format):
            success_count += 1

    print(f"\nConversion complete: {success_count}/{len(input_files)} files converted to {output_dir}")
    return success_count


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert JSSP benchmark files (.txt) to OptDSL format (.dsl)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--input-dir",
        help="Input directory containing benchmark files (batch mode)",
    )
    mode_group.add_argument(
        "--input-file",
        help="Single input file to convert",
    )
    
    parser.add_argument(
        "--output-dir",
        help="Output directory for batch conversion (required with --input-dir)",
    )
    parser.add_argument(
        "--output-file",
        help="Output file for single conversion (required with --input-file)",
    )
    parser.add_argument(
        "--format",
        default="txt",
        choices=["txt"],
        help="Input file format (default: txt)",
    )
    
    args = parser.parse_args()
    
    # Batch mode
    if args.input_dir:
        if not args.output_dir:
            parser.error("--output-dir required with --input-dir")
        convert_batch(args.input_dir, args.output_dir, format=args.format)
    
    # Single file mode
    elif args.input_file:
        if not args.output_file:
            parser.error("--output-file required with --input-file")
        if not Path(args.input_file).exists():
            parser.error(f"Input file not found: {args.input_file}")
        success = convert_single(args.input_file, args.output_file, format=args.format)
        exit(0 if success else 1)


if __name__ == "__main__":
    main()
