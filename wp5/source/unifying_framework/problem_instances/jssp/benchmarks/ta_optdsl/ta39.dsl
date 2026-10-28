# Job Shop Scheduling instance: ta39
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 21583

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[95, 75, 64, 56, 24, 20, 15, 35, 27, 6, 79, 60, 69, 37, 84], [56, 27, 30, 74, 30, 32, 11, 58, 44, 46, 55, 57, 43, 41, 63], [50, 75, 28, 37, 71, 13, 8, 99, 83, 43, 56, 57, 70, 14, 86], [73, 47, 10, 87, 11, 68, 27, 30, 66, 17, 22, 70, 21, 10, 33], [6, 11, 73, 1, 88, 69, 46, 84, 84, 50, 52, 49, 92, 50, 12], [85, 7, 67, 35, 68, 30, 64, 79, 22, 22, 11, 65, 14, 75, 45], [40, 36, 53, 58, 93, 55, 45, 10, 67, 85, 3, 20, 17, 66, 63], [39, 42, 67, 58, 27, 63, 54, 37, 8, 18, 68, 16, 32, 75, 24], [48, 22, 12, 3, 68, 27, 16, 33, 25, 44, 80, 63, 83, 75, 86], [93, 69, 66, 66, 7, 81, 20, 6, 73, 54, 88, 2, 81, 66, 14], [41, 70, 95, 29, 36, 6, 81, 86, 92, 22, 10, 18, 46, 62, 15], [38, 30, 21, 55, 62, 14, 47, 59, 97, 8, 48, 68, 74, 9, 23], [26, 69, 73, 35, 3, 58, 67, 83, 81, 54, 12, 34, 19, 15, 88], [34, 93, 80, 7, 4, 32, 97, 98, 58, 58, 3, 90, 42, 40, 15], [28, 39, 81, 3, 38, 65, 10, 71, 44, 77, 6, 68, 42, 51, 43], [78, 41, 20, 47, 55, 88, 39, 29, 81, 64, 77, 7, 40, 12, 18], [26, 47, 28, 67, 3, 26, 57, 61, 20, 61, 60, 90, 60, 76, 24], [27, 51, 11, 13, 26, 97, 28, 82, 63, 26, 36, 19, 66, 33, 35], [1, 20, 21, 49, 81, 49, 84, 99, 7, 92, 71, 67, 96, 88, 77], [67, 69, 87, 31, 8, 92, 80, 17, 9, 1, 83, 17, 16, 50, 61], [81, 35, 65, 73, 14, 42, 86, 83, 19, 30, 25, 38, 83, 22, 21], [96, 84, 82, 44, 13, 38, 13, 30, 51, 61, 67, 90, 20, 14, 60], [24, 76, 96, 16, 67, 51, 44, 20, 40, 75, 87, 4, 90, 61, 51], [52, 68, 76, 62, 51, 1, 22, 35, 48, 8, 37, 25, 39, 58, 4], [62, 91, 54, 52, 88, 40, 51, 34, 81, 32, 96, 27, 96, 11, 90], [73, 24, 87, 23, 93, 1, 71, 40, 81, 92, 3, 20, 17, 52, 35], [82, 34, 1, 85, 90, 32, 80, 65, 23, 81, 44, 48, 20, 58, 56], [18, 65, 88, 76, 68, 24, 11, 82, 37, 61, 72, 33, 2, 48, 65], [8, 81, 55, 43, 57, 81, 36, 17, 97, 94, 34, 25, 14, 59, 2], [1, 96, 50, 20, 41, 13, 3, 57, 45, 91, 23, 64, 84, 89, 7]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[5, 3, 12, 6, 9, 1, 14, 4, 2, 13, 10, 0, 8, 11, 7], [1, 7, 0, 2, 4, 11, 10, 14, 5, 12, 8, 3, 9, 6, 13], [9, 1, 6, 4, 0, 10, 5, 13, 7, 11, 14, 2, 3, 8, 12], [5, 8, 6, 14, 1, 0, 3, 11, 12, 10, 7, 13, 4, 2, 9], [0, 11, 1, 5, 9, 13, 14, 2, 7, 12, 3, 8, 4, 10, 6], [12, 1, 10, 7, 14, 9, 0, 2, 6, 13, 8, 3, 11, 5, 4], [8, 12, 3, 11, 6, 5, 2, 7, 10, 13, 14, 1, 4, 0, 9], [8, 4, 10, 0, 14, 2, 12, 1, 6, 9, 3, 13, 7, 5, 11], [12, 5, 3, 8, 4, 11, 7, 14, 2, 1, 13, 6, 9, 10, 0], [0, 9, 5, 14, 1, 13, 6, 11, 7, 10, 4, 8, 2, 3, 12], [13, 6, 4, 7, 2, 8, 12, 10, 5, 11, 0, 1, 3, 9, 14], [6, 0, 7, 8, 4, 13, 2, 1, 9, 14, 12, 10, 5, 11, 3], [6, 0, 4, 7, 2, 12, 10, 8, 13, 11, 14, 9, 3, 5, 1], [3, 12, 5, 1, 6, 4, 7, 2, 11, 9, 13, 14, 0, 8, 10], [11, 3, 1, 13, 7, 9, 8, 14, 10, 4, 6, 2, 12, 0, 5], [7, 13, 9, 4, 10, 2, 0, 6, 5, 3, 8, 1, 14, 11, 12], [7, 5, 14, 10, 13, 6, 3, 2, 9, 12, 4, 8, 1, 0, 11], [13, 7, 10, 1, 5, 11, 8, 0, 14, 6, 4, 3, 12, 2, 9], [5, 10, 7, 11, 14, 1, 12, 0, 13, 2, 4, 6, 3, 9, 8], [10, 7, 5, 2, 11, 14, 3, 9, 0, 6, 4, 12, 13, 8, 1], [11, 3, 6, 2, 7, 10, 1, 13, 0, 4, 8, 5, 14, 9, 12], [10, 9, 0, 3, 4, 5, 8, 11, 1, 7, 6, 14, 12, 13, 2], [10, 9, 0, 4, 7, 2, 1, 13, 6, 14, 12, 8, 11, 3, 5], [6, 0, 7, 13, 5, 3, 14, 1, 9, 12, 8, 2, 4, 11, 10], [7, 6, 11, 5, 13, 12, 8, 4, 14, 9, 0, 3, 1, 2, 10], [7, 5, 10, 6, 11, 13, 9, 0, 12, 2, 8, 14, 1, 3, 4], [13, 7, 2, 9, 1, 11, 0, 5, 8, 10, 12, 6, 3, 14, 4], [7, 9, 4, 14, 13, 2, 12, 3, 8, 10, 0, 6, 11, 5, 1], [9, 12, 7, 11, 4, 5, 0, 1, 13, 8, 3, 10, 2, 6, 14], [10, 11, 14, 13, 5, 1, 12, 9, 3, 6, 8, 2, 0, 4, 7]]

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
