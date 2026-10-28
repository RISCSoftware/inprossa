# Job Shop Scheduling instance: la39
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11554

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[88, 44, 67, 24, 18, 80, 38, 80, 45, 64, 51, 24, 15, 72, 43], [40, 47, 21, 52, 32, 59, 40, 31, 70, 88, 77, 20, 43, 76, 5], [32, 26, 14, 49, 47, 64, 94, 58, 80, 85, 5, 11, 96, 26, 59], [75, 9, 79, 34, 75, 23, 9, 20, 66, 52, 68, 43, 37, 10, 83], [6, 26, 54, 28, 79, 42, 84, 88, 54, 59, 40, 16, 69, 36, 62], [56, 86, 23, 68, 82, 29, 5, 59, 64, 12, 13, 17, 53, 78, 59], [16, 85, 58, 69, 81, 83, 62, 90, 66, 7, 83, 69, 65, 46, 42], [33, 82, 24, 72, 24, 82, 10, 73, 64, 20, 71, 99, 43, 27, 65], [38, 34, 8, 92, 82, 35, 21, 30, 45, 35, 6, 15, 52, 83, 23], [85, 94, 84, 60, 28, 7, 79, 70, 66, 66, 6, 29, 39, 27, 80], [5, 72, 36, 44, 21, 14, 58, 61, 65, 25, 42, 51, 52, 14, 55], [46, 79, 63, 93, 49, 78, 51, 91, 79, 27, 72, 12, 17, 26, 43], [49, 93, 70, 61, 71, 78, 21, 49, 91, 44, 41, 47, 91, 84, 28], [66, 30, 45, 25, 85, 24, 91, 67, 84, 53, 95, 11, 21, 32, 89], [99, 40, 69, 92, 41, 66, 57, 93, 73, 44, 37, 18, 69, 97, 22]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[10, 14, 7, 4, 6, 3, 2, 12, 11, 13, 8, 5, 9, 1, 0], [6, 9, 10, 5, 11, 3, 8, 0, 4, 13, 12, 7, 2, 14, 1], [0, 3, 10, 5, 7, 8, 6, 11, 1, 13, 14, 9, 4, 12, 2], [5, 6, 0, 12, 11, 2, 4, 3, 7, 13, 14, 10, 9, 8, 1], [12, 9, 3, 14, 13, 1, 6, 11, 8, 5, 2, 0, 10, 7, 4], [13, 12, 11, 5, 4, 2, 9, 8, 1, 7, 6, 3, 14, 10, 0], [10, 13, 9, 12, 11, 6, 0, 2, 8, 5, 7, 14, 4, 3, 1], [7, 10, 8, 6, 9, 11, 4, 14, 5, 3, 12, 1, 13, 2, 0], [4, 1, 3, 2, 0, 8, 6, 5, 12, 9, 11, 14, 10, 13, 7], [2, 5, 9, 10, 4, 13, 6, 7, 0, 1, 3, 14, 12, 8, 11], [3, 6, 13, 8, 1, 5, 12, 4, 9, 0, 11, 7, 14, 10, 2], [14, 10, 5, 11, 12, 0, 9, 6, 2, 1, 8, 7, 4, 13, 3], [7, 0, 4, 5, 9, 10, 12, 13, 8, 6, 11, 14, 3, 2, 1], [3, 4, 0, 2, 10, 12, 8, 5, 9, 7, 6, 11, 13, 1, 14], [3, 7, 0, 1, 10, 12, 5, 6, 14, 9, 8, 13, 11, 2, 4]]

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
