# Job Shop Scheduling instance: ta30
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20052

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[51, 86, 46, 36, 37, 56, 34, 77, 62, 15, 8, 52, 60, 5, 11, 9, 43, 86, 84, 43], [12, 73, 63, 78, 53, 1, 99, 65, 60, 31, 62, 97, 3, 56, 8, 63, 16, 32, 61, 12], [27, 86, 55, 58, 59, 21, 15, 53, 2, 38, 86, 17, 42, 70, 34, 77, 85, 12, 20, 32], [21, 94, 3, 58, 21, 67, 91, 54, 86, 92, 56, 63, 57, 68, 87, 88, 13, 7, 8, 13], [24, 34, 89, 18, 12, 48, 90, 75, 62, 95, 18, 38, 29, 4, 17, 74, 11, 15, 21, 35], [91, 75, 49, 78, 31, 70, 11, 7, 74, 80, 99, 8, 14, 90, 67, 22, 66, 66, 80, 13], [51, 76, 86, 27, 33, 18, 31, 71, 9, 63, 87, 97, 70, 45, 48, 63, 74, 11, 1, 76], [94, 72, 2, 71, 81, 17, 61, 4, 22, 18, 30, 17, 5, 38, 93, 16, 20, 64, 19, 15], [80, 59, 32, 95, 9, 90, 20, 70, 76, 2, 46, 66, 62, 72, 82, 61, 74, 78, 97, 41], [82, 13, 86, 62, 37, 82, 29, 61, 28, 19, 92, 84, 15, 62, 89, 59, 48, 45, 90, 86], [55, 68, 43, 18, 49, 44, 94, 53, 32, 97, 79, 61, 47, 86, 67, 50, 3, 7, 79, 85], [24, 9, 25, 9, 26, 4, 60, 42, 54, 90, 20, 77, 72, 62, 50, 61, 69, 5, 19, 43], [26, 50, 81, 47, 36, 72, 40, 45, 97, 42, 58, 94, 84, 59, 90, 33, 28, 44, 85, 73], [2, 40, 81, 17, 97, 30, 46, 7, 9, 26, 69, 46, 44, 9, 81, 99, 73, 67, 88, 81], [93, 40, 86, 62, 97, 3, 75, 96, 46, 9, 16, 16, 30, 69, 50, 15, 29, 62, 90, 30], [81, 86, 64, 38, 62, 23, 95, 35, 73, 31, 88, 60, 5, 36, 12, 65, 54, 2, 26, 56], [36, 98, 67, 66, 62, 99, 3, 93, 30, 3, 90, 82, 17, 32, 1, 79, 1, 75, 20, 81], [35, 63, 23, 26, 76, 28, 79, 58, 54, 16, 13, 47, 68, 28, 52, 84, 86, 76, 22, 52], [99, 4, 62, 34, 37, 97, 25, 26, 19, 11, 53, 46, 48, 29, 98, 68, 24, 54, 60, 74], [65, 33, 87, 87, 63, 24, 52, 91, 26, 10, 17, 15, 89, 41, 58, 67, 3, 92, 77, 67]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[18, 15, 6, 8, 14, 12, 19, 11, 7, 4, 9, 16, 10, 13, 3, 5, 2, 0, 1, 17], [18, 13, 8, 3, 1, 19, 14, 16, 0, 2, 9, 10, 11, 4, 5, 12, 6, 7, 15, 17], [10, 7, 4, 17, 14, 0, 8, 1, 16, 5, 3, 13, 2, 15, 6, 18, 19, 12, 11, 9], [2, 19, 5, 16, 11, 15, 13, 4, 0, 8, 17, 6, 18, 10, 9, 3, 1, 7, 12, 14], [12, 15, 2, 3, 11, 7, 10, 17, 9, 16, 0, 13, 4, 14, 1, 19, 8, 6, 5, 18], [6, 12, 13, 8, 14, 0, 5, 11, 7, 2, 19, 3, 1, 18, 4, 15, 10, 16, 9, 17], [11, 15, 17, 7, 18, 9, 12, 4, 16, 1, 2, 10, 8, 5, 0, 3, 14, 6, 13, 19], [18, 17, 0, 7, 4, 12, 1, 10, 2, 15, 13, 14, 19, 5, 6, 3, 9, 8, 11, 16], [15, 11, 12, 7, 1, 0, 14, 9, 18, 8, 13, 5, 16, 3, 19, 4, 10, 6, 17, 2], [7, 18, 4, 19, 12, 9, 13, 5, 2, 15, 10, 14, 0, 16, 1, 6, 8, 17, 11, 3], [17, 13, 18, 14, 19, 1, 6, 11, 12, 4, 15, 0, 16, 3, 10, 8, 2, 9, 7, 5], [10, 14, 12, 9, 2, 0, 19, 5, 4, 13, 7, 11, 3, 15, 18, 16, 1, 6, 17, 8], [7, 19, 1, 10, 11, 14, 8, 9, 4, 5, 12, 15, 17, 13, 3, 6, 2, 18, 0, 16], [17, 11, 13, 1, 2, 4, 7, 0, 10, 8, 3, 19, 14, 6, 9, 5, 18, 16, 12, 15], [11, 3, 5, 19, 10, 1, 17, 7, 6, 13, 2, 18, 0, 15, 12, 8, 14, 16, 9, 4], [12, 8, 16, 0, 18, 13, 7, 19, 4, 9, 17, 5, 11, 14, 10, 3, 6, 15, 1, 2], [9, 5, 19, 7, 11, 12, 16, 14, 13, 0, 8, 4, 10, 18, 1, 6, 3, 17, 15, 2], [19, 4, 6, 1, 14, 2, 0, 18, 7, 10, 3, 12, 15, 9, 13, 5, 8, 17, 16, 11], [19, 3, 15, 4, 7, 12, 13, 16, 18, 14, 17, 5, 8, 0, 2, 11, 6, 10, 9, 1], [11, 17, 13, 4, 3, 15, 18, 12, 0, 10, 5, 19, 9, 2, 7, 14, 6, 8, 1, 16]]

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
