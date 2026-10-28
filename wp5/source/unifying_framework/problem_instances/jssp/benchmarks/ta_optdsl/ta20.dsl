# Job Shop Scheduling instance: ta20
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15133

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[58, 98, 12, 73, 26, 45, 28, 84, 45, 36, 87, 30, 71, 73, 95], [82, 79, 56, 75, 29, 57, 34, 47, 22, 94, 35, 14, 4, 15, 23], [94, 73, 63, 49, 36, 66, 74, 48, 60, 8, 15, 91, 90, 26, 39], [57, 50, 7, 40, 75, 1, 40, 75, 41, 23, 7, 35, 93, 60, 72], [67, 14, 53, 47, 13, 33, 18, 39, 65, 94, 61, 15, 17, 52, 16], [72, 88, 54, 87, 17, 82, 80, 77, 36, 90, 44, 37, 17, 84, 54], [42, 67, 31, 67, 4, 33, 39, 30, 86, 83, 62, 67, 31, 39, 62], [39, 97, 46, 55, 53, 65, 22, 29, 13, 69, 29, 69, 24, 17, 26], [36, 99, 80, 12, 71, 51, 35, 14, 70, 35, 58, 73, 28, 70, 12], [61, 90, 59, 26, 60, 49, 4, 26, 94, 3, 88, 34, 74, 60, 91], [1, 16, 9, 90, 89, 97, 62, 58, 95, 18, 13, 73, 32, 36, 19], [7, 95, 72, 15, 81, 19, 47, 49, 96, 71, 41, 73, 46, 24, 63], [97, 46, 19, 9, 45, 70, 32, 70, 15, 78, 23, 86, 6, 77, 62], [86, 27, 76, 98, 53, 59, 1, 98, 12, 11, 46, 98, 74, 91, 98], [57, 7, 17, 91, 73, 14, 32, 70, 32, 10, 79, 19, 56, 96, 73], [67, 19, 81, 27, 20, 79, 39, 7, 24, 42, 67, 58, 11, 9, 87], [81, 14, 47, 46, 99, 89, 81, 40, 27, 76, 14, 3, 11, 85, 64], [20, 93, 29, 8, 5, 60, 63, 15, 4, 55, 33, 16, 71, 71, 83], [67, 79, 25, 8, 47, 22, 23, 97, 48, 94, 17, 96, 92, 24, 86], [57, 35, 47, 5, 98, 59, 69, 88, 37, 62, 74, 80, 77, 54, 13]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 0, 12, 4, 1, 9, 2, 11, 10, 14, 5, 6, 13, 3, 8], [4, 8, 7, 3, 9, 13, 12, 0, 11, 10, 1, 6, 5, 14, 2], [1, 4, 7, 13, 3, 8, 10, 5, 12, 14, 9, 6, 2, 0, 11], [5, 11, 9, 12, 7, 1, 6, 13, 8, 2, 0, 14, 3, 4, 10], [4, 11, 12, 1, 0, 9, 6, 13, 2, 14, 5, 10, 3, 8, 7], [2, 6, 3, 8, 14, 0, 4, 10, 11, 1, 7, 13, 12, 5, 9], [4, 14, 5, 10, 8, 7, 6, 1, 0, 12, 9, 13, 11, 3, 2], [7, 10, 11, 14, 3, 2, 4, 5, 1, 12, 9, 6, 13, 0, 8], [14, 11, 0, 13, 3, 2, 1, 8, 5, 7, 4, 12, 6, 10, 9], [0, 5, 12, 1, 13, 10, 9, 4, 2, 8, 14, 11, 7, 6, 3], [4, 3, 8, 12, 9, 11, 2, 14, 5, 7, 13, 6, 10, 1, 0], [9, 6, 1, 0, 14, 7, 13, 12, 2, 11, 5, 8, 10, 3, 4], [4, 3, 0, 14, 13, 9, 7, 2, 11, 8, 10, 1, 6, 12, 5], [12, 10, 3, 6, 4, 5, 0, 7, 2, 8, 13, 11, 14, 9, 1], [14, 7, 5, 8, 11, 0, 2, 13, 12, 4, 6, 1, 10, 9, 3], [6, 14, 12, 2, 7, 5, 8, 13, 11, 9, 0, 3, 4, 1, 10], [9, 5, 14, 10, 12, 1, 4, 13, 0, 11, 3, 2, 7, 6, 8], [9, 12, 4, 14, 11, 8, 0, 7, 5, 3, 1, 10, 6, 13, 2], [12, 2, 3, 14, 5, 1, 6, 11, 13, 9, 7, 10, 8, 0, 4], [3, 12, 10, 5, 14, 0, 9, 8, 13, 6, 11, 1, 7, 2, 4]]

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
