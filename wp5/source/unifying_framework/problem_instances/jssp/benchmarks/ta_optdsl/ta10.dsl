# Job Shop Scheduling instance: ta10
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11356

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[14, 85, 78, 70, 93, 90, 36, 79, 35, 95, 49, 1, 53, 14, 65], [71, 12, 83, 63, 29, 54, 22, 93, 41, 16, 85, 52, 30, 62, 45], [24, 37, 98, 92, 86, 60, 57, 69, 71, 81, 60, 43, 50, 66, 2], [30, 94, 44, 51, 52, 57, 6, 16, 35, 14, 1, 93, 25, 59, 95], [32, 95, 50, 75, 69, 38, 11, 78, 96, 4, 39, 63, 95, 98, 2], [99, 13, 28, 33, 88, 47, 23, 73, 49, 43, 57, 7, 72, 21, 38], [52, 67, 3, 31, 64, 2, 25, 16, 18, 83, 80, 90, 93, 64, 91], [5, 54, 17, 5, 37, 95, 30, 63, 68, 46, 42, 22, 54, 23, 89], [51, 18, 26, 18, 59, 72, 87, 62, 44, 60, 15, 55, 40, 3, 35], [91, 59, 27, 19, 33, 30, 14, 11, 55, 24, 88, 67, 77, 29, 11], [67, 49, 19, 38, 50, 88, 32, 99, 2, 94, 83, 29, 37, 70, 58], [12, 7, 84, 93, 1, 82, 7, 58, 60, 16, 83, 69, 81, 3, 8], [4, 44, 4, 74, 5, 60, 8, 9, 78, 78, 50, 94, 75, 92, 81], [88, 32, 68, 45, 82, 22, 55, 51, 10, 99, 84, 44, 31, 31, 75], [28, 67, 64, 12, 74, 17, 46, 65, 96, 42, 95, 56, 86, 35, 93]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 2, 7, 14, 12, 0, 4, 3, 13, 5, 9, 10, 6, 1, 11], [2, 8, 6, 4, 11, 0, 9, 7, 5, 3, 1, 10, 13, 14, 12], [5, 11, 8, 14, 12, 1, 4, 9, 10, 6, 13, 0, 2, 3, 7], [9, 13, 8, 6, 12, 5, 10, 2, 1, 0, 14, 11, 3, 4, 7], [8, 10, 3, 13, 14, 5, 4, 0, 12, 11, 9, 6, 2, 1, 7], [7, 2, 9, 5, 10, 4, 3, 1, 11, 8, 6, 14, 13, 0, 12], [2, 10, 1, 12, 14, 3, 0, 4, 9, 5, 11, 13, 7, 8, 6], [13, 6, 11, 12, 8, 7, 14, 5, 3, 4, 0, 10, 2, 1, 9], [8, 4, 6, 7, 0, 11, 13, 12, 2, 3, 10, 1, 5, 14, 9], [2, 6, 12, 9, 8, 11, 1, 3, 13, 4, 10, 5, 0, 7, 14], [0, 9, 4, 8, 10, 2, 11, 12, 14, 6, 3, 7, 5, 1, 13], [8, 1, 12, 5, 7, 10, 9, 4, 11, 6, 13, 2, 14, 0, 3], [13, 14, 2, 9, 7, 8, 12, 4, 10, 6, 1, 0, 5, 11, 3], [1, 0, 12, 2, 13, 8, 3, 14, 4, 7, 6, 9, 11, 10, 5], [3, 13, 2, 5, 9, 6, 7, 4, 8, 0, 12, 10, 14, 1, 11]]

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
