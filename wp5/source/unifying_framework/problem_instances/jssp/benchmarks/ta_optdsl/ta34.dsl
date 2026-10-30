# Job Shop Scheduling instance: ta34
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 23443

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[11, 54, 64, 32, 87, 56, 22, 7, 95, 55, 33, 14, 34, 12, 5], [55, 71, 31, 9, 99, 48, 33, 57, 33, 1, 56, 11, 96, 46, 52], [38, 90, 57, 88, 36, 8, 48, 68, 80, 19, 7, 25, 41, 31, 31], [29, 63, 1, 27, 7, 24, 22, 87, 35, 87, 49, 55, 18, 98, 55], [75, 67, 58, 8, 95, 55, 80, 5, 31, 17, 53, 87, 36, 33, 31], [81, 85, 16, 72, 76, 78, 25, 78, 75, 27, 14, 22, 37, 71, 86], [15, 43, 7, 90, 49, 98, 90, 81, 75, 54, 10, 88, 24, 10, 4], [36, 37, 91, 31, 98, 1, 96, 85, 81, 43, 9, 65, 35, 96, 92], [21, 53, 25, 94, 72, 94, 68, 98, 45, 6, 63, 35, 40, 37, 87], [84, 13, 71, 23, 31, 65, 89, 76, 88, 35, 26, 98, 55, 59, 35], [99, 59, 2, 45, 45, 44, 42, 60, 91, 76, 53, 77, 58, 34, 63], [35, 85, 47, 76, 95, 82, 30, 94, 63, 6, 56, 47, 90, 36, 60], [94, 48, 71, 2, 19, 33, 69, 3, 27, 58, 64, 86, 17, 28, 81], [38, 68, 7, 55, 3, 95, 47, 40, 47, 97, 44, 11, 24, 93, 36], [25, 60, 33, 55, 79, 57, 38, 76, 5, 65, 79, 5, 96, 31, 78], [50, 75, 70, 77, 29, 5, 80, 25, 91, 50, 71, 38, 84, 76, 31], [63, 41, 76, 85, 50, 96, 40, 73, 58, 11, 27, 54, 84, 64, 74], [75, 54, 93, 59, 8, 53, 3, 16, 22, 4, 89, 6, 10, 29, 66], [58, 2, 18, 55, 59, 76, 7, 17, 70, 26, 66, 84, 99, 5, 45], [11, 84, 54, 66, 34, 57, 92, 51, 50, 34, 60, 59, 58, 42, 18], [77, 29, 91, 61, 37, 31, 29, 49, 85, 67, 46, 18, 42, 18, 46], [63, 59, 66, 42, 83, 75, 4, 76, 62, 2, 20, 67, 80, 95, 71], [7, 83, 46, 84, 79, 36, 6, 94, 82, 90, 60, 94, 37, 76, 46], [47, 99, 66, 51, 28, 22, 19, 70, 91, 87, 8, 68, 60, 66, 11], [68, 39, 2, 5, 11, 12, 86, 78, 17, 79, 86, 88, 75, 91, 86], [21, 18, 88, 49, 66, 31, 57, 95, 57, 11, 91, 31, 45, 90, 36], [60, 90, 96, 31, 5, 56, 49, 18, 97, 45, 45, 2, 4, 57, 9], [29, 65, 78, 19, 67, 84, 38, 75, 61, 41, 96, 95, 85, 77, 65], [52, 82, 64, 32, 66, 93, 78, 39, 62, 26, 21, 47, 65, 27, 45], [68, 22, 83, 31, 57, 36, 41, 48, 52, 32, 82, 98, 39, 92, 85]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 0, 12, 5, 11, 10, 8, 2, 13, 6, 4, 3, 1, 14, 9], [7, 11, 6, 10, 3, 1, 4, 2, 14, 8, 12, 13, 9, 5, 0], [1, 2, 8, 5, 4, 10, 12, 14, 13, 6, 7, 9, 11, 0, 3], [7, 5, 2, 10, 1, 3, 13, 6, 8, 12, 4, 14, 11, 9, 0], [13, 12, 0, 9, 3, 5, 10, 14, 4, 8, 1, 6, 11, 7, 2], [8, 6, 4, 3, 5, 11, 0, 12, 9, 1, 13, 2, 14, 7, 10], [3, 9, 5, 13, 8, 14, 12, 10, 2, 0, 1, 6, 7, 4, 11], [6, 8, 14, 3, 10, 11, 12, 4, 7, 1, 9, 13, 2, 5, 0], [12, 8, 3, 0, 14, 6, 11, 10, 13, 1, 7, 5, 9, 2, 4], [14, 12, 10, 11, 3, 5, 8, 2, 9, 13, 0, 4, 7, 1, 6], [11, 13, 7, 9, 12, 14, 2, 5, 8, 6, 10, 3, 4, 1, 0], [9, 10, 11, 4, 13, 8, 1, 2, 14, 0, 5, 12, 6, 3, 7], [9, 3, 6, 4, 10, 8, 12, 5, 1, 14, 11, 13, 0, 2, 7], [13, 7, 5, 14, 0, 6, 12, 9, 11, 3, 2, 1, 4, 10, 8], [10, 2, 9, 5, 3, 14, 13, 1, 4, 0, 7, 12, 11, 8, 6], [1, 4, 3, 9, 14, 0, 5, 7, 2, 11, 8, 10, 12, 6, 13], [13, 3, 5, 9, 7, 1, 4, 10, 6, 11, 0, 14, 12, 2, 8], [14, 0, 1, 9, 7, 11, 10, 13, 6, 12, 2, 5, 4, 3, 8], [7, 5, 11, 14, 8, 13, 3, 6, 9, 4, 1, 2, 10, 0, 12], [5, 1, 8, 2, 6, 9, 12, 7, 4, 10, 13, 3, 14, 0, 11], [8, 5, 1, 11, 10, 6, 7, 4, 12, 13, 0, 9, 3, 14, 2], [9, 2, 5, 4, 0, 8, 14, 10, 3, 1, 6, 11, 13, 7, 12], [14, 1, 0, 12, 10, 13, 6, 3, 8, 11, 5, 4, 2, 9, 7], [10, 12, 1, 7, 5, 8, 11, 9, 14, 3, 2, 6, 4, 0, 13], [13, 2, 1, 5, 4, 8, 14, 0, 11, 10, 7, 12, 6, 3, 9], [1, 13, 10, 0, 12, 11, 4, 3, 7, 9, 8, 5, 14, 6, 2], [5, 7, 10, 14, 12, 11, 2, 0, 9, 13, 4, 6, 1, 3, 8], [11, 10, 9, 7, 8, 1, 3, 6, 2, 12, 0, 14, 13, 4, 5], [2, 8, 0, 10, 1, 13, 5, 12, 3, 11, 4, 7, 14, 6, 9], [1, 8, 5, 3, 6, 13, 11, 0, 4, 9, 10, 12, 2, 7, 14]]

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
