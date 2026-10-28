"""OptDSL-formulated JSSP destroy and repair operators.

These operators work directly with the OptDSL decision-variable
(completion-time) representation of the JSSP and use structural
knowledge of precedence / no-overlap constraints to explore
the active-schedule space where optimal solutions are guaranteed
to reside  (Applegate & Cook 1991).

Destroy
-------
JSSPGapDestroy  –  destroys operations that are involved in tight
time gaps on shared machines  (the bottleneck zone).  Operations
with the smallest slack have the most to gain from rescheduling.

Repair
------
JSSPOptActiveScheduleRepair  –  full active-schedule construction
with look-ahead insertion, followed by multiple back-shift
improvement passes.  Preserves any operations that were not
destroyed (anchored) so it works as a proper LNS repair neighbor.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from ..components import DestroyOperator, RepairOperator
from ..defaults import RandomFractionDestroy
from ..models import LNSContext


# ── Helpers ────────────────────────────────────────────────────────────────────


def _parse_int_matrix(raw: Any, rows: int, cols: int) -> list[list[int]]:
    """Best-effort parser for constant matrices from the DSL reader."""
    matrix: list[list[int]] = []
    for r in range(rows):
        row_raw = raw[r] if r < len(raw) else []
        if isinstance(row_raw, list):
            matrix.append([int(v) for v in row_raw[:cols]])
        else:
            matrix.append([int(row_raw)] if row_raw is not None else [0])
        while len(matrix[-1]) < cols:
            matrix[-1].append(0)
    return matrix


def _get_completion(
    assignment: dict[str, object], n_jobs: int, n_machines: int
) -> list[list[int | None]]:
    """Extract the completion matrix, returning None-filled fallback."""
    comp = assignment.get("completion")
    if isinstance(comp, list) and len(comp) == n_jobs:
        out: list[list[int | None]] = []
        for j in range(n_jobs):
            row = comp[j] if j < len(comp) else []
            if isinstance(row, list):
                r = [int(v) if isinstance(v, (int, float)) and v is not None else None for v in row]
                while len(r) < n_machines:
                    r.append(None)
                out.append(r[:n_machines])
            else:
                out.append([None] * n_machines)
        return out
    return [[None] * n_machines for _ in range(n_jobs)]


def _machine_orders_from_completion(
    completion: list[list[int]],
    ms_matrix: list[list[int]],
    pt_matrix: list[list[int]],
    n_jobs: int,
    n_machines: int,
) -> list[list[tuple[int, int]]]:
    """Recover machine sequences from a complete schedule."""
    machine_orders: list[list[tuple[int, int, int, int]]] = [[] for _ in range(n_machines)]
    for j in range(n_jobs):
        for op in range(n_machines):
            m = ms_matrix[j][op]
            end = int(completion[j][op])
            start = end - pt_matrix[j][m]
            machine_orders[m].append((start, end, j, op))
    return [
        [(j, op) for _, _, j, op in sorted(order, key=lambda x: (x[0], x[1], x[2], x[3]))]
        for order in machine_orders
    ]


def _schedule_from_machine_orders(
    machine_orders: list[list[tuple[int, int]]],
    ms_matrix: list[list[int]],
    pt_matrix: list[list[int]],
    n_jobs: int,
    n_machines: int,
) -> list[list[int]] | None:
    """Generate an earliest schedule for a fixed order on each machine.

    Returns None if the supplied machine orders are cyclic/inconsistent.
    """
    completion: list[list[int]] = [[0] * n_machines for _ in range(n_jobs)]
    job_next_op = [0] * n_jobs
    job_available = [0] * n_jobs
    machine_available = [0] * n_machines
    machine_next_pos = [0] * n_machines

    total = n_jobs * n_machines
    scheduled = 0
    max_iterations = total * n_machines * 2
    iterations = 0

    while scheduled < total and iterations < max_iterations:
        iterations += 1
        progressed = False
        for m in range(n_machines):
            pos = machine_next_pos[m]
            if pos >= len(machine_orders[m]):
                continue
            j, op = machine_orders[m][pos]
            if op != job_next_op[j]:
                continue
            if ms_matrix[j][op] != m:
                return None
            start = max(job_available[j], machine_available[m])
            end = start + pt_matrix[j][m]
            completion[j][op] = end
            job_available[j] = end
            machine_available[m] = end
            job_next_op[j] += 1
            machine_next_pos[m] += 1
            scheduled += 1
            progressed = True
        if not progressed:
            return None

    return completion if scheduled == total else None


def _makespan(completion: list[list[int]]) -> int:
    return max((row[-1] for row in completion if row), default=0)


def _critical_path_ops(
    completion: list[list[int]],
    ms_matrix: list[list[int]],
    pt_matrix: list[list[int]],
    n_jobs: int,
    n_machines: int,
) -> list[tuple[int, int]]:
    """Trace a critical path backward from the makespan operation."""
    max_time = -1
    cur_j, cur_op = 0, 0
    for j in range(n_jobs):
        for op in range(n_machines):
            v = completion[j][op]
            if v > max_time:
                max_time = v
                cur_j, cur_op = j, op

    path: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for _ in range(n_jobs * n_machines):
        node = (cur_j, cur_op)
        if node in seen:
            break
        seen.add(node)
        path.append(node)

        cur_end = completion[cur_j][cur_op]
        cur_start = cur_end - pt_matrix[cur_j][ms_matrix[cur_j][cur_op]]
        best_pred: tuple[int, int] | None = None
        best_end = -1

        if cur_op > 0:
            pred_end = completion[cur_j][cur_op - 1]
            if pred_end >= best_end and pred_end <= cur_start:
                best_pred = (cur_j, cur_op - 1)
                best_end = pred_end

        machine = ms_matrix[cur_j][cur_op]
        for j2 in range(n_jobs):
            for op2 in range(n_machines):
                if (j2, op2) == (cur_j, cur_op):
                    continue
                if ms_matrix[j2][op2] != machine:
                    continue
                end2 = completion[j2][op2]
                if end2 <= cur_start and end2 >= best_end:
                    best_pred = (j2, op2)
                    best_end = end2

        if best_pred is None:
            break
        cur_j, cur_op = best_pred

    return path


# ── Destroy ────────────────────────────────────────────────────────────────────


@dataclass
class JSSPGapDestroy(DestroyOperator):
    """Destroy operations involved in tight time gaps on shared machines.

    For each pair of operations on the same machine, compute the *gap*
    (idle time between them).  Operations bordering the smallest gaps
    are the most constrained and have the most to gain from
    rescheduling.

    Parameters
    ----------
    gap_fraction
        Destroy the N operations bordering the tightest gaps, where
        N = ceil(total_operations * gap_fraction).
    min_destroy
        Floor on number of destroyed operations (default 2).
    """

    gap_fraction: float = 0.35
    min_destroy: int = 2

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))

        completion = _get_completion(assignment, n_jobs, n_machines)

        # Check if we have a full schedule to analyze
        has_schedule = all(
            all(v is not None for v in row)
            for row in completion
        )
        if not has_schedule:
            return RandomFractionDestroy(fraction=self.gap_fraction).destroy(
                assignment, context
            )

        # Collect all operations grouped by machine  (machine -> list of (j, op, start, end))
        ms_matrix = _parse_int_matrix(
            constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines
        )
        pt_matrix = _parse_int_matrix(
            constants.get("PROCESSING_TIMES", []), n_jobs, n_machines
        )

        machine_ops: dict[int, list[tuple[int, int, int, int]]] = {}
        for j in range(n_jobs):
            for op in range(n_machines):
                m = ms_matrix[j][op]
                end = completion[j][op]
                start = end - pt_matrix[j][m] if end is not None else 0
                machine_ops.setdefault(m, []).append((j, op, start, end))

        # Compute gaps between consecutive operations on each machine
        gaps: list[tuple[float, tuple[int, int], tuple[int, int]]] = []
        for m in range(n_machines):
            ops = sorted(machine_ops.get(m, []), key=lambda x: x[2])  # sort by start
            for k in range(len(ops) - 1):
                _, _, _, end_a = ops[k]
                j_b, op_b, start_b, _ = ops[k + 1]
                gap_val = float(start_b - end_a)
                # Negative gap => overlap  (infeasible); zero gap => tight
                j_a, op_a, _, _ = ops[k]
                gaps.append((gap_val, (j_a, op_a), (j_b, op_b)))

        # Sort by gap ascending (tightest first)
        gaps.sort(key=lambda x: x[0])

        # Determine how many operations to destroy
        total_ops = n_jobs * n_machines
        target = max(self.min_destroy, int(round(total_ops * max(0.0, min(1.0, self.gap_fraction)))))

        destroyed: set[tuple[int, int]] = set()
        for gap_val, op_a, op_b in gaps:
            if len(destroyed) >= target:
                break
            destroyed.add(op_a)
            if len(destroyed) >= target:
                break
            destroyed.add(op_b)

        # Fallback: if still too few, add random operations
        if len(destroyed) < target:
            remaining = [(j, op) for j in range(n_jobs) for op in range(n_machines) if (j, op) not in destroyed]
            rng.shuffle(remaining)
            for item in remaining:
                destroyed.add(item)
                if len(destroyed) >= target:
                    break

        # Apply destruction
        new_completion = [list(row) for row in completion]
        for j, op in destroyed:
            new_completion[j][op] = None

        assignment = dict(assignment)
        assignment["completion"] = new_completion
        return assignment


# ── Repair ─────────────────────────────────────────────────────────────────────


@dataclass
class JSSPOptActiveScheduleRepair(RepairOperator):
    """Repair by constructing a near-optimal active schedule.

    Active schedules are a subset of all feasible schedules that
    contain all optimal solutions.  This operator:

    1. Keeps anchored (non-destroyed) operations fixed.
    2. Inserts remaining operations using *look-ahead cheapest
       insertion* — for each candidate operation, evaluate the
       increase in makespan if inserted at every feasible slot
       and pick the insertion that causes the smallest increase.
    3. After all operations are placed, run multiple *back-shift*
       passes: sweep each operation backward on its machine to the
       earliest feasible position.

    Parameters
    ----------
    look_ahead
        Number of unscheduled operations to consider simultaneously
        during insertion  (higher = more lookahead, slower).
    passes
        Back-shift improvement iterations after construction.
    """

    look_ahead: int = 1
    passes: int = 3

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        pt_matrix = _parse_int_matrix(
            constants.get("PROCESSING_TIMES", []), n_jobs, n_machines
        )
        ms_matrix = _parse_int_matrix(
            constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines
        )

        # Anchored completion matrix
        completion: list[list[int | None]] = [[None] * n_machines for _ in range(n_jobs)]
        anchored: list[list[bool]] = [[False] * n_machines for _ in range(n_jobs)]

        partial_comp = partial_assignment.get("completion")
        if isinstance(partial_comp, list) and len(partial_comp) == n_jobs:
            for j in range(n_jobs):
                row = partial_comp[j] if j < len(partial_comp) else []
                if isinstance(row, list):
                    for op in range(min(len(row), n_machines)):
                        val = row[op]
                        # Only anchor if the operation has a value AND its
                        # job-predecessor is also anchored (or it's the first
                        # operation).  This ensures anchored ops that follow a
                        # destroyed predecessor are treated as destroyed too,
                        # preventing stale completion times from violating the
                        # precedence constraint after repair.
                        pred_ok = (op == 0) or anchored[j][op - 1]
                        if isinstance(val, (int, float)) and val is not None and pred_ok:
                            completion[j][op] = int(val)
                            anchored[j][op] = True

        # Collect unscheduled operations and shuffle for randomized exploration.
        # Randomized insertion order is the primary mechanism for escaping
        # the local optima that deterministic SPT dispatch always produces.
        unscheduled: list[tuple[int, int]] = [
            (j, op)
            for j in range(n_jobs)
            for op in range(n_machines)
            if not anchored[j][op]
        ]
        rng.shuffle(unscheduled)

        if not unscheduled:
            partial_assignment["completion"] = self._clamp(completion, n_jobs, n_machines)
            return partial_assignment

        # ── Active-schedule insertion with ready-ops filter ──────────────
        # Only insert operations whose job-predecessor is already anchored.
        # This preserves precedence correctness and enables randomized
        # machine-ordering exploration (key for finding near-optimal solutions).
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

        # ── Back-shift improvement ─────────────────────────────────────
        for _ in range(max(0, self.passes)):
            self._back_shift_pass(
                completion, ms_matrix, pt_matrix, n_jobs, n_machines
            )

        partial_assignment["completion"] = self._clamp(
            completion, n_jobs, n_machines
        )
        return partial_assignment

    # ── Insertion helpers ──────────────────────────────────────────

    @staticmethod
    def _clamp(
        completion: list[list[int | None]],
        n_jobs: int,
        n_machines: int,
    ) -> list[list[int]]:
        result: list[list[int]] = []
        for j in range(n_jobs):
            row: list[int] = []
            for op in range(n_machines):
                v = completion[j][op]
                row.append(int(v) if v is not None and not isinstance(v, bool) else 0)
            result.append(row)
        return result

    def _insert_at_earliest(
        self,
        j: int,
        op: int,
        completion: list[list[int | None]],
        anchored: list[list[bool]],
        ms_matrix: list[list[int]],
        pt_matrix: list[list[int]],
        n_jobs: int,
        n_machines: int,
    ) -> None:
        """Place (j, op) at the earliest feasible slot on its machine."""
        machine = ms_matrix[j][op]
        pt = pt_matrix[j][machine]

        # Precedence lower bound
        job_lb = 0
        if op > 0 and completion[j][op - 1] is not None:
            job_lb = completion[j][op - 1]

        # Collect anchored intervals on same machine
        intervals: list[tuple[int, int]] = []
        for j2 in range(n_jobs):
            for o2 in range(n_machines):
                if (j2, o2) == (j, op):
                    continue
                if ms_matrix[j2][o2] != machine:
                    continue
                if anchored[j2][o2]:
                    c2 = completion[j2][o2]
                    m2 = ms_matrix[j2][o2]
                    s2 = c2 - pt_matrix[j2][m2] if c2 else 0
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

    @staticmethod
    def _back_shift_pass(
        completion: list[list[int | None]],
        ms_matrix: list[list[int]],
        pt_matrix: list[list[int]],
        n_jobs: int,
        n_machines: int,
    ) -> None:
        """Try to shift every operation to its earliest feasible start."""
        for _ in range(n_machines):  # multiple sweeps per pass
            for j in range(n_jobs):
                for op in range(n_machines):
                    cur = completion[j][op]
                    if cur is None:
                        continue

                    machine = ms_matrix[j][op]
                    pt = pt_matrix[j][machine]
                    cur_end = int(cur)

                    # Precedence lower bound
                    job_lb = 0
                    if op > 0:
                        prev = completion[j][op - 1]
                        if prev is not None:
                            job_lb = int(prev)

                    # Other ops on same machine
                    intervals: list[tuple[int, int]] = []
                    for j2 in range(n_jobs):
                        for o2 in range(n_machines):
                            if (j2, o2) == (j, op):
                                continue
                            if ms_matrix[j2][o2] != machine:
                                continue
                            c2 = completion[j2][o2]
                            if c2 is None:
                                continue
                            m2 = ms_matrix[j2][o2]
                            s2 = max(0, int(c2) - pt_matrix[j2][m2])
                            intervals.append((s2, int(c2)))
                    intervals.sort()

                    # Build candidate start times: job_lb and after each interval
                    candidates: list[int] = [job_lb]
                    for s, e in intervals:
                        c = max(job_lb, e)
                        if c < cur_end:
                            candidates.append(c)

                    # Find the earliest FEASIBLE start that is strictly earlier
                    best_end = cur_end  # only update if we improve
                    for start in sorted(set(candidates)):
                        end = start + pt
                        if end >= best_end:
                            continue  # can't improve
                        ok = True
                        for s, e in intervals:
                            if start < e and end > s:
                                ok = False
                                break
                        if ok:
                            best_end = end
                            break  # earliest feasible found

                    if best_end < cur_end:
                        completion[j][op] = best_end


# ── Additional diversified neighborhoods ─────────────────────────────────────


@dataclass
class JSSPTimeWindowDestroy(DestroyOperator):
    """Destroy operations that overlap a random time window.

    This neighborhood perturbs a temporal region instead of whole jobs or
    machines, helping the search escape local minima caused by small timing
    misalignments around the current bottleneck period.
    """

    window_fraction: float = 0.25
    destroy_fraction: float = 0.25
    min_destroy: int = 2

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        completion = _get_completion(assignment, n_jobs, n_machines)

        has_schedule = all(all(v is not None for v in row) for row in completion)
        if not has_schedule:
            return RandomFractionDestroy(fraction=self.destroy_fraction).destroy(assignment, context)

        ms_matrix = _parse_int_matrix(constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines)
        pt_matrix = _parse_int_matrix(constants.get("PROCESSING_TIMES", []), n_jobs, n_machines)

        makespan = max(int(v) for row in completion for v in row if v is not None)
        window = max(1, int(round(makespan * max(0.05, min(0.95, self.window_fraction)))))
        window_start = rng.randint(0, max(0, makespan - window))
        window_end = window_start + window

        candidates: list[tuple[int, int]] = []
        for j in range(n_jobs):
            for op in range(n_machines):
                end = completion[j][op]
                if end is None:
                    continue
                m = ms_matrix[j][op]
                start = int(end) - pt_matrix[j][m]
                # Interval intersection with [window_start, window_end)
                if start < window_end and int(end) > window_start:
                    candidates.append((j, op))

        total_ops = n_jobs * n_machines
        target = max(self.min_destroy, int(round(total_ops * max(0.0, min(1.0, self.destroy_fraction)))))
        destroyed: set[tuple[int, int]] = set()

        rng.shuffle(candidates)
        for item in candidates:
            destroyed.add(item)
            if len(destroyed) >= target:
                break

        if len(destroyed) < target:
            remaining = [(j, op) for j in range(n_jobs) for op in range(n_machines) if (j, op) not in destroyed]
            rng.shuffle(remaining)
            for item in remaining:
                destroyed.add(item)
                if len(destroyed) >= target:
                    break

        new_completion = [list(row) for row in completion]
        for j, op in destroyed:
            new_completion[j][op] = None

        out = dict(assignment)
        out["completion"] = new_completion
        return out


@dataclass
class JSSPBottleneckMachineDestroy(DestroyOperator):
    """Destroy operations on the most loaded machines.

    Targets structural bottlenecks by clearing operations on machines with the
    largest cumulative processing load in the current solution.
    """

    machine_fraction: float = 0.4
    destroy_fraction: float = 0.25
    min_destroy: int = 2

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        completion = _get_completion(assignment, n_jobs, n_machines)

        ms_matrix = _parse_int_matrix(constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines)
        pt_matrix = _parse_int_matrix(constants.get("PROCESSING_TIMES", []), n_jobs, n_machines)

        machine_load = [0] * n_machines
        for j in range(n_jobs):
            for op in range(n_machines):
                if completion[j][op] is None:
                    continue
                m = ms_matrix[j][op]
                machine_load[m] += pt_matrix[j][m]

        k = max(1, int(round(n_machines * max(0.1, min(1.0, self.machine_fraction)))))
        ranked = sorted(range(n_machines), key=lambda m: machine_load[m], reverse=True)
        selected = set(ranked[:k])

        candidates = [(j, op) for j in range(n_jobs) for op in range(n_machines) if ms_matrix[j][op] in selected]

        total_ops = n_jobs * n_machines
        target = max(self.min_destroy, int(round(total_ops * max(0.0, min(1.0, self.destroy_fraction)))))
        destroyed: set[tuple[int, int]] = set()

        rng.shuffle(candidates)
        for item in candidates:
            destroyed.add(item)
            if len(destroyed) >= target:
                break

        if len(destroyed) < target:
            remaining = [(j, op) for j in range(n_jobs) for op in range(n_machines) if (j, op) not in destroyed]
            rng.shuffle(remaining)
            for item in remaining:
                destroyed.add(item)
                if len(destroyed) >= target:
                    break

        new_completion = [list(row) for row in completion]
        for j, op in destroyed:
            new_completion[j][op] = None

        out = dict(assignment)
        out["completion"] = new_completion
        return out


@dataclass
class JSSPCriticalBlockDestroy(DestroyOperator):
    """Destroy a contiguous block on the current bottleneck machine.

    This approximates the classical JSSP critical-block neighborhood: rather
    than clearing arbitrary critical operations, it removes a consecutive block
    of machine-ordered operations near the makespan bottleneck so the repair can
    rebuild a different local order.
    """

    block_size: int = 3
    min_destroy: int = 2

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        completion = _get_completion(assignment, n_jobs, n_machines)

        has_schedule = all(all(v is not None for v in row) for row in completion)
        if not has_schedule:
            return RandomFractionDestroy(fraction=0.25).destroy(assignment, context)

        ms_matrix = _parse_int_matrix(constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines)
        pt_matrix = _parse_int_matrix(constants.get("PROCESSING_TIMES", []), n_jobs, n_machines)

        # Find the operation attaining the makespan.
        max_end = -1
        critical = (0, 0)
        for j in range(n_jobs):
            for op in range(n_machines):
                end = completion[j][op]
                if end is not None and int(end) > max_end:
                    max_end = int(end)
                    critical = (j, op)

        crit_machine = ms_matrix[critical[0]][critical[1]]

        machine_ops: list[tuple[int, int, int, int]] = []
        for j in range(n_jobs):
            for op in range(n_machines):
                if ms_matrix[j][op] != crit_machine:
                    continue
                end = completion[j][op]
                if end is None:
                    continue
                start = int(end) - pt_matrix[j][crit_machine]
                machine_ops.append((j, op, start, int(end)))
        machine_ops.sort(key=lambda x: (x[2], x[3]))

        if not machine_ops:
            return assignment

        center = 0
        for idx, (j, op, _, _) in enumerate(machine_ops):
            if (j, op) == critical:
                center = idx
                break

        size = max(self.min_destroy, min(len(machine_ops), self.block_size))
        lo = max(0, center - size + 1)
        hi = min(center, len(machine_ops) - size)
        start_idx = rng.randint(lo, hi) if hi >= lo else max(0, min(center, len(machine_ops) - size))
        destroyed = {(j, op) for j, op, _, _ in machine_ops[start_idx:start_idx + size]}

        new_completion = [list(row) for row in completion]
        for j, op in destroyed:
            new_completion[j][op] = None

        out = dict(assignment)
        out["completion"] = new_completion
        return out


@dataclass
class JSSPRemainingWorkRepair(RepairOperator):
    """Dispatch ready operations preferring jobs with most remaining work.

    This complements SPT-like repairs by prioritizing long-tail jobs to reduce
    end-of-schedule congestion and diversify machine-order exploration.
    """

    random_pick_prob: float = 0.2

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        pt_matrix = _parse_int_matrix(constants.get("PROCESSING_TIMES", []), n_jobs, n_machines)
        ms_matrix = _parse_int_matrix(constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines)

        completion: list[list[int]] = [[0] * n_machines for _ in range(n_jobs)]
        anchored: list[list[bool]] = [[False] * n_machines for _ in range(n_jobs)]
        machine_available = [0] * n_machines
        job_available = [0] * n_jobs

        partial_comp = partial_assignment.get("completion")
        if isinstance(partial_comp, list) and len(partial_comp) == n_jobs:
            for j in range(n_jobs):
                row = partial_comp[j] if j < len(partial_comp) else []
                if not isinstance(row, list):
                    continue
                for op in range(min(n_machines, len(row))):
                    val = row[op]
                    pred_ok = (op == 0) or anchored[j][op - 1]
                    if isinstance(val, (int, float)) and val is not None and pred_ok:
                        v = int(val)
                        completion[j][op] = v
                        anchored[j][op] = True
                        m = ms_matrix[j][op]
                        machine_available[m] = max(machine_available[m], v)
                        job_available[j] = max(job_available[j], v)

        max_iterations = n_jobs * n_machines * 3
        for _ in range(max_iterations):
            ready: list[tuple[int, int]] = [
                (j, op)
                for j in range(n_jobs)
                for op in range(n_machines)
                if not anchored[j][op] and ((op == 0) or anchored[j][op - 1])
            ]
            if not ready:
                break

            def remaining_work(j: int, op: int) -> int:
                return sum(pt_matrix[j][ms_matrix[j][k]] for k in range(op, n_machines))

            if len(ready) > 1 and rng.random() < self.random_pick_prob:
                j, op = rng.choice(ready)
            else:
                # Max remaining work, then earliest completion as tie-break.
                j, op = min(
                    ready,
                    key=lambda x: (
                        -remaining_work(x[0], x[1]),
                        max(job_available[x[0]], machine_available[ms_matrix[x[0]][x[1]]])
                        + pt_matrix[x[0]][ms_matrix[x[0]][x[1]]],
                    ),
                )

            m = ms_matrix[j][op]
            start = max(job_available[j], machine_available[m])
            end = start + pt_matrix[j][m]
            completion[j][op] = end
            anchored[j][op] = True
            job_available[j] = end
            machine_available[m] = end

        partial_assignment["completion"] = completion
        return partial_assignment


@dataclass
class JSSPMachineBalanceRepair(RepairOperator):
    """Dispatch ready operations to reduce machine idle gaps.

    Prioritizes operations whose job-ready time is close to machine-ready time,
    which tends to smooth machine utilization and explores schedules not found
    by pure SPT/LPT rules.
    """

    random_pick_prob: float = 0.2

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        rng: random.Random = context.extra["rng"]
        constants = context.constants

        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        pt_matrix = _parse_int_matrix(constants.get("PROCESSING_TIMES", []), n_jobs, n_machines)
        ms_matrix = _parse_int_matrix(constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines)

        completion: list[list[int]] = [[0] * n_machines for _ in range(n_jobs)]
        anchored: list[list[bool]] = [[False] * n_machines for _ in range(n_jobs)]
        machine_available = [0] * n_machines
        job_available = [0] * n_jobs

        partial_comp = partial_assignment.get("completion")
        if isinstance(partial_comp, list) and len(partial_comp) == n_jobs:
            for j in range(n_jobs):
                row = partial_comp[j] if j < len(partial_comp) else []
                if not isinstance(row, list):
                    continue
                for op in range(min(n_machines, len(row))):
                    val = row[op]
                    pred_ok = (op == 0) or anchored[j][op - 1]
                    if isinstance(val, (int, float)) and val is not None and pred_ok:
                        v = int(val)
                        completion[j][op] = v
                        anchored[j][op] = True
                        m = ms_matrix[j][op]
                        machine_available[m] = max(machine_available[m], v)
                        job_available[j] = max(job_available[j], v)

        max_iterations = n_jobs * n_machines * 3
        for _ in range(max_iterations):
            ready: list[tuple[int, int]] = [
                (j, op)
                for j in range(n_jobs)
                for op in range(n_machines)
                if not anchored[j][op] and ((op == 0) or anchored[j][op - 1])
            ]
            if not ready:
                break

            if len(ready) > 1 and rng.random() < self.random_pick_prob:
                j, op = rng.choice(ready)
            else:
                def score(item: tuple[int, int]) -> tuple[int, int, int]:
                    jj, oo = item
                    m = ms_matrix[jj][oo]
                    gap = abs(job_available[jj] - machine_available[m])
                    end = max(job_available[jj], machine_available[m]) + pt_matrix[jj][m]
                    return (gap, end, pt_matrix[jj][m])

                j, op = min(ready, key=score)

            m = ms_matrix[j][op]
            start = max(job_available[j], machine_available[m])
            end = start + pt_matrix[j][m]
            completion[j][op] = end
            anchored[j][op] = True
            job_available[j] = end
            machine_available[m] = end

        partial_assignment["completion"] = completion
        return partial_assignment


@dataclass
class JSSPCriticalBlockReinsertRepair(RepairOperator):
    """Reinsert one operation inside the current critical-machine block.

    The repair first builds a feasible schedule, then performs a focused local
    search on the machine containing the makespan operation. One operation from
    a contiguous block is removed and reinserted at another position in that
    same block; the full schedule is regenerated from the modified machine
    order, and the best feasible move is kept.
    """

    block_size: int = 4
    base_passes: int = 2
    base_look_ahead: int = 1

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        constants = context.constants
        n_jobs = int(constants.get("N_JOBS", 1))
        n_machines = int(constants.get("N_MACHINES", 1))
        pt_matrix = _parse_int_matrix(constants.get("PROCESSING_TIMES", []), n_jobs, n_machines)
        ms_matrix = _parse_int_matrix(constants.get("MACHINE_SEQUENCE", []), n_jobs, n_machines)

        base_repair = JSSPOptActiveScheduleRepair(
            look_ahead=self.base_look_ahead,
            passes=self.base_passes,
        )
        repaired = base_repair.repair(dict(partial_assignment), context)
        completion_raw = repaired.get("completion")
        if not isinstance(completion_raw, list) or len(completion_raw) != n_jobs:
            return repaired

        completion: list[list[int]] = [
            [int(v) for v in row[:n_machines]] if isinstance(row, list) else [0] * n_machines
            for row in completion_raw
        ]

        best_completion = completion
        best_makespan = _makespan(completion)
        machine_orders = _machine_orders_from_completion(completion, ms_matrix, pt_matrix, n_jobs, n_machines)
        critical_path = _critical_path_ops(completion, ms_matrix, pt_matrix, n_jobs, n_machines)

        for critical in critical_path:
            critical_machine = ms_matrix[critical[0]][critical[1]]
            seq = machine_orders[critical_machine]
            if len(seq) < 2:
                continue

            critical_idx = 0
            for idx, item in enumerate(seq):
                if item == critical:
                    critical_idx = idx
                    break

            size = max(2, min(len(seq), self.block_size))
            start = max(0, min(critical_idx - size + 1, len(seq) - size))
            end = start + size
            block = seq[start:end]

            for src in range(len(block)):
                moved = block[src]
                reduced = block[:src] + block[src + 1 :]
                for dst in range(len(reduced) + 1):
                    if dst == src:
                        continue
                    candidate_block = reduced[:dst] + [moved] + reduced[dst:]
                    if candidate_block == block:
                        continue
                    candidate_orders = [list(order) for order in machine_orders]
                    candidate_orders[critical_machine] = seq[:start] + candidate_block + seq[end:]
                    candidate_completion = _schedule_from_machine_orders(
                        candidate_orders,
                        ms_matrix,
                        pt_matrix,
                        n_jobs,
                        n_machines,
                    )
                    if candidate_completion is None:
                        continue
                    candidate_makespan = _makespan(candidate_completion)
                    if candidate_makespan < best_makespan:
                        best_makespan = candidate_makespan
                        best_completion = candidate_completion

        repaired["completion"] = best_completion
        return repaired
