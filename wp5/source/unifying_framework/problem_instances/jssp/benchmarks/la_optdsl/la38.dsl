# Job Shop Scheduling instance: la38
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11217

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[72, 26, 38, 19, 30, 98, 74, 8, 43, 75, 23, 85, 67, 43, 13], [39, 19, 9, 73, 55, 26, 50, 61, 93, 80, 7, 57, 46, 72, 42], [91, 68, 72, 96, 99, 68, 60, 43, 11, 11, 43, 70, 34, 12, 7], [30, 74, 84, 40, 49, 69, 69, 9, 27, 72, 59, 45, 99, 60, 63], [75, 90, 91, 17, 8, 37, 71, 50, 65, 98, 72, 9, 91, 31, 98], [38, 49, 90, 62, 39, 72, 80, 63, 52, 25, 35, 35, 47, 21, 74], [5, 88, 68, 50, 53, 24, 20, 57, 52, 58, 24, 49, 18, 91, 19], [33, 38, 99, 9, 68, 35, 18, 77, 60, 15, 18, 90, 10, 60, 72], [80, 60, 40, 56, 51, 89, 91, 72, 86, 79, 95, 23, 92, 6, 23], [10, 46, 72, 40, 47, 34, 28, 24, 77, 29, 48, 77, 8, 55, 49], [7, 6, 20, 20, 89, 11, 38, 5, 52, 15, 22, 30, 79, 28, 9], [55, 8, 37, 22, 88, 73, 58, 93, 17, 85, 71, 69, 9, 25, 56], [20, 33, 49, 46, 30, 26, 37, 21, 64, 85, 77, 56, 99, 74, 58], [63, 42, 64, 24, 89, 15, 75, 52, 98, 38, 17, 60, 54, 92, 23], [97, 7, 43, 8, 57, 17, 7, 93, 29, 62, 88, 56, 87, 35, 26]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 12, 0, 6, 14, 8, 4, 3, 10, 11, 5, 13, 2, 7, 9], [14, 0, 4, 12, 1, 8, 9, 5, 10, 6, 11, 3, 2, 7, 13], [3, 4, 12, 6, 7, 14, 13, 8, 11, 10, 0, 1, 9, 5, 2], [14, 11, 4, 1, 8, 0, 9, 7, 12, 13, 5, 6, 2, 3, 10], [2, 0, 9, 3, 10, 13, 11, 14, 7, 5, 4, 8, 1, 12, 6], [11, 6, 4, 3, 14, 5, 10, 9, 1, 8, 7, 2, 13, 12, 0], [14, 7, 10, 13, 3, 0, 11, 12, 9, 5, 8, 1, 2, 6, 4], [7, 14, 5, 11, 4, 6, 3, 0, 8, 10, 12, 13, 1, 2, 9], [13, 8, 2, 9, 12, 11, 5, 10, 6, 7, 0, 1, 3, 4, 14], [1, 6, 5, 11, 4, 0, 14, 8, 10, 7, 12, 2, 13, 9, 3], [10, 4, 12, 0, 9, 1, 11, 6, 5, 8, 3, 7, 14, 2, 13], [5, 14, 2, 3, 13, 6, 1, 7, 4, 8, 12, 11, 10, 9, 0], [9, 14, 3, 8, 2, 6, 1, 4, 5, 0, 13, 10, 12, 11, 7], [10, 3, 4, 5, 11, 1, 8, 2, 13, 0, 7, 12, 6, 14, 9], [3, 5, 11, 7, 14, 9, 6, 10, 0, 1, 2, 8, 13, 12, 4]]

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
