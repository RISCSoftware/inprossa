# Job Shop Scheduling instance: ta19
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14773

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[13, 22, 41, 90, 71, 59, 13, 46, 78, 42, 89, 97, 62, 69, 48], [74, 87, 17, 24, 44, 1, 89, 77, 60, 56, 35, 3, 29, 92, 12], [57, 55, 6, 57, 94, 25, 57, 89, 73, 36, 47, 46, 21, 2, 67], [39, 1, 37, 84, 74, 80, 50, 70, 25, 40, 44, 27, 65, 52, 12], [13, 96, 91, 74, 39, 14, 15, 72, 57, 25, 46, 8, 31, 69, 13], [63, 36, 95, 85, 33, 50, 68, 16, 40, 32, 10, 1, 2, 22, 32], [30, 88, 98, 52, 64, 10, 76, 25, 29, 43, 34, 35, 21, 15, 45], [87, 92, 43, 19, 54, 85, 13, 2, 21, 14, 78, 6, 85, 61, 86], [64, 21, 73, 58, 14, 47, 67, 77, 16, 33, 29, 10, 99, 47, 8], [51, 68, 93, 86, 84, 28, 63, 46, 26, 99, 6, 55, 52, 83, 55], [36, 15, 19, 18, 69, 60, 43, 97, 32, 36, 13, 79, 23, 14, 48], [72, 68, 68, 63, 49, 18, 50, 28, 13, 12, 52, 68, 10, 90, 36], [67, 31, 41, 40, 47, 16, 6, 58, 76, 73, 37, 75, 73, 23, 5], [4, 62, 52, 21, 29, 6, 13, 58, 93, 44, 82, 93, 58, 20, 90], [93, 24, 47, 71, 77, 10, 40, 56, 63, 96, 98, 9, 63, 66, 94], [86, 87, 93, 72, 10, 18, 18, 58, 33, 32, 95, 3, 30, 45, 80], [13, 71, 83, 3, 86, 11, 87, 41, 62, 8, 40, 65, 32, 69, 77], [21, 29, 82, 88, 51, 63, 77, 61, 6, 18, 50, 76, 76, 77, 42], [58, 80, 98, 88, 95, 85, 16, 97, 59, 87, 8, 69, 27, 42, 11], [95, 19, 25, 25, 94, 44, 20, 28, 16, 34, 74, 66, 67, 48, 85]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 1, 10, 7, 9, 5, 6, 3, 2, 13, 4, 0, 14, 11, 12], [1, 9, 4, 5, 0, 11, 6, 7, 12, 2, 14, 8, 13, 10, 3], [6, 2, 8, 9, 3, 5, 4, 12, 11, 7, 10, 13, 0, 14, 1], [4, 9, 1, 2, 13, 3, 6, 0, 12, 5, 10, 7, 8, 11, 14], [6, 7, 9, 13, 11, 1, 5, 0, 12, 3, 14, 2, 4, 8, 10], [2, 12, 6, 13, 8, 4, 1, 14, 5, 9, 10, 0, 3, 7, 11], [13, 2, 12, 5, 11, 6, 8, 4, 10, 7, 1, 0, 3, 9, 14], [9, 8, 14, 7, 3, 10, 1, 12, 4, 13, 11, 6, 5, 0, 2], [14, 3, 6, 8, 12, 9, 4, 5, 1, 7, 0, 10, 2, 11, 13], [11, 4, 14, 8, 13, 10, 9, 0, 5, 6, 2, 12, 3, 1, 7], [6, 2, 8, 0, 3, 5, 7, 10, 14, 9, 11, 13, 4, 1, 12], [9, 1, 14, 0, 13, 2, 7, 8, 5, 11, 4, 10, 6, 3, 12], [8, 11, 12, 3, 7, 13, 6, 1, 14, 5, 9, 2, 4, 0, 10], [8, 12, 7, 11, 3, 14, 6, 10, 5, 1, 2, 9, 0, 4, 13], [10, 13, 12, 8, 3, 11, 5, 14, 0, 4, 2, 6, 1, 9, 7], [8, 6, 10, 14, 1, 11, 3, 5, 12, 9, 2, 4, 0, 7, 13], [13, 2, 8, 14, 7, 0, 9, 6, 3, 11, 10, 5, 12, 1, 4], [0, 13, 12, 6, 7, 2, 11, 14, 8, 3, 4, 10, 1, 5, 9], [9, 6, 2, 12, 0, 8, 11, 4, 5, 1, 7, 3, 14, 10, 13], [2, 8, 6, 12, 14, 10, 13, 5, 0, 7, 11, 9, 3, 4, 1]]

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
