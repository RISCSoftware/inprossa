# Job Shop Scheduling instance: swv13
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 25860

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[72, 39, 79, 65, 68, 82, 82, 33, 66, 55], [18, 27, 14, 45, 72, 50, 90, 57, 19, 19], [64, 77, 19, 18, 25, 11, 97, 65, 27, 81], [29, 39, 31, 70, 62, 91, 91, 98, 12, 2], [29, 27, 90, 38, 51, 64, 67, 86, 95, 60], [55, 76, 97, 69, 90, 57, 24, 94, 65, 80], [90, 23, 41, 24, 13, 81, 94, 8, 69, 76], [16, 37, 68, 19, 4, 33, 45, 30, 79, 4], [76, 19, 36, 97, 71, 84, 97, 43, 64, 87], [71, 77, 20, 73, 47, 100, 77, 88, 69, 16], [8, 40, 61, 55, 96, 89, 59, 29, 46, 71], [18, 59, 21, 37, 97, 80, 2, 79, 85, 59], [95, 83, 1, 48, 19, 56, 81, 59, 57, 37], [8, 60, 27, 85, 91, 31, 62, 94, 12, 39], [17, 38, 96, 10, 2, 76, 21, 46, 64, 81], [11, 4, 46, 41, 25, 96, 10, 25, 32, 56], [21, 77, 72, 53, 22, 2, 83, 23, 52, 28], [2, 15, 74, 9, 37, 83, 90, 51, 26, 80], [57, 7, 4, 6, 56, 57, 94, 11, 12, 29], [96, 40, 93, 65, 66, 93, 94, 32, 85, 5], [73, 38, 19, 7, 22, 63, 23, 84, 28, 11], [29, 96, 94, 59, 10, 26, 37, 22, 52, 50], [8, 38, 76, 31, 8, 95, 50, 62, 5, 25], [15, 66, 84, 76, 100, 95, 56, 56, 94, 85], [42, 84, 38, 73, 37, 16, 60, 24, 23, 59], [80, 79, 44, 43, 65, 81, 55, 7, 93, 34], [12, 60, 8, 55, 2, 83, 6, 91, 31, 91], [8, 47, 57, 47, 46, 51, 54, 98, 74, 55], [35, 41, 56, 62, 90, 15, 73, 4, 66, 89], [2, 68, 54, 44, 39, 90, 53, 7, 76, 29], [94, 23, 34, 1, 45, 49, 67, 84, 83, 49], [19, 19, 70, 92, 4, 70, 48, 33, 82, 50], [70, 91, 76, 83, 64, 3, 92, 98, 37, 75], [20, 17, 28, 96, 13, 87, 54, 21, 98, 65], [68, 38, 90, 98, 40, 9, 47, 45, 21, 3], [58, 32, 16, 74, 19, 58, 93, 1, 80, 32], [32, 95, 99, 2, 8, 6, 32, 68, 26, 55], [97, 56, 19, 7, 45, 59, 20, 22, 98, 72], [28, 23, 97, 43, 98, 3, 71, 58, 75, 43], [88, 82, 88, 31, 65, 53, 60, 68, 99, 15], [100, 11, 95, 28, 4, 80, 25, 25, 9, 87], [75, 60, 80, 10, 59, 75, 33, 31, 87, 10], [54, 72, 49, 6, 7, 69, 32, 72, 64, 86], [84, 18, 96, 19, 15, 58, 38, 62, 64, 71], [50, 32, 83, 83, 80, 81, 55, 82, 10, 33], [65, 18, 64, 84, 95, 87, 70, 74, 68, 27], [96, 50, 49, 1, 89, 88, 64, 3, 42, 91], [91, 5, 100, 44, 77, 13, 20, 25, 71, 71], [86, 19, 69, 71, 91, 13, 98, 13, 87, 43], [60, 8, 93, 31, 8, 85, 8, 19, 24, 1]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 1, 2, 0, 3, 5, 7, 6, 8, 9], [2, 3, 0, 4, 1, 7, 6, 8, 9, 5], [4, 1, 0, 3, 2, 8, 6, 9, 7, 5], [3, 0, 2, 1, 4, 8, 9, 5, 7, 6], [2, 4, 3, 1, 0, 6, 8, 9, 7, 5], [4, 0, 3, 1, 2, 7, 5, 8, 9, 6], [1, 4, 0, 3, 2, 8, 7, 5, 6, 9], [3, 1, 0, 4, 2, 6, 8, 9, 7, 5], [2, 0, 3, 4, 1, 9, 6, 8, 5, 7], [2, 1, 0, 3, 4, 7, 5, 9, 8, 6], [3, 4, 0, 2, 1, 8, 7, 9, 5, 6], [2, 0, 3, 4, 1, 7, 6, 5, 8, 9], [4, 1, 2, 0, 3, 9, 7, 5, 8, 6], [0, 1, 4, 3, 2, 9, 5, 6, 7, 8], [4, 3, 0, 1, 2, 6, 9, 8, 5, 7], [2, 1, 4, 3, 0, 5, 9, 6, 7, 8], [0, 1, 4, 2, 3, 9, 7, 5, 8, 6], [3, 4, 0, 2, 1, 8, 5, 6, 7, 9], [3, 1, 0, 2, 4, 7, 5, 8, 6, 9], [1, 2, 3, 4, 0, 9, 7, 8, 5, 6], [1, 2, 4, 0, 3, 5, 8, 6, 9, 7], [1, 4, 0, 3, 2, 5, 7, 8, 6, 9], [1, 3, 2, 0, 4, 6, 5, 8, 9, 7], [0, 2, 4, 3, 1, 7, 5, 8, 6, 9], [3, 2, 1, 0, 4, 5, 7, 9, 6, 8], [3, 1, 0, 2, 4, 5, 7, 8, 6, 9], [2, 4, 0, 3, 1, 9, 6, 5, 8, 7], [0, 4, 3, 2, 1, 9, 8, 7, 6, 5], [2, 4, 1, 0, 3, 7, 5, 9, 6, 8], [0, 4, 3, 1, 2, 7, 8, 9, 5, 6], [2, 0, 3, 1, 4, 8, 7, 5, 6, 9], [4, 2, 1, 0, 3, 5, 7, 9, 8, 6], [4, 2, 0, 3, 1, 7, 8, 5, 9, 6], [3, 1, 0, 4, 2, 7, 9, 5, 6, 8], [0, 4, 3, 2, 1, 7, 8, 5, 9, 6], [0, 4, 2, 3, 1, 9, 5, 6, 7, 8], [0, 2, 1, 3, 4, 9, 6, 8, 5, 7], [3, 4, 2, 0, 1, 7, 9, 8, 5, 6], [2, 4, 3, 0, 1, 5, 8, 9, 7, 6], [3, 0, 2, 1, 4, 5, 9, 7, 6, 8], [4, 0, 2, 1, 3, 5, 7, 9, 6, 8], [0, 3, 4, 2, 1, 5, 8, 6, 9, 7], [0, 3, 4, 1, 2, 7, 8, 6, 9, 5], [4, 3, 1, 0, 2, 9, 8, 6, 5, 7], [1, 4, 2, 3, 0, 5, 7, 9, 8, 6], [0, 4, 3, 2, 1, 9, 6, 7, 5, 8], [1, 2, 0, 3, 4, 8, 5, 9, 6, 7], [3, 0, 1, 2, 4, 6, 5, 7, 9, 8], [0, 4, 1, 2, 3, 5, 8, 6, 9, 7], [4, 0, 3, 2, 1, 9, 7, 6, 5, 8]]

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
