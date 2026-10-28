# Job Shop Scheduling instance: ta33
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 23693

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[98, 87, 27, 32, 93, 89, 77, 55, 47, 40, 36, 32, 95, 72, 15], [73, 44, 35, 76, 5, 68, 72, 66, 42, 13, 24, 55, 7, 47, 84], [7, 61, 61, 85, 44, 7, 98, 28, 3, 3, 71, 12, 59, 57, 98], [92, 19, 27, 3, 4, 93, 97, 97, 9, 27, 19, 70, 1, 76, 16], [92, 79, 19, 35, 63, 53, 71, 36, 49, 16, 36, 60, 52, 27, 23], [65, 53, 25, 28, 62, 67, 97, 48, 63, 6, 51, 88, 68, 15, 79], [81, 26, 43, 70, 54, 26, 15, 72, 71, 48, 98, 49, 65, 79, 60], [82, 34, 87, 35, 28, 98, 43, 28, 73, 28, 74, 88, 5, 18, 58], [62, 66, 93, 86, 2, 98, 47, 14, 51, 83, 18, 90, 67, 62, 70], [28, 69, 57, 6, 79, 47, 21, 94, 71, 75, 66, 66, 84, 35, 66], [37, 76, 20, 40, 71, 5, 92, 87, 90, 15, 63, 45, 62, 79, 19], [5, 62, 59, 71, 27, 71, 70, 90, 99, 82, 7, 83, 54, 92, 12], [48, 87, 84, 66, 3, 79, 21, 86, 49, 74, 11, 46, 98, 58, 90], [45, 22, 49, 7, 32, 56, 11, 17, 80, 96, 19, 84, 5, 96, 93], [25, 65, 88, 19, 93, 35, 69, 46, 73, 18, 40, 53, 78, 85, 16], [87, 64, 36, 39, 34, 18, 87, 80, 63, 34, 74, 49, 36, 42, 40], [18, 63, 1, 34, 95, 81, 84, 35, 15, 27, 79, 58, 73, 52, 67], [48, 66, 64, 11, 82, 19, 42, 27, 55, 37, 1, 12, 93, 83, 42], [15, 93, 61, 66, 34, 77, 13, 39, 55, 62, 72, 20, 73, 71, 45], [77, 72, 71, 49, 96, 81, 76, 85, 15, 81, 53, 97, 65, 68, 70], [27, 62, 16, 36, 19, 34, 84, 10, 23, 21, 69, 98, 63, 51, 58], [89, 52, 80, 82, 30, 17, 69, 60, 78, 50, 87, 17, 77, 67, 53], [85, 36, 66, 12, 79, 32, 56, 40, 11, 89, 85, 37, 32, 37, 98], [49, 22, 13, 92, 32, 86, 56, 8, 24, 20, 95, 68, 55, 25, 46], [2, 92, 1, 92, 49, 10, 84, 53, 53, 65, 92, 39, 75, 48, 26], [31, 67, 51, 14, 67, 33, 8, 61, 54, 7, 24, 63, 84, 22, 38], [55, 4, 17, 27, 96, 55, 26, 45, 60, 98, 76, 68, 10, 30, 65], [9, 19, 66, 47, 98, 85, 3, 70, 22, 24, 72, 97, 40, 51, 73], [57, 71, 19, 84, 54, 75, 18, 72, 46, 25, 80, 38, 92, 29, 41], [92, 55, 53, 91, 20, 35, 79, 78, 98, 78, 8, 2, 61, 64, 16]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[10, 11, 9, 8, 1, 7, 6, 2, 5, 13, 4, 14, 0, 12, 3], [12, 8, 14, 3, 1, 7, 13, 6, 10, 5, 4, 2, 9, 11, 0], [12, 0, 3, 13, 14, 10, 2, 6, 9, 1, 11, 4, 5, 7, 8], [14, 3, 7, 2, 6, 5, 10, 8, 11, 1, 0, 9, 13, 12, 4], [6, 5, 7, 4, 9, 3, 13, 10, 1, 0, 14, 11, 8, 12, 2], [7, 11, 12, 9, 8, 2, 3, 5, 4, 1, 10, 0, 6, 13, 14], [11, 12, 1, 7, 14, 6, 3, 5, 8, 9, 13, 4, 10, 0, 2], [3, 9, 11, 14, 2, 13, 12, 10, 6, 7, 0, 1, 4, 5, 8], [9, 2, 3, 13, 10, 14, 12, 1, 7, 0, 6, 8, 11, 4, 5], [0, 7, 3, 14, 4, 8, 13, 2, 1, 9, 12, 5, 6, 10, 11], [2, 12, 0, 4, 14, 10, 8, 13, 7, 3, 6, 9, 5, 1, 11], [5, 2, 8, 6, 4, 12, 9, 1, 10, 0, 14, 7, 13, 11, 3], [14, 5, 0, 3, 7, 1, 4, 8, 2, 12, 11, 13, 9, 10, 6], [5, 2, 14, 6, 12, 4, 10, 9, 3, 8, 13, 7, 1, 0, 11], [4, 9, 0, 6, 1, 10, 13, 3, 2, 12, 5, 11, 7, 8, 14], [2, 5, 12, 4, 1, 7, 6, 14, 3, 8, 13, 10, 9, 0, 11], [6, 10, 1, 8, 12, 2, 11, 9, 14, 5, 0, 7, 13, 3, 4], [2, 0, 4, 10, 3, 5, 7, 12, 14, 13, 11, 9, 8, 1, 6], [5, 6, 8, 0, 10, 11, 13, 14, 7, 2, 12, 1, 4, 9, 3], [13, 8, 11, 7, 9, 10, 3, 14, 4, 12, 1, 6, 2, 5, 0], [1, 6, 14, 3, 12, 10, 7, 13, 5, 0, 4, 11, 9, 2, 8], [7, 11, 0, 10, 1, 2, 5, 4, 3, 9, 14, 8, 6, 12, 13], [6, 7, 12, 13, 11, 3, 8, 1, 10, 9, 0, 5, 2, 14, 4], [4, 6, 1, 10, 12, 9, 14, 7, 11, 0, 5, 3, 13, 8, 2], [7, 2, 10, 9, 5, 3, 1, 13, 11, 8, 4, 14, 12, 6, 0], [3, 4, 12, 0, 7, 11, 10, 2, 13, 5, 8, 6, 14, 9, 1], [11, 12, 0, 13, 6, 2, 1, 9, 5, 7, 3, 10, 4, 14, 8], [0, 9, 8, 12, 3, 14, 10, 7, 2, 1, 6, 11, 4, 5, 13], [4, 2, 7, 11, 6, 3, 1, 10, 8, 9, 13, 0, 12, 14, 5], [14, 6, 2, 8, 10, 4, 11, 13, 12, 7, 3, 5, 1, 0, 9]]

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
