# Job Shop Scheduling instance: ta15
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14591

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[44, 87, 48, 95, 44, 79, 49, 15, 40, 59, 88, 75, 89, 43, 11], [32, 15, 79, 46, 44, 4, 56, 76, 6, 44, 5, 1, 18, 92, 40], [45, 78, 4, 76, 49, 51, 80, 82, 61, 53, 36, 26, 94, 49, 36], [19, 3, 88, 5, 85, 38, 18, 69, 28, 66, 70, 58, 10, 34, 87], [11, 2, 83, 42, 26, 24, 7, 89, 39, 13, 75, 39, 10, 61, 78], [40, 42, 49, 6, 3, 88, 36, 80, 98, 11, 15, 62, 13, 92, 59], [32, 76, 53, 70, 81, 31, 75, 7, 48, 1, 78, 1, 82, 12, 83], [49, 80, 84, 68, 9, 57, 77, 75, 41, 64, 15, 11, 82, 13, 50], [54, 9, 26, 80, 88, 39, 49, 48, 18, 50, 77, 64, 97, 27, 99], [78, 26, 82, 27, 87, 75, 31, 12, 47, 66, 85, 49, 86, 25, 68], [28, 75, 72, 76, 52, 26, 74, 51, 98, 73, 60, 93, 3, 87, 1], [86, 13, 67, 5, 14, 58, 28, 27, 33, 94, 32, 79, 14, 70, 38], [69, 83, 46, 89, 8, 67, 84, 18, 91, 85, 8, 22, 20, 4, 25], [20, 43, 30, 78, 64, 3, 10, 12, 43, 25, 18, 32, 49, 65, 53], [23, 53, 86, 68, 29, 1, 49, 71, 99, 65, 7, 50, 91, 99, 89], [1, 11, 62, 55, 24, 94, 78, 56, 19, 13, 31, 16, 76, 13, 43], [6, 41, 30, 6, 25, 43, 47, 86, 24, 6, 49, 20, 67, 85, 44], [80, 77, 68, 97, 15, 29, 23, 72, 22, 92, 41, 36, 49, 80, 4], [83, 51, 58, 61, 34, 75, 74, 13, 10, 65, 96, 80, 78, 14, 43], [67, 69, 33, 90, 21, 22, 89, 83, 20, 11, 56, 59, 89, 15, 16]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 12, 6, 3, 8, 5, 0, 9, 1, 10, 2, 4, 13, 14, 11], [8, 3, 12, 5, 6, 9, 1, 14, 4, 2, 11, 0, 10, 13, 7], [1, 0, 8, 4, 11, 14, 12, 6, 13, 9, 2, 5, 7, 10, 3], [11, 13, 10, 0, 4, 7, 14, 5, 3, 2, 9, 1, 12, 8, 6], [14, 6, 2, 10, 11, 5, 12, 9, 3, 1, 13, 4, 0, 7, 8], [7, 5, 12, 13, 9, 11, 1, 4, 3, 6, 2, 8, 0, 14, 10], [14, 13, 8, 9, 1, 0, 11, 4, 2, 3, 10, 6, 7, 12, 5], [7, 13, 4, 11, 0, 10, 5, 2, 6, 1, 8, 12, 3, 9, 14], [5, 11, 4, 1, 12, 14, 13, 7, 8, 6, 9, 2, 0, 3, 10], [9, 4, 3, 8, 14, 5, 6, 13, 11, 10, 12, 7, 1, 2, 0], [11, 13, 6, 5, 10, 3, 12, 8, 2, 4, 9, 1, 0, 14, 7], [11, 1, 4, 7, 12, 3, 5, 10, 14, 2, 13, 0, 6, 9, 8], [1, 5, 7, 12, 13, 6, 11, 4, 8, 3, 14, 10, 0, 9, 2], [4, 10, 7, 8, 3, 13, 0, 14, 11, 12, 9, 6, 1, 2, 5], [8, 4, 11, 13, 1, 9, 0, 6, 12, 5, 2, 10, 3, 7, 14], [13, 8, 10, 5, 6, 14, 11, 7, 12, 0, 1, 4, 9, 2, 3], [5, 8, 13, 11, 9, 14, 10, 1, 12, 6, 4, 7, 3, 0, 2], [2, 9, 4, 0, 5, 7, 8, 10, 12, 11, 3, 13, 6, 1, 14], [1, 4, 8, 10, 6, 11, 9, 5, 13, 0, 7, 12, 3, 14, 2], [1, 10, 13, 12, 5, 4, 6, 14, 11, 7, 8, 2, 9, 0, 3]]

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
