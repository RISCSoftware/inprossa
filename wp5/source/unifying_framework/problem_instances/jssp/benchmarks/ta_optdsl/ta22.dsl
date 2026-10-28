# Job Shop Scheduling instance: ta22
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20143

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[92, 34, 61, 94, 20, 30, 51, 88, 16, 67, 40, 68, 53, 84, 12, 16, 30, 55, 61, 12], [86, 89, 48, 10, 29, 33, 92, 47, 77, 35, 21, 40, 75, 75, 22, 46, 9, 87, 1, 2], [99, 53, 91, 20, 79, 39, 84, 41, 21, 93, 17, 97, 67, 14, 22, 97, 54, 8, 32, 19], [9, 35, 81, 45, 54, 4, 32, 37, 97, 2, 43, 93, 41, 76, 6, 10, 35, 13, 97, 77], [4, 33, 23, 69, 95, 86, 65, 20, 26, 47, 58, 20, 70, 38, 89, 77, 67, 53, 71, 87], [73, 5, 33, 87, 96, 89, 86, 16, 33, 93, 87, 68, 87, 6, 98, 46, 26, 67, 37, 12], [74, 34, 92, 30, 68, 37, 2, 76, 20, 84, 50, 67, 3, 11, 96, 37, 38, 89, 80, 27], [44, 73, 54, 36, 99, 60, 13, 80, 28, 44, 27, 80, 97, 69, 82, 82, 33, 24, 90, 42], [4, 93, 79, 31, 64, 83, 16, 11, 62, 80, 27, 24, 19, 35, 57, 12, 72, 4, 96, 20], [28, 84, 86, 85, 63, 14, 16, 46, 76, 89, 50, 2, 86, 46, 44, 79, 19, 61, 60, 58], [46, 3, 62, 27, 19, 10, 78, 10, 26, 86, 97, 61, 44, 75, 22, 30, 92, 10, 88, 22], [5, 50, 16, 75, 21, 80, 86, 61, 20, 38, 81, 3, 52, 25, 83, 82, 94, 51, 26, 57], [27, 7, 49, 26, 94, 74, 82, 80, 17, 14, 86, 12, 6, 46, 3, 82, 86, 26, 27, 97], [28, 46, 91, 61, 67, 79, 72, 49, 21, 22, 2, 99, 17, 34, 38, 14, 42, 83, 1, 61], [63, 52, 80, 3, 40, 1, 86, 49, 53, 68, 39, 62, 71, 50, 70, 61, 58, 43, 97, 5], [51, 20, 30, 24, 93, 37, 72, 41, 91, 31, 58, 40, 86, 15, 61, 53, 16, 49, 25, 8], [32, 85, 34, 72, 57, 75, 44, 5, 61, 45, 19, 77, 23, 89, 40, 83, 86, 77, 35, 77], [1, 77, 34, 3, 37, 70, 16, 21, 53, 24, 22, 60, 42, 15, 32, 69, 67, 33, 75, 64], [1, 16, 20, 83, 96, 58, 55, 53, 68, 88, 30, 1, 5, 79, 54, 66, 91, 84, 55, 14], [68, 19, 79, 80, 49, 51, 83, 64, 96, 65, 9, 4, 88, 84, 92, 81, 92, 66, 32, 21]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 2, 19, 11, 10, 13, 16, 15, 1, 0, 12, 17, 18, 9, 5, 7, 14, 4, 8, 6], [14, 12, 4, 17, 7, 2, 10, 15, 8, 9, 3, 6, 16, 13, 11, 1, 0, 5, 19, 18], [18, 17, 0, 13, 7, 1, 11, 19, 5, 3, 2, 16, 15, 4, 8, 14, 9, 12, 10, 6], [17, 10, 8, 12, 5, 16, 14, 11, 6, 1, 9, 4, 19, 0, 18, 15, 3, 2, 13, 7], [8, 12, 1, 10, 13, 15, 5, 17, 9, 7, 18, 3, 4, 0, 2, 14, 19, 11, 16, 6], [6, 0, 9, 16, 14, 18, 17, 10, 2, 13, 11, 7, 19, 1, 8, 3, 4, 15, 12, 5], [12, 1, 6, 14, 11, 15, 3, 10, 9, 19, 5, 17, 2, 4, 8, 18, 7, 0, 13, 16], [5, 12, 19, 1, 8, 13, 18, 9, 10, 2, 17, 3, 15, 6, 16, 7, 0, 4, 11, 14], [2, 8, 3, 10, 16, 15, 0, 17, 7, 13, 5, 14, 12, 9, 19, 6, 18, 11, 4, 1], [17, 2, 7, 19, 11, 16, 13, 10, 15, 1, 5, 6, 8, 9, 3, 12, 18, 14, 0, 4], [7, 12, 8, 11, 16, 15, 4, 3, 14, 9, 19, 2, 13, 17, 6, 1, 10, 18, 5, 0], [4, 17, 11, 16, 15, 18, 14, 19, 6, 7, 5, 10, 13, 0, 3, 9, 2, 8, 1, 12], [8, 16, 12, 2, 5, 15, 10, 17, 7, 13, 4, 1, 0, 3, 19, 9, 18, 14, 11, 6], [1, 8, 18, 11, 17, 9, 10, 16, 19, 5, 12, 4, 3, 6, 7, 2, 14, 0, 13, 15], [13, 7, 4, 0, 19, 2, 14, 3, 11, 17, 16, 10, 1, 9, 12, 6, 15, 8, 5, 18], [15, 0, 18, 16, 8, 4, 5, 14, 7, 17, 1, 3, 10, 19, 6, 2, 13, 12, 9, 11], [3, 11, 2, 9, 15, 1, 10, 7, 19, 5, 8, 13, 17, 6, 0, 16, 14, 12, 18, 4], [17, 6, 11, 5, 16, 4, 12, 9, 18, 0, 10, 14, 7, 3, 15, 1, 8, 19, 2, 13], [5, 6, 8, 12, 2, 9, 16, 13, 18, 1, 7, 17, 0, 15, 19, 3, 11, 4, 14, 10], [3, 15, 10, 4, 18, 1, 16, 9, 12, 7, 11, 0, 2, 19, 13, 14, 17, 5, 6, 8]]

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
