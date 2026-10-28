# Job Shop Scheduling instance: ta12
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15559

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[81, 48, 55, 8, 21, 66, 11, 7, 59, 8, 80, 59, 91, 5, 64], [46, 68, 15, 23, 76, 82, 80, 5, 76, 51, 48, 9, 40, 51, 86], [23, 26, 33, 20, 55, 70, 84, 84, 70, 54, 31, 39, 97, 42, 33], [77, 60, 11, 3, 82, 14, 21, 22, 82, 92, 89, 36, 52, 85, 3], [87, 36, 81, 96, 33, 11, 89, 91, 83, 24, 13, 26, 15, 59, 99], [41, 7, 51, 95, 87, 1, 45, 99, 55, 77, 89, 74, 91, 67, 20], [35, 34, 99, 33, 71, 9, 27, 28, 77, 2, 68, 85, 18, 47, 92], [20, 33, 58, 86, 92, 84, 1, 66, 80, 28, 96, 37, 76, 97, 68], [95, 49, 25, 11, 18, 90, 38, 17, 36, 61, 33, 17, 62, 57, 73], [57, 77, 42, 65, 89, 96, 44, 82, 43, 64, 68, 38, 87, 76, 84], [54, 13, 64, 15, 16, 53, 84, 48, 94, 66, 57, 93, 63, 8, 62], [67, 67, 46, 42, 16, 83, 76, 5, 26, 46, 70, 29, 29, 83, 21], [74, 54, 16, 58, 45, 49, 50, 14, 35, 41, 42, 96, 69, 8, 9], [71, 48, 11, 45, 27, 31, 90, 69, 85, 20, 18, 29, 92, 17, 86], [24, 71, 41, 5, 24, 50, 8, 75, 42, 54, 34, 93, 80, 35, 82], [16, 24, 88, 61, 79, 63, 43, 53, 67, 18, 5, 41, 85, 54, 4], [12, 56, 27, 96, 23, 41, 65, 95, 37, 55, 70, 56, 24, 36, 17], [12, 67, 6, 69, 56, 79, 81, 36, 88, 74, 89, 98, 16, 19, 3], [38, 45, 80, 74, 21, 91, 97, 98, 54, 76, 47, 46, 79, 35, 92], [13, 39, 34, 88, 82, 62, 38, 50, 62, 26, 89, 63, 56, 42, 33]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 5, 1, 8, 3, 4, 14, 7, 10, 13, 11, 9, 12, 6, 0], [14, 8, 12, 4, 11, 3, 6, 9, 0, 10, 1, 13, 2, 7, 5], [7, 12, 1, 8, 2, 10, 3, 11, 13, 14, 5, 6, 0, 9, 4], [1, 8, 5, 11, 7, 6, 3, 2, 4, 9, 12, 13, 0, 14, 10], [8, 4, 12, 1, 3, 14, 2, 9, 13, 6, 5, 10, 11, 7, 0], [2, 14, 10, 7, 3, 0, 1, 13, 9, 6, 11, 12, 4, 5, 8], [0, 4, 13, 1, 8, 10, 11, 6, 9, 2, 5, 12, 7, 3, 14], [12, 2, 11, 9, 8, 10, 13, 4, 5, 14, 6, 3, 1, 7, 0], [7, 3, 4, 5, 13, 0, 11, 10, 9, 1, 8, 6, 12, 14, 2], [7, 14, 12, 6, 5, 9, 10, 0, 3, 4, 2, 1, 8, 13, 11], [0, 9, 13, 7, 6, 3, 11, 8, 10, 4, 2, 1, 14, 12, 5], [14, 10, 3, 12, 5, 7, 4, 6, 1, 2, 0, 13, 9, 11, 8], [11, 10, 5, 1, 3, 13, 9, 7, 8, 14, 0, 2, 6, 12, 4], [7, 6, 13, 10, 3, 1, 5, 11, 4, 8, 0, 12, 9, 2, 14], [2, 4, 14, 5, 0, 7, 10, 12, 1, 9, 3, 8, 6, 13, 11], [5, 14, 12, 7, 3, 13, 0, 9, 10, 6, 1, 2, 8, 4, 11], [14, 8, 1, 10, 11, 12, 7, 0, 3, 2, 9, 13, 5, 6, 4], [5, 2, 10, 3, 12, 4, 6, 11, 0, 13, 8, 14, 7, 1, 9], [0, 9, 10, 4, 2, 6, 13, 1, 3, 14, 7, 8, 5, 12, 11], [2, 12, 9, 8, 4, 6, 10, 14, 7, 5, 1, 11, 3, 0, 13]]

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
