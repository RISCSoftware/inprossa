# Job Shop Scheduling instance: ta02
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11356

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[98, 43, 8, 94, 10, 49, 21, 71, 25, 86, 65, 73, 90, 59, 60], [23, 11, 86, 93, 62, 20, 65, 28, 28, 37, 68, 38, 82, 35, 36], [67, 22, 60, 38, 20, 91, 96, 33, 82, 79, 40, 88, 62, 81, 83], [88, 24, 4, 90, 68, 78, 58, 7, 16, 13, 70, 14, 53, 73, 73], [73, 41, 19, 13, 52, 19, 85, 99, 19, 95, 71, 93, 59, 63, 60], [10, 93, 60, 41, 72, 62, 58, 63, 88, 46, 16, 76, 83, 62, 69], [34, 8, 92, 70, 85, 50, 62, 53, 5, 44, 68, 25, 78, 90, 70], [64, 11, 96, 44, 94, 21, 91, 1, 12, 92, 41, 59, 60, 63, 19], [16, 91, 83, 68, 23, 51, 13, 40, 63, 90, 46, 93, 24, 37, 49], [6, 3, 5, 21, 64, 76, 66, 17, 94, 37, 14, 63, 62, 98, 35], [25, 52, 9, 41, 73, 68, 39, 98, 34, 27, 50, 35, 41, 62, 42], [32, 62, 39, 32, 29, 8, 33, 68, 10, 91, 35, 8, 23, 20, 58], [28, 81, 42, 53, 24, 3, 44, 2, 28, 59, 8, 66, 45, 31, 23], [36, 23, 11, 59, 27, 93, 64, 77, 53, 62, 60, 23, 72, 7, 97], [84, 36, 24, 20, 38, 68, 72, 47, 30, 1, 98, 91, 85, 30, 42]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 14, 4, 13, 10, 3, 7, 8, 0, 5, 1, 2, 12, 6, 11], [10, 8, 11, 14, 3, 13, 9, 7, 4, 2, 6, 1, 5, 12, 0], [7, 0, 6, 5, 14, 13, 2, 11, 4, 12, 1, 9, 3, 10, 8], [9, 11, 14, 0, 1, 8, 5, 10, 12, 4, 13, 3, 6, 7, 2], [11, 4, 13, 3, 8, 1, 10, 12, 2, 14, 6, 7, 0, 9, 5], [5, 2, 1, 10, 0, 4, 8, 14, 6, 3, 9, 7, 11, 12, 13], [5, 10, 13, 0, 9, 8, 1, 11, 14, 7, 12, 2, 6, 4, 3], [12, 0, 9, 3, 13, 6, 5, 7, 2, 14, 11, 8, 10, 1, 4], [11, 10, 5, 13, 1, 9, 8, 7, 3, 6, 0, 2, 14, 12, 4], [2, 14, 3, 10, 6, 1, 0, 13, 11, 4, 5, 8, 7, 12, 9], [11, 14, 13, 5, 4, 9, 1, 6, 12, 0, 2, 8, 10, 3, 7], [12, 3, 10, 8, 4, 7, 13, 11, 14, 1, 2, 0, 5, 6, 9], [8, 13, 5, 0, 11, 9, 4, 12, 1, 10, 6, 2, 7, 14, 3], [2, 5, 4, 3, 9, 1, 11, 13, 7, 6, 10, 14, 0, 8, 12], [1, 10, 4, 2, 0, 7, 6, 9, 11, 12, 5, 14, 3, 13, 8]]

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
