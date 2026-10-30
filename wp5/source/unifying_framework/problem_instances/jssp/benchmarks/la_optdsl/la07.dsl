# Job Shop Scheduling instance: la07
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 5
MAX_TIME : int = 3745

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[47, 71, 14, 96, 57], [75, 60, 65, 79, 22], [33, 31, 69, 32, 58], [44, 34, 47, 58, 51], [62, 44, 17, 29, 8], [97, 15, 40, 66, 38], [57, 39, 58, 50, 20], [63, 21, 57, 32, 87], [84, 85, 90, 61, 56], [20, 67, 70, 30, 15], [82, 23, 45, 38, 84], [18, 29, 21, 50, 41], [52, 52, 38, 54, 16], [54, 62, 74, 57, 37], [81, 61, 30, 68, 57]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 4, 1, 3, 2], [0, 1, 4, 3, 2], [3, 0, 2, 1, 4], [0, 1, 4, 3, 2], [3, 1, 0, 2, 4], [1, 2, 0, 4, 3], [2, 1, 0, 4, 3], [2, 3, 4, 0, 1], [4, 0, 2, 1, 3], [4, 0, 1, 3, 2], [4, 0, 1, 2, 3], [3, 2, 0, 4, 1], [4, 1, 0, 2, 3], [4, 0, 3, 2, 1], [4, 1, 0, 2, 3]]

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
