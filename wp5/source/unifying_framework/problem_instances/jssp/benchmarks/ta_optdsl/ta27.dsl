# Job Shop Scheduling instance: ta27
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 21091

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[38, 51, 81, 2, 21, 44, 99, 86, 7, 65, 81, 70, 88, 43, 94, 72, 37, 61, 38, 99], [89, 17, 13, 44, 70, 73, 65, 80, 32, 45, 83, 71, 55, 91, 84, 7, 90, 66, 28, 50], [71, 96, 64, 99, 88, 10, 44, 7, 27, 33, 34, 90, 44, 59, 30, 94, 98, 43, 99, 37], [4, 84, 34, 9, 63, 60, 97, 52, 35, 97, 79, 91, 4, 3, 3, 66, 54, 5, 9, 39], [24, 78, 61, 52, 59, 51, 2, 92, 81, 74, 96, 21, 72, 4, 49, 3, 51, 54, 49, 24], [27, 78, 82, 80, 10, 96, 10, 38, 91, 42, 56, 77, 88, 47, 73, 69, 26, 16, 92, 3], [77, 4, 80, 38, 86, 83, 54, 19, 67, 99, 30, 77, 31, 69, 31, 74, 96, 50, 68, 87], [22, 77, 40, 38, 83, 16, 2, 55, 87, 62, 69, 30, 10, 58, 80, 25, 47, 98, 3, 19], [5, 52, 17, 29, 62, 98, 25, 93, 25, 37, 26, 69, 63, 23, 58, 70, 90, 92, 28, 41], [65, 78, 95, 17, 71, 53, 14, 73, 58, 66, 97, 79, 97, 12, 4, 68, 58, 34, 69, 41], [28, 35, 4, 80, 83, 50, 34, 90, 5, 12, 27, 81, 37, 63, 20, 41, 23, 17, 36, 86], [30, 19, 88, 19, 85, 75, 47, 29, 59, 75, 43, 58, 90, 76, 6, 95, 9, 10, 92, 94], [36, 52, 4, 73, 23, 87, 50, 76, 14, 32, 28, 26, 87, 74, 22, 47, 13, 35, 64, 61], [43, 12, 60, 61, 95, 80, 51, 59, 68, 37, 95, 67, 66, 98, 92, 38, 22, 45, 60, 41], [19, 96, 26, 30, 59, 25, 57, 11, 69, 45, 57, 40, 82, 52, 85, 11, 32, 91, 19, 58], [1, 81, 77, 26, 54, 83, 61, 41, 48, 27, 23, 63, 82, 2, 25, 32, 45, 95, 56, 99], [42, 47, 90, 2, 96, 68, 46, 35, 23, 60, 66, 9, 89, 68, 28, 96, 46, 86, 9, 75], [14, 59, 79, 52, 9, 73, 64, 25, 73, 33, 44, 90, 80, 55, 10, 41, 79, 31, 30, 18], [52, 92, 57, 92, 88, 56, 74, 47, 13, 91, 59, 76, 81, 72, 93, 25, 85, 67, 35, 36], [3, 59, 75, 30, 91, 15, 13, 34, 28, 17, 87, 31, 85, 53, 19, 81, 89, 67, 11, 66]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 13, 17, 6, 8, 11, 4, 3, 12, 18, 9, 2, 0, 1, 10, 16, 15, 14, 5, 19], [7, 17, 16, 10, 0, 15, 12, 1, 2, 9, 18, 5, 3, 6, 19, 14, 4, 11, 8, 13], [11, 17, 19, 0, 2, 4, 8, 14, 10, 3, 5, 12, 18, 15, 1, 16, 6, 7, 9, 13], [2, 7, 17, 12, 1, 16, 13, 6, 19, 3, 18, 11, 5, 0, 4, 14, 8, 10, 15, 9], [3, 5, 12, 0, 10, 17, 16, 2, 7, 8, 9, 18, 19, 4, 13, 11, 1, 6, 15, 14], [9, 13, 6, 0, 7, 18, 12, 17, 19, 10, 3, 4, 16, 1, 15, 8, 2, 11, 14, 5], [7, 3, 5, 17, 14, 19, 8, 9, 13, 11, 1, 12, 16, 0, 2, 18, 15, 4, 10, 6], [15, 16, 12, 5, 4, 9, 18, 3, 8, 19, 17, 6, 13, 11, 0, 7, 14, 10, 1, 2], [2, 5, 6, 19, 4, 18, 1, 0, 8, 9, 7, 12, 13, 14, 17, 15, 16, 3, 10, 11], [19, 0, 17, 14, 7, 11, 8, 6, 12, 4, 10, 2, 16, 13, 3, 9, 1, 15, 18, 5], [10, 4, 14, 9, 19, 6, 18, 0, 13, 12, 16, 5, 7, 8, 17, 3, 1, 2, 15, 11], [4, 18, 12, 15, 3, 8, 19, 9, 5, 6, 16, 14, 10, 0, 2, 1, 17, 13, 11, 7], [4, 5, 6, 7, 11, 10, 0, 17, 2, 9, 14, 13, 1, 16, 8, 19, 15, 12, 3, 18], [5, 0, 17, 14, 8, 12, 2, 9, 18, 6, 19, 3, 13, 7, 4, 15, 11, 1, 10, 16], [10, 1, 15, 5, 8, 4, 9, 13, 14, 2, 17, 6, 3, 16, 19, 11, 7, 18, 0, 12], [1, 5, 2, 16, 11, 17, 14, 8, 9, 18, 4, 12, 15, 19, 7, 0, 13, 6, 10, 3], [1, 18, 2, 14, 5, 8, 10, 6, 19, 4, 13, 9, 16, 7, 11, 12, 15, 0, 3, 17], [11, 3, 14, 7, 1, 13, 18, 9, 19, 12, 8, 15, 4, 6, 16, 17, 2, 10, 0, 5], [10, 2, 17, 7, 8, 18, 13, 6, 5, 16, 0, 15, 1, 3, 12, 11, 9, 14, 19, 4], [8, 16, 0, 2, 11, 10, 19, 17, 7, 14, 3, 4, 13, 15, 6, 5, 1, 9, 12, 18]]

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
