# Job Shop Scheduling instance: abz7
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 7366

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[21, 30, 24, 12, 27, 31, 25, 26, 27, 17, 19, 18, 26, 39, 16], [11, 24, 36, 15, 28, 26, 30, 15, 23, 26, 28, 19, 20, 15, 20], [22, 14, 20, 12, 22, 16, 35, 32, 16, 17, 23, 29, 19, 23, 22], [32, 19, 29, 13, 30, 21, 29, 14, 20, 20, 24, 29, 33, 18, 25], [24, 28, 24, 24, 18, 18, 32, 16, 24, 23, 34, 23, 15, 20, 28], [25, 33, 26, 23, 15, 40, 35, 34, 24, 28, 36, 19, 13, 38, 21], [17, 29, 39, 30, 27, 36, 21, 33, 19, 13, 21, 17, 12, 27, 12], [13, 36, 27, 21, 19, 27, 29, 22, 14, 20, 40, 37, 12, 39, 39], [27, 32, 21, 27, 21, 40, 16, 28, 24, 26, 13, 29, 28, 32, 27], [34, 11, 28, 24, 15, 39, 33, 23, 30, 26, 15, 31, 35, 11, 18], [36, 31, 39, 27, 20, 37, 25, 25, 13, 25, 28, 14, 29, 31, 14], [22, 18, 29, 11, 31, 28, 15, 32, 21, 20, 18, 25, 17, 35, 19], [38, 36, 36, 28, 15, 32, 20, 19, 14, 32, 16, 12, 39, 37, 22], [20, 29, 21, 27, 34, 33, 27, 28, 28, 33, 17, 21, 23, 20, 40], [11, 34, 14, 30, 23, 14, 23, 27, 33, 21, 12, 16, 38, 40, 34], [13, 18, 29, 36, 17, 33, 33, 36, 25, 13, 23, 13, 13, 24, 40], [21, 31, 28, 25, 12, 15, 31, 39, 35, 16, 33, 36, 40, 27, 19], [12, 18, 20, 31, 13, 12, 26, 32, 39, 20, 14, 17, 22, 29, 31], [13, 12, 13, 17, 38, 18, 17, 38, 30, 16, 30, 20, 40, 15, 22], [16, 14, 22, 31, 29, 33, 28, 11, 39, 31, 17, 22, 27, 36, 14]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 3, 9, 4, 0, 6, 8, 7, 1, 5, 11, 14, 13, 10, 12], [6, 3, 12, 11, 1, 13, 10, 2, 5, 7, 0, 8, 14, 9, 4], [6, 0, 13, 7, 2, 3, 12, 10, 9, 1, 5, 11, 8, 4, 14], [9, 6, 1, 7, 12, 4, 0, 5, 11, 10, 14, 2, 3, 8, 13], [11, 13, 1, 6, 7, 5, 8, 9, 3, 10, 2, 0, 14, 12, 4], [8, 11, 14, 1, 7, 6, 5, 10, 3, 2, 4, 9, 13, 12, 0], [13, 3, 6, 8, 12, 4, 2, 9, 14, 5, 10, 11, 1, 0, 7], [5, 4, 6, 9, 3, 10, 8, 14, 13, 2, 1, 12, 11, 7, 0], [13, 11, 8, 3, 5, 4, 9, 0, 14, 6, 2, 10, 7, 12, 1], [12, 1, 5, 14, 7, 0, 3, 13, 8, 11, 4, 10, 2, 9, 6], [10, 5, 12, 1, 7, 8, 14, 4, 3, 9, 13, 11, 6, 2, 0], [0, 11, 5, 13, 4, 8, 9, 14, 2, 7, 10, 1, 3, 12, 6], [12, 5, 2, 8, 3, 13, 0, 6, 7, 11, 14, 1, 4, 9, 10], [8, 1, 14, 12, 4, 5, 6, 10, 0, 7, 11, 2, 13, 9, 3], [9, 14, 3, 12, 0, 11, 2, 5, 1, 8, 4, 13, 10, 6, 7], [9, 14, 7, 4, 0, 5, 8, 13, 10, 3, 2, 1, 11, 6, 12], [3, 5, 2, 12, 7, 1, 8, 6, 11, 4, 10, 14, 9, 13, 0], [12, 10, 0, 2, 5, 1, 11, 8, 14, 3, 7, 9, 13, 4, 6], [5, 10, 7, 14, 13, 11, 9, 3, 1, 2, 12, 6, 8, 4, 0], [9, 8, 12, 1, 5, 3, 11, 13, 0, 7, 14, 4, 6, 2, 10]]

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
