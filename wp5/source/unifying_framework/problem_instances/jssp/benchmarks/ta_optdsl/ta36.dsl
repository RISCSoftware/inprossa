# Job Shop Scheduling instance: ta36
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 22959

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[88, 3, 96, 63, 97, 73, 16, 3, 91, 75, 33, 63, 66, 86, 88], [36, 94, 4, 21, 83, 79, 7, 90, 50, 26, 83, 33, 87, 15, 38], [96, 2, 88, 23, 24, 65, 94, 86, 37, 11, 93, 81, 5, 45, 94], [61, 92, 88, 4, 10, 38, 62, 1, 37, 21, 42, 54, 61, 9, 24], [27, 16, 48, 87, 46, 37, 74, 86, 84, 28, 76, 69, 52, 76, 91], [99, 53, 53, 46, 60, 17, 27, 84, 78, 33, 88, 35, 88, 13, 75], [52, 72, 72, 99, 98, 52, 48, 17, 85, 24, 79, 25, 99, 4, 85], [6, 80, 25, 17, 44, 73, 32, 18, 73, 60, 67, 4, 77, 46, 67], [16, 75, 2, 41, 54, 47, 15, 2, 88, 57, 51, 29, 16, 10, 26], [65, 44, 1, 88, 40, 17, 11, 50, 10, 20, 50, 40, 81, 36, 27], [42, 73, 30, 62, 80, 60, 36, 6, 42, 40, 55, 97, 67, 25, 11], [8, 43, 3, 86, 3, 29, 67, 4, 12, 55, 97, 74, 16, 89, 59], [31, 23, 25, 22, 72, 42, 3, 83, 91, 87, 38, 88, 78, 39, 14], [69, 74, 20, 7, 43, 42, 61, 7, 74, 51, 82, 43, 5, 59, 83], [49, 61, 65, 20, 45, 75, 92, 28, 48, 14, 39, 28, 71, 25, 9], [87, 57, 94, 84, 33, 12, 42, 22, 61, 47, 58, 35, 33, 12, 47], [52, 70, 72, 35, 67, 42, 42, 86, 96, 3, 71, 94, 44, 96, 73], [27, 63, 70, 66, 57, 17, 30, 95, 95, 6, 70, 33, 99, 48, 64], [93, 88, 80, 92, 93, 33, 15, 44, 39, 14, 65, 86, 65, 86, 22], [50, 36, 14, 17, 11, 42, 91, 16, 34, 71, 2, 78, 55, 29, 47], [58, 6, 35, 97, 10, 76, 24, 40, 17, 49, 61, 13, 72, 67, 93], [45, 43, 4, 56, 83, 39, 86, 11, 30, 16, 52, 80, 89, 60, 59], [20, 49, 82, 63, 73, 44, 5, 68, 40, 17, 3, 92, 49, 66, 37], [80, 67, 67, 57, 85, 80, 60, 1, 34, 43, 93, 81, 98, 69, 73], [42, 27, 76, 50, 33, 20, 82, 97, 55, 87, 15, 42, 96, 93, 82], [79, 90, 8, 54, 69, 19, 68, 24, 82, 93, 47, 73, 44, 47, 97], [50, 89, 40, 73, 2, 40, 11, 52, 19, 98, 14, 44, 57, 38, 96], [52, 84, 44, 94, 78, 18, 28, 5, 28, 64, 17, 9, 37, 68, 45], [25, 57, 19, 54, 71, 57, 22, 68, 15, 83, 23, 88, 62, 69, 63], [99, 96, 11, 54, 67, 10, 28, 18, 16, 97, 50, 50, 8, 47, 79]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 13, 9, 1, 4, 0, 14, 12, 6, 11, 5, 7, 3, 8, 10], [3, 11, 14, 1, 5, 0, 8, 10, 2, 4, 6, 9, 12, 13, 7], [2, 8, 6, 5, 4, 7, 0, 14, 11, 1, 10, 12, 3, 13, 9], [6, 0, 8, 7, 4, 9, 2, 14, 12, 10, 11, 1, 3, 5, 13], [12, 3, 5, 0, 10, 11, 13, 6, 7, 4, 8, 2, 1, 14, 9], [11, 1, 3, 0, 5, 8, 7, 10, 4, 2, 6, 9, 12, 14, 13], [10, 1, 11, 5, 9, 4, 13, 3, 7, 0, 8, 6, 14, 12, 2], [12, 1, 4, 5, 13, 9, 2, 14, 7, 3, 11, 8, 6, 10, 0], [10, 14, 11, 9, 4, 0, 3, 2, 6, 8, 5, 13, 7, 1, 12], [14, 2, 3, 1, 5, 9, 10, 4, 11, 0, 8, 7, 6, 13, 12], [7, 6, 12, 1, 2, 11, 3, 14, 4, 13, 5, 0, 8, 9, 10], [14, 3, 13, 0, 7, 12, 6, 1, 11, 10, 2, 8, 9, 4, 5], [3, 11, 13, 8, 2, 1, 10, 14, 4, 9, 12, 5, 6, 0, 7], [8, 0, 13, 1, 6, 14, 10, 4, 5, 11, 2, 9, 7, 12, 3], [5, 12, 4, 6, 14, 8, 3, 7, 13, 9, 1, 10, 2, 11, 0], [2, 5, 12, 11, 1, 4, 7, 14, 0, 9, 8, 6, 3, 13, 10], [10, 3, 1, 4, 7, 5, 2, 0, 14, 12, 8, 6, 13, 9, 11], [2, 6, 13, 4, 3, 8, 7, 5, 14, 10, 9, 12, 1, 11, 0], [2, 0, 6, 11, 5, 12, 7, 14, 13, 4, 3, 1, 10, 8, 9], [6, 5, 2, 3, 0, 7, 10, 1, 14, 4, 8, 13, 9, 11, 12], [5, 13, 2, 14, 11, 0, 6, 4, 1, 9, 7, 10, 12, 3, 8], [12, 6, 0, 14, 9, 10, 5, 4, 7, 3, 8, 13, 11, 1, 2], [1, 5, 10, 4, 12, 3, 0, 7, 8, 14, 9, 13, 11, 2, 6], [13, 3, 8, 2, 14, 6, 10, 7, 9, 1, 4, 0, 5, 11, 12], [8, 1, 3, 12, 0, 2, 4, 6, 14, 9, 13, 11, 5, 7, 10], [2, 0, 7, 5, 11, 8, 13, 1, 14, 9, 4, 10, 6, 12, 3], [7, 6, 9, 11, 10, 13, 12, 0, 5, 1, 4, 3, 8, 2, 14], [7, 0, 14, 10, 3, 2, 11, 5, 12, 1, 6, 4, 8, 13, 9], [10, 14, 5, 1, 6, 4, 13, 8, 2, 11, 0, 9, 12, 3, 7], [13, 1, 2, 0, 6, 12, 10, 7, 9, 5, 3, 11, 4, 8, 14]]

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
