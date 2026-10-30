# Job Shop Scheduling instance: ta14
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14310

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[69, 30, 83, 17, 90, 88, 30, 63, 56, 42, 9, 20, 22, 25, 75], [72, 59, 16, 79, 20, 56, 35, 52, 35, 66, 14, 39, 15, 60, 2], [70, 14, 49, 49, 55, 30, 92, 40, 81, 31, 50, 13, 77, 70, 5], [64, 21, 48, 8, 30, 60, 52, 37, 25, 93, 21, 29, 63, 24, 10], [48, 22, 4, 89, 10, 23, 32, 30, 45, 59, 60, 42, 37, 77, 15], [23, 14, 13, 44, 10, 57, 27, 95, 29, 30, 45, 98, 42, 68, 61], [51, 55, 86, 23, 21, 55, 50, 9, 48, 22, 50, 25, 55, 87, 47], [33, 73, 37, 59, 18, 11, 20, 43, 65, 87, 84, 31, 92, 34, 26], [94, 89, 20, 9, 21, 55, 11, 97, 91, 34, 96, 11, 61, 28, 92], [35, 74, 87, 10, 18, 80, 12, 6, 5, 22, 86, 58, 95, 64, 86], [82, 79, 7, 74, 14, 20, 60, 20, 32, 47, 68, 54, 6, 46, 6], [26, 1, 86, 33, 16, 99, 50, 20, 35, 25, 98, 55, 87, 23, 78], [34, 65, 14, 77, 38, 48, 66, 13, 85, 58, 52, 35, 47, 33, 71], [18, 31, 85, 32, 15, 81, 68, 83, 78, 86, 12, 38, 10, 80, 44], [28, 41, 34, 39, 8, 16, 60, 56, 24, 52, 39, 69, 37, 57, 58], [28, 58, 48, 41, 12, 32, 4, 13, 91, 36, 76, 83, 68, 62, 87], [47, 98, 93, 66, 41, 1, 34, 84, 93, 58, 64, 67, 83, 75, 86], [84, 11, 35, 8, 61, 74, 92, 31, 14, 53, 12, 57, 50, 50, 49], [37, 10, 75, 60, 66, 75, 38, 19, 61, 49, 67, 77, 52, 94, 89], [95, 90, 60, 10, 39, 2, 99, 62, 19, 21, 70, 29, 40, 73, 17]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 13, 3, 7, 10, 6, 14, 12, 9, 2, 0, 4, 5, 11, 1], [11, 4, 6, 3, 8, 9, 12, 5, 13, 0, 7, 10, 14, 2, 1], [14, 9, 4, 0, 2, 13, 6, 7, 11, 1, 3, 5, 10, 12, 8], [0, 12, 10, 1, 11, 14, 8, 5, 9, 13, 2, 6, 3, 4, 7], [2, 6, 4, 13, 8, 12, 3, 10, 9, 11, 0, 7, 1, 5, 14], [1, 4, 13, 7, 12, 8, 3, 0, 14, 5, 10, 11, 9, 6, 2], [6, 12, 3, 11, 0, 1, 7, 13, 4, 8, 5, 9, 14, 10, 2], [5, 7, 14, 11, 4, 3, 10, 0, 1, 6, 13, 12, 8, 9, 2], [3, 2, 6, 4, 11, 10, 0, 8, 14, 7, 13, 5, 1, 9, 12], [3, 11, 14, 10, 2, 4, 1, 13, 6, 9, 5, 8, 12, 7, 0], [9, 10, 6, 7, 4, 12, 5, 14, 13, 1, 8, 0, 2, 3, 11], [7, 5, 11, 14, 8, 0, 13, 12, 2, 9, 10, 1, 4, 3, 6], [11, 0, 6, 12, 5, 10, 13, 3, 4, 1, 9, 14, 2, 8, 7], [2, 9, 4, 6, 3, 7, 13, 5, 12, 10, 1, 11, 8, 14, 0], [6, 14, 5, 8, 13, 4, 1, 3, 0, 7, 12, 2, 10, 11, 9], [10, 14, 8, 7, 6, 5, 1, 13, 11, 2, 3, 9, 12, 0, 4], [5, 11, 1, 4, 7, 6, 14, 13, 8, 12, 3, 2, 0, 9, 10], [4, 14, 2, 6, 0, 11, 7, 13, 9, 1, 5, 3, 8, 10, 12], [7, 14, 10, 1, 5, 9, 2, 4, 0, 11, 13, 3, 6, 12, 8], [11, 13, 7, 8, 6, 0, 5, 4, 10, 1, 3, 2, 9, 12, 14]]

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
