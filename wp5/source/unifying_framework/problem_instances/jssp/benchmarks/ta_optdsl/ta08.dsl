# Job Shop Scheduling instance: ta08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11402

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[19, 80, 88, 83, 30, 65, 1, 96, 49, 92, 9, 64, 81, 54, 32], [83, 79, 4, 84, 92, 38, 76, 68, 66, 38, 96, 99, 68, 21, 51], [75, 55, 59, 66, 96, 58, 24, 24, 46, 56, 88, 82, 80, 35, 57], [76, 30, 81, 3, 98, 34, 59, 81, 38, 81, 39, 53, 71, 69, 8], [27, 96, 36, 3, 14, 80, 99, 9, 34, 95, 27, 90, 42, 85, 57], [61, 72, 66, 81, 84, 2, 92, 56, 35, 73, 69, 11, 23, 98, 28], [76, 99, 77, 37, 44, 95, 36, 22, 21, 89, 5, 16, 5, 85, 46], [99, 44, 6, 87, 84, 38, 41, 80, 83, 49, 83, 68, 61, 79, 9], [77, 69, 6, 5, 51, 68, 99, 26, 51, 82, 90, 6, 1, 27, 34], [4, 76, 95, 76, 14, 18, 52, 55, 85, 33, 91, 64, 34, 68, 89], [51, 33, 16, 11, 8, 36, 1, 80, 75, 90, 65, 47, 40, 5, 42], [41, 47, 20, 38, 48, 15, 16, 97, 89, 10, 21, 95, 97, 74, 83], [65, 15, 37, 24, 11, 23, 6, 28, 22, 28, 89, 4, 88, 14, 39], [4, 7, 66, 48, 6, 4, 14, 59, 2, 1, 54, 75, 5, 82, 58], [50, 14, 66, 16, 96, 79, 23, 15, 3, 4, 24, 86, 63, 20, 91]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 6, 7, 13, 4, 1, 12, 10, 8, 14, 0, 9, 5, 2, 11], [2, 12, 1, 13, 3, 4, 8, 14, 0, 10, 7, 5, 9, 11, 6], [8, 14, 3, 0, 10, 5, 9, 13, 2, 11, 6, 4, 7, 1, 12], [5, 13, 11, 4, 14, 2, 9, 8, 10, 3, 6, 7, 1, 0, 12], [13, 5, 2, 14, 1, 8, 4, 3, 11, 6, 7, 12, 9, 0, 10], [14, 11, 2, 5, 8, 10, 0, 4, 9, 7, 13, 3, 1, 6, 12], [8, 12, 5, 10, 7, 11, 2, 13, 0, 14, 6, 9, 1, 4, 3], [9, 7, 12, 3, 6, 2, 10, 13, 1, 8, 14, 4, 0, 5, 11], [0, 4, 5, 1, 11, 7, 6, 2, 14, 13, 8, 9, 3, 10, 12], [8, 11, 7, 1, 14, 13, 12, 4, 6, 9, 10, 0, 5, 2, 3], [12, 4, 5, 13, 6, 0, 1, 7, 9, 8, 11, 10, 14, 2, 3], [3, 14, 4, 13, 5, 9, 8, 0, 7, 12, 6, 1, 10, 11, 2], [10, 8, 4, 1, 2, 0, 7, 14, 12, 13, 9, 6, 3, 11, 5], [6, 2, 0, 14, 1, 4, 12, 3, 10, 7, 8, 9, 5, 13, 11], [10, 2, 9, 13, 5, 0, 6, 7, 1, 14, 11, 4, 12, 3, 8]]

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
