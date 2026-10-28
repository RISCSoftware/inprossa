# Job Shop Scheduling instance: ta35
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 22433

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[72, 80, 94, 4, 23, 76, 16, 44, 76, 97, 5, 27, 9, 38, 90], [47, 32, 55, 48, 69, 8, 25, 90, 84, 25, 34, 37, 62, 2, 92], [96, 12, 36, 89, 6, 76, 56, 17, 80, 42, 54, 26, 87, 71, 1], [11, 38, 37, 6, 95, 25, 34, 50, 98, 69, 98, 19, 19, 76, 50], [36, 41, 55, 94, 22, 78, 32, 59, 58, 56, 63, 22, 10, 16, 6], [93, 69, 7, 84, 10, 90, 12, 59, 95, 48, 14, 23, 64, 93, 95], [17, 76, 63, 59, 6, 3, 94, 30, 43, 27, 29, 25, 1, 42, 77], [27, 59, 27, 43, 6, 56, 32, 59, 5, 48, 27, 11, 14, 43, 25], [67, 63, 4, 25, 49, 9, 40, 47, 14, 75, 29, 15, 32, 21, 27], [36, 87, 86, 22, 70, 16, 52, 97, 70, 99, 1, 93, 2, 43, 87], [63, 63, 5, 22, 63, 69, 90, 67, 28, 79, 46, 23, 35, 77, 24], [25, 69, 71, 38, 29, 88, 25, 51, 65, 66, 24, 20, 34, 70, 58], [84, 70, 29, 97, 68, 66, 56, 60, 21, 34, 80, 50, 55, 4, 4], [52, 38, 81, 7, 14, 66, 50, 38, 59, 88, 97, 72, 33, 80, 46], [41, 10, 94, 78, 53, 86, 76, 13, 98, 89, 88, 35, 99, 50, 25], [42, 35, 98, 35, 79, 92, 40, 52, 44, 44, 71, 35, 17, 16, 73], [82, 74, 61, 70, 39, 55, 84, 75, 47, 46, 44, 89, 80, 26, 34], [12, 8, 76, 77, 43, 56, 57, 80, 69, 89, 34, 42, 40, 77, 25], [99, 1, 76, 89, 89, 49, 44, 37, 98, 2, 3, 50, 96, 73, 53], [32, 92, 89, 31, 94, 22, 62, 7, 66, 23, 44, 10, 91, 2, 70], [21, 13, 64, 58, 55, 36, 46, 23, 33, 92, 66, 70, 15, 57, 67], [34, 67, 35, 90, 80, 48, 93, 74, 76, 39, 70, 94, 49, 58, 46], [99, 90, 99, 72, 42, 5, 59, 36, 17, 17, 83, 24, 60, 37, 10], [26, 59, 24, 1, 89, 96, 22, 30, 94, 29, 69, 99, 13, 47, 66], [79, 82, 9, 91, 1, 8, 54, 87, 36, 42, 21, 52, 66, 33, 59], [22, 69, 43, 72, 83, 48, 40, 93, 85, 89, 31, 83, 68, 67, 76], [64, 98, 63, 15, 7, 21, 35, 89, 95, 67, 54, 79, 54, 59, 26], [87, 16, 36, 93, 8, 90, 59, 15, 40, 20, 8, 57, 61, 14, 14], [60, 87, 12, 19, 19, 8, 2, 73, 6, 82, 37, 81, 12, 2, 35], [70, 7, 55, 99, 14, 39, 9, 9, 29, 47, 4, 78, 75, 18, 59]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 11, 14, 5, 8, 6, 13, 0, 1, 2, 9, 10, 7, 12, 4], [0, 3, 4, 8, 9, 10, 5, 1, 12, 7, 13, 14, 2, 6, 11], [12, 10, 5, 8, 7, 14, 11, 2, 1, 6, 13, 4, 9, 3, 0], [5, 0, 9, 1, 8, 14, 10, 7, 11, 13, 3, 4, 12, 2, 6], [12, 6, 3, 11, 2, 8, 14, 5, 0, 9, 13, 4, 7, 1, 10], [6, 7, 14, 13, 0, 2, 8, 4, 11, 9, 3, 12, 10, 5, 1], [8, 12, 9, 7, 11, 5, 6, 14, 4, 13, 0, 1, 10, 2, 3], [12, 7, 10, 1, 5, 4, 9, 13, 2, 0, 3, 6, 11, 8, 14], [8, 7, 13, 12, 10, 6, 1, 3, 4, 2, 0, 14, 5, 9, 11], [8, 7, 6, 3, 14, 1, 0, 2, 12, 11, 10, 5, 4, 9, 13], [2, 8, 13, 11, 1, 5, 12, 3, 6, 10, 7, 4, 0, 14, 9], [1, 6, 8, 4, 7, 5, 13, 0, 14, 11, 10, 3, 12, 2, 9], [14, 13, 9, 8, 7, 12, 1, 4, 10, 6, 2, 3, 0, 5, 11], [9, 2, 6, 1, 0, 3, 12, 14, 8, 7, 4, 5, 11, 13, 10], [11, 10, 8, 3, 5, 7, 2, 14, 13, 6, 9, 0, 4, 1, 12], [0, 13, 8, 6, 3, 10, 7, 11, 2, 14, 5, 9, 1, 4, 12], [9, 5, 1, 12, 11, 2, 14, 7, 4, 8, 3, 6, 13, 10, 0], [13, 12, 4, 2, 8, 11, 14, 10, 1, 3, 6, 5, 7, 0, 9], [12, 14, 10, 5, 2, 7, 11, 13, 8, 6, 3, 9, 1, 0, 4], [7, 12, 0, 10, 13, 8, 6, 5, 9, 1, 14, 3, 11, 4, 2], [6, 12, 7, 11, 13, 14, 3, 9, 10, 4, 1, 8, 2, 5, 0], [9, 2, 3, 1, 10, 11, 5, 8, 6, 14, 0, 13, 7, 12, 4], [0, 14, 1, 12, 5, 8, 11, 10, 13, 6, 9, 2, 4, 3, 7], [8, 10, 13, 5, 7, 9, 6, 0, 11, 12, 1, 14, 4, 3, 2], [3, 10, 9, 0, 5, 2, 12, 4, 14, 8, 6, 11, 7, 1, 13], [10, 7, 12, 3, 0, 8, 6, 14, 5, 11, 9, 4, 2, 1, 13], [0, 13, 2, 12, 5, 11, 6, 8, 4, 9, 3, 7, 10, 1, 14], [14, 3, 0, 7, 8, 9, 12, 10, 4, 11, 13, 5, 1, 2, 6], [13, 1, 5, 6, 2, 14, 8, 7, 9, 10, 3, 11, 4, 12, 0], [10, 7, 1, 14, 8, 5, 2, 13, 0, 4, 9, 12, 11, 3, 6]]

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
