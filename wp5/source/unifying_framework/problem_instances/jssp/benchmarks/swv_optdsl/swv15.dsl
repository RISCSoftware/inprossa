# Job Shop Scheduling instance: swv15
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 24989

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 77, 93, 77, 40, 16, 51, 92, 11, 74], [92, 76, 70, 59, 80, 86, 78, 30, 93, 17], [53, 44, 92, 96, 77, 84, 14, 49, 59, 10], [73, 60, 19, 76, 85, 68, 78, 13, 93, 50], [24, 2, 20, 41, 4, 16, 39, 79, 81, 44], [15, 32, 35, 41, 18, 19, 29, 14, 98, 26], [45, 59, 98, 44, 53, 84, 23, 45, 39, 89], [51, 30, 84, 25, 51, 45, 60, 89, 25, 97], [47, 58, 40, 18, 62, 36, 15, 93, 77, 90], [41, 68, 20, 33, 72, 22, 69, 47, 22, 47], [35, 100, 28, 26, 20, 24, 42, 100, 32, 41], [65, 40, 12, 93, 53, 60, 89, 23, 18, 53], [58, 60, 50, 31, 97, 64, 85, 38, 35, 85], [58, 49, 45, 64, 9, 99, 22, 7, 49, 15], [10, 77, 37, 72, 85, 70, 83, 45, 57, 8], [87, 87, 18, 4, 93, 67, 17, 35, 78, 20], [56, 45, 15, 57, 72, 40, 41, 81, 32, 85], [36, 5, 32, 63, 79, 21, 25, 86, 35, 91], [9, 38, 83, 73, 29, 18, 41, 50, 29, 99], [100, 64, 60, 29, 63, 26, 35, 22, 71, 9], [60, 81, 68, 62, 48, 69, 79, 28, 92, 10], [40, 41, 10, 68, 80, 25, 82, 33, 28, 51], [35, 70, 12, 17, 30, 37, 94, 18, 93, 29], [78, 36, 41, 27, 36, 25, 88, 64, 66, 92], [32, 40, 65, 27, 74, 88, 92, 83, 73, 42], [48, 85, 92, 61, 95, 58, 89, 11, 72, 76], [70, 42, 50, 84, 24, 100, 70, 4, 68, 55], [95, 85, 11, 98, 41, 64, 8, 26, 6, 6], [84, 17, 49, 69, 55, 28, 45, 59, 75, 38], [29, 64, 48, 41, 1, 23, 56, 64, 12, 31], [22, 50, 81, 33, 25, 74, 83, 85, 33, 56], [21, 62, 20, 8, 25, 91, 36, 49, 90, 9], [16, 43, 91, 96, 24, 11, 66, 41, 35, 91], [42, 91, 20, 87, 44, 38, 15, 89, 42, 57], [33, 80, 22, 95, 68, 22, 69, 53, 13, 70], [15, 24, 31, 47, 41, 52, 39, 59, 14, 28], [42, 57, 95, 67, 5, 9, 30, 20, 70, 21], [15, 20, 54, 64, 83, 89, 91, 6, 48, 40], [22, 77, 16, 25, 27, 19, 75, 4, 72, 61], [83, 82, 16, 68, 2, 41, 66, 10, 88, 21], [76, 64, 85, 71, 97, 97, 40, 8, 70, 35], [94, 45, 94, 44, 84, 30, 19, 47, 41, 22], [82, 10, 23, 93, 90, 22, 87, 9, 67, 18], [75, 57, 27, 9, 97, 50, 23, 31, 62, 14], [75, 42, 35, 41, 18, 56, 38, 38, 51, 65], [33, 63, 27, 41, 72, 52, 14, 42, 71, 10], [44, 89, 91, 26, 91, 22, 49, 5, 31, 69], [4, 34, 16, 42, 34, 67, 86, 25, 99, 25], [26, 93, 9, 81, 34, 76, 10, 96, 79, 68], [32, 47, 98, 19, 13, 34, 52, 12, 49, 45]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 4, 0, 3, 1, 5, 9, 8, 6, 7], [0, 4, 1, 3, 2, 5, 9, 6, 7, 8], [1, 2, 3, 4, 0, 9, 7, 5, 8, 6], [1, 2, 3, 0, 4, 7, 8, 5, 9, 6], [2, 0, 3, 1, 4, 9, 7, 8, 5, 6], [3, 2, 1, 4, 0, 8, 6, 5, 7, 9], [1, 0, 4, 3, 2, 5, 6, 7, 8, 9], [1, 4, 3, 0, 2, 6, 5, 7, 8, 9], [0, 3, 2, 4, 1, 5, 7, 8, 9, 6], [3, 1, 0, 4, 2, 6, 7, 5, 9, 8], [2, 1, 4, 0, 3, 5, 9, 6, 7, 8], [0, 2, 4, 3, 1, 8, 7, 5, 6, 9], [0, 1, 4, 3, 2, 9, 5, 7, 6, 8], [3, 0, 1, 2, 4, 8, 6, 5, 9, 7], [0, 4, 3, 2, 1, 5, 7, 9, 6, 8], [4, 0, 1, 2, 3, 8, 5, 9, 6, 7], [4, 0, 3, 2, 1, 6, 5, 9, 8, 7], [0, 3, 4, 2, 1, 6, 7, 9, 5, 8], [2, 4, 0, 1, 3, 7, 9, 5, 8, 6], [0, 3, 2, 4, 1, 8, 6, 5, 9, 7], [1, 0, 3, 4, 2, 7, 5, 8, 6, 9], [0, 4, 1, 2, 3, 8, 9, 7, 6, 5], [4, 2, 0, 3, 1, 9, 7, 8, 6, 5], [1, 2, 3, 4, 0, 7, 6, 5, 9, 8], [2, 3, 4, 0, 1, 5, 8, 6, 7, 9], [0, 1, 2, 4, 3, 8, 9, 5, 7, 6], [3, 2, 0, 4, 1, 9, 5, 6, 7, 8], [0, 4, 2, 3, 1, 5, 6, 7, 8, 9], [0, 2, 1, 3, 4, 8, 6, 9, 7, 5], [2, 0, 4, 1, 3, 5, 7, 9, 6, 8], [2, 4, 3, 0, 1, 5, 9, 8, 7, 6], [1, 4, 0, 2, 3, 6, 9, 5, 8, 7], [1, 0, 2, 3, 4, 5, 9, 7, 8, 6], [1, 2, 4, 0, 3, 9, 6, 5, 8, 7], [0, 3, 4, 2, 1, 7, 8, 9, 5, 6], [0, 3, 1, 2, 4, 8, 9, 7, 5, 6], [2, 0, 4, 1, 3, 6, 9, 8, 5, 7], [2, 0, 1, 3, 4, 9, 7, 5, 6, 8], [0, 4, 1, 3, 2, 8, 9, 6, 7, 5], [3, 1, 2, 0, 4, 7, 8, 5, 9, 6], [1, 0, 2, 3, 4, 5, 7, 6, 8, 9], [0, 1, 2, 4, 3, 8, 5, 7, 6, 9], [2, 1, 0, 3, 4, 8, 7, 9, 5, 6], [0, 2, 4, 3, 1, 9, 5, 7, 8, 6], [1, 3, 2, 0, 4, 9, 7, 6, 8, 5], [4, 1, 0, 2, 3, 5, 7, 9, 6, 8], [2, 1, 0, 4, 3, 6, 5, 8, 9, 7], [3, 1, 0, 4, 2, 6, 7, 8, 5, 9], [4, 1, 0, 3, 2, 7, 8, 9, 5, 6], [3, 1, 4, 2, 0, 7, 9, 6, 8, 5]]

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
