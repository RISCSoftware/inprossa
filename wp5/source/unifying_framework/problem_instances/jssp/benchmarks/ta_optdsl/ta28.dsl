# Job Shop Scheduling instance: ta28
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20202

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[69, 58, 32, 20, 95, 14, 99, 8, 89, 42, 26, 35, 87, 25, 30, 51, 83, 24, 59, 48], [97, 73, 47, 29, 44, 91, 32, 38, 31, 7, 34, 37, 74, 8, 13, 25, 79, 1, 5, 6], [78, 1, 44, 29, 90, 33, 79, 31, 44, 92, 73, 79, 83, 67, 35, 21, 68, 27, 82, 37], [74, 5, 14, 5, 76, 77, 84, 11, 58, 63, 50, 20, 8, 13, 20, 34, 56, 32, 85, 1], [9, 72, 51, 26, 24, 13, 91, 45, 79, 96, 12, 40, 78, 31, 38, 83, 72, 71, 5, 91], [98, 82, 61, 65, 51, 83, 5, 28, 8, 82, 9, 35, 93, 77, 82, 66, 56, 22, 83, 83], [75, 37, 93, 98, 53, 68, 91, 11, 21, 15, 68, 57, 10, 83, 78, 35, 15, 38, 88, 56], [32, 98, 33, 79, 45, 34, 78, 72, 19, 59, 77, 3, 88, 78, 2, 19, 67, 26, 97, 28], [26, 67, 95, 59, 85, 80, 9, 99, 32, 95, 28, 68, 44, 84, 70, 49, 17, 46, 70, 98], [58, 66, 60, 92, 51, 26, 96, 11, 51, 90, 58, 76, 62, 98, 6, 17, 94, 65, 27, 17], [9, 92, 27, 13, 6, 2, 66, 92, 37, 71, 63, 8, 21, 5, 50, 11, 78, 56, 80, 57], [42, 21, 55, 75, 94, 70, 25, 57, 6, 23, 13, 53, 17, 72, 16, 70, 69, 24, 34, 50], [75, 80, 93, 86, 76, 50, 94, 4, 35, 63, 87, 51, 82, 37, 71, 1, 49, 8, 44, 74], [98, 30, 19, 93, 94, 10, 35, 55, 32, 84, 40, 31, 60, 61, 71, 91, 61, 73, 85, 92], [13, 37, 41, 83, 33, 29, 19, 7, 30, 46, 8, 39, 5, 62, 68, 96, 17, 83, 73, 75], [42, 20, 2, 79, 87, 7, 58, 6, 49, 24, 67, 88, 19, 10, 37, 51, 83, 45, 55, 80], [59, 85, 88, 15, 26, 22, 68, 24, 89, 62, 2, 20, 33, 7, 14, 53, 66, 8, 58, 27], [73, 13, 41, 9, 72, 44, 88, 60, 24, 88, 15, 95, 77, 19, 76, 39, 91, 93, 71, 93], [62, 22, 52, 34, 77, 62, 85, 27, 59, 93, 82, 77, 36, 74, 28, 1, 52, 33, 34, 39], [5, 64, 38, 12, 90, 82, 15, 79, 18, 32, 37, 41, 37, 91, 81, 91, 73, 83, 1, 12]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[17, 7, 9, 12, 4, 5, 14, 8, 0, 2, 18, 3, 10, 11, 16, 13, 19, 15, 1, 6], [18, 10, 6, 3, 4, 16, 1, 14, 15, 13, 11, 19, 17, 8, 0, 9, 2, 5, 12, 7], [13, 16, 8, 7, 4, 3, 15, 19, 18, 17, 5, 1, 10, 14, 12, 11, 6, 9, 2, 0], [13, 18, 4, 6, 5, 14, 9, 19, 1, 3, 10, 7, 12, 2, 15, 11, 8, 17, 16, 0], [17, 10, 8, 12, 3, 14, 16, 15, 2, 0, 7, 5, 13, 19, 11, 18, 6, 4, 9, 1], [5, 0, 19, 17, 8, 7, 12, 6, 1, 3, 13, 16, 15, 2, 14, 10, 9, 11, 18, 4], [17, 14, 6, 8, 18, 2, 16, 12, 5, 0, 4, 15, 7, 10, 3, 19, 1, 11, 9, 13], [11, 1, 15, 16, 2, 13, 9, 14, 0, 6, 18, 10, 7, 5, 4, 17, 3, 19, 12, 8], [17, 10, 7, 2, 16, 13, 11, 0, 8, 4, 19, 3, 1, 12, 5, 18, 9, 14, 6, 15], [18, 15, 14, 12, 9, 19, 10, 16, 7, 17, 6, 11, 0, 2, 4, 8, 13, 5, 3, 1], [1, 0, 9, 6, 19, 17, 11, 18, 15, 16, 14, 8, 7, 13, 3, 10, 12, 4, 5, 2], [15, 2, 10, 19, 9, 3, 17, 16, 13, 11, 4, 6, 1, 7, 14, 12, 5, 18, 0, 8], [6, 1, 19, 14, 17, 11, 10, 3, 13, 2, 12, 15, 4, 16, 8, 18, 5, 0, 9, 7], [2, 10, 1, 19, 5, 12, 8, 14, 17, 13, 11, 4, 16, 18, 15, 0, 6, 7, 9, 3], [14, 0, 8, 3, 9, 10, 2, 17, 4, 6, 19, 1, 16, 5, 12, 13, 15, 7, 18, 11], [8, 12, 13, 10, 7, 0, 4, 16, 5, 15, 18, 3, 9, 2, 11, 19, 14, 6, 1, 17], [8, 12, 19, 11, 10, 4, 2, 7, 9, 6, 0, 15, 13, 1, 16, 14, 5, 3, 17, 18], [9, 6, 16, 4, 3, 2, 14, 8, 12, 7, 17, 15, 19, 18, 1, 0, 5, 10, 13, 11], [9, 18, 12, 10, 14, 16, 1, 17, 4, 7, 0, 8, 2, 15, 19, 6, 5, 3, 11, 13], [6, 2, 17, 9, 19, 11, 14, 7, 4, 3, 8, 12, 18, 15, 16, 0, 5, 1, 10, 13]]

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
