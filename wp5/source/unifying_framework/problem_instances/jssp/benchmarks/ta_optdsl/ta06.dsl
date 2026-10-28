# Job Shop Scheduling instance: ta06
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11351

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[18, 57, 5, 28, 43, 71, 12, 96, 26, 71, 63, 91, 23, 27, 16], [81, 45, 73, 23, 60, 95, 55, 73, 32, 5, 92, 44, 20, 79, 72], [24, 79, 26, 29, 93, 66, 63, 63, 93, 10, 97, 69, 27, 66, 8], [87, 16, 3, 2, 28, 4, 68, 23, 32, 71, 67, 74, 80, 54, 68], [27, 81, 96, 10, 98, 65, 75, 57, 46, 2, 93, 41, 11, 87, 43], [92, 27, 7, 66, 13, 95, 92, 88, 91, 36, 13, 87, 67, 5, 66], [82, 33, 78, 2, 90, 4, 67, 93, 94, 42, 85, 70, 12, 76, 5], [5, 83, 44, 83, 79, 44, 45, 78, 60, 42, 24, 3, 59, 29, 41], [55, 55, 84, 73, 74, 20, 6, 19, 37, 63, 55, 62, 40, 54, 66], [70, 7, 64, 27, 90, 6, 59, 30, 35, 77, 37, 59, 25, 6, 1], [88, 4, 10, 52, 53, 44, 35, 6, 16, 99, 89, 99, 38, 38, 51], [28, 80, 38, 60, 34, 66, 44, 11, 35, 39, 40, 29, 49, 51, 76], [40, 15, 16, 41, 39, 64, 93, 97, 25, 81, 32, 61, 40, 85, 31], [61, 24, 76, 23, 21, 79, 55, 91, 8, 79, 22, 68, 99, 9, 92], [63, 48, 30, 45, 58, 28, 67, 64, 80, 93, 23, 29, 55, 48, 80]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 12, 5, 8, 3, 14, 13, 9, 0, 1, 4, 2, 6, 11, 10], [8, 0, 5, 13, 6, 1, 4, 2, 3, 11, 10, 12, 9, 14, 7], [6, 8, 7, 1, 9, 5, 12, 4, 0, 2, 14, 11, 3, 13, 10], [12, 0, 14, 7, 13, 1, 6, 8, 11, 2, 3, 9, 5, 10, 4], [8, 2, 12, 11, 10, 9, 4, 3, 14, 5, 0, 7, 6, 13, 1], [13, 8, 6, 11, 14, 9, 12, 7, 0, 1, 10, 2, 5, 3, 4], [4, 1, 2, 13, 7, 6, 0, 8, 12, 14, 10, 9, 5, 3, 11], [4, 10, 14, 3, 6, 13, 11, 9, 0, 5, 1, 12, 8, 7, 2], [7, 1, 5, 4, 14, 8, 0, 9, 12, 3, 10, 2, 13, 11, 6], [3, 6, 13, 4, 5, 10, 2, 8, 12, 11, 9, 7, 14, 1, 0], [1, 4, 7, 2, 14, 10, 12, 13, 6, 5, 9, 0, 3, 8, 11], [0, 7, 14, 13, 8, 3, 6, 9, 5, 12, 10, 4, 1, 2, 11], [14, 10, 0, 8, 12, 13, 4, 11, 1, 3, 6, 5, 2, 9, 7], [13, 4, 8, 6, 5, 2, 9, 0, 11, 12, 1, 3, 14, 7, 10], [14, 2, 6, 4, 3, 11, 1, 5, 7, 0, 8, 10, 9, 12, 13]]

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
