# Job Shop Scheduling instance: abz8
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 7586

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[19, 31, 32, 34, 36, 26, 25, 13, 34, 33, 39, 40, 33, 18, 30], [29, 23, 40, 20, 25, 12, 38, 39, 26, 11, 22, 22, 19, 19, 19], [24, 39, 35, 25, 17, 39, 20, 38, 17, 19, 32, 24, 31, 40, 16], [39, 13, 34, 36, 30, 40, 25, 18, 26, 12, 31, 37, 17, 12, 22], [38, 35, 38, 40, 21, 11, 22, 13, 32, 16, 31, 23, 32, 37, 15], [20, 30, 27, 28, 12, 14, 25, 29, 11, 11, 23, 26, 38, 21, 27], [15, 27, 32, 12, 40, 17, 39, 38, 38, 27, 22, 22, 27, 20, 21], [26, 15, 29, 21, 28, 30, 33, 33, 15, 19, 38, 11, 21, 24, 13], [16, 19, 18, 34, 35, 26, 17, 12, 20, 23, 16, 26, 24, 27, 13], [38, 18, 30, 17, 21, 40, 17, 37, 22, 40, 30, 24, 32, 24, 27], [22, 22, 29, 17, 33, 22, 18, 23, 19, 39, 34, 19, 17, 36, 35], [11, 11, 15, 22, 13, 13, 32, 24, 13, 38, 33, 17, 24, 25, 16], [20, 37, 26, 11, 14, 29, 36, 32, 25, 34, 25, 12, 12, 16, 16], [14, 36, 31, 33, 37, 34, 26, 33, 20, 38, 24, 27, 39, 15, 34], [17, 21, 34, 40, 26, 32, 13, 19, 31, 13, 17, 25, 40, 14, 23], [19, 35, 31, 14, 12, 26, 35, 19, 38, 29, 36, 35, 17, 17, 37], [33, 30, 29, 16, 37, 27, 31, 31, 16, 37, 14, 38, 28, 36, 20], [39, 11, 26, 37, 12, 12, 15, 19, 14, 18, 29, 18, 11, 32, 16], [20, 38, 11, 39, 19, 28, 33, 31, 28, 35, 34, 11, 22, 17, 20], [19, 24, 12, 26, 12, 23, 27, 17, 21, 30, 36, 39, 25, 34, 23]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 9, 2, 13, 10, 8, 6, 4, 11, 12, 1, 14, 3, 5, 7], [9, 10, 14, 5, 4, 6, 0, 7, 13, 11, 1, 3, 2, 12, 8], [3, 8, 11, 13, 10, 14, 5, 9, 0, 1, 4, 2, 7, 6, 12], [14, 3, 2, 12, 4, 13, 1, 6, 9, 7, 10, 0, 5, 8, 11], [12, 14, 1, 7, 8, 11, 6, 4, 0, 2, 3, 10, 5, 13, 9], [10, 12, 8, 14, 9, 6, 5, 4, 2, 11, 7, 3, 13, 0, 1], [6, 8, 0, 12, 10, 9, 2, 4, 3, 13, 14, 11, 5, 7, 1], [11, 13, 10, 8, 9, 14, 5, 0, 2, 6, 12, 1, 3, 4, 7], [8, 6, 5, 3, 9, 0, 2, 4, 12, 10, 11, 7, 14, 13, 1], [1, 7, 14, 9, 5, 6, 8, 3, 10, 0, 4, 12, 11, 13, 2], [11, 0, 13, 6, 5, 3, 14, 10, 7, 8, 2, 1, 12, 4, 9], [6, 3, 12, 5, 4, 1, 0, 13, 8, 2, 10, 11, 14, 9, 7], [14, 13, 1, 8, 2, 3, 9, 4, 0, 6, 12, 5, 10, 7, 11], [8, 10, 11, 9, 5, 12, 7, 4, 2, 13, 14, 3, 6, 1, 0], [8, 0, 9, 1, 10, 7, 13, 3, 5, 11, 2, 14, 6, 12, 4], [8, 12, 3, 13, 4, 1, 6, 0, 10, 7, 9, 2, 5, 11, 14], [14, 3, 0, 10, 5, 7, 8, 6, 12, 9, 4, 2, 11, 1, 13], [11, 3, 14, 6, 8, 12, 13, 5, 1, 10, 7, 4, 9, 2, 0], [11, 2, 12, 9, 14, 7, 4, 3, 5, 6, 10, 1, 0, 13, 8], [2, 12, 5, 8, 6, 9, 14, 11, 3, 13, 7, 1, 4, 0, 10]]

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
