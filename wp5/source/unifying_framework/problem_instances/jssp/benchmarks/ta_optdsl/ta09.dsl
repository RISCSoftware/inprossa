# Job Shop Scheduling instance: ta09
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11835

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[98, 66, 90, 91, 26, 19, 78, 8, 69, 53, 7, 45, 94, 15, 56], [74, 87, 3, 85, 43, 73, 96, 78, 88, 1, 49, 80, 90, 34, 40], [95, 88, 12, 99, 69, 39, 71, 77, 46, 27, 79, 1, 41, 82, 98], [56, 62, 56, 72, 21, 1, 56, 20, 44, 67, 46, 33, 23, 79, 50], [62, 15, 52, 93, 73, 86, 79, 86, 80, 79, 18, 44, 8, 16, 15], [70, 55, 66, 62, 3, 14, 54, 89, 12, 79, 9, 63, 35, 86, 94], [30, 78, 92, 42, 37, 34, 38, 39, 9, 25, 16, 42, 76, 29, 80], [67, 51, 52, 29, 43, 49, 38, 46, 20, 53, 18, 35, 98, 25, 96], [3, 68, 68, 73, 8, 15, 63, 72, 68, 89, 59, 98, 20, 88, 41], [71, 14, 32, 36, 88, 6, 63, 7, 16, 43, 63, 80, 51, 64, 30], [69, 92, 55, 79, 72, 25, 43, 58, 89, 86, 83, 35, 90, 88, 18], [69, 57, 40, 88, 50, 42, 28, 4, 73, 18, 37, 25, 82, 64, 83], [45, 13, 72, 96, 38, 50, 49, 96, 75, 41, 66, 2, 31, 29, 66], [93, 80, 55, 15, 90, 36, 50, 49, 87, 31, 89, 76, 38, 23, 19], [24, 99, 45, 6, 75, 10, 22, 65, 16, 4, 85, 24, 72, 75, 44]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 13, 11, 4, 2, 9, 10, 6, 12, 7, 5, 14, 8, 1, 0], [13, 9, 14, 0, 4, 5, 6, 11, 1, 7, 8, 12, 10, 3, 2], [1, 14, 13, 8, 10, 4, 0, 12, 5, 2, 11, 6, 9, 7, 3], [14, 5, 4, 3, 10, 7, 1, 11, 13, 6, 9, 12, 2, 8, 0], [14, 1, 13, 6, 12, 4, 5, 2, 9, 0, 3, 7, 11, 8, 10], [9, 11, 14, 10, 13, 7, 8, 2, 1, 0, 12, 5, 4, 6, 3], [3, 7, 11, 8, 4, 9, 1, 12, 10, 6, 0, 14, 5, 2, 13], [14, 13, 5, 0, 9, 8, 2, 3, 1, 11, 6, 10, 4, 7, 12], [3, 2, 0, 11, 1, 4, 5, 13, 7, 12, 9, 10, 8, 6, 14], [14, 9, 11, 13, 1, 5, 3, 4, 0, 12, 6, 2, 8, 10, 7], [14, 12, 2, 5, 4, 1, 13, 0, 8, 10, 7, 11, 3, 6, 9], [4, 13, 3, 1, 11, 8, 9, 7, 0, 2, 6, 10, 5, 12, 14], [11, 9, 1, 8, 12, 14, 2, 10, 7, 0, 13, 6, 3, 5, 4], [1, 4, 5, 6, 11, 3, 9, 10, 8, 2, 7, 13, 14, 12, 0], [13, 2, 4, 12, 7, 3, 8, 0, 11, 14, 9, 6, 1, 5, 10]]

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
