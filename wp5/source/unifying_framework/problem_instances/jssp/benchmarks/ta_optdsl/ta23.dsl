# Job Shop Scheduling instance: ta23
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20086

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[81, 13, 58, 7, 8, 19, 50, 33, 90, 65, 68, 7, 9, 50, 69, 74, 91, 28, 91, 53], [28, 5, 37, 69, 51, 55, 4, 9, 99, 46, 94, 91, 10, 94, 10, 59, 93, 58, 95, 10], [70, 4, 35, 74, 35, 69, 12, 91, 82, 46, 13, 65, 87, 16, 84, 79, 31, 94, 34, 39], [96, 94, 22, 13, 15, 25, 56, 40, 66, 47, 23, 72, 81, 67, 53, 84, 17, 50, 24, 79], [48, 21, 32, 78, 77, 62, 81, 92, 88, 23, 34, 21, 88, 91, 78, 50, 78, 10, 10, 7], [71, 50, 24, 9, 90, 55, 90, 59, 66, 83, 18, 43, 87, 63, 66, 6, 19, 52, 25, 22], [26, 29, 71, 38, 72, 42, 55, 80, 66, 17, 32, 41, 64, 35, 39, 91, 61, 63, 10, 27], [77, 5, 85, 49, 64, 18, 92, 62, 57, 46, 30, 93, 77, 84, 85, 12, 24, 11, 33, 43], [30, 90, 72, 75, 55, 1, 87, 87, 43, 31, 30, 38, 52, 21, 4, 57, 3, 30, 25, 79], [9, 20, 40, 91, 39, 97, 11, 27, 49, 17, 47, 70, 78, 40, 59, 22, 2, 69, 91, 67], [77, 55, 34, 67, 1, 64, 32, 27, 26, 37, 23, 3, 90, 82, 94, 47, 57, 77, 54, 14], [49, 5, 54, 13, 25, 99, 53, 33, 3, 32, 27, 32, 85, 45, 28, 86, 12, 99, 35, 73], [68, 47, 82, 81, 98, 64, 73, 63, 32, 75, 16, 72, 64, 77, 25, 31, 12, 58, 32, 84], [44, 45, 73, 44, 82, 99, 21, 48, 39, 1, 62, 79, 50, 44, 89, 43, 72, 17, 98, 60], [87, 42, 20, 30, 88, 84, 44, 63, 52, 25, 8, 43, 87, 46, 88, 74, 41, 77, 88, 77], [39, 23, 35, 93, 43, 3, 56, 45, 79, 21, 49, 68, 48, 7, 60, 44, 75, 8, 71, 20], [60, 83, 7, 75, 48, 99, 33, 80, 16, 83, 43, 99, 34, 43, 34, 92, 48, 94, 6, 11], [73, 37, 97, 97, 11, 10, 58, 54, 11, 30, 2, 47, 37, 37, 84, 24, 90, 80, 89, 31], [54, 8, 20, 97, 42, 94, 50, 36, 38, 16, 52, 1, 56, 31, 72, 7, 32, 76, 29, 68], [75, 86, 29, 7, 81, 37, 95, 79, 29, 49, 91, 16, 1, 52, 46, 47, 21, 31, 47, 44]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 4, 0, 10, 17, 18, 16, 15, 3, 11, 5, 6, 9, 19, 12, 8, 14, 13, 2, 1], [3, 19, 17, 14, 11, 1, 2, 7, 16, 13, 9, 5, 8, 0, 18, 10, 6, 4, 15, 12], [15, 0, 4, 8, 2, 14, 18, 12, 7, 5, 6, 16, 17, 11, 10, 13, 19, 9, 1, 3], [17, 7, 12, 9, 0, 13, 1, 14, 2, 16, 10, 18, 8, 4, 6, 15, 19, 5, 3, 11], [19, 6, 5, 15, 13, 4, 2, 18, 3, 16, 11, 14, 1, 17, 8, 9, 7, 10, 12, 0], [14, 0, 5, 18, 11, 2, 12, 7, 6, 13, 4, 19, 15, 1, 3, 10, 16, 17, 9, 8], [8, 14, 18, 7, 6, 3, 1, 11, 17, 10, 15, 19, 4, 2, 16, 13, 9, 0, 5, 12], [17, 18, 13, 15, 5, 8, 19, 16, 0, 2, 7, 3, 1, 9, 11, 14, 6, 10, 4, 12], [11, 0, 9, 18, 1, 19, 16, 12, 6, 10, 7, 14, 15, 8, 4, 13, 17, 5, 2, 3], [0, 8, 18, 4, 13, 14, 1, 7, 19, 15, 16, 10, 3, 6, 11, 5, 12, 17, 9, 2], [16, 6, 3, 8, 10, 1, 19, 17, 0, 13, 2, 4, 5, 12, 9, 15, 7, 18, 11, 14], [4, 7, 16, 10, 9, 0, 18, 1, 19, 8, 14, 2, 13, 11, 6, 5, 12, 15, 3, 17], [12, 13, 2, 18, 9, 8, 0, 10, 7, 3, 15, 17, 6, 16, 14, 5, 4, 11, 1, 19], [17, 18, 5, 8, 2, 4, 9, 15, 7, 10, 3, 12, 13, 16, 14, 1, 0, 6, 11, 19], [12, 7, 10, 2, 18, 4, 19, 14, 13, 3, 6, 1, 5, 16, 15, 8, 9, 0, 11, 17], [0, 3, 15, 1, 16, 13, 14, 7, 18, 10, 5, 11, 6, 19, 2, 17, 8, 9, 12, 4], [3, 15, 1, 4, 2, 11, 13, 17, 18, 14, 16, 0, 6, 8, 12, 5, 9, 19, 7, 10], [2, 17, 10, 1, 19, 12, 6, 8, 15, 14, 5, 9, 3, 18, 11, 13, 0, 4, 16, 7], [11, 3, 19, 1, 15, 14, 8, 6, 4, 16, 0, 5, 13, 10, 17, 2, 18, 12, 7, 9], [2, 17, 9, 10, 3, 5, 1, 0, 16, 14, 15, 12, 11, 8, 18, 4, 13, 19, 6, 7]]

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
