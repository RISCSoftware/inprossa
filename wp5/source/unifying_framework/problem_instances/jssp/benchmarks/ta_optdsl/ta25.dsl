# Job Shop Scheduling instance: ta25
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 19654

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[31, 98, 32, 10, 15, 50, 62, 61, 40, 14, 34, 30, 7, 53, 81, 24, 43, 60, 65, 27], [45, 54, 61, 20, 84, 42, 66, 37, 38, 87, 12, 24, 69, 45, 4, 72, 49, 69, 17, 12], [30, 49, 40, 88, 92, 75, 60, 18, 45, 25, 74, 26, 1, 68, 65, 69, 95, 69, 25, 34], [26, 91, 91, 91, 61, 14, 33, 58, 99, 84, 7, 77, 46, 81, 49, 65, 8, 42, 95, 21], [12, 67, 46, 54, 34, 99, 52, 10, 68, 60, 35, 62, 99, 53, 53, 59, 2, 31, 87, 88], [3, 44, 51, 54, 40, 31, 9, 8, 17, 92, 69, 21, 32, 84, 95, 51, 33, 86, 83, 1], [41, 20, 45, 46, 39, 51, 2, 62, 45, 69, 12, 6, 87, 17, 19, 3, 10, 93, 56, 51], [44, 23, 84, 9, 3, 9, 59, 55, 3, 22, 43, 78, 82, 83, 1, 11, 29, 77, 10, 97], [3, 16, 39, 77, 55, 55, 94, 65, 34, 18, 84, 69, 4, 90, 2, 10, 27, 89, 99, 94], [24, 7, 85, 92, 26, 6, 74, 46, 28, 82, 54, 85, 59, 81, 49, 60, 87, 4, 98, 97], [28, 93, 97, 30, 21, 56, 92, 99, 91, 51, 23, 95, 94, 49, 3, 38, 31, 55, 22, 42], [32, 66, 16, 1, 8, 56, 51, 97, 5, 41, 45, 3, 71, 81, 52, 13, 88, 50, 26, 65], [9, 12, 59, 40, 50, 40, 93, 67, 29, 78, 90, 83, 83, 28, 25, 22, 28, 90, 43, 91], [30, 6, 86, 87, 50, 14, 13, 33, 64, 91, 50, 65, 49, 43, 83, 19, 46, 67, 77, 30], [46, 69, 17, 29, 39, 76, 61, 69, 60, 92, 42, 17, 32, 58, 41, 97, 76, 55, 98, 96], [32, 44, 4, 72, 38, 98, 77, 37, 65, 58, 72, 60, 92, 16, 88, 91, 60, 84, 31, 20], [20, 57, 9, 63, 79, 51, 68, 14, 15, 93, 51, 41, 37, 21, 73, 15, 9, 51, 80, 25], [40, 32, 64, 30, 6, 81, 1, 97, 15, 19, 36, 7, 76, 50, 52, 19, 62, 40, 77, 50], [41, 29, 39, 79, 1, 7, 54, 29, 79, 93, 85, 54, 59, 92, 65, 74, 7, 35, 56, 72], [84, 13, 60, 82, 1, 24, 68, 56, 31, 87, 4, 76, 58, 17, 9, 44, 39, 4, 54, 48]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 6, 2, 14, 18, 13, 0, 1, 10, 19, 17, 16, 11, 15, 7, 8, 12, 4, 5, 3], [10, 5, 17, 19, 4, 11, 9, 12, 0, 7, 8, 15, 1, 6, 13, 14, 2, 3, 16, 18], [6, 8, 19, 10, 14, 5, 4, 17, 2, 11, 15, 0, 7, 3, 1, 13, 9, 12, 16, 18], [11, 4, 17, 15, 8, 13, 9, 6, 16, 19, 0, 7, 1, 10, 18, 3, 2, 5, 12, 14], [11, 19, 16, 0, 8, 5, 2, 10, 18, 13, 9, 3, 12, 15, 7, 4, 1, 17, 6, 14], [11, 9, 16, 7, 6, 15, 1, 19, 10, 18, 8, 17, 2, 14, 4, 12, 13, 3, 0, 5], [3, 12, 2, 7, 16, 14, 15, 9, 19, 18, 1, 5, 0, 10, 11, 8, 13, 6, 17, 4], [18, 12, 0, 9, 3, 7, 16, 8, 4, 17, 11, 10, 5, 2, 14, 15, 6, 19, 1, 13], [0, 17, 8, 12, 6, 15, 13, 1, 9, 5, 11, 2, 18, 3, 7, 4, 16, 10, 19, 14], [11, 18, 5, 6, 0, 10, 2, 1, 15, 14, 3, 12, 4, 19, 16, 8, 13, 7, 17, 9], [13, 7, 6, 17, 15, 10, 2, 19, 12, 11, 1, 16, 8, 14, 3, 0, 5, 4, 9, 18], [6, 19, 12, 13, 5, 10, 9, 18, 14, 16, 7, 11, 0, 2, 3, 15, 4, 17, 1, 8], [6, 9, 10, 14, 12, 5, 11, 7, 2, 17, 19, 4, 15, 0, 1, 13, 16, 3, 18, 8], [11, 19, 5, 7, 10, 9, 15, 4, 2, 14, 6, 12, 0, 13, 16, 17, 1, 18, 3, 8], [9, 19, 5, 10, 4, 11, 0, 6, 2, 3, 7, 13, 1, 18, 8, 15, 16, 14, 17, 12], [7, 4, 6, 2, 3, 18, 0, 5, 1, 8, 13, 17, 11, 14, 19, 16, 12, 15, 10, 9], [15, 12, 5, 2, 8, 7, 14, 9, 4, 3, 13, 6, 16, 17, 19, 1, 11, 10, 18, 0], [19, 13, 9, 5, 6, 4, 8, 3, 15, 10, 2, 12, 0, 1, 18, 16, 14, 11, 7, 17], [7, 17, 5, 12, 4, 14, 13, 2, 18, 9, 1, 11, 0, 6, 16, 10, 15, 8, 19, 3], [8, 14, 11, 18, 15, 16, 19, 13, 17, 1, 9, 5, 6, 0, 3, 4, 10, 2, 7, 12]]

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
