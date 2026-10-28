# Job Shop Scheduling instance: ta03
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11181

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[62, 3, 3, 62, 82, 88, 66, 69, 81, 88, 12, 81, 80, 38, 54], [89, 51, 52, 76, 18, 22, 89, 22, 85, 15, 5, 47, 83, 26, 30], [54, 62, 47, 38, 96, 78, 9, 90, 71, 93, 33, 21, 44, 71, 19], [41, 3, 30, 10, 11, 55, 80, 31, 92, 12, 82, 26, 75, 33, 96], [89, 36, 65, 19, 10, 72, 69, 11, 49, 37, 57, 73, 12, 32, 43], [56, 94, 6, 52, 76, 83, 46, 72, 32, 30, 87, 36, 13, 62, 32], [21, 27, 78, 64, 99, 29, 72, 16, 17, 49, 15, 14, 19, 38, 43], [27, 3, 50, 25, 12, 18, 55, 74, 62, 15, 4, 49, 71, 5, 38], [33, 22, 59, 97, 16, 31, 94, 61, 25, 47, 86, 13, 48, 40, 69], [4, 46, 96, 35, 23, 84, 96, 74, 18, 27, 80, 23, 49, 46, 72], [92, 81, 17, 47, 51, 82, 23, 36, 96, 35, 54, 38, 67, 7, 5], [78, 24, 42, 79, 9, 56, 76, 80, 58, 1, 49, 26, 43, 24, 62], [57, 17, 96, 36, 99, 14, 11, 17, 38, 64, 38, 38, 86, 58, 83], [63, 90, 86, 75, 77, 8, 27, 96, 64, 69, 62, 93, 40, 10, 61], [14, 73, 3, 53, 84, 58, 87, 95, 84, 90, 47, 71, 68, 12, 75]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 11, 8, 3, 12, 1, 13, 0, 14, 6, 9, 4, 2, 10, 5], [12, 1, 11, 9, 6, 3, 2, 4, 5, 8, 13, 14, 10, 0, 7], [1, 2, 9, 0, 3, 5, 8, 4, 14, 10, 12, 13, 7, 6, 11], [13, 10, 6, 2, 14, 7, 4, 11, 0, 5, 9, 3, 8, 1, 12], [1, 8, 4, 14, 6, 5, 3, 2, 9, 10, 13, 7, 11, 0, 12], [5, 14, 2, 12, 10, 1, 11, 4, 6, 9, 0, 13, 8, 3, 7], [5, 2, 0, 1, 8, 14, 11, 10, 7, 9, 6, 12, 4, 13, 3], [4, 7, 10, 1, 9, 8, 2, 14, 11, 3, 5, 6, 13, 12, 0], [14, 11, 0, 9, 10, 5, 3, 12, 8, 13, 6, 1, 7, 2, 4], [9, 0, 3, 10, 12, 13, 5, 1, 6, 14, 8, 11, 2, 7, 4], [7, 2, 1, 12, 3, 14, 4, 6, 5, 9, 8, 13, 10, 0, 11], [0, 8, 14, 12, 9, 5, 6, 10, 7, 11, 3, 4, 1, 13, 2], [8, 12, 10, 11, 14, 3, 6, 1, 4, 5, 0, 9, 13, 2, 7], [13, 2, 11, 0, 14, 10, 3, 1, 12, 4, 5, 6, 7, 9, 8], [1, 13, 0, 11, 2, 10, 4, 8, 3, 5, 7, 6, 9, 12, 14]]

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
