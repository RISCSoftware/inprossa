# Job Shop Scheduling instance: swv19
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 25595

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[11, 27, 70, 89, 97, 66, 58, 74, 77, 17], [11, 50, 38, 60, 2, 10, 94, 35, 20, 52], [65, 51, 4, 19, 10, 2, 93, 17, 62, 91], [17, 85, 82, 3, 87, 13, 44, 16, 100, 81], [78, 25, 68, 68, 53, 2, 33, 35, 3, 18], [66, 5, 36, 24, 55, 34, 60, 11, 41, 43], [50, 24, 15, 23, 99, 2, 62, 19, 73, 52], [86, 36, 43, 27, 85, 99, 35, 53, 30, 21], [6, 18, 12, 81, 55, 31, 43, 79, 73, 99], [40, 15, 31, 7, 90, 43, 100, 96, 23, 25], [100, 83, 62, 48, 88, 61, 10, 42, 20, 19], [86, 93, 69, 58, 47, 58, 16, 41, 77, 35], [40, 51, 61, 43, 99, 9, 39, 46, 88, 37], [98, 91, 84, 48, 15, 98, 17, 91, 38, 23], [43, 83, 42, 26, 24, 58, 37, 38, 55, 27], [77, 90, 31, 22, 26, 21, 97, 57, 78, 82], [4, 64, 45, 90, 3, 52, 14, 18, 35, 44], [43, 68, 85, 67, 22, 44, 59, 93, 60, 38], [100, 45, 74, 26, 77, 77, 99, 98, 41, 14], [65, 80, 41, 13, 70, 64, 81, 42, 38, 57], [76, 78, 27, 10, 22, 55, 5, 71, 39, 36], [5, 60, 61, 63, 35, 85, 97, 70, 44, 81], [94, 41, 46, 40, 41, 20, 48, 99, 87, 38], [25, 76, 79, 78, 85, 13, 9, 30, 81, 93], [36, 98, 68, 34, 6, 78, 51, 48, 58, 59], [38, 47, 56, 8, 90, 37, 56, 97, 7, 37], [66, 39, 14, 24, 73, 89, 99, 3, 15, 54], [50, 74, 49, 12, 79, 55, 1, 98, 95, 37], [80, 54, 87, 99, 13, 99, 13, 61, 99, 79], [80, 51, 91, 32, 91, 84, 20, 58, 62, 21], [37, 11, 14, 39, 10, 34, 94, 2, 38, 12], [59, 86, 97, 40, 30, 55, 76, 9, 100, 86], [94, 49, 17, 33, 26, 17, 17, 42, 70, 24], [94, 20, 58, 51, 75, 82, 24, 70, 51, 93], [71, 9, 76, 59, 98, 62, 48, 53, 59, 79], [59, 32, 35, 36, 69, 89, 90, 51, 27, 28], [79, 3, 37, 10, 97, 10, 85, 80, 39, 86], [27, 16, 36, 69, 22, 69, 67, 60, 58, 31], [7, 92, 27, 2, 40, 16, 15, 43, 16, 60], [27, 79, 61, 86, 34, 29, 17, 99, 67, 56], [71, 90, 99, 64, 73, 27, 57, 100, 3, 17], [7, 63, 80, 65, 54, 23, 39, 59, 32, 77], [99, 64, 95, 10, 98, 1, 17, 56, 44, 80], [81, 21, 59, 60, 89, 25, 30, 74, 60, 19], [42, 67, 47, 2, 99, 34, 100, 11, 93, 15], [96, 41, 55, 61, 66, 93, 61, 87, 83, 35], [49, 19, 19, 70, 73, 25, 93, 29, 22, 62], [75, 28, 14, 40, 93, 97, 66, 41, 11, 62], [20, 13, 43, 90, 47, 4, 61, 76, 64, 50], [30, 68, 19, 38, 11, 37, 79, 57, 42, 64]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 1, 5, 3, 6, 0, 8, 9, 2, 4], [5, 0, 2, 3, 1, 7, 6, 9, 4, 8], [7, 0, 6, 8, 9, 5, 1, 2, 3, 4], [4, 3, 9, 0, 6, 2, 7, 5, 8, 1], [9, 6, 7, 0, 2, 3, 8, 5, 4, 1], [2, 8, 6, 9, 0, 5, 3, 7, 1, 4], [9, 4, 6, 0, 1, 8, 7, 3, 2, 5], [4, 9, 3, 7, 0, 1, 6, 5, 8, 2], [6, 5, 9, 2, 0, 7, 3, 1, 8, 4], [4, 6, 1, 0, 7, 9, 5, 8, 2, 3], [5, 4, 6, 3, 0, 2, 1, 8, 7, 9], [9, 7, 6, 3, 0, 2, 5, 1, 4, 8], [2, 0, 4, 1, 7, 6, 3, 9, 8, 5], [4, 8, 2, 5, 6, 1, 7, 9, 3, 0], [3, 2, 8, 4, 0, 1, 9, 7, 6, 5], [5, 8, 6, 0, 9, 4, 3, 1, 7, 2], [4, 9, 3, 1, 5, 8, 7, 2, 0, 6], [8, 6, 3, 2, 0, 7, 5, 4, 1, 9], [4, 8, 2, 6, 0, 1, 9, 3, 7, 5], [8, 9, 7, 5, 1, 6, 4, 3, 2, 0], [9, 4, 8, 0, 1, 2, 5, 3, 6, 7], [7, 9, 1, 5, 3, 6, 2, 8, 0, 4], [9, 0, 2, 5, 8, 1, 4, 3, 7, 6], [7, 6, 5, 2, 8, 0, 9, 4, 3, 1], [4, 8, 6, 7, 2, 3, 5, 9, 1, 0], [4, 6, 7, 9, 0, 1, 2, 3, 5, 8], [0, 8, 1, 5, 7, 9, 3, 2, 6, 4], [3, 9, 4, 8, 0, 1, 6, 5, 7, 2], [8, 9, 3, 2, 0, 4, 5, 6, 1, 7], [1, 9, 3, 6, 0, 7, 2, 5, 8, 4], [1, 8, 2, 9, 3, 5, 0, 6, 4, 7], [6, 9, 3, 4, 2, 0, 8, 7, 5, 1], [3, 1, 0, 2, 6, 8, 5, 7, 4, 9], [4, 1, 9, 2, 3, 0, 6, 7, 8, 5], [8, 1, 3, 5, 9, 7, 6, 4, 2, 0], [6, 2, 5, 0, 9, 7, 4, 3, 1, 8], [5, 6, 4, 1, 0, 9, 3, 7, 2, 8], [7, 0, 5, 8, 6, 2, 9, 3, 1, 4], [2, 5, 6, 4, 8, 1, 9, 7, 3, 0], [1, 7, 0, 9, 5, 6, 8, 4, 3, 2], [6, 7, 4, 9, 8, 3, 2, 0, 5, 1], [2, 5, 4, 6, 9, 3, 7, 0, 1, 8], [4, 6, 8, 5, 3, 7, 2, 9, 0, 1], [8, 7, 3, 6, 0, 5, 4, 9, 2, 1], [1, 0, 8, 2, 5, 7, 6, 9, 4, 3], [9, 3, 5, 8, 7, 4, 0, 2, 1, 6], [8, 5, 7, 3, 6, 1, 0, 9, 2, 4], [8, 4, 5, 1, 2, 0, 7, 3, 9, 6], [7, 6, 8, 3, 0, 2, 9, 1, 5, 4], [3, 4, 0, 5, 7, 9, 1, 8, 2, 6]]

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
