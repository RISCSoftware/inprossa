# Job Shop Scheduling instance: swv14
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 25017

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[37, 1, 65, 64, 69, 67, 79, 72, 43, 34], [7, 11, 52, 68, 43, 36, 29, 81, 12, 71], [14, 1, 1, 29, 90, 13, 97, 41, 38, 21], [26, 46, 36, 20, 83, 56, 42, 65, 23, 4], [39, 62, 92, 53, 46, 46, 87, 65, 74, 68], [75, 44, 67, 43, 13, 95, 5, 28, 85, 94], [65, 1, 99, 86, 36, 17, 15, 71, 32, 61], [59, 33, 18, 15, 63, 63, 85, 95, 34, 3], [82, 26, 25, 23, 13, 41, 24, 22, 16, 35], [21, 7, 73, 1, 39, 29, 32, 77, 89, 21], [16, 53, 64, 27, 55, 78, 20, 20, 60, 32], [20, 71, 54, 21, 23, 99, 94, 61, 71, 40], [75, 7, 76, 91, 72, 63, 53, 71, 32, 53], [64, 3, 12, 30, 35, 94, 79, 31, 67, 14], [89, 28, 52, 87, 63, 37, 44, 92, 2, 21], [79, 65, 17, 78, 35, 54, 23, 57, 90, 91], [76, 93, 23, 20, 61, 10, 77, 20, 34, 87], [37, 92, 17, 59, 30, 47, 13, 45, 7, 60], [46, 2, 36, 74, 90, 83, 9, 88, 90, 39], [85, 94, 20, 83, 88, 16, 14, 62, 9, 53], [4, 60, 64, 79, 16, 37, 49, 67, 5, 95], [86, 5, 77, 32, 66, 68, 4, 15, 1, 40], [2, 48, 58, 25, 23, 27, 85, 14, 21, 55], [81, 71, 56, 99, 92, 43, 66, 79, 47, 42], [71, 77, 19, 72, 85, 34, 62, 9, 58, 14], [3, 76, 61, 98, 38, 14, 44, 43, 26, 56], [62, 68, 93, 22, 54, 77, 57, 79, 45, 19], [68, 96, 62, 24, 56, 41, 19, 2, 73, 50], [53, 89, 86, 3, 37, 59, 19, 100, 35, 23], [21, 85, 78, 90, 94, 94, 90, 56, 28, 92], [8, 86, 97, 27, 85, 68, 57, 5, 96, 26], [58, 79, 1, 4, 49, 16, 44, 13, 10, 87], [24, 41, 59, 85, 23, 58, 52, 77, 20, 75], [47, 89, 68, 17, 88, 92, 48, 47, 84, 100], [1, 30, 73, 61, 20, 43, 74, 41, 78, 52], [11, 18, 67, 66, 58, 62, 71, 88, 42, 49], [11, 20, 51, 67, 5, 1, 42, 37, 25, 57], [58, 21, 9, 68, 83, 19, 28, 32, 66, 77], [65, 80, 58, 85, 50, 43, 18, 79, 29, 9], [11, 23, 29, 74, 34, 77, 83, 84, 57, 82], [97, 21, 6, 66, 67, 17, 12, 96, 90, 46], [100, 5, 13, 12, 34, 75, 91, 59, 63, 89], [33, 30, 66, 70, 16, 58, 80, 86, 8, 66], [46, 77, 1, 55, 19, 37, 59, 85, 69, 32], [16, 48, 3, 51, 8, 94, 19, 72, 58, 59], [18, 92, 19, 30, 23, 50, 57, 64, 27, 32], [72, 6, 18, 67, 92, 51, 32, 55, 100, 14], [87, 96, 58, 83, 48, 26, 86, 77, 77, 72], [50, 80, 85, 65, 5, 47, 33, 88, 50, 75], [96, 78, 99, 5, 80, 38, 44, 29, 69, 58]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 0, 3, 1, 2, 9, 5, 8, 7, 6], [1, 0, 3, 4, 2, 6, 9, 7, 8, 5], [4, 3, 1, 2, 0, 8, 5, 9, 7, 6], [1, 0, 4, 2, 3, 9, 8, 7, 5, 6], [4, 0, 2, 3, 1, 9, 7, 8, 6, 5], [4, 1, 3, 2, 0, 6, 9, 5, 7, 8], [1, 2, 4, 3, 0, 8, 5, 7, 6, 9], [2, 4, 3, 0, 1, 7, 5, 6, 8, 9], [4, 2, 0, 3, 1, 7, 9, 8, 6, 5], [3, 1, 0, 2, 4, 6, 7, 5, 8, 9], [1, 3, 4, 0, 2, 5, 9, 8, 7, 6], [1, 2, 3, 0, 4, 9, 5, 7, 6, 8], [2, 4, 3, 0, 1, 6, 8, 7, 5, 9], [2, 1, 4, 0, 3, 5, 8, 7, 6, 9], [4, 1, 3, 0, 2, 8, 9, 7, 6, 5], [0, 1, 4, 3, 2, 8, 5, 9, 7, 6], [3, 1, 4, 0, 2, 5, 8, 7, 9, 6], [0, 2, 1, 4, 3, 5, 8, 7, 6, 9], [4, 3, 0, 2, 1, 6, 5, 8, 7, 9], [3, 0, 2, 4, 1, 6, 5, 7, 9, 8], [0, 4, 2, 1, 3, 5, 6, 7, 9, 8], [3, 0, 1, 4, 2, 7, 5, 9, 8, 6], [0, 1, 4, 3, 2, 9, 7, 8, 6, 5], [1, 4, 3, 2, 0, 7, 6, 9, 8, 5], [1, 4, 3, 2, 0, 5, 7, 9, 6, 8], [4, 0, 2, 3, 1, 5, 9, 8, 7, 6], [1, 4, 0, 2, 3, 6, 7, 9, 5, 8], [2, 1, 4, 0, 3, 5, 6, 7, 8, 9], [2, 0, 3, 1, 4, 7, 5, 9, 6, 8], [3, 4, 0, 2, 1, 5, 6, 8, 9, 7], [4, 2, 0, 3, 1, 9, 7, 8, 5, 6], [0, 3, 4, 2, 1, 8, 6, 9, 5, 7], [3, 0, 4, 1, 2, 8, 6, 5, 9, 7], [0, 1, 2, 4, 3, 6, 8, 9, 5, 7], [1, 0, 3, 4, 2, 8, 7, 9, 5, 6], [0, 4, 3, 2, 1, 8, 7, 9, 5, 6], [4, 2, 3, 1, 0, 7, 6, 8, 9, 5], [0, 4, 2, 3, 1, 6, 9, 5, 7, 8], [3, 2, 0, 1, 4, 7, 5, 8, 9, 6], [3, 2, 0, 1, 4, 7, 8, 5, 6, 9], [2, 4, 0, 3, 1, 8, 9, 6, 5, 7], [4, 1, 2, 0, 3, 8, 7, 5, 6, 9], [1, 2, 0, 3, 4, 6, 5, 8, 7, 9], [3, 0, 2, 1, 4, 7, 9, 6, 5, 8], [2, 0, 1, 4, 3, 7, 6, 8, 9, 5], [3, 4, 1, 0, 2, 9, 6, 5, 7, 8], [2, 0, 4, 1, 3, 8, 6, 9, 5, 7], [4, 0, 1, 2, 3, 8, 5, 7, 9, 6], [1, 4, 0, 3, 2, 7, 5, 6, 8, 9], [1, 0, 4, 3, 2, 9, 5, 7, 8, 6]]

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
