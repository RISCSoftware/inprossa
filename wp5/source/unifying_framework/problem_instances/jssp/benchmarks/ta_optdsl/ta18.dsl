# Job Shop Scheduling instance: ta18
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14919

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[55, 70, 46, 7, 14, 33, 6, 14, 57, 18, 29, 92, 62, 66, 55], [30, 84, 1, 19, 80, 81, 10, 75, 98, 53, 73, 15, 62, 97, 63], [74, 42, 6, 24, 70, 90, 61, 61, 38, 11, 78, 60, 35, 60, 1], [84, 71, 66, 86, 3, 27, 13, 57, 72, 17, 27, 98, 76, 90, 84], [50, 55, 42, 14, 76, 6, 24, 35, 80, 12, 58, 26, 33, 38, 38], [85, 13, 87, 84, 1, 18, 25, 2, 77, 59, 54, 29, 19, 63, 51], [4, 68, 88, 83, 68, 19, 55, 22, 71, 39, 11, 19, 68, 37, 80], [97, 3, 19, 2, 43, 38, 56, 33, 98, 90, 76, 1, 11, 76, 83], [40, 19, 23, 74, 99, 43, 75, 88, 65, 40, 48, 39, 56, 39, 25], [97, 71, 54, 74, 9, 29, 98, 46, 25, 74, 23, 85, 65, 12, 66], [74, 3, 76, 40, 90, 93, 12, 67, 52, 67, 71, 81, 20, 24, 16], [16, 27, 46, 95, 85, 85, 1, 67, 59, 67, 79, 26, 13, 56, 64], [62, 64, 66, 26, 35, 7, 1, 56, 8, 42, 94, 32, 60, 94, 29], [21, 3, 1, 93, 7, 53, 58, 88, 25, 40, 82, 55, 19, 30, 75], [51, 77, 66, 48, 78, 38, 98, 88, 38, 61, 25, 41, 93, 14, 16], [19, 74, 23, 32, 7, 69, 60, 2, 41, 54, 33, 15, 22, 79, 83], [26, 69, 61, 6, 34, 66, 15, 80, 3, 73, 75, 59, 65, 39, 85], [6, 58, 31, 96, 16, 35, 26, 57, 52, 29, 79, 52, 74, 72, 22], [79, 42, 81, 71, 11, 25, 81, 84, 90, 70, 88, 49, 61, 60, 8], [91, 52, 43, 72, 66, 27, 97, 88, 23, 42, 50, 82, 3, 62, 57]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 6, 10, 14, 7, 5, 13, 4, 3, 8, 0, 9, 12, 2, 11], [0, 9, 3, 2, 8, 5, 14, 12, 6, 11, 10, 7, 4, 1, 13], [1, 6, 2, 11, 3, 4, 10, 9, 12, 8, 7, 5, 0, 14, 13], [12, 14, 8, 9, 5, 3, 0, 1, 13, 10, 6, 11, 4, 7, 2], [14, 10, 8, 6, 0, 4, 5, 9, 11, 3, 7, 13, 1, 12, 2], [8, 2, 9, 12, 3, 0, 13, 14, 5, 11, 7, 1, 4, 6, 10], [5, 3, 8, 7, 0, 12, 4, 2, 14, 6, 10, 11, 9, 1, 13], [5, 8, 12, 1, 7, 4, 2, 9, 6, 14, 13, 0, 3, 10, 11], [14, 8, 7, 12, 6, 10, 0, 1, 11, 9, 5, 4, 2, 3, 13], [0, 14, 2, 5, 10, 4, 9, 7, 11, 6, 3, 13, 1, 12, 8], [1, 3, 11, 0, 9, 5, 2, 14, 6, 7, 8, 12, 13, 10, 4], [12, 8, 3, 10, 2, 0, 7, 9, 14, 5, 4, 1, 11, 13, 6], [1, 6, 14, 2, 11, 4, 8, 3, 13, 10, 0, 9, 12, 7, 5], [1, 4, 9, 3, 11, 14, 8, 0, 13, 10, 2, 6, 5, 7, 12], [2, 7, 3, 1, 8, 4, 14, 11, 12, 5, 10, 0, 13, 6, 9], [10, 2, 4, 6, 1, 9, 7, 12, 3, 11, 13, 14, 5, 8, 0], [2, 0, 5, 14, 4, 6, 11, 10, 8, 7, 13, 1, 3, 9, 12], [3, 0, 11, 14, 5, 10, 4, 13, 9, 6, 8, 1, 7, 2, 12], [1, 0, 7, 5, 9, 8, 14, 13, 2, 10, 4, 3, 12, 11, 6], [1, 12, 14, 4, 7, 9, 8, 3, 6, 0, 10, 2, 11, 13, 5]]

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
