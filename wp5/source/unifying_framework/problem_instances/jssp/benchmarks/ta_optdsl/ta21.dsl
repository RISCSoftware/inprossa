# Job Shop Scheduling instance: ta21
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20169

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[15, 57, 98, 20, 94, 45, 64, 9, 94, 9, 47, 1, 14, 87, 85, 81, 93, 66, 62, 59], [83, 58, 78, 60, 47, 7, 96, 64, 39, 83, 88, 68, 91, 97, 44, 25, 42, 3, 33, 77], [22, 96, 82, 66, 88, 94, 27, 62, 15, 65, 89, 39, 60, 10, 92, 53, 26, 10, 66, 14], [57, 70, 31, 79, 51, 18, 99, 33, 51, 74, 96, 91, 88, 78, 7, 92, 8, 18, 93, 83], [20, 68, 4, 39, 68, 6, 30, 50, 54, 73, 82, 23, 40, 82, 54, 86, 35, 21, 30, 53], [94, 95, 23, 27, 60, 56, 99, 79, 30, 32, 93, 9, 36, 29, 21, 78, 58, 91, 76, 92], [42, 52, 14, 65, 31, 87, 26, 78, 61, 96, 29, 93, 83, 30, 62, 50, 16, 88, 70, 42], [61, 19, 73, 75, 32, 37, 24, 68, 20, 9, 4, 87, 43, 52, 54, 49, 18, 66, 91, 85], [7, 57, 83, 3, 82, 56, 96, 13, 87, 30, 62, 6, 7, 78, 80, 62, 85, 35, 99, 91], [6, 17, 88, 66, 5, 8, 69, 60, 89, 85, 13, 15, 88, 41, 30, 78, 59, 45, 66, 82], [8, 49, 32, 91, 73, 90, 89, 6, 35, 27, 47, 28, 43, 51, 8, 90, 80, 75, 1, 93], [33, 62, 50, 60, 28, 84, 97, 67, 80, 34, 31, 3, 20, 65, 33, 69, 77, 45, 58, 87], [30, 7, 75, 90, 75, 35, 56, 96, 16, 51, 17, 89, 18, 28, 59, 48, 17, 63, 44, 21], [83, 26, 68, 61, 37, 20, 85, 20, 34, 97, 16, 9, 8, 57, 5, 36, 42, 87, 12, 73], [63, 41, 35, 97, 45, 11, 12, 22, 5, 86, 74, 78, 33, 8, 33, 9, 47, 10, 44, 10], [94, 5, 51, 16, 23, 15, 57, 55, 84, 35, 96, 33, 34, 50, 11, 69, 60, 21, 59, 12], [81, 34, 40, 48, 25, 4, 12, 72, 42, 46, 85, 16, 25, 62, 8, 5, 27, 67, 50, 15], [20, 86, 91, 28, 21, 40, 24, 73, 43, 68, 92, 55, 97, 60, 4, 25, 19, 83, 38, 3], [98, 12, 80, 81, 96, 71, 79, 49, 7, 39, 46, 16, 64, 99, 28, 97, 46, 75, 29, 32], [93, 4, 86, 11, 49, 13, 7, 80, 47, 24, 9, 92, 75, 71, 8, 35, 82, 34, 29, 6]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 1, 15, 2, 19, 13, 16, 18, 3, 12, 14, 5, 10, 7, 8, 9, 0, 17, 11, 4], [8, 6, 10, 9, 19, 1, 0, 17, 2, 11, 7, 13, 18, 15, 4, 14, 5, 3, 16, 12], [1, 3, 4, 12, 0, 14, 7, 19, 10, 11, 5, 18, 13, 15, 16, 8, 9, 2, 17, 6], [18, 15, 10, 1, 19, 9, 2, 12, 4, 0, 13, 16, 14, 11, 3, 5, 8, 17, 6, 7], [2, 10, 12, 15, 7, 14, 17, 5, 8, 1, 13, 0, 3, 16, 4, 9, 11, 18, 6, 19], [0, 16, 10, 9, 17, 8, 5, 3, 19, 11, 15, 2, 14, 4, 12, 13, 1, 6, 7, 18], [11, 0, 1, 19, 9, 10, 8, 17, 18, 16, 4, 3, 12, 7, 6, 15, 5, 14, 2, 13], [16, 3, 8, 10, 18, 7, 1, 14, 19, 2, 12, 6, 5, 11, 17, 4, 13, 9, 15, 0], [17, 18, 15, 11, 10, 12, 14, 3, 1, 0, 16, 9, 6, 19, 7, 8, 4, 2, 13, 5], [9, 5, 3, 2, 11, 4, 16, 14, 7, 13, 1, 18, 8, 15, 12, 6, 17, 19, 0, 10], [5, 9, 18, 0, 3, 16, 6, 1, 2, 11, 15, 19, 7, 8, 4, 10, 12, 17, 14, 13], [11, 5, 9, 4, 3, 15, 17, 7, 18, 19, 13, 1, 6, 12, 10, 0, 14, 16, 2, 8], [15, 3, 4, 7, 18, 13, 19, 9, 2, 10, 11, 14, 6, 17, 12, 16, 0, 8, 1, 5], [13, 10, 16, 8, 4, 1, 2, 19, 14, 12, 18, 17, 0, 5, 9, 7, 6, 3, 11, 15], [0, 5, 4, 19, 14, 8, 1, 16, 15, 10, 12, 2, 11, 6, 7, 18, 13, 3, 17, 9], [11, 16, 17, 10, 15, 12, 0, 5, 4, 8, 3, 7, 13, 1, 18, 9, 19, 6, 14, 2], [7, 8, 5, 13, 19, 16, 11, 1, 14, 18, 10, 6, 3, 15, 4, 2, 0, 9, 17, 12], [17, 10, 15, 5, 4, 14, 8, 18, 13, 6, 19, 3, 1, 9, 11, 2, 12, 16, 7, 0], [14, 3, 16, 0, 10, 18, 4, 1, 5, 19, 12, 9, 11, 15, 13, 7, 17, 8, 6, 2], [13, 10, 3, 14, 1, 8, 0, 16, 19, 4, 6, 9, 11, 5, 2, 7, 17, 12, 15, 18]]

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
