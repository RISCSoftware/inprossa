# Job Shop Scheduling instance: ta32
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 23206

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[31, 9, 88, 73, 29, 82, 53, 98, 99, 92, 42, 15, 16, 79, 49], [48, 63, 73, 89, 91, 41, 42, 76, 53, 99, 44, 13, 15, 54, 37], [30, 89, 7, 40, 68, 2, 94, 73, 73, 14, 25, 44, 49, 3, 52], [10, 13, 7, 34, 29, 62, 47, 62, 40, 86, 80, 57, 87, 49, 28], [23, 34, 45, 91, 91, 12, 90, 39, 48, 87, 41, 90, 71, 98, 54], [69, 89, 33, 54, 57, 63, 68, 53, 12, 9, 72, 30, 72, 61, 36], [67, 1, 62, 64, 78, 65, 75, 2, 40, 37, 26, 56, 34, 65, 14], [65, 89, 37, 41, 25, 67, 8, 22, 74, 56, 94, 73, 76, 84, 98], [13, 77, 62, 60, 39, 52, 41, 40, 87, 47, 44, 65, 11, 86, 33], [74, 20, 43, 49, 63, 31, 88, 6, 41, 80, 73, 11, 50, 30, 77], [69, 69, 12, 85, 74, 7, 33, 84, 97, 36, 2, 53, 19, 52, 52], [74, 82, 51, 75, 81, 64, 37, 70, 48, 84, 55, 7, 33, 8, 33], [97, 30, 84, 6, 99, 20, 68, 70, 14, 79, 41, 54, 71, 28, 51], [56, 86, 55, 36, 91, 10, 98, 77, 90, 69, 72, 27, 78, 14, 30], [47, 69, 93, 97, 71, 13, 65, 44, 10, 92, 71, 46, 26, 18, 31], [49, 47, 14, 5, 77, 47, 81, 5, 91, 84, 62, 58, 55, 5, 5], [2, 57, 67, 47, 25, 61, 9, 67, 94, 38, 66, 96, 79, 46, 74], [58, 50, 30, 93, 81, 70, 85, 47, 52, 74, 43, 75, 42, 62, 58], [42, 14, 85, 63, 20, 5, 65, 36, 41, 49, 40, 70, 42, 28, 6], [72, 85, 1, 30, 98, 7, 31, 91, 21, 33, 36, 54, 61, 79, 32], [7, 51, 64, 49, 37, 1, 20, 21, 12, 44, 79, 43, 62, 16, 82], [68, 69, 71, 6, 87, 84, 89, 74, 56, 72, 83, 19, 75, 25, 94], [62, 19, 66, 48, 22, 21, 3, 15, 29, 53, 1, 7, 27, 92, 92], [34, 75, 32, 50, 11, 72, 14, 37, 35, 12, 93, 83, 46, 6, 33], [81, 48, 87, 58, 16, 56, 9, 63, 75, 80, 41, 71, 55, 70, 92], [27, 29, 51, 81, 33, 47, 86, 18, 66, 67, 53, 73, 30, 75, 55], [89, 75, 60, 18, 53, 72, 68, 92, 91, 85, 82, 35, 5, 61, 17], [67, 40, 19, 96, 54, 32, 77, 59, 27, 20, 84, 87, 46, 7, 82], [79, 99, 89, 51, 65, 26, 23, 91, 27, 69, 59, 51, 52, 51, 70], [83, 68, 4, 31, 27, 30, 57, 30, 5, 27, 16, 62, 32, 39, 13]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[13, 0, 10, 2, 12, 8, 5, 6, 4, 14, 1, 11, 9, 3, 7], [7, 3, 0, 12, 13, 14, 8, 1, 10, 4, 11, 2, 6, 9, 5], [12, 14, 10, 1, 13, 5, 3, 11, 6, 2, 4, 7, 8, 0, 9], [14, 13, 1, 12, 7, 0, 4, 5, 3, 2, 6, 8, 11, 10, 9], [7, 5, 1, 3, 8, 12, 2, 13, 0, 4, 6, 10, 11, 14, 9], [11, 5, 4, 14, 10, 3, 0, 9, 7, 12, 6, 2, 13, 8, 1], [5, 8, 12, 9, 3, 2, 14, 4, 1, 13, 7, 0, 11, 6, 10], [7, 14, 5, 9, 3, 1, 4, 10, 12, 2, 6, 13, 11, 0, 8], [10, 14, 6, 5, 13, 12, 3, 8, 0, 7, 2, 9, 4, 11, 1], [6, 5, 4, 3, 12, 14, 7, 9, 1, 13, 11, 8, 2, 0, 10], [5, 1, 0, 11, 13, 6, 12, 7, 2, 9, 3, 4, 10, 8, 14], [12, 13, 0, 3, 2, 5, 10, 11, 4, 1, 7, 14, 9, 6, 8], [11, 0, 9, 12, 7, 2, 13, 8, 5, 4, 3, 1, 14, 6, 10], [5, 8, 13, 10, 14, 7, 9, 0, 12, 2, 6, 4, 11, 3, 1], [9, 3, 10, 5, 2, 6, 7, 11, 4, 1, 12, 13, 14, 8, 0], [1, 7, 2, 5, 6, 9, 10, 8, 14, 11, 4, 12, 0, 3, 13], [13, 11, 5, 2, 0, 6, 8, 9, 10, 4, 7, 1, 12, 14, 3], [9, 8, 1, 10, 3, 2, 6, 11, 0, 7, 5, 12, 13, 14, 4], [5, 12, 3, 0, 13, 10, 7, 9, 6, 14, 1, 4, 2, 8, 11], [5, 10, 11, 7, 4, 6, 9, 0, 8, 12, 2, 3, 1, 13, 14], [10, 14, 3, 1, 11, 13, 9, 12, 6, 8, 0, 5, 2, 7, 4], [14, 12, 8, 13, 6, 9, 5, 2, 7, 10, 3, 1, 4, 11, 0], [11, 8, 7, 6, 0, 9, 13, 10, 12, 5, 2, 14, 1, 4, 3], [1, 9, 12, 7, 5, 8, 13, 2, 3, 14, 6, 0, 10, 11, 4], [2, 5, 13, 0, 9, 3, 8, 1, 12, 14, 6, 4, 10, 11, 7], [1, 8, 7, 14, 10, 3, 5, 6, 4, 12, 13, 11, 0, 2, 9], [2, 14, 3, 13, 10, 5, 12, 7, 1, 8, 0, 11, 4, 6, 9], [14, 4, 3, 2, 9, 0, 8, 6, 7, 11, 1, 13, 12, 5, 10], [9, 12, 5, 4, 2, 3, 0, 13, 8, 7, 6, 10, 1, 11, 14], [11, 6, 7, 8, 5, 14, 13, 3, 10, 1, 12, 0, 2, 9, 4]]

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
