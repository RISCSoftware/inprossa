# Job Shop Scheduling instance: ta37
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 23807

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[81, 6, 87, 97, 96, 49, 47, 82, 94, 40, 57, 68, 47, 75, 91], [42, 67, 78, 41, 79, 21, 62, 36, 8, 55, 43, 39, 61, 91, 82], [52, 37, 50, 48, 96, 28, 54, 2, 25, 68, 72, 68, 95, 7, 98], [93, 86, 87, 46, 61, 59, 81, 30, 71, 10, 71, 10, 24, 94, 43], [13, 79, 22, 71, 36, 57, 30, 46, 30, 58, 65, 88, 70, 71, 78], [95, 56, 15, 40, 43, 68, 31, 57, 73, 32, 60, 98, 34, 32, 66], [30, 22, 21, 16, 57, 33, 93, 24, 12, 27, 42, 19, 64, 58, 67], [77, 38, 26, 49, 95, 84, 61, 43, 87, 51, 58, 53, 49, 62, 65], [92, 82, 55, 81, 54, 13, 57, 87, 97, 89, 93, 48, 70, 68, 59], [23, 96, 53, 33, 78, 78, 72, 94, 28, 47, 66, 60, 87, 28, 36], [69, 4, 89, 88, 15, 98, 53, 82, 34, 27, 64, 63, 5, 69, 29], [68, 50, 74, 5, 89, 2, 59, 86, 93, 76, 19, 15, 79, 97, 87], [62, 60, 31, 89, 52, 95, 55, 39, 51, 62, 11, 67, 13, 29, 47], [29, 5, 62, 79, 92, 85, 14, 61, 52, 52, 51, 76, 63, 85, 20], [93, 73, 57, 88, 91, 51, 61, 41, 45, 46, 23, 97, 28, 45, 66], [50, 33, 41, 59, 58, 59, 59, 32, 49, 14, 67, 53, 14, 30, 57], [43, 99, 7, 98, 23, 97, 52, 94, 58, 80, 8, 52, 51, 18, 66], [30, 2, 95, 70, 99, 18, 97, 14, 57, 72, 12, 2, 72, 97, 33], [89, 55, 71, 24, 14, 79, 89, 63, 32, 14, 75, 10, 64, 42, 70], [76, 24, 44, 82, 15, 82, 98, 97, 25, 1, 75, 22, 27, 16, 27], [36, 76, 6, 4, 72, 78, 47, 26, 51, 29, 91, 27, 93, 18, 84], [35, 39, 89, 90, 13, 7, 53, 73, 89, 12, 70, 9, 16, 49, 85], [84, 56, 77, 40, 7, 47, 51, 93, 65, 87, 54, 36, 6, 41, 66], [14, 74, 43, 3, 42, 45, 56, 67, 78, 57, 29, 1, 65, 45, 13], [99, 39, 81, 72, 52, 47, 2, 8, 73, 69, 29, 25, 74, 6, 5], [86, 36, 93, 99, 64, 68, 91, 17, 43, 97, 21, 94, 61, 82, 22], [52, 42, 18, 97, 60, 7, 75, 98, 62, 20, 37, 46, 28, 98, 47], [55, 3, 30, 5, 7, 90, 31, 11, 86, 27, 9, 85, 81, 6, 15], [53, 12, 35, 1, 62, 93, 19, 23, 40, 65, 65, 4, 73, 53, 87], [50, 92, 5, 40, 96, 81, 22, 68, 34, 43, 66, 53, 13, 70, 13]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 12, 9, 11, 5, 14, 10, 0, 2, 1, 7, 6, 3, 8, 13], [0, 9, 14, 12, 1, 4, 11, 10, 6, 3, 2, 7, 8, 5, 13], [0, 5, 3, 8, 7, 14, 12, 13, 9, 4, 10, 2, 11, 6, 1], [6, 5, 3, 4, 14, 8, 12, 10, 7, 2, 1, 9, 11, 0, 13], [8, 13, 10, 0, 6, 2, 7, 12, 11, 14, 1, 5, 3, 9, 4], [5, 9, 13, 2, 11, 0, 7, 14, 4, 6, 12, 10, 8, 1, 3], [9, 10, 7, 8, 1, 4, 6, 13, 14, 12, 0, 3, 2, 11, 5], [7, 9, 11, 13, 10, 1, 5, 14, 8, 2, 4, 6, 0, 12, 3], [10, 3, 2, 14, 12, 13, 8, 6, 11, 0, 1, 9, 7, 5, 4], [11, 3, 10, 1, 0, 14, 13, 2, 5, 4, 7, 6, 9, 8, 12], [5, 2, 9, 8, 3, 4, 10, 12, 1, 11, 13, 7, 14, 6, 0], [13, 14, 1, 0, 9, 2, 4, 11, 3, 5, 12, 6, 8, 10, 7], [1, 14, 12, 9, 5, 11, 3, 10, 13, 4, 0, 2, 8, 6, 7], [11, 4, 13, 14, 7, 6, 2, 9, 1, 12, 0, 5, 3, 8, 10], [6, 13, 0, 5, 11, 9, 3, 12, 2, 8, 10, 4, 14, 1, 7], [8, 4, 7, 13, 6, 14, 9, 1, 12, 5, 2, 3, 0, 10, 11], [7, 11, 2, 12, 10, 1, 5, 14, 3, 8, 6, 0, 9, 4, 13], [6, 8, 9, 13, 10, 3, 14, 12, 7, 1, 4, 0, 5, 2, 11], [12, 10, 7, 4, 1, 11, 0, 6, 3, 8, 14, 5, 2, 13, 9], [9, 5, 12, 11, 2, 7, 0, 13, 14, 1, 6, 8, 3, 10, 4], [7, 3, 13, 8, 6, 11, 2, 14, 4, 9, 10, 1, 5, 0, 12], [0, 1, 2, 6, 14, 5, 3, 12, 10, 13, 7, 4, 9, 8, 11], [1, 3, 6, 5, 2, 8, 0, 7, 10, 14, 12, 11, 9, 13, 4], [6, 11, 9, 13, 3, 0, 1, 10, 12, 2, 14, 4, 7, 5, 8], [2, 3, 0, 4, 9, 1, 12, 5, 10, 8, 13, 14, 6, 7, 11], [7, 4, 9, 11, 3, 5, 1, 10, 14, 12, 8, 2, 13, 6, 0], [9, 12, 7, 5, 2, 10, 4, 14, 8, 6, 1, 0, 3, 11, 13], [10, 14, 11, 0, 4, 13, 1, 9, 7, 6, 5, 12, 3, 8, 2], [13, 14, 5, 4, 6, 1, 0, 12, 11, 3, 10, 2, 9, 7, 8], [14, 6, 8, 2, 7, 5, 11, 10, 4, 0, 3, 13, 1, 12, 9]]

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
