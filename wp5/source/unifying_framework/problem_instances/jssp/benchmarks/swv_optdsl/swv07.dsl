# Job Shop Scheduling instance: swv07
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14564

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 49, 93, 92, 52, 57, 48, 27, 16, 96, 60, 19, 6, 6, 76], [9, 87, 94, 96, 83, 4, 52, 49, 63, 31, 47, 85, 46, 26, 48], [25, 34, 82, 11, 37, 43, 34, 34, 89, 71, 23, 77, 20, 32, 55], [64, 51, 76, 49, 84, 12, 52, 45, 20, 100, 42, 93, 5, 75, 48], [99, 1, 35, 15, 80, 78, 49, 24, 28, 88, 100, 20, 7, 1, 71], [42, 28, 8, 69, 3, 21, 24, 42, 8, 50, 33, 40, 13, 5, 73], [83, 65, 62, 100, 15, 5, 27, 89, 38, 92, 82, 47, 96, 81, 65], [57, 93, 75, 74, 24, 10, 98, 44, 12, 24, 8, 51, 82, 59, 65], [44, 42, 81, 47, 55, 75, 30, 29, 81, 47, 100, 34, 77, 31, 92], [37, 91, 18, 67, 1, 42, 20, 98, 21, 21, 100, 59, 100, 77, 57], [74, 16, 7, 42, 19, 7, 70, 34, 46, 74, 42, 60, 50, 71, 88], [15, 22, 7, 31, 45, 70, 12, 99, 44, 46, 70, 5, 87, 88, 45], [50, 49, 9, 23, 51, 39, 28, 84, 65, 12, 30, 62, 17, 5, 40], [67, 88, 70, 18, 13, 85, 92, 69, 42, 5, 19, 82, 21, 52, 10], [60, 52, 51, 43, 34, 70, 2, 66, 53, 19, 75, 45, 96, 1, 44], [84, 44, 4, 16, 10, 48, 31, 42, 78, 37, 35, 44, 21, 67, 11], [11, 20, 68, 37, 40, 6, 42, 77, 5, 82, 44, 43, 17, 100, 3], [5, 70, 59, 40, 63, 14, 42, 50, 45, 74, 21, 64, 83, 32, 29], [28, 54, 24, 79, 25, 98, 70, 22, 69, 73, 74, 75, 65, 93, 9], [41, 3, 46, 41, 69, 100, 18, 7, 94, 86, 90, 97, 30, 83, 96]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 1, 2, 6, 0, 4, 5, 8, 12, 13, 11, 9, 7, 14, 10], [5, 3, 6, 1, 2, 4, 0, 11, 10, 8, 9, 13, 12, 7, 14], [1, 6, 4, 2, 0, 5, 3, 9, 14, 7, 11, 12, 8, 10, 13], [3, 5, 6, 2, 0, 1, 4, 10, 12, 7, 8, 11, 14, 13, 9], [2, 1, 3, 6, 5, 4, 0, 9, 7, 11, 10, 8, 14, 13, 12], [3, 6, 5, 4, 1, 2, 0, 10, 11, 9, 8, 13, 12, 7, 14], [0, 4, 2, 6, 5, 1, 3, 14, 10, 7, 13, 9, 8, 11, 12], [6, 4, 2, 0, 1, 3, 5, 7, 13, 11, 12, 14, 10, 8, 9], [4, 0, 3, 5, 2, 6, 1, 10, 8, 7, 13, 9, 11, 12, 14], [2, 5, 0, 4, 3, 6, 1, 8, 14, 12, 10, 11, 13, 9, 7], [3, 1, 4, 6, 2, 0, 5, 12, 9, 8, 14, 13, 10, 7, 11], [6, 4, 2, 0, 1, 3, 5, 13, 9, 8, 14, 12, 11, 7, 10], [4, 5, 0, 2, 3, 6, 1, 13, 12, 14, 10, 11, 8, 7, 9], [6, 0, 5, 1, 3, 4, 2, 7, 14, 13, 8, 11, 10, 12, 9], [4, 0, 1, 5, 2, 6, 3, 10, 11, 8, 12, 13, 14, 7, 9], [6, 1, 0, 3, 4, 2, 5, 13, 14, 12, 8, 7, 11, 9, 10], [1, 4, 3, 2, 6, 0, 5, 10, 11, 12, 14, 7, 13, 9, 8], [5, 0, 3, 1, 4, 2, 6, 9, 13, 7, 10, 14, 12, 11, 8], [6, 0, 3, 4, 5, 2, 1, 12, 13, 10, 7, 9, 11, 8, 14], [5, 2, 4, 3, 1, 6, 0, 8, 11, 12, 14, 7, 9, 13, 10]]

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
