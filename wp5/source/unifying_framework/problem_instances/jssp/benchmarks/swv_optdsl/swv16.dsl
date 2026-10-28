# Job Shop Scheduling instance: swv16
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 25333

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[47, 55, 12, 46, 79, 71, 91, 57, 29, 30], [55, 95, 96, 10, 2, 95, 94, 37, 98, 82], [23, 60, 41, 93, 15, 42, 43, 14, 30, 56], [45, 93, 59, 35, 33, 33, 85, 76, 46, 62], [75, 8, 45, 36, 13, 6, 96, 96, 11, 2], [4, 4, 38, 13, 42, 12, 30, 75, 28, 51], [93, 96, 11, 37, 33, 94, 77, 89, 64, 58], [88, 58, 60, 67, 27, 55, 37, 46, 19, 92], [23, 32, 88, 14, 60, 69, 56, 4, 60, 25], [62, 68, 98, 78, 31, 56, 63, 61, 45, 70], [18, 26, 8, 97, 90, 38, 90, 66, 80, 47], [16, 34, 57, 90, 53, 81, 86, 6, 49, 56], [24, 61, 69, 71, 15, 20, 71, 71, 65, 58], [55, 71, 75, 81, 84, 20, 46, 46, 98, 58], [92, 54, 100, 23, 39, 6, 58, 90, 18, 73], [69, 49, 32, 61, 3, 58, 97, 46, 2, 32], [78, 99, 98, 26, 98, 69, 12, 14, 25, 45], [68, 95, 50, 35, 82, 36, 27, 78, 83, 25], [75, 93, 66, 64, 14, 52, 29, 20, 55, 63], [18, 11, 39, 83, 81, 38, 11, 2, 52, 42], [21, 8, 69, 91, 11, 83, 61, 10, 99, 2], [41, 14, 85, 5, 47, 11, 67, 65, 5, 11], [51, 32, 4, 51, 30, 34, 2, 9, 16, 60], [93, 13, 41, 8, 95, 97, 28, 42, 46, 31], [58, 19, 14, 75, 1, 34, 91, 100, 49, 82], [44, 10, 32, 28, 51, 68, 20, 68, 47, 30], [89, 80, 4, 9, 12, 93, 18, 10, 13, 86], [22, 81, 21, 30, 24, 12, 27, 28, 95, 100], [68, 87, 64, 33, 43, 95, 1, 59, 82, 14], [86, 85, 14, 21, 99, 12, 98, 8, 85, 7], [88, 52, 22, 51, 62, 47, 97, 33, 43, 90], [26, 73, 59, 71, 76, 57, 10, 26, 59, 70], [11, 53, 10, 35, 83, 79, 92, 55, 76, 45], [52, 94, 39, 92, 3, 70, 60, 67, 35, 96], [17, 42, 64, 96, 65, 81, 46, 46, 59, 26], [82, 21, 74, 21, 63, 56, 83, 94, 46, 6], [79, 29, 33, 60, 93, 23, 89, 97, 78, 4], [46, 46, 76, 14, 20, 84, 61, 91, 76, 83], [27, 36, 45, 62, 81, 71, 76, 82, 43, 93], [100, 36, 82, 44, 85, 12, 52, 51, 66, 27], [3, 78, 24, 75, 1, 10, 63, 13, 60, 56], [1, 2, 82, 16, 32, 48, 39, 35, 74, 67], [8, 37, 41, 59, 23, 69, 27, 24, 96, 4], [96, 23, 85, 3, 60, 18, 93, 47, 6, 3], [87, 53, 14, 81, 39, 3, 99, 86, 89, 16], [77, 76, 55, 78, 69, 67, 95, 2, 53, 71], [37, 5, 47, 88, 77, 31, 89, 20, 27, 4], [33, 66, 55, 76, 15, 37, 35, 35, 54, 91], [23, 65, 59, 79, 52, 2, 17, 27, 53, 35], [55, 3, 86, 87, 69, 14, 89, 100, 46, 100]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 3, 5, 8, 0, 2, 7, 4, 6, 9], [2, 6, 8, 0, 3, 1, 5, 7, 9, 4], [6, 3, 8, 2, 0, 1, 7, 4, 5, 9], [0, 6, 2, 7, 1, 9, 4, 8, 5, 3], [2, 3, 8, 6, 7, 1, 0, 5, 4, 9], [9, 7, 0, 3, 5, 1, 2, 6, 4, 8], [9, 4, 6, 2, 3, 8, 5, 7, 1, 0], [6, 3, 0, 9, 8, 4, 7, 1, 2, 5], [4, 2, 0, 5, 8, 1, 7, 6, 9, 3], [2, 5, 1, 6, 7, 3, 8, 0, 4, 9], [7, 8, 0, 3, 9, 5, 1, 2, 6, 4], [0, 7, 4, 6, 5, 8, 3, 2, 1, 9], [2, 8, 5, 4, 1, 3, 6, 9, 0, 7], [4, 5, 9, 0, 8, 2, 7, 3, 1, 6], [5, 6, 7, 1, 9, 0, 4, 3, 2, 8], [2, 5, 6, 1, 3, 0, 8, 4, 9, 7], [0, 7, 4, 3, 8, 9, 6, 2, 1, 5], [2, 1, 4, 9, 0, 8, 5, 7, 3, 6], [6, 7, 8, 4, 2, 5, 0, 9, 1, 3], [1, 0, 9, 4, 7, 2, 3, 6, 5, 8], [4, 8, 9, 7, 3, 5, 6, 0, 2, 1], [9, 7, 1, 2, 3, 8, 5, 4, 6, 0], [9, 7, 8, 2, 5, 6, 4, 1, 0, 3], [9, 2, 1, 6, 5, 3, 7, 4, 8, 0], [4, 6, 8, 3, 1, 7, 0, 2, 5, 9], [3, 5, 9, 7, 1, 6, 8, 4, 0, 2], [9, 3, 1, 0, 5, 4, 8, 7, 6, 2], [0, 5, 8, 4, 3, 1, 2, 7, 9, 6], [1, 0, 2, 3, 7, 5, 6, 9, 8, 4], [2, 6, 0, 1, 8, 5, 4, 7, 3, 9], [5, 9, 0, 1, 8, 4, 7, 3, 6, 2], [2, 7, 4, 0, 3, 8, 1, 9, 5, 6], [6, 2, 9, 0, 1, 3, 8, 4, 7, 5], [9, 4, 3, 7, 6, 8, 5, 0, 2, 1], [4, 0, 9, 7, 5, 1, 2, 6, 3, 8], [9, 3, 8, 0, 2, 5, 7, 6, 4, 1], [6, 5, 8, 2, 9, 7, 3, 1, 0, 4], [0, 1, 4, 7, 2, 9, 3, 6, 5, 8], [7, 8, 6, 1, 0, 9, 5, 4, 2, 3], [7, 9, 5, 6, 4, 8, 0, 3, 2, 1], [3, 7, 6, 1, 4, 8, 2, 5, 9, 0], [5, 4, 2, 0, 1, 7, 3, 9, 8, 6], [7, 0, 8, 3, 2, 4, 1, 9, 5, 6], [1, 9, 2, 6, 5, 7, 0, 8, 4, 3], [6, 2, 9, 3, 8, 1, 7, 4, 5, 0], [5, 8, 0, 4, 2, 3, 6, 1, 7, 9], [1, 6, 0, 3, 7, 9, 4, 8, 5, 2], [1, 2, 4, 7, 3, 9, 6, 5, 8, 0], [3, 5, 6, 1, 7, 8, 4, 9, 0, 2], [9, 0, 5, 2, 4, 3, 8, 1, 6, 7]]

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
