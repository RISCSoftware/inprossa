# Job Shop Scheduling instance: la34
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 10
MAX_TIME : int = 15341

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[27, 35, 51, 81, 74, 73, 13, 59, 32, 65], [28, 55, 33, 38, 64, 75, 53, 33, 10, 49], [6, 23, 72, 7, 39, 52, 83, 21, 90, 72], [61, 23, 93, 82, 78, 21, 88, 53, 65, 28], [81, 70, 62, 77, 41, 73, 12, 24, 6, 12], [15, 51, 33, 28, 98, 94, 42, 99, 15, 72], [32, 94, 23, 31, 15, 7, 78, 86, 22, 96], [24, 42, 97, 43, 35, 73, 72, 93, 68, 88], [44, 63, 14, 49, 17, 67, 85, 5, 13, 66], [8, 68, 99, 72, 26, 27, 21, 82, 45, 15], [51, 96, 56, 49, 93, 53, 23, 52, 54, 36], [14, 23, 24, 38, 70, 83, 48, 37, 60, 55], [62, 82, 37, 12, 45, 33, 26, 15, 69, 23], [59, 9, 73, 64, 87, 28, 72, 15, 92, 12], [50, 14, 80, 71, 48, 46, 44, 90, 24, 61], [22, 97, 54, 73, 46, 16, 61, 75, 54, 94], [40, 32, 6, 67, 30, 93, 77, 6, 47, 55], [22, 30, 7, 98, 92, 9, 79, 79, 36, 36], [49, 82, 52, 73, 31, 7, 82, 72, 37, 54], [35, 73, 76, 83, 43, 92, 28, 45, 39, 29], [26, 48, 58, 80, 98, 70, 96, 34, 52, 94], [42, 70, 93, 21, 14, 26, 90, 18, 23, 36], [17, 84, 67, 43, 28, 84, 76, 25, 87, 88], [21, 92, 15, 91, 80, 8, 12, 30, 52, 37], [47, 28, 77, 15, 7, 39, 92, 46, 54, 69], [41, 24, 64, 5, 93, 44, 33, 75, 38, 50], [17, 61, 21, 34, 63, 77, 87, 94, 92, 28], [50, 43, 9, 72, 28, 95, 64, 96, 98, 5], [85, 98, 85, 71, 55, 60, 35, 24, 39, 22], [90, 11, 46, 78, 70, 20, 49, 6, 74, 34]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 7, 1, 5, 9, 0, 6, 3, 8, 4], [4, 7, 5, 2, 8, 0, 3, 6, 9, 1], [6, 1, 2, 3, 9, 0, 4, 5, 8, 7], [3, 1, 2, 4, 6, 7, 9, 8, 5, 0], [4, 6, 9, 3, 1, 7, 0, 5, 2, 8], [4, 3, 6, 9, 0, 8, 5, 2, 1, 7], [0, 8, 9, 4, 6, 3, 5, 1, 2, 7], [7, 2, 3, 5, 0, 8, 9, 1, 4, 6], [2, 0, 8, 5, 1, 3, 7, 4, 6, 9], [7, 9, 3, 4, 0, 1, 6, 8, 2, 5], [4, 6, 0, 8, 3, 1, 2, 9, 5, 7], [8, 0, 4, 9, 1, 5, 3, 2, 7, 6], [0, 7, 8, 9, 1, 6, 4, 5, 3, 2], [6, 1, 7, 5, 8, 9, 0, 3, 4, 2], [0, 1, 7, 5, 3, 4, 2, 9, 8, 6], [0, 9, 5, 3, 2, 8, 4, 1, 6, 7], [9, 3, 6, 4, 7, 1, 8, 5, 2, 0], [1, 3, 7, 0, 6, 2, 8, 9, 5, 4], [8, 7, 2, 4, 1, 9, 5, 6, 3, 0], [1, 3, 7, 2, 4, 9, 0, 5, 8, 6], [2, 0, 1, 8, 7, 6, 5, 4, 3, 9], [1, 8, 5, 4, 6, 2, 3, 0, 7, 9], [4, 6, 7, 0, 1, 2, 8, 3, 9, 5], [7, 3, 8, 4, 0, 5, 9, 2, 6, 1], [1, 4, 7, 6, 2, 3, 9, 8, 0, 5], [9, 5, 2, 8, 4, 6, 7, 0, 1, 3], [7, 0, 6, 2, 8, 9, 1, 4, 3, 5], [3, 8, 9, 4, 2, 5, 6, 1, 0, 7], [0, 2, 8, 1, 7, 3, 5, 4, 9, 6], [3, 6, 2, 1, 0, 5, 9, 7, 4, 8]]

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
