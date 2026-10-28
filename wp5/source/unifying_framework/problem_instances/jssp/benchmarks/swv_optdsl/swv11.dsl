# Job Shop Scheduling instance: swv11
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 25399

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[92, 49, 91, 56, 47, 39, 1, 12, 37, 63], [86, 75, 100, 92, 90, 11, 38, 85, 54, 100], [92, 4, 40, 44, 94, 68, 40, 27, 53, 5], [48, 59, 92, 35, 87, 91, 99, 46, 83, 27], [83, 78, 44, 64, 76, 63, 31, 98, 12, 91], [15, 100, 24, 49, 18, 26, 92, 29, 24, 65], [28, 85, 47, 53, 84, 34, 35, 100, 90, 88], [13, 34, 61, 54, 71, 97, 97, 27, 2, 47], [85, 33, 75, 49, 72, 12, 87, 23, 90, 42], [75, 65, 24, 20, 33, 29, 84, 74, 44, 47], [23, 66, 48, 27, 1, 63, 35, 46, 44, 29], [4, 69, 79, 46, 61, 34, 50, 10, 88, 19], [16, 25, 3, 77, 31, 22, 79, 97, 88, 49], [39, 40, 93, 48, 15, 51, 63, 91, 46, 74], [93, 5, 8, 50, 48, 88, 48, 46, 97, 35], [32, 8, 65, 70, 84, 72, 43, 10, 9, 60], [21, 26, 28, 91, 58, 39, 43, 93, 64, 90], [51, 50, 60, 93, 90, 89, 12, 20, 27, 33], [53, 21, 47, 3, 34, 68, 71, 1, 8, 67], [48, 11, 36, 57, 26, 30, 57, 25, 92, 44], [20, 20, 48, 74, 6, 80, 10, 27, 15, 77], [86, 40, 23, 71, 29, 28, 100, 99, 56, 77], [61, 86, 99, 27, 83, 60, 26, 31, 40, 84], [33, 94, 60, 46, 68, 86, 70, 46, 89, 63], [38, 13, 91, 27, 33, 87, 23, 31, 82, 27], [24, 38, 12, 30, 58, 59, 37, 36, 2, 37], [75, 47, 62, 39, 5, 31, 77, 60, 61, 65], [21, 53, 3, 74, 100, 28, 6, 91, 34, 80], [3, 8, 88, 54, 18, 54, 34, 42, 59, 4], [83, 23, 17, 33, 72, 70, 24, 78, 60, 96], [97, 99, 36, 70, 63, 41, 71, 97, 73, 92], [30, 37, 28, 55, 24, 9, 51, 17, 38, 77], [46, 99, 14, 15, 18, 10, 41, 47, 80, 48], [29, 63, 51, 78, 89, 14, 32, 70, 84, 7], [23, 69, 92, 15, 26, 47, 95, 56, 42, 83], [10, 38, 44, 47, 23, 70, 21, 65, 56, 63], [35, 29, 66, 42, 85, 90, 75, 85, 25, 46], [46, 48, 96, 99, 74, 52, 13, 88, 4, 30], [8, 15, 25, 80, 47, 5, 93, 70, 23, 61], [90, 86, 51, 66, 5, 59, 97, 85, 9, 28], [59, 50, 93, 23, 40, 14, 34, 61, 63, 96], [21, 62, 72, 15, 30, 77, 13, 2, 22, 22], [2, 4, 20, 85, 14, 48, 62, 90, 90, 33], [49, 89, 64, 49, 46, 83, 13, 66, 6, 72], [25, 55, 73, 16, 74, 26, 22, 19, 63, 38], [15, 8, 96, 13, 97, 66, 95, 2, 57, 46], [22, 97, 90, 39, 73, 98, 65, 85, 31, 64], [38, 77, 67, 43, 11, 7, 69, 61, 97, 95], [35, 5, 68, 46, 4, 58, 44, 51, 98, 69], [2, 81, 68, 4, 59, 69, 14, 21, 69, 53]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 4, 3, 2, 1, 5, 9, 7, 6, 8], [0, 2, 1, 3, 4, 5, 7, 8, 9, 6], [1, 4, 3, 2, 0, 8, 6, 9, 5, 7], [4, 0, 1, 2, 3, 6, 7, 9, 8, 5], [0, 1, 4, 3, 2, 8, 9, 6, 7, 5], [3, 0, 1, 4, 2, 6, 9, 5, 7, 8], [0, 3, 4, 2, 1, 7, 5, 6, 8, 9], [2, 4, 3, 1, 0, 9, 8, 6, 7, 5], [0, 2, 1, 4, 3, 7, 5, 8, 6, 9], [2, 3, 1, 4, 0, 9, 6, 8, 7, 5], [2, 3, 4, 0, 1, 6, 7, 9, 5, 8], [2, 0, 4, 3, 1, 7, 8, 9, 6, 5], [0, 4, 3, 2, 1, 8, 7, 9, 6, 5], [1, 0, 4, 2, 3, 6, 9, 8, 7, 5], [4, 0, 2, 3, 1, 6, 7, 9, 5, 8], [3, 1, 2, 0, 4, 8, 6, 7, 5, 9], [0, 2, 1, 3, 4, 9, 6, 8, 5, 7], [1, 2, 0, 4, 3, 7, 9, 8, 6, 5], [1, 3, 2, 4, 0, 9, 8, 5, 7, 6], [3, 4, 2, 0, 1, 9, 7, 5, 8, 6], [1, 0, 4, 3, 2, 9, 8, 5, 7, 6], [3, 1, 0, 2, 4, 7, 8, 6, 9, 5], [4, 0, 3, 1, 2, 7, 5, 8, 9, 6], [4, 1, 3, 2, 0, 7, 5, 9, 6, 8], [4, 1, 2, 3, 0, 8, 7, 6, 9, 5], [4, 3, 0, 2, 1, 8, 9, 5, 6, 7], [2, 1, 4, 3, 0, 7, 9, 8, 6, 5], [4, 0, 1, 3, 2, 8, 6, 7, 9, 5], [1, 0, 2, 3, 4, 9, 6, 5, 8, 7], [3, 4, 0, 2, 1, 6, 8, 9, 7, 5], [4, 2, 3, 0, 1, 6, 9, 5, 8, 7], [2, 1, 4, 0, 3, 8, 5, 9, 7, 6], [3, 0, 2, 4, 1, 9, 6, 5, 7, 8], [4, 3, 2, 1, 0, 7, 9, 5, 8, 6], [4, 1, 2, 3, 0, 8, 6, 5, 9, 7], [1, 2, 3, 4, 0, 9, 7, 6, 5, 8], [3, 4, 1, 0, 2, 9, 8, 5, 7, 6], [3, 0, 4, 2, 1, 5, 6, 7, 8, 9], [1, 3, 4, 2, 0, 9, 7, 8, 6, 5], [0, 2, 3, 4, 1, 5, 6, 9, 7, 8], [0, 1, 4, 3, 2, 7, 9, 8, 6, 5], [1, 2, 4, 0, 3, 5, 6, 7, 8, 9], [2, 4, 3, 1, 0, 9, 7, 5, 8, 6], [0, 3, 4, 1, 2, 9, 8, 5, 6, 7], [4, 1, 2, 0, 3, 7, 9, 6, 5, 8], [3, 2, 1, 0, 4, 6, 7, 5, 8, 9], [4, 1, 3, 0, 2, 9, 6, 8, 5, 7], [3, 2, 0, 1, 4, 7, 5, 9, 8, 6], [0, 2, 1, 3, 4, 7, 6, 5, 9, 8], [2, 1, 0, 3, 4, 9, 8, 5, 6, 7]]

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
