# Job Shop Scheduling instance: ta38
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 22323

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[54, 8, 81, 33, 22, 26, 23, 69, 14, 88, 52, 75, 18, 59, 42], [76, 99, 1, 79, 75, 14, 4, 28, 58, 66, 59, 41, 41, 42, 60], [38, 78, 21, 70, 37, 55, 63, 44, 27, 79, 6, 79, 46, 45, 18], [27, 37, 37, 72, 63, 24, 27, 34, 31, 51, 73, 58, 7, 32, 56], [95, 23, 89, 20, 12, 33, 78, 26, 35, 35, 17, 81, 34, 60, 32], [31, 74, 70, 58, 82, 11, 70, 65, 90, 80, 82, 64, 31, 63, 81], [43, 22, 86, 45, 37, 17, 63, 81, 37, 28, 92, 99, 7, 1, 10], [41, 45, 93, 22, 86, 42, 28, 77, 74, 11, 62, 92, 59, 81, 57], [37, 12, 90, 6, 63, 37, 66, 89, 83, 74, 21, 78, 70, 56, 39], [59, 24, 31, 21, 46, 48, 73, 11, 27, 47, 45, 38, 67, 91, 42], [52, 9, 17, 63, 96, 50, 7, 27, 59, 81, 19, 74, 41, 64, 59], [47, 81, 93, 59, 86, 91, 46, 29, 65, 61, 73, 21, 75, 10, 65], [62, 63, 63, 99, 43, 37, 53, 62, 9, 32, 25, 10, 93, 81, 85], [29, 87, 62, 51, 81, 88, 8, 66, 90, 7, 68, 26, 46, 50, 41], [20, 6, 86, 31, 86, 5, 23, 57, 76, 42, 45, 90, 63, 8, 98], [11, 42, 94, 51, 36, 39, 95, 96, 1, 43, 74, 74, 42, 82, 74], [57, 13, 25, 31, 39, 78, 55, 85, 77, 12, 55, 60, 87, 9, 12], [6, 42, 79, 55, 46, 4, 89, 15, 44, 72, 12, 73, 47, 81, 33], [77, 62, 19, 70, 19, 36, 50, 33, 82, 69, 97, 30, 44, 17, 70], [84, 98, 3, 7, 6, 6, 42, 26, 49, 42, 34, 59, 70, 4, 52], [84, 17, 84, 1, 2, 31, 75, 10, 3, 97, 2, 53, 76, 10, 18], [13, 62, 28, 77, 76, 37, 85, 33, 63, 76, 81, 6, 20, 27, 87], [25, 70, 7, 39, 20, 49, 89, 98, 64, 46, 60, 67, 78, 76, 27], [65, 92, 8, 30, 88, 9, 39, 94, 51, 22, 9, 24, 66, 3, 27], [60, 71, 6, 79, 64, 85, 88, 64, 66, 3, 33, 17, 44, 2, 62], [91, 31, 52, 81, 53, 53, 5, 8, 50, 53, 15, 83, 24, 22, 11], [84, 13, 62, 13, 53, 91, 69, 16, 92, 17, 87, 44, 92, 72, 13], [27, 14, 12, 62, 14, 61, 69, 82, 61, 83, 51, 64, 2, 26, 34], [22, 71, 82, 70, 25, 81, 68, 42, 5, 22, 83, 6, 53, 94, 54], [22, 67, 89, 87, 78, 35, 67, 72, 46, 34, 69, 87, 47, 86, 57]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 13, 1, 9, 8, 12, 4, 10, 11, 3, 6, 7, 14, 5, 0], [6, 3, 0, 10, 13, 7, 4, 14, 11, 5, 1, 8, 12, 9, 2], [4, 6, 12, 11, 0, 7, 14, 13, 5, 1, 9, 8, 10, 2, 3], [11, 4, 14, 0, 1, 9, 2, 8, 5, 10, 12, 3, 7, 13, 6], [0, 5, 11, 1, 7, 4, 14, 13, 2, 6, 3, 9, 8, 12, 10], [11, 5, 3, 2, 0, 1, 4, 12, 7, 8, 13, 14, 9, 6, 10], [11, 9, 6, 7, 2, 14, 12, 5, 1, 3, 10, 13, 4, 8, 0], [4, 11, 8, 2, 5, 6, 12, 7, 13, 0, 9, 1, 10, 3, 14], [1, 2, 12, 7, 5, 13, 10, 9, 4, 14, 0, 8, 11, 6, 3], [11, 12, 8, 7, 10, 3, 6, 9, 2, 1, 0, 13, 4, 5, 14], [3, 2, 14, 7, 9, 6, 10, 0, 11, 1, 5, 8, 12, 13, 4], [1, 5, 13, 6, 8, 10, 3, 2, 12, 0, 9, 4, 14, 7, 11], [2, 8, 13, 5, 9, 0, 12, 1, 6, 3, 7, 11, 14, 4, 10], [11, 12, 9, 13, 10, 4, 5, 7, 8, 3, 2, 0, 1, 14, 6], [11, 13, 12, 7, 6, 5, 0, 1, 3, 9, 4, 8, 14, 10, 2], [0, 2, 1, 6, 9, 3, 12, 5, 13, 8, 7, 4, 14, 10, 11], [14, 8, 1, 3, 13, 4, 0, 2, 10, 11, 12, 6, 7, 9, 5], [3, 5, 10, 1, 4, 6, 8, 14, 7, 11, 12, 9, 13, 2, 0], [0, 12, 1, 13, 3, 4, 9, 14, 11, 10, 8, 5, 2, 7, 6], [1, 9, 13, 7, 0, 10, 2, 11, 14, 12, 8, 6, 4, 3, 5], [4, 2, 3, 12, 13, 10, 6, 7, 9, 8, 14, 11, 5, 0, 1], [8, 11, 3, 6, 12, 2, 10, 9, 7, 4, 13, 14, 0, 5, 1], [4, 1, 6, 10, 8, 3, 11, 12, 2, 9, 0, 5, 14, 13, 7], [13, 9, 5, 12, 6, 8, 3, 1, 7, 2, 11, 14, 4, 10, 0], [3, 10, 14, 5, 11, 7, 8, 13, 1, 6, 4, 9, 12, 0, 2], [0, 12, 6, 1, 4, 9, 7, 10, 14, 5, 13, 11, 8, 3, 2], [10, 2, 0, 5, 4, 9, 13, 14, 12, 8, 7, 3, 1, 6, 11], [9, 3, 8, 13, 4, 6, 14, 5, 2, 12, 0, 10, 11, 1, 7], [14, 2, 6, 10, 1, 5, 11, 7, 0, 9, 13, 4, 12, 8, 3], [6, 7, 12, 5, 4, 9, 1, 13, 2, 10, 8, 14, 11, 0, 3]]

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
