# Job Shop Scheduling instance: swv09
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15024

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[69, 78, 38, 73, 62, 8, 6, 48, 59, 79, 80, 22, 58, 77, 49], [5, 82, 69, 34, 29, 63, 94, 15, 61, 29, 5, 94, 61, 75, 17], [25, 52, 30, 46, 86, 3, 17, 9, 53, 23, 68, 34, 71, 76, 70], [53, 97, 50, 24, 20, 79, 92, 75, 59, 74, 75, 99, 52, 84, 3], [61, 6, 15, 47, 38, 21, 49, 70, 71, 33, 100, 8, 18, 24, 83], [92, 23, 66, 58, 48, 50, 2, 36, 66, 84, 12, 12, 88, 64, 4], [25, 44, 42, 29, 86, 87, 44, 58, 28, 74, 86, 16, 94, 59, 77], [94, 93, 44, 58, 31, 69, 92, 79, 63, 80, 75, 39, 47, 3, 80], [76, 69, 27, 16, 31, 19, 86, 35, 24, 69, 43, 37, 33, 19, 9], [42, 60, 75, 78, 60, 59, 41, 54, 31, 20, 15, 61, 18, 69, 60], [55, 27, 21, 2, 89, 78, 20, 97, 41, 70, 99, 77, 30, 79, 98], [14, 9, 10, 51, 84, 72, 1, 22, 10, 19, 100, 43, 14, 65, 65], [81, 42, 13, 49, 89, 50, 75, 79, 25, 100, 7, 38, 78, 37, 54], [60, 42, 44, 77, 9, 26, 73, 100, 46, 61, 85, 92, 14, 12, 49], [53, 43, 72, 13, 87, 65, 59, 76, 71, 71, 89, 2, 25, 12, 21], [6, 36, 60, 96, 48, 33, 28, 54, 39, 40, 60, 79, 20, 34, 52], [21, 21, 12, 11, 61, 82, 34, 95, 7, 4, 62, 82, 86, 54, 53], [13, 87, 11, 46, 87, 72, 97, 45, 43, 39, 30, 66, 55, 34, 85], [19, 39, 69, 30, 73, 19, 63, 13, 14, 36, 96, 62, 27, 59, 76], [96, 7, 27, 79, 14, 24, 43, 27, 69, 96, 79, 30, 2, 34, 75]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[5, 3, 0, 2, 6, 4, 1, 9, 8, 13, 11, 10, 12, 14, 7], [3, 4, 2, 0, 5, 1, 6, 14, 11, 9, 10, 13, 7, 8, 12], [1, 2, 0, 6, 3, 4, 5, 14, 11, 9, 10, 13, 8, 12, 7], [2, 4, 3, 0, 1, 5, 6, 14, 12, 10, 9, 8, 7, 13, 11], [2, 0, 3, 4, 6, 5, 1, 11, 8, 14, 13, 12, 9, 7, 10], [4, 5, 2, 0, 6, 3, 1, 9, 8, 10, 7, 14, 12, 13, 11], [3, 0, 6, 5, 2, 1, 4, 8, 10, 9, 14, 13, 12, 7, 11], [4, 3, 0, 5, 2, 1, 6, 9, 8, 12, 13, 7, 11, 14, 10], [1, 2, 0, 5, 6, 3, 4, 12, 9, 13, 10, 14, 11, 7, 8], [2, 3, 6, 4, 5, 0, 1, 12, 8, 10, 7, 14, 9, 11, 13], [4, 6, 1, 5, 3, 2, 0, 13, 11, 10, 9, 12, 7, 8, 14], [6, 2, 4, 5, 0, 1, 3, 7, 14, 10, 13, 11, 8, 12, 9], [5, 2, 3, 6, 1, 0, 4, 9, 14, 13, 10, 11, 8, 12, 7], [2, 3, 5, 1, 4, 6, 0, 9, 10, 12, 11, 7, 14, 8, 13], [2, 0, 1, 5, 6, 4, 3, 8, 12, 9, 10, 11, 7, 14, 13], [2, 6, 5, 1, 0, 3, 4, 9, 11, 10, 8, 13, 7, 12, 14], [5, 2, 3, 4, 1, 0, 6, 12, 14, 8, 9, 7, 10, 13, 11], [5, 0, 3, 6, 1, 4, 2, 7, 14, 11, 8, 9, 13, 10, 12], [1, 5, 0, 4, 6, 3, 2, 9, 7, 10, 12, 13, 14, 11, 8], [1, 4, 3, 2, 6, 0, 5, 11, 7, 12, 8, 14, 13, 10, 9]]

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
