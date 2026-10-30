# Job Shop Scheduling instance: abz9
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 7442

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[15, 11, 23, 13, 11, 21, 14, 11, 13, 35, 18, 17, 11, 20, 35], [13, 35, 14, 26, 34, 31, 14, 38, 16, 17, 19, 15, 20, 12, 12], [30, 40, 40, 40, 35, 17, 30, 38, 29, 26, 35, 36, 11, 37, 23], [23, 40, 29, 12, 12, 18, 16, 40, 23, 14, 23, 25, 14, 16, 32], [38, 23, 35, 15, 30, 27, 32, 29, 29, 37, 27, 28, 31, 11, 17], [33, 21, 31, 33, 38, 33, 19, 36, 35, 40, 19, 28, 40, 26, 25], [32, 17, 34, 35, 32, 15, 28, 23, 19, 14, 32, 33, 18, 25, 26], [14, 40, 16, 21, 32, 26, 15, 30, 12, 34, 35, 30, 33, 40, 26], [14, 29, 17, 36, 15, 40, 24, 23, 26, 20, 16, 23, 22, 11, 20], [34, 36, 11, 40, 27, 15, 23, 30, 31, 37, 12, 14, 32, 25, 28], [22, 19, 17, 27, 27, 25, 20, 14, 14, 22, 21, 27, 22, 25, 18], [22, 37, 32, 29, 31, 39, 40, 17, 33, 13, 15, 16, 20, 34, 34], [22, 11, 24, 17, 17, 19, 12, 31, 11, 25, 12, 31, 27, 33, 11], [16, 30, 18, 34, 22, 22, 29, 20, 32, 11, 32, 18, 33, 19, 15], [12, 24, 18, 26, 18, 27, 37, 27, 34, 40, 28, 11, 12, 26, 19], [20, 13, 34, 23, 25, 28, 32, 38, 15, 25, 32, 11, 14, 20, 16], [29, 15, 13, 14, 13, 24, 35, 22, 37, 34, 22, 19, 26, 32, 22], [34, 35, 13, 22, 33, 33, 30, 36, 12, 20, 30, 12, 35, 28, 29], [17, 22, 38, 39, 27, 35, 14, 26, 29, 13, 35, 31, 15, 19, 26], [16, 36, 16, 27, 19, 16, 39, 34, 17, 40, 39, 33, 35, 29, 38]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 5, 8, 4, 1, 14, 13, 11, 10, 12, 2, 3, 0, 7, 9], [1, 5, 0, 3, 6, 9, 7, 12, 10, 13, 8, 4, 11, 14, 2], [0, 4, 2, 10, 6, 14, 8, 13, 7, 3, 9, 12, 1, 11, 5], [7, 5, 4, 8, 0, 9, 13, 12, 10, 3, 6, 14, 1, 11, 2], [2, 3, 12, 11, 6, 4, 10, 7, 0, 13, 1, 14, 5, 9, 8], [5, 3, 6, 12, 10, 0, 13, 2, 11, 7, 4, 1, 14, 9, 8], [13, 0, 11, 12, 4, 6, 5, 3, 9, 2, 7, 10, 1, 14, 8], [2, 12, 9, 11, 13, 8, 14, 5, 6, 3, 1, 4, 0, 7, 10], [2, 10, 14, 6, 8, 3, 12, 0, 13, 9, 7, 1, 11, 4, 5], [4, 9, 3, 11, 13, 7, 0, 2, 5, 12, 1, 10, 14, 8, 6], [13, 0, 3, 8, 5, 6, 14, 7, 1, 2, 4, 9, 12, 11, 10], [14, 10, 0, 3, 13, 6, 7, 2, 12, 5, 4, 11, 1, 8, 9], [6, 12, 4, 2, 8, 5, 14, 3, 9, 1, 11, 13, 7, 10, 0], [5, 14, 0, 8, 7, 4, 9, 13, 1, 12, 6, 11, 3, 10, 2], [5, 3, 10, 6, 4, 12, 11, 13, 7, 9, 14, 1, 2, 0, 8], [8, 5, 9, 6, 1, 7, 11, 2, 4, 0, 10, 3, 12, 14, 13], [1, 4, 8, 3, 10, 5, 12, 7, 9, 14, 11, 13, 0, 2, 6], [7, 5, 13, 9, 10, 4, 14, 0, 3, 11, 6, 8, 1, 2, 12], [14, 11, 5, 2, 13, 10, 4, 8, 3, 9, 6, 7, 0, 1, 12], [1, 7, 11, 8, 14, 6, 5, 3, 13, 2, 0, 4, 9, 12, 10]]

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
