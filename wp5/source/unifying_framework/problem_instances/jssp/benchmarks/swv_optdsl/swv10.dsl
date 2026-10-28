# Job Shop Scheduling instance: swv10
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15737

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[95, 79, 73, 8, 9, 5, 69, 91, 85, 52, 24, 43, 38, 89, 32], [20, 70, 71, 24, 84, 18, 45, 60, 21, 98, 70, 23, 34, 52, 52], [39, 85, 98, 61, 68, 40, 16, 60, 16, 66, 77, 73, 88, 43, 84], [72, 17, 94, 68, 89, 56, 98, 88, 8, 60, 88, 48, 61, 27, 65], [73, 69, 24, 52, 21, 28, 78, 82, 83, 43, 29, 48, 92, 48, 32], [82, 75, 4, 47, 54, 14, 31, 58, 31, 45, 27, 61, 72, 91, 31], [14, 28, 65, 93, 88, 92, 62, 33, 31, 44, 34, 72, 61, 47, 32], [52, 59, 19, 6, 39, 98, 53, 22, 74, 37, 33, 92, 48, 49, 41], [2, 73, 51, 34, 97, 95, 85, 75, 21, 28, 7, 85, 73, 42, 61], [77, 28, 56, 82, 2, 94, 79, 34, 96, 88, 93, 41, 44, 56, 5], [58, 82, 15, 14, 33, 88, 18, 3, 36, 36, 42, 62, 85, 19, 57], [13, 37, 74, 30, 4, 78, 33, 18, 59, 21, 61, 81, 62, 56, 2], [41, 75, 65, 97, 92, 40, 45, 11, 40, 100, 27, 91, 44, 53, 66], [84, 83, 52, 66, 71, 3, 5, 18, 3, 35, 42, 63, 50, 41, 43], [26, 59, 84, 91, 44, 81, 81, 42, 63, 15, 64, 53, 40, 41, 89], [97, 46, 69, 71, 97, 67, 88, 10, 79, 87, 74, 52, 20, 34, 44], [36, 57, 67, 71, 100, 24, 13, 88, 21, 86, 14, 28, 60, 3, 79], [97, 51, 41, 19, 40, 73, 24, 76, 60, 27, 11, 83, 70, 98, 12], [49, 33, 52, 48, 96, 88, 10, 31, 4, 7, 38, 5, 94, 49, 23], [100, 21, 85, 83, 30, 51, 91, 23, 19, 48, 95, 47, 23, 22, 78]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 2, 1, 0, 6, 4, 5, 8, 9, 11, 14, 7, 10, 13, 12], [6, 1, 4, 3, 5, 0, 2, 8, 7, 9, 10, 13, 12, 11, 14], [6, 4, 1, 0, 5, 2, 3, 10, 7, 11, 9, 14, 8, 13, 12], [0, 1, 3, 4, 2, 6, 5, 10, 13, 9, 12, 8, 7, 11, 14], [6, 2, 5, 0, 4, 1, 3, 14, 8, 11, 10, 13, 12, 9, 7], [4, 6, 5, 3, 0, 1, 2, 8, 12, 7, 9, 13, 14, 11, 10], [4, 1, 5, 6, 3, 0, 2, 7, 9, 8, 14, 11, 13, 12, 10], [0, 1, 5, 3, 2, 6, 4, 8, 12, 10, 13, 11, 7, 14, 9], [0, 6, 3, 2, 4, 5, 1, 14, 9, 12, 8, 11, 7, 13, 10], [5, 1, 0, 2, 6, 4, 3, 9, 10, 12, 14, 8, 7, 13, 11], [2, 5, 6, 3, 1, 0, 4, 13, 10, 9, 14, 12, 7, 11, 8], [3, 6, 0, 4, 2, 1, 5, 14, 13, 9, 10, 11, 7, 8, 12], [5, 1, 6, 0, 3, 2, 4, 7, 12, 8, 9, 11, 14, 13, 10], [1, 2, 0, 3, 5, 6, 4, 13, 10, 11, 12, 14, 8, 9, 7], [4, 0, 1, 6, 2, 5, 3, 13, 7, 11, 8, 14, 9, 10, 12], [1, 0, 5, 4, 3, 6, 2, 14, 12, 11, 13, 10, 8, 7, 9], [3, 6, 4, 2, 1, 5, 0, 7, 14, 8, 9, 12, 11, 10, 13], [0, 6, 2, 4, 1, 5, 3, 9, 12, 13, 10, 11, 7, 8, 14], [5, 3, 1, 4, 6, 0, 2, 10, 13, 7, 12, 14, 9, 11, 8], [2, 0, 5, 6, 1, 3, 4, 12, 9, 8, 11, 10, 7, 14, 13]]

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
