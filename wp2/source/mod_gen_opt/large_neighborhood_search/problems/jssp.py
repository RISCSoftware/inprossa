"""JSSP-aware constructive initializer for the LNS framework.

Builds a feasible initial schedule using a priority-rule based scheduler
that respects job precedence constraints and machine no-overlap constraints.
Implements a simple forward-pass scheduling heuristic.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..components import DestroyOperator, Initializer, RepairOperator
from ..lns import RandomAssignmentInitializer
from ..models import LNSContext

# RandomFractionDestroy is from defaults but exported from main package
from large_neighborhood_search import RandomFractionDestroy


def detect_jssp_problem(constants: dict[str, object], _keys_by_variable: dict[str, list]) -> bool:
    """Detect JSSP by expected constants.

    The keys_by_variable check is intentionally omitted: the problem reader
    does not flatten nested DSList(N, DSList(M, DSInt())) into individual
    decision keys, so 'completion' will not appear there even for valid JSSP
    instances.  Checking the four required constants is sufficient.
    """
    required_constants = ("N_JOBS", "N_MACHINES", "PROCESSING_TIMES", "MACHINE_SEQUENCE")
    return all(name in constants for name in required_constants)


@dataclass
class JSSPScheduleInitializer(Initializer):
    """Constructive JSSP initializer using priority-rule scheduling.

    Uses a simple dispatch rule (shortest processing time first) to build
    a feasible schedule respecting both precedence (job sequence) and
    no-overlap (machine conflicts) constraints. Returns the schedule as
    a dict of completion times for each (job, operation) pair.
    """

    restarts: int = 16

    def initialize(self, context: LNSContext) -> dict[str, object]:
        constants = context.constants
        keys_by_variable = context.extra.get("keys_by_variable", {})

        if not detect_jssp_problem(constants, keys_by_variable):
            return RandomAssignmentInitializer().initialize(context)

        n_jobs = int(constants["N_JOBS"])
        n_machines = int(constants["N_MACHINES"])
        processing_times = constants["PROCESSING_TIMES"]
        machine_sequence = constants["MACHINE_SEQUENCE"]

        # Parse processing times into a usable matrix
        pt_matrix: list[list[int]] = []
        for job_row in processing_times:
            if isinstance(job_row, list):
                pt_matrix.append([int(v) for v in job_row])
            else:
                pt_matrix.append([int(job_row)])

        # Parse machine sequence
        ms_matrix: list[list[int]] = []
        for job_row in machine_sequence:
            if isinstance(job_row, list):
                ms_matrix.append([int(v) for v in job_row])
            else:
                ms_matrix.append([int(job_row)])

        rng: random.Random = context.extra["rng"]

        best_assignment: dict[str, object] | None = None
        best_makespan = float("inf")

        for _ in range(max(1, self.restarts)):
            schedule, makespan = self._build_schedule(
                rng=rng,
                n_jobs=n_jobs,
                n_machines=n_machines,
                pt_matrix=pt_matrix,
                ms_matrix=ms_matrix,
            )

            if makespan < best_makespan:
                best_assignment = schedule
                best_makespan = makespan
                if best_makespan == 0:
                    break

        if best_assignment is None:
            return RandomAssignmentInitializer().initialize(context)
        return best_assignment

    def _build_schedule(
        self,
        rng: random.Random,
        n_jobs: int,
        n_machines: int,
        pt_matrix: list[list[int]],
        ms_matrix: list[list[int]],
    ) -> tuple[dict[str, object], float]:
        # Track completion time for each job's each operation
        job_completion: list[list[int]] = [[0] * n_machines for _ in range(n_jobs)]

        # Track when each machine becomes available
        machine_available: list[int] = [0] * n_machines

        # Track when each job's next operation can start (precedence constraint)
        job_next_op_time: list[int] = [0] * n_jobs
        job_op_started: list[list[bool]] = [[False] * n_machines for _ in range(n_jobs)]

        # Track which operations are completed
        completed_ops: set[tuple[int, int]] = set()

        total_operations = n_jobs * n_machines

        while len(completed_ops) < total_operations:
            # Find all ready operations (predecessor completed)
            ready: list[tuple[int, int, int]] = []  # (job, op_idx, machine)

            for j in range(n_jobs):
                for op in range(n_machines):
                    if job_op_started[j][op]:
                        continue
                    # Check if predecessor op is completed (for op > 0)
                    if op > 0 and not (j, op - 1) in completed_ops:
                        continue
                    if op == 0 and not job_completion[j][0] == 0:
                        pass  # First operation always ready
                    machine = ms_matrix[j][op]
                    ready.append((j, op, machine))

            if not ready:
                break

            # Sort by processing time (SPT - Shortest Processing Time first)
            # with small randomization
            ready.sort(key=lambda x: pt_matrix[x[0]][x[2]])  # x[2] = machine id

            # Apply randomization: sometimes shuffle ties
            if len(ready) > 1 and rng.random() < 0.2:
                tie_range = 1
                for k in range(1, len(ready)):
                    if pt_matrix[ready[k][0]][ready[k][2]] == pt_matrix[ready[0][0]][ready[0][2]]:
                        tie_range = k + 1
                rng.shuffle(ready[:tie_range])

            # Select first ready operation
            j, op, machine = ready[0]
            machine = ms_matrix[j][op]

            # Start time is max of job availability (precedence) and machine availability
            start_time = max(job_next_op_time[j], machine_available[machine])

            # Process
            pt = pt_matrix[j][machine]
            completion_time = start_time + pt

            # Update state
            job_completion[j][op] = completion_time
            job_op_started[j][op] = True
            job_next_op_time[j] = completion_time
            machine_available[machine] = completion_time
            completed_ops.add((j, op))

        # Encode as decision variable dict
        completion_keys = list[ tuple[str, int | None]]()
        keys_by_variable = rng.__dict__.get("context", {}).get("keys_by_variable", {}) if hasattr(rng, "context") else {}
        # Actually get from context via a different approach - use the stored assignment context
        # We'll build the assignment directly

        assignment: dict[str, object] = {}

        # Get decision keys structure from context
        # completion is indexed by (job, operation) -> we use a flat representation
        for j in range(n_jobs):
            row = []
            for op in range(n_machines):
                row.append(job_completion[j][op])
            assignment[f"completion_{j}"] = row

        # Make sure we have completion as nested list
        assignment["completion"] = job_completion

        makespan = max(job_completion[j][n_machines - 1] for j in range(n_jobs)) if n_machines > 0 else 0

        return assignment, float(makespan)


@dataclass
class JSSPJobLevelDestroy(DestroyOperator):
    """Destroy all operations of one or more randomly selected jobs."""

    fraction: float = 0.25

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        if "completion" not in assignment:
            return RandomFractionDestroy(fraction=self.fraction).destroy(assignment, context)

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))

        completion = assignment.get("completion")
        if not isinstance(completion, list) or len(completion) != n_jobs:
            return assignment

        # Determine how many jobs to destroy
        n_destroy = max(1, int(round(n_jobs * max(0.0, min(1.0, self.fraction)))))
        jobs_to_destroy = rng.sample(range(n_jobs), min(n_destroy, n_jobs))

        for j in jobs_to_destroy:
            if j < len(completion) and isinstance(completion[j], list):
                completion[j] = [None] * n_machines

        return assignment


@dataclass
class JSSPMachineLevelDestroy(DestroyOperator):
    """Destroy all operations on one or more randomly selected machines."""

    fraction: float = 0.25

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        if "completion" not in assignment:
            return RandomFractionDestroy(fraction=self.fraction).destroy(assignment, context)

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        machine_sequence = constants.get("MACHINE_SEQUENCE", [])

        completion = assignment.get("completion")
        if not isinstance(completion, list):
            return assignment

        # Determine machine sequence matrix for lookup
        ms_matrix: list[list[int]] = []
        for job_row in machine_sequence:
            if isinstance(job_row, list):
                ms_matrix.append([int(v) for v in job_row])
            else:
                ms_matrix.append([int(job_row)])

        # Determine how many machines to clear
        n_destroy = max(1, int(round(n_machines * max(0.0, min(1.0, self.fraction)))))
        machines_to_destroy = rng.sample(range(n_machines), min(n_destroy, n_machines))

        for j in range(n_jobs):
            if j >= len(completion) or not isinstance(completion[j], list):
                continue
            new_row = list(completion[j])
            for op in range(n_machines):
                if op < len(ms_matrix) and op < len(ms_matrix[j]):
                    if ms_matrix[j][op] in machines_to_destroy:
                        new_row[op] = None
            completion[j] = new_row

        return assignment


@dataclass
class JSSPGanttRepair(RepairOperator):
    """Repair JSSP schedule using priority-rule scheduling (SPT dispatch)."""

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants
        keys_by_variable = context.extra.get("keys_by_variable", {})

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        processing_times = constants.get("PROCESSING_TIMES", [])
        machine_sequence = constants.get("MACHINE_SEQUENCE", [])

        # Parse processing times
        pt_matrix: list[list[int]] = []
        for job_row in processing_times:
            if isinstance(job_row, list):
                pt_matrix.append([int(v) for v in job_row])
            else:
                pt_matrix.append([int(job_row)])

        # Parse machine sequence
        ms_matrix: list[list[int]] = []
        for job_row in machine_sequence:
            if isinstance(job_row, list):
                ms_matrix.append([int(v) for v in job_row])
            else:
                ms_matrix.append([int(job_row)])

        # Build job_completion from partial_assignment
        completion = partial_assignment.get("completion")
        if not isinstance(completion, list) or len(completion) != n_jobs:
            completion = [[0] * n_machines for _ in range(n_jobs)]
        else:
            # Ensure proper structure
            for j in range(n_jobs):
                if not isinstance(completion[j], list):
                    completion[j] = [0] * n_machines
                elif len(completion[j]) != n_machines:
                    completion[j].extend([0] * (n_machines - len(completion[j])))

        # Track current state
        job_completion: list[list[int]] = [[0] * n_machines for _ in range(n_jobs)]
        job_started: list[list[bool]] = [[False] * n_machines for _ in range(n_jobs)]
        machine_available: list[int] = [0] * n_machines
        job_available: list[int] = [0] * n_jobs
        completed: set[tuple[int, int]] = set()

        # Initialize from partial assignment - keep already completed operations
        # Predecessor-chain fix: only anchor op if predecessor is also anchored.
        for j in range(n_jobs):
            for op in range(n_machines):
                if j < len(completion) and op < len(completion[j]):
                    val = completion[j][op]
                    if isinstance(val, (int, float)) and val is not None:
                        if op > 0 and (j, op - 1) not in completed:
                            continue  # predecessor not anchored – skip
                        job_completion[j][op] = int(val)
                        job_started[j][op] = True
                        completed.add((j, op))
                        machine = ms_matrix[j][op] if j < len(ms_matrix) and op < len(ms_matrix[j]) else 0
                        machine_available[machine] = max(machine_available[machine], int(val))
                        if op == 0:
                            job_available[j] = max(job_available[j], int(val))
                        elif (j, op - 1) in completed:
                            job_available[j] = max(job_available[j], int(val))

        # Re-schedule remaining operations
        max_iterations = n_jobs * n_machines * 10  # Safety limit
        iteration = 0

        while len(completed) < n_jobs * n_machines and iteration < max_iterations:
            iteration += 1

            # Find ready operations
            ready: list[tuple[int, int, int]] = []  # (job, op, machine)

            for j in range(n_jobs):
                for op in range(n_machines):
                    if (j, op) in completed:
                        continue
                    if job_started[j][op]:
                        continue
                    # First operation always ready
                    if op == 0:
                        ready.append((j, op, ms_matrix[j][op] if j < len(ms_matrix) else 0))
                        continue
                    # Check if predecessor is done
                    if (j, op - 1) in completed:
                        machine = ms_matrix[j][op] if j < len(ms_matrix) and op < len(ms_matrix[j]) else 0
                        ready.append((j, op, machine))

            if not ready:
                # No ready operations - force one by clearing an inconsistency
                # This shouldn't happen with proper constraints
                for j in range(n_jobs):
                    for op in range(n_machines):
                        if not (j, op) in completed and not job_started[j][op]:
                            job_started[j][op] = True  # Mark as started to skip
                            break
                    else:
                        continue
                    break
                continue

            # Sort by processing time (SPT) as base heuristic
            ready.sort(key=lambda x: pt_matrix[x[0]][x[2]])  # x[2] = machine id

            # Randomized selection: 35% chance to pick a random ready op
            # instead of SPT; enables escape from local optima.
            if len(ready) > 1 and rng.random() < 0.35:
                j, op, machine = rng.choice(ready)
            else:
                j, op, machine = ready[0]

            start_time = max(job_available[j], machine_available[machine])
            pt = pt_matrix[j][machine]
            completion_time = start_time + pt

            job_completion[j][op] = completion_time
            job_started[j][op] = True
            job_available[j] = completion_time
            machine_available[machine] = completion_time
            completed.add((j, op))

        partial_assignment["completion"] = job_completion
        return partial_assignment


# ── Additional JSSP-specific destroy operators ─────────────────────────────────


@dataclass
class JSSPShuffleDestroy(DestroyOperator):
    """Destroy by shuffling the operation order within selected jobs.

    Takes a random contiguous segment of operations within a job and reverses
    or randomizes their order.  Keeps the set of assigned machines for each
    operation but changes which machine processes which operation index.
    This breaks the precedence chain and forces a non-trivial reschedule.
    """

    fraction: float = 0.3  # fraction of jobs to reshuffle

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))

        completion = assignment.get("completion")
        if not isinstance(completion, list) or len(completion) != n_jobs:
            return RandomFractionDestroy(fraction=self.fraction).destroy(assignment, context)

        n_destroy = max(1, int(round(n_jobs * max(0.0, min(1.0, self.fraction)))))
        jobs_to_shuffle = rng.sample(range(n_jobs), min(n_destroy, n_jobs))

        for j in jobs_to_shuffle:
            if j >= len(completion) or not isinstance(completion[j], list):
                continue
            row = list(completion[j])
            # Pick a random contiguous segment and reverse it
            if len(row) >= 2:
                seg_len = rng.randint(1, max(1, len(row) - 1))
                start = rng.randint(0, len(row) - seg_len)
                segment = row[start:start + seg_len]
                rng.shuffle(segment)
                row[start:start + seg_len] = segment
            completion[j] = row

        return assignment


@dataclass
class JSSPSwapDestroy(DestroyOperator):
    """Destroy by swapping operation blocks between two selected jobs.

    Identifies a contiguous segment in job A and swaps it with a segment
    of the same length in job B (starting from the same operation index).
    The machines each operation runs on are preserved, but the execution
    order on those machines is changed significantly.

    Falls back to shuffle if fewer than 2 jobs are available.
    """

    fraction: float = 0.3  # fraction of (job-pair × segment) to swap

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))

        completion = assignment.get("completion")
        if not isinstance(completion, list) or len(completion) != n_jobs:
            return RandomFractionDestroy(fraction=self.fraction).destroy(assignment, context)

        if n_jobs < 2:
            return assignment

        # Select up to two distinct jobs to swap between
        n_swap_pairs = max(1, int(round(n_jobs * max(0.0, min(1.0, self.fraction)))))
        jobs_to_swap = rng.sample(range(n_jobs), min(n_swap_pairs * 2, n_jobs))

        for k in range(0, len(jobs_to_swap) - 1, 2):
            j_a = jobs_to_swap[k]
            j_b = jobs_to_swap[k + 1]

            if (j_a >= len(completion) or not isinstance(completion[j_a], list) or
                    j_b >= len(completion) or not isinstance(completion[j_b], list)):
                continue

            seg_len = rng.randint(1, max(1, n_machines - 1))
            max_start = n_machines - seg_len
            start = rng.randint(0, max_start)
            seg_a = list(completion[j_a][start:start + seg_len])
            seg_b = list(completion[j_b][start:start + seg_len])
            completion[j_a][start:start + seg_len] = seg_b
            completion[j_b][start:start + seg_len] = seg_a

        return assignment


@dataclass
class JSSPShiftTimesDestroy(DestroyOperator):
    """Destroy by adding a small random time shift to all operations of selected jobs.

    Adds a uniform random offset Δ ∈ [-max_shift, +max_shift] to every operation
    completion time in the selected jobs.  This breaks the schedule timing
    while keeping all jobs machine assignments intact.  The repair step will
    need to re-propagate precedence and machine no-overlap constraints.
    """

    fraction: float = 0.25
    max_shift: int = 10

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))

        completion = assignment.get("completion")
        if not isinstance(completion, list) or len(completion) != n_jobs:
            return RandomFractionDestroy(fraction=self.fraction).destroy(assignment, context)

        n_destroy = max(1, int(round(n_jobs * max(0.0, min(1.0, self.fraction)))))
        jobs_to_shift = rng.sample(range(n_jobs), min(n_destroy, n_jobs))

        for j in jobs_to_shift:
            if not isinstance(completion[j], list):
                continue
            delta = rng.randint(-self.max_shift, self.max_shift)
            if delta < 0:
                # Clamp negative delta to avoid generating negative completion times,
                # which would violate the DSInt(0, …) lower bound.
                delta = max(0, delta)
            for k in range(len(completion[j])):
                if isinstance(completion[j][k], (int, float)) and completion[j][k] is not None:
                    completion[j][k] = completion[j][k] + delta

        return assignment


# ── Improved JSSP repair operator ──────────────────────────────────────────────


@dataclass
class JSSPConstraintAwareRepair(RepairOperator):
    """Repair JSSP schedule preserving the structure of non-destroyed operations.

    This repair never moves operations that still have valid completion times
    (i.e. were not cleared by the destroy step).  It extends the schedule
    forward from the last known good state, respecting both precedence and
    machine no-overlap constraints.

    Comparable to JSSPGanttRepair but with harder guarantees: once an
    operation's completion time is fixed, it cannot be moved.
    """

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        processing_times = constants.get("PROCESSING_TIMES", [])
        machine_sequence = constants.get("MACHINE_SEQUENCE", [])

        # Parse matrices
        pt_matrix: list[list[int]] = [[int(v) for v in row] for row in processing_times]
        ms_matrix: list[list[int]] = [[int(v) for v in row] for row in machine_sequence]

        # Build working schedule from partial assignment
        completion: list[list[int]] = [[0] * n_machines for _ in range(n_jobs)]
        anchored: list[list[bool]] = [[False] * n_machines for _ in range(n_jobs)]
        machine_available: list[int] = [0] * n_machines
        job_available: list[int] = [0] * n_jobs

        partial = partial_assignment.get("completion")
        if isinstance(partial, list) and len(partial) == n_jobs:
            for j in range(n_jobs):
                for op in range(n_machines):
                    val = partial[j][op] if op < len(partial[j]) else None
                    # Predecessor-chain fix: only anchor if predecessor is anchored.
                    pred_ok = (op == 0) or anchored[j][op - 1]
                    if isinstance(val, (int, float)) and val is not None and pred_ok:
                        completion[j][op] = int(val)
                        anchored[j][op] = True
                        machine = ms_matrix[j][op]
                        if val > machine_available[machine]:
                            machine_available[machine] = int(val)
                        if op == 0:
                            job_available[j] = int(val)
                        elif anchored[j][op - 1]:
                            job_available[j] = int(val)

        # Randomized dispatch: collect ALL ready ops each step, pick one randomly.
        # This lets the LNS explore different machine orderings and escape local optima.
        max_iterations = n_jobs * n_machines * 2
        for _ in range(max_iterations):
            ready: list[tuple[int, int]] = [
                (j, op)
                for j in range(n_jobs)
                for op in range(n_machines)
                if not anchored[j][op]
                and ((op == 0) or anchored[j][op - 1])
            ]
            if not ready:
                break
            rng.shuffle(ready)
            j, op = ready[0]
            machine = ms_matrix[j][op]
            earliest_start = max(job_available[j], machine_available[machine])
            pt = pt_matrix[j][machine]
            completion_time = earliest_start + pt
            completion[j][op] = completion_time
            anchored[j][op] = True
            job_available[j] = completion_time
            machine_available[machine] = completion_time

        partial_assignment["completion"] = completion
        return partial_assignment


# ── JSSP critical path destroy operator ─────────────────────────────────────

@dataclass
class JSSPCriticalPathDestroy(DestroyOperator):
    """Destroy operations along (or near) the critical path.

    The critical path is the chain of operations that determines the
    current makespan.  Clearing these operations forces a full reschedule
    of the bottleneck area, which is where the most improvement can be
    gained.

    ``strategy``
        ``critical`` – only operations on the critical path itself
        ``neighbor`` – critical path + nearby operations on same machines
    ``min_destroy``  – minimum number of (job,op) pairs to destroy
    ``fraction``     – additional random-job fallback when critical path
                        alone is too small for effective search.
    """

    fraction: float = 0.3
    strategy: str = "critical"  # "critical" | "neighbor"
    min_destroy: int = 0

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        processing_times = constants.get("PROCESSING_TIMES", [])
        machine_sequence = constants.get("MACHINE_SEQUENCE", [])

        pt_matrix: list[list[int]] = [[int(v) for v in row] for row in processing_times]
        ms_matrix: list[list[int]] = [[int(v) for v in row] for row in machine_sequence]

        completion = assignment.get("completion")
        if not isinstance(completion, list) or len(completion) != n_jobs:
            return JSSPJobLevelDestroy(fraction=self.fraction).destroy(assignment, context)

        critical_ops = self._find_critical_path(
            completion, ms_matrix, pt_matrix, n_jobs, n_machines
        )

        new_completion = [list(row) if isinstance(row, list) else list(completion) for row in completion]
        destroyed: set[tuple[int, int]] = set()

        for j, op in critical_ops:
            if 0 <= j < len(new_completion) and isinstance(new_completion[j], list) and 0 <= op < len(new_completion[j]):
                new_completion[j][op] = None
                destroyed.add((j, op))

        # Neighbor strategy: also clear operations that are adjacent
        # on the same machines as the critical path
        if self.strategy == "neighbor":
            for j, op in critical_ops:
                machine = ms_matrix[j][op]
                cv = completion[j][op]
                if not isinstance(cv, (int, float)) or cv is None:
                    continue
                op_start_j = int(cv) - pt_matrix[j][machine]

                for j2 in range(n_jobs):
                    if j2 == j:
                        continue
                    for op2 in range(n_machines):
                        if ms_matrix[j2][op2] != machine:
                            continue
                        if (j2, op2) in destroyed:
                            continue
                        v2 = new_completion[j2][op2]
                        if not isinstance(v2, (int, float)) or v2 is None:
                            continue
                        end2 = int(v2)
                        # Adjacent operation whose end is close to our start
                        if abs(end2 - op_start_j) <= pt_matrix[j][machine]:
                            new_completion[j2][op2] = None
                            destroyed.add((j2, op2))

        # Fallback: if critical path is too short, destroy extra random jobs
        target = max(self.min_destroy, max(2, n_machines))
        if len(destroyed) < target:
            n_extra = max(1, int(round(n_jobs * max(0.0, min(1.0, self.fraction)))))
            candidates = [jj for jj in range(n_jobs) if (jj, 0) not in destroyed]
            extra = rng.sample(candidates, min(n_extra, len(candidates)))
            for jj in extra:
                if isinstance(new_completion[jj], list):
                    for oo in range(n_machines):
                        new_completion[jj][oo] = None
                        destroyed.add((jj, oo))
                if len(destroyed) >= target:
                    break

        assignment = dict(assignment)
        assignment["completion"] = new_completion
        return assignment

    def _find_critical_path(
        self,
        completion: list[list[int | None]],
        ms_matrix: list[list[int]],
        pt_matrix: list[list[int]],
        n_jobs: int,
        n_machines: int,
    ) -> list[tuple[int, int]]:
        """Trace the critical path backwards from the makespan operation."""
        path: list[tuple[int, int]] = []

        max_time = -1
        max_j, max_op = 0, 0
        for j in range(n_jobs):
            for op in range(n_machines):
                v = completion[j][op] if op < len(completion[j]) else None
                if isinstance(v, (int, float)) and v is not None and v > max_time:
                    max_time = v
                    max_j, max_op = j, op

        cur_j, cur_op = max_j, max_op
        visited: set[tuple[int, int]] = set()
        path.append((cur_j, cur_op))
        visited.add((cur_j, cur_op))

        for _ in range(n_jobs * n_machines):
            cv = completion[cur_j][cur_op]
            if not isinstance(cv, (int, float)) or cv is None:
                break
            cur_start = int(cv) - pt_matrix[cur_j][ms_matrix[cur_j][cur_op]]

            best_pred: tuple[tuple[int, int], int] | None = None

            # Job predecessor (precedence constraint)
            if cur_op > 0:
                v = completion[cur_j][cur_op - 1]
                if isinstance(v, (int, float)) and v is not None:
                    best_pred = ((cur_j, cur_op - 1), int(v))

            # Machine predecessor: operation on same machine finishing
            # just before cur_start (the one that forces cur to wait)
            machine = ms_matrix[cur_j][cur_op]
            best_end = -1
            for j2 in range(n_jobs):
                for op2 in range(n_machines):
                    if (j2, op2) == (cur_j, cur_op):
                        continue
                    if ms_matrix[j2][op2] != machine:
                        continue
                    v2 = completion[j2][op2]
                    if not isinstance(v2, (int, float)) or v2 is None:
                        continue
                    if int(v2) <= cur_start and int(v2) > best_end:
                        best_end = int(v2)

            if best_end >= 0:
                for j2 in range(n_jobs):
                    for op2 in range(n_machines):
                        if (j2, op2) == (cur_j, cur_op):
                            continue
                        if ms_matrix[j2][op2] != machine:
                            continue
                        v2 = completion[j2][op2]
                        if isinstance(v2, (int, float)) and v2 is not None and int(v2) == best_end:
                            if best_pred is None or best_end > best_pred[1]:
                                best_pred = ((j2, op2), best_end)

            if best_pred is None:
                break
            pred = best_pred[0]
            if pred in visited:
                break
            path.append(pred)
            visited.add(pred)
            cur_j, cur_op = pred

        return path


# ── JSSP insertion-based repair (active schedule) ────────────────────────────

@dataclass
class JSSPInsertionRepair(RepairOperator):
    """Insert each unscheduled operation at its best (earliest) position.

    Searches the space of non-delay active schedules (applicable to the
    Deb-Gen/Taillard family of methods).  Optimal JSSP solutions are
    guaranteed to be contained within the active schedule space
    (Applegate & Cook 1991).

    ``order`` – sorting of unscheduled operations before insertion:
        ``priority``        – shortest processing time first  (default)
        ``fifo``            – natural (job, op) index order
        ``random``          – random permutation
        ``most_remaining``  – jobs with the most unscheduled ops first

    ``improve`` – if True, run a local insertion improvement pass after
                  the initial repair to try to reduce the makespan further.
    """

    order: str = "priority"
    improve: bool = True

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        processing_times = constants.get("PROCESSING_TIMES", [])
        machine_sequence = constants.get("MACHINE_SEQUENCE", [])

        pt_matrix: list[list[int]] = [[int(v) for v in row] for row in processing_times]
        ms_matrix: list[list[int]] = [[int(v) for v in row] for row in machine_sequence]

        # Working schedule from partial assignment
        completion: list[list[int | None]] = [
            [None] * n_machines for _ in range(n_jobs)
        ]
        anchored: list[list[bool]] = [
            [False] * n_machines for _ in range(n_jobs)
        ]

        partial = partial_assignment.get("completion")
        if isinstance(partial, list) and len(partial) == n_jobs:
            for j in range(n_jobs):
                row = partial[j] if j < len(partial) else []
                for op in range(n_machines):
                    if isinstance(row, list) and op < len(row):
                        val = row[op]
                        # Predecessor-chain fix
                        pred_ok = (op == 0) or anchored[j][op - 1]
                        if isinstance(val, (int, float)) and val is not None and pred_ok:
                            completion[j][op] = int(val)
                            anchored[j][op] = True

        # Collect unscheduled (non-anchored) operations
        unscheduled: list[tuple[int, int]] = []
        for j in range(n_jobs):
            for op in range(n_machines):
                if not anchored[j][op]:
                    unscheduled.append((j, op))

        # Sort by chosen order
        if self.order == "random":
            rng.shuffle(unscheduled)
        elif self.order == "priority":
            unscheduled.sort(key=lambda x: (pt_matrix[x[0]][ms_matrix[x[0]][x[1]]], x[0]))
        elif self.order == "most_remaining":
            unscheduled.sort(
                key=lambda x: sum(
                    1 for _o in range(n_machines) if not anchored[x[0]][_o]
                ),
                reverse=True,
            )
        # else: fifo (index order)

        # Insert only ready operations first; defer ops with unscheduled predecessors.
        # Multiple passes ensure all ops are eventually inserted.
        max_passes = n_machines + 1
        for _ in range(max_passes):
            remaining: list[tuple[int, int]] = []
            for j, op in unscheduled:
                if op == 0 or anchored[j][op - 1]:
                    self._insert_at_earliest(
                        j, op, completion, anchored, ms_matrix, pt_matrix,
                        n_jobs, n_machines,
                    )
                else:
                    remaining.append((j, op))
            unscheduled = remaining
            if not unscheduled:
                break

        # Optional improvement pass
        if self.improve:
            self._improvement_pass(
                completion,
                ms_matrix, pt_matrix,
                n_jobs, n_machines,
            )

        # Clamp None to 0
        for j in range(n_jobs):
            for op in range(n_machines):
                if completion[j][op] is None:
                    completion[j][op] = 0

        partial_assignment["completion"] = completion
        return partial_assignment

    def _insert_at_earliest(
        self,
        j: int, op: int,
        completion: list[list[int | None]],
        anchored: list[list[bool]],
        ms_matrix: list[list[int]],
        pt_matrix: list[list[int]],
        n_jobs: int,
        n_machines: int,
    ) -> None:
        """Insert (j, op) at the earliest feasible position on its machine."""
        machine = ms_matrix[j][op]
        pt = pt_matrix[j][machine]

        # Precedence lower bound
        job_lb = 0
        if op > 0 and completion[j][op - 1] is not None:
            job_lb = completion[j][op - 1]

        # Anchored intervals on same machine: (start, end)
        intervals: list[tuple[int, int]] = []
        for j2 in range(n_jobs):
            for o2 in range(n_machines):
                if (j2, o2) == (j, op) or ms_matrix[j2][o2] != machine:
                    continue
                if anchored[j2][o2]:
                    c2 = completion[j2][o2]
                    s2 = c2 - pt_matrix[j2][ms_matrix[j2][o2]] if c2 else 0
                    intervals.append((s2, c2))
        intervals.sort()

        # Candidate start times: job_lb and immediately after each interval
        candidates: list[int] = [job_lb]
        for s, e in intervals:
            candidates.append(max(job_lb, e))

        # Find the EARLIEST feasible start
        best_end: int | None = None
        for start in sorted(set(candidates)):
            end = start + pt
            ok = True
            for s, e in intervals:
                if start < e and end > s:
                    ok = False
                    break
            if ok:
                best_end = end
                break  # earliest found

        if best_end is None:
            best_end = job_lb + pt  # fallback

        completion[j][op] = best_end
        anchored[j][op] = True

    def _improvement_pass(
        self,
        completion: list[list[int | None]],
        ms_matrix: list[list[int]],
        pt_matrix: list[list[int]],
        n_jobs: int,
        n_machines: int,
    ) -> None:
        """Try to improve each operation by moving it to an earlier slot."""
        for j in range(n_jobs):
            for op in range(n_machines):
                machine = ms_matrix[j][op]
                pt = pt_matrix[j][machine]
                cur_end = completion[j][op] if completion[j][op] else 0
                cur_start = cur_end - pt

                # Precedence lower bound
                job_lb = 0
                if op > 0:
                    job_lb = completion[j][op - 1] if completion[j][op - 1] else 0

                # Other anchored intervals on same machine
                intervals: list[tuple[int, int]] = []
                for j2 in range(n_jobs):
                    for o2 in range(n_machines):
                        if (j2, o2) == (j, op) or ms_matrix[j2][o2] != machine:
                            continue
                        c2 = completion[j2][o2]
                        s2 = c2 - pt_matrix[j2][ms_matrix[j2][o2]] if c2 else 0
                        intervals.append((s2, c2))
                intervals.sort()

                best_start = cur_start

                # Try starting earlier: job_lb, and after each preceding interval
                for s, e in intervals:
                    if e <= cur_start:
                        best_start = max(best_start, e)

                # Try job_lb directly
                test_start = max(job_lb, best_start) if best_start >= cur_start else job_lb
                for candidate in [job_lb] + [e for s, e in intervals if e <= cur_start]:
                    end = max(candidate, job_lb) + pt
                    if end >= cur_end:
                        continue
                    ok = True
                    for s, e in intervals:
                        if max(candidate, job_lb) < e and end > s:
                            ok = False
                            break
                    if ok:
                        completion[j][op] = end


# ── JSSP non-delay active schedule repair ─────────────────────────────────────

@dataclass
class JSSPNonDelayRepair(RepairOperator):
    """Repair producing a non-delay active schedule.

    A non-delay schedule never keeps a ready operation idle when its machine
    is available.  This is the standard construction from Deb & Gen (1991)
    and Taillard (1990).

    ``selection`` – which ready operation to schedule first:
        ``spt``                – shortest processing time
        ``most_work_remaining`` – job with most remaining operations
        ``random``             – random shuffle
    ``passes``    – number of local insertion improvement passes after
                    the initial construction.
    """

    selection: str = "spt"
    passes: int = 2

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        processing_times = constants.get("PROCESSING_TIMES", [])
        machine_sequence = constants.get("MACHINE_SEQUENCE", [])

        pt_matrix: list[list[int]] = [[int(v) for v in row] for row in processing_times]
        ms_matrix: list[list[int]] = [[int(v) for v in row] for row in machine_sequence]

        # Working schedule
        completion: list[list[int | None]] = [
            [None] * n_machines for _ in range(n_jobs)
        ]
        anchored: list[list[bool]] = [
            [False] * n_machines for _ in range(n_jobs)
        ]

        partial_comp = partial_assignment.get("completion")
        if isinstance(partial_comp, list) and len(partial_comp) == n_jobs:
            for j in range(n_jobs):
                row = partial_comp[j] if j < len(partial_comp) else []
                for op in range(n_machines):
                    if isinstance(row, list) and op < len(row):
                        val = row[op]
                        # Predecessor-chain fix
                        pred_ok = (op == 0) or anchored[j][op - 1]
                        if isinstance(val, (int, float)) and val is not None and pred_ok:
                            completion[j][op] = int(val)
                            anchored[j][op] = True

        # Machine and job availability from anchored operations
        machine_available: list[int] = [0] * n_machines
        job_available: list[int] = [0] * n_jobs
        job_next_op: list[int] = [0] * n_jobs  # next unscheduled op per job

        for j in range(n_jobs):
            for op in range(n_machines):
                if anchored[j][op]:
                    c = completion[j][op]
                    m = ms_matrix[j][op]
                    machine_available[m] = max(machine_available[m], c)
                    if op + 1 > job_next_op[j]:
                        job_next_op[j] = op + 1
                    # Update job availability only if this op determines it
                    if op == 0 or not anchored[j][op - 1]:
                        job_available[j] = max(job_available[j], c)

        # Non-delay construction: schedule ready ops greedily
        total_ops = n_jobs * n_machines
        scheduled_count = sum(
            1 for j in range(n_jobs)
            for op in range(n_machines)
            if anchored[j][op]
        )

        max_iter = total_ops * 20
        for _ in range(max_iter):
            if scheduled_count >= total_ops:
                break

            # Collect ready operations
            ready: list[tuple[int, int]] = []
            for j in range(n_jobs):
                op = job_next_op[j]
                if op < n_machines:
                    ready.append((j, op))
            if not ready:
                break

            # Sort by selection criterion
            if self.selection == "spt":
                ready.sort(key=lambda x: pt_matrix[x[0]][ms_matrix[x[0]][x[1]]])
            elif self.selection == "most_work_remaining":
                ready.sort(key=lambda x: n_machines - job_next_op[x[0]], reverse=True)
            elif self.selection == "random":
                rng.shuffle(ready)

            # Schedule the first ready operation (non-delay)
            j, op = ready[0]
            machine = ms_matrix[j][op]
            pt = pt_matrix[j][machine]

            start = max(job_available[j], machine_available[machine])
            end = start + pt

            completion[j][op] = end
            anchored[j][op] = True
            job_available[j] = end
            machine_available[machine] = end
            job_next_op[j] = op + 1
            scheduled_count += 1

        # Improvement passes
        for _ in range(self.passes):
            self._improvement_pass(
                completion, ms_matrix, pt_matrix,
                n_jobs, n_machines,
            )

        # Clamp None
        for j in range(n_jobs):
            for op in range(n_machines):
                if completion[j][op] is None:
                    completion[j][op] = 0

        partial_assignment["completion"] = completion
        return partial_assignment

    def _improvement_pass(
        self,
        completion: list[list[int | None]],
        ms_matrix: list[list[int]],
        pt_matrix: list[list[int]],
        n_jobs: int,
        n_machines: int,
    ) -> bool:
        """Try to improve makespan by moving each operation earlier.

        Returns True if any improvement was made.
        """
        improved = False
        for j in range(n_jobs):
            for op in range(n_machines):
                machine = ms_matrix[j][op]
                pt = pt_matrix[j][machine]
                cur_end = completion[j][op] if isinstance(completion[j][op], (int, float)) else 0
                if cur_end <= 0:
                    continue  # cannot improve an unset value
                cur_start = max(0, cur_end - pt)

                job_lb = 0
                if op > 0:
                    job_lb = completion[j][op - 1] if isinstance(completion[j][op - 1], (int, float)) else 0

                # Other ops on same machine
                intervals: list[tuple[int, int]] = []
                for j2 in range(n_jobs):
                    for o2 in range(n_machines):
                        if (j2, o2) == (j, op) or ms_matrix[j2][o2] != machine:
                            continue
                        c2 = completion[j2][o2]
                        if not isinstance(c2, (int, float)):
                            continue  # skip unassigned
                        s2 = max(0, c2 - pt_matrix[j2][ms_matrix[j2][o2]])
                        intervals.append((s2, c2))
                intervals.sort()

                # Try starting at job_lb and after each interval before cur_start
                candidates: list[int] = [job_lb]
                for s, e in intervals:
                    if e <= cur_start:
                        candidates.append(max(job_lb, e))

                for start in candidates:
                    end = start + pt
                    if end >= cur_end:
                        continue
                    ok = True
                    for s, e in intervals:
                        if start < e and end > s:
                            ok = False
                            break
                    if ok:
                        completion[j][op] = end
                        improved = True
                        break

        return improved
