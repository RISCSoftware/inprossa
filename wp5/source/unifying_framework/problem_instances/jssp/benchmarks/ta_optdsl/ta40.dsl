# Job Shop Scheduling instance: ta40
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 22310

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[63, 98, 79, 47, 92, 76, 51, 35, 81, 1, 70, 4, 21, 75, 20], [37, 13, 57, 65, 3, 63, 73, 59, 85, 45, 38, 71, 26, 91, 74], [35, 86, 74, 5, 78, 28, 1, 37, 41, 60, 49, 92, 95, 73, 2], [24, 73, 4, 49, 28, 77, 66, 69, 29, 3, 41, 88, 95, 23, 47], [65, 26, 96, 60, 55, 28, 54, 36, 81, 45, 26, 87, 71, 10, 95], [30, 85, 5, 78, 40, 96, 56, 41, 86, 25, 25, 36, 63, 98, 78], [89, 97, 90, 15, 46, 42, 87, 22, 87, 22, 1, 59, 60, 54, 52], [50, 20, 88, 20, 24, 75, 2, 42, 86, 19, 88, 90, 20, 29, 51], [94, 74, 96, 43, 68, 52, 78, 8, 44, 63, 92, 10, 87, 11, 77], [37, 78, 91, 45, 88, 99, 75, 82, 71, 52, 27, 76, 70, 43, 27], [12, 91, 39, 10, 47, 10, 8, 99, 16, 37, 24, 11, 76, 85, 38], [57, 58, 14, 99, 58, 62, 57, 36, 90, 68, 54, 52, 2, 98, 52], [68, 37, 65, 66, 83, 73, 6, 86, 88, 57, 53, 15, 53, 23, 80], [38, 7, 2, 73, 54, 4, 12, 69, 12, 5, 95, 82, 65, 15, 22], [57, 27, 42, 57, 86, 69, 49, 59, 29, 20, 59, 29, 62, 79, 22], [64, 55, 66, 52, 95, 94, 38, 43, 54, 29, 81, 2, 24, 24, 15], [58, 33, 20, 91, 3, 70, 25, 25, 36, 38, 5, 61, 22, 6, 73], [12, 22, 21, 30, 22, 51, 7, 8, 28, 69, 66, 98, 98, 20, 61], [3, 64, 56, 11, 30, 70, 3, 77, 23, 15, 77, 54, 97, 52, 93], [1, 22, 15, 66, 41, 48, 13, 55, 85, 9, 48, 99, 7, 67, 34], [79, 15, 89, 68, 31, 50, 76, 7, 10, 50, 28, 94, 44, 33, 23], [2, 76, 64, 42, 26, 73, 57, 93, 60, 35, 73, 17, 26, 93, 50], [79, 92, 64, 71, 55, 39, 27, 97, 22, 38, 28, 56, 7, 99, 14], [84, 33, 12, 12, 58, 3, 98, 74, 99, 37, 92, 79, 2, 69, 41], [93, 1, 24, 48, 69, 46, 77, 26, 23, 9, 44, 54, 94, 71, 44], [83, 16, 41, 6, 21, 21, 39, 8, 1, 17, 72, 6, 61, 60, 86], [11, 23, 52, 56, 59, 49, 24, 97, 28, 43, 34, 49, 83, 58, 62], [75, 57, 82, 94, 51, 67, 97, 40, 23, 63, 20, 4, 75, 15, 23], [75, 36, 16, 33, 92, 13, 1, 74, 24, 96, 14, 20, 48, 14, 79], [58, 62, 32, 95, 49, 33, 32, 98, 13, 64, 89, 89, 43, 11, 56]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[5, 11, 1, 9, 6, 4, 13, 3, 7, 10, 12, 14, 2, 8, 0], [11, 8, 4, 9, 1, 2, 12, 5, 10, 13, 6, 7, 14, 0, 3], [9, 2, 0, 13, 10, 6, 11, 3, 8, 14, 12, 5, 7, 4, 1], [12, 1, 13, 5, 14, 0, 8, 11, 7, 3, 4, 6, 2, 10, 9], [5, 10, 12, 8, 7, 2, 14, 9, 13, 4, 11, 0, 6, 1, 3], [4, 11, 2, 14, 12, 5, 10, 8, 1, 6, 9, 0, 13, 3, 7], [2, 3, 0, 6, 14, 11, 7, 5, 4, 12, 13, 8, 9, 1, 10], [14, 5, 6, 8, 9, 10, 1, 2, 4, 7, 11, 3, 13, 12, 0], [13, 2, 10, 0, 6, 9, 8, 7, 4, 14, 5, 1, 3, 11, 12], [6, 1, 14, 10, 7, 2, 4, 11, 0, 13, 9, 8, 3, 5, 12], [4, 6, 7, 13, 11, 8, 10, 5, 3, 0, 9, 2, 14, 12, 1], [5, 13, 9, 2, 0, 12, 14, 7, 1, 10, 3, 6, 11, 8, 4], [12, 6, 2, 0, 10, 3, 11, 4, 14, 5, 7, 9, 13, 8, 1], [3, 12, 4, 10, 8, 7, 5, 1, 6, 11, 9, 14, 13, 2, 0], [10, 6, 11, 5, 13, 3, 1, 12, 0, 14, 8, 2, 7, 9, 4], [10, 13, 1, 4, 11, 5, 6, 7, 14, 3, 8, 2, 0, 12, 9], [2, 6, 5, 13, 4, 10, 14, 7, 0, 8, 3, 12, 11, 9, 1], [14, 13, 2, 1, 4, 9, 11, 0, 3, 12, 8, 7, 6, 5, 10], [7, 0, 3, 8, 2, 4, 10, 1, 13, 5, 6, 12, 14, 11, 9], [0, 1, 11, 14, 5, 2, 9, 13, 8, 4, 6, 10, 12, 3, 7], [12, 11, 13, 10, 14, 4, 8, 1, 9, 3, 7, 5, 0, 6, 2], [10, 0, 1, 4, 14, 13, 7, 9, 2, 3, 11, 12, 8, 5, 6], [0, 11, 8, 5, 6, 9, 14, 4, 2, 13, 10, 7, 12, 1, 3], [12, 5, 1, 7, 13, 4, 8, 11, 0, 10, 6, 14, 9, 2, 3], [5, 8, 3, 4, 13, 9, 12, 10, 1, 7, 0, 11, 2, 6, 14], [0, 14, 3, 12, 6, 10, 8, 7, 9, 13, 2, 1, 5, 4, 11], [8, 4, 14, 7, 2, 13, 11, 12, 0, 5, 6, 3, 9, 10, 1], [12, 2, 0, 3, 5, 13, 14, 1, 11, 4, 8, 7, 9, 6, 10], [10, 3, 2, 13, 8, 6, 11, 9, 0, 1, 4, 7, 5, 14, 12], [5, 10, 11, 4, 0, 2, 3, 9, 13, 8, 12, 7, 6, 14, 1]]

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
