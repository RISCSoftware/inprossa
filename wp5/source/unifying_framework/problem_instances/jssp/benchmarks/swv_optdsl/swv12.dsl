# Job Shop Scheduling instance: swv12
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 25526

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[92, 93, 1, 48, 49, 6, 57, 52, 6, 16], [54, 86, 69, 25, 82, 31, 15, 6, 18, 5], [31, 26, 49, 46, 48, 47, 91, 82, 74, 93], [34, 82, 43, 25, 37, 55, 11, 34, 77, 71], [91, 97, 49, 54, 22, 98, 27, 46, 89, 2], [44, 3, 46, 70, 24, 94, 60, 22, 58, 65], [99, 80, 74, 53, 29, 98, 72, 54, 60, 69], [36, 87, 57, 96, 7, 94, 47, 70, 36, 26], [57, 59, 47, 5, 28, 44, 19, 35, 79, 24], [96, 4, 43, 60, 39, 2, 89, 97, 91, 81], [24, 75, 23, 98, 74, 10, 74, 44, 93, 57], [49, 90, 36, 36, 5, 74, 85, 53, 62, 4], [30, 47, 44, 75, 81, 31, 29, 42, 100, 81], [18, 2, 27, 88, 5, 36, 51, 30, 51, 31], [57, 21, 100, 100, 59, 98, 38, 21, 77, 84], [42, 70, 72, 99, 97, 59, 94, 13, 78, 90], [7, 70, 19, 16, 74, 50, 7, 88, 46, 74], [52, 12, 28, 45, 91, 45, 7, 15, 31, 22], [90, 8, 3, 56, 25, 31, 22, 51, 99, 65], [23, 49, 5, 28, 17, 62, 84, 40, 65, 30], [86, 41, 88, 12, 8, 94, 67, 80, 11, 77], [19, 10, 100, 42, 81, 23, 93, 36, 18, 71], [51, 9, 73, 63, 74, 81, 96, 7, 39, 22], [66, 1, 65, 44, 19, 77, 23, 10, 26, 76], [79, 54, 18, 22, 99, 2, 42, 90, 54, 28], [54, 28, 97, 16, 1, 71, 53, 26, 32, 28], [82, 50, 18, 5, 71, 41, 93, 62, 54, 89], [42, 74, 63, 59, 32, 50, 21, 29, 83, 64], [4, 6, 76, 44, 29, 29, 89, 95, 66, 81], [42, 36, 64, 55, 84, 81, 76, 4, 85, 16], [46, 69, 3, 41, 100, 41, 18, 94, 97, 30], [98, 58, 18, 34, 35, 53, 85, 86, 17, 78], [3, 99, 89, 92, 68, 10, 52, 30, 66, 69], [21, 76, 14, 65, 19, 24, 45, 73, 54, 84], [68, 96, 87, 92, 47, 90, 29, 39, 29, 100], [60, 61, 35, 72, 61, 77, 53, 1, 94, 57], [79, 71, 38, 85, 43, 87, 44, 51, 61, 37], [59, 100, 33, 94, 25, 88, 19, 66, 4, 50], [85, 80, 8, 1, 75, 30, 60, 17, 57, 32], [34, 94, 98, 49, 25, 72, 50, 80, 25, 37], [73, 53, 7, 51, 49, 55, 96, 19, 42, 41], [57, 86, 1, 66, 61, 56, 28, 68, 21, 65], [47, 100, 98, 4, 28, 32, 72, 34, 66, 55], [74, 39, 20, 63, 2, 88, 8, 22, 73, 3], [1, 43, 44, 52, 4, 61, 36, 38, 58, 75], [57, 74, 21, 32, 6, 72, 91, 94, 10, 34], [59, 45, 23, 53, 26, 55, 98, 34, 12, 43], [6, 53, 4, 95, 57, 86, 30, 92, 1, 20], [85, 98, 77, 65, 51, 30, 79, 23, 41, 17], [74, 64, 43, 14, 58, 80, 33, 37, 78, 42]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 4, 1, 3, 2, 7, 6, 9, 5, 8], [4, 3, 2, 1, 0, 6, 5, 9, 7, 8], [0, 1, 3, 2, 4, 8, 7, 5, 9, 6], [0, 4, 1, 3, 2, 6, 9, 5, 7, 8], [4, 0, 3, 2, 1, 9, 7, 5, 6, 8], [2, 3, 1, 0, 4, 9, 6, 5, 8, 7], [3, 0, 1, 2, 4, 6, 7, 5, 8, 9], [3, 1, 0, 2, 4, 8, 9, 5, 6, 7], [3, 2, 1, 0, 4, 9, 8, 6, 5, 7], [0, 1, 3, 2, 4, 7, 5, 9, 6, 8], [2, 4, 3, 0, 1, 9, 8, 6, 5, 7], [3, 4, 2, 0, 1, 8, 5, 9, 6, 7], [2, 1, 3, 4, 0, 7, 8, 9, 6, 5], [1, 0, 3, 2, 4, 5, 7, 6, 8, 9], [1, 0, 3, 2, 4, 8, 7, 5, 6, 9], [4, 2, 1, 3, 0, 6, 5, 9, 8, 7], [3, 2, 1, 0, 4, 6, 5, 9, 8, 7], [3, 4, 2, 0, 1, 5, 6, 7, 9, 8], [3, 2, 1, 4, 0, 8, 6, 9, 7, 5], [0, 3, 1, 2, 4, 7, 9, 5, 8, 6], [2, 0, 4, 1, 3, 6, 9, 5, 7, 8], [4, 3, 0, 2, 1, 5, 9, 8, 6, 7], [4, 2, 3, 1, 0, 8, 7, 6, 5, 9], [1, 3, 0, 4, 2, 7, 6, 8, 9, 5], [1, 2, 4, 0, 3, 5, 6, 8, 7, 9], [3, 4, 1, 0, 2, 5, 6, 8, 7, 9], [0, 3, 2, 4, 1, 5, 7, 9, 6, 8], [2, 3, 0, 1, 4, 5, 6, 7, 8, 9], [4, 2, 1, 3, 0, 9, 5, 7, 8, 6], [3, 4, 1, 0, 2, 5, 8, 6, 7, 9], [4, 0, 1, 3, 2, 6, 5, 7, 8, 9], [3, 4, 2, 1, 0, 9, 8, 5, 6, 7], [4, 2, 1, 0, 3, 5, 6, 7, 8, 9], [0, 3, 4, 2, 1, 9, 6, 5, 8, 7], [4, 0, 2, 3, 1, 6, 5, 8, 7, 9], [2, 0, 4, 1, 3, 9, 8, 5, 7, 6], [3, 2, 0, 4, 1, 6, 5, 8, 7, 9], [1, 2, 3, 0, 4, 5, 9, 6, 8, 7], [2, 0, 1, 4, 3, 7, 9, 6, 5, 8], [4, 2, 1, 3, 0, 9, 7, 6, 8, 5], [3, 4, 1, 2, 0, 6, 7, 9, 5, 8], [0, 1, 2, 4, 3, 6, 5, 7, 8, 9], [2, 1, 0, 4, 3, 7, 9, 5, 6, 8], [4, 0, 2, 1, 3, 5, 9, 7, 6, 8], [2, 0, 3, 1, 4, 6, 9, 8, 5, 7], [2, 4, 3, 1, 0, 5, 8, 9, 6, 7], [4, 0, 3, 1, 2, 5, 8, 7, 6, 9], [2, 1, 4, 3, 0, 6, 8, 7, 9, 5], [1, 2, 3, 4, 0, 7, 6, 5, 8, 9], [4, 2, 3, 0, 1, 7, 8, 6, 9, 5]]

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
