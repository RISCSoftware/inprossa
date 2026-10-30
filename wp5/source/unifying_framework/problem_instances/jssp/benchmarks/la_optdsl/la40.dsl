# Job Shop Scheduling instance: la40
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11472

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[27, 35, 51, 81, 74, 73, 13, 59, 32, 65, 28, 55, 33, 38, 75], [64, 53, 33, 10, 6, 49, 23, 72, 7, 52, 39, 83, 21, 90, 72], [61, 23, 93, 82, 78, 21, 88, 53, 65, 28, 81, 70, 62, 77, 73], [41, 12, 24, 6, 15, 12, 51, 33, 28, 94, 98, 42, 99, 15, 72], [32, 94, 23, 31, 15, 7, 78, 86, 22, 96, 24, 42, 97, 43, 73], [35, 72, 93, 68, 44, 88, 63, 14, 49, 67, 17, 85, 5, 13, 66], [8, 68, 99, 72, 26, 27, 21, 82, 45, 15, 51, 96, 56, 49, 53], [93, 23, 52, 54, 14, 36, 23, 24, 38, 83, 70, 48, 37, 60, 55], [62, 82, 37, 12, 45, 33, 26, 15, 69, 23, 59, 9, 73, 64, 28], [87, 72, 15, 92, 50, 12, 14, 80, 71, 46, 48, 44, 90, 24, 61], [22, 97, 54, 73, 46, 16, 61, 75, 54, 94, 40, 32, 6, 67, 93], [30, 77, 6, 47, 22, 55, 30, 7, 98, 9, 92, 79, 79, 36, 36], [49, 82, 52, 73, 31, 7, 82, 72, 37, 54, 35, 73, 76, 83, 92], [43, 28, 45, 39, 26, 29, 48, 58, 80, 70, 98, 96, 34, 52, 94], [42, 70, 93, 21, 14, 26, 90, 18, 23, 36, 17, 84, 67, 43, 84]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 10, 4, 12, 2, 14, 5, 8, 6, 3, 1, 7, 13, 11, 0], [0, 1, 11, 2, 4, 9, 14, 8, 13, 12, 6, 3, 10, 5, 7], [14, 3, 1, 12, 6, 5, 8, 11, 7, 10, 2, 13, 0, 9, 4], [1, 6, 7, 4, 14, 10, 9, 5, 11, 2, 13, 8, 3, 12, 0], [12, 5, 9, 4, 14, 13, 0, 8, 11, 1, 2, 7, 6, 10, 3], [1, 5, 2, 13, 4, 14, 6, 7, 9, 10, 11, 0, 3, 12, 8], [9, 7, 6, 14, 3, 13, 2, 4, 12, 8, 1, 10, 0, 5, 11], [3, 7, 4, 8, 5, 2, 14, 12, 11, 0, 13, 10, 1, 6, 9], [3, 8, 6, 9, 14, 1, 5, 4, 13, 7, 11, 12, 10, 2, 0], [0, 5, 7, 4, 10, 12, 1, 13, 6, 8, 11, 9, 2, 14, 3], [2, 0, 6, 4, 3, 5, 12, 9, 14, 13, 8, 7, 11, 10, 1], [10, 14, 4, 9, 3, 1, 12, 13, 6, 8, 11, 7, 5, 2, 0], [0, 13, 3, 6, 1, 14, 11, 4, 10, 9, 5, 8, 7, 2, 12], [10, 12, 13, 4, 1, 3, 8, 5, 9, 0, 6, 7, 2, 14, 11], [1, 10, 6, 12, 4, 8, 3, 7, 13, 11, 5, 9, 2, 14, 0]]

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
