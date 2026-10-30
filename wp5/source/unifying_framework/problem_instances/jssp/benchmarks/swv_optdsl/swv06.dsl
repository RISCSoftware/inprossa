# Job Shop Scheduling instance: swv06
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15239

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[57, 16, 22, 9, 24, 53, 58, 41, 92, 44, 63, 93, 43, 26, 20], [86, 94, 89, 13, 41, 55, 54, 98, 14, 1, 63, 100, 90, 38, 80], [57, 26, 39, 32, 75, 9, 96, 9, 41, 75, 8, 30, 54, 57, 28], [24, 97, 36, 37, 74, 63, 71, 32, 24, 6, 61, 71, 45, 53, 19], [55, 21, 23, 57, 90, 84, 79, 55, 14, 41, 99, 8, 68, 4, 59], [78, 13, 81, 78, 10, 10, 48, 88, 51, 37, 93, 21, 75, 55, 11], [87, 37, 52, 54, 74, 26, 100, 55, 13, 50, 94, 68, 88, 88, 73], [62, 95, 72, 30, 47, 70, 7, 69, 89, 65, 18, 25, 81, 89, 64], [72, 10, 89, 59, 92, 53, 1, 48, 8, 26, 49, 97, 76, 69, 52], [39, 99, 47, 87, 45, 32, 85, 96, 98, 11, 56, 13, 71, 78, 95], [17, 96, 21, 87, 31, 41, 41, 64, 17, 97, 71, 95, 31, 29, 3], [87, 62, 95, 56, 34, 66, 9, 68, 86, 56, 82, 97, 82, 52, 42], [2, 37, 49, 86, 4, 63, 30, 76, 84, 39, 5, 63, 18, 13, 47], [29, 53, 63, 7, 26, 19, 34, 87, 42, 5, 98, 44, 22, 77, 11], [77, 91, 58, 51, 91, 14, 44, 55, 95, 17, 37, 54, 40, 1, 31], [43, 56, 7, 39, 47, 59, 39, 69, 47, 6, 43, 93, 32, 75, 93], [7, 30, 55, 97, 24, 8, 17, 70, 29, 14, 87, 51, 20, 29, 32], [96, 50, 29, 17, 99, 67, 91, 19, 36, 6, 91, 11, 14, 14, 83], [7, 23, 83, 31, 30, 76, 60, 89, 73, 24, 53, 17, 72, 9, 76], [89, 46, 2, 63, 1, 74, 86, 34, 72, 30, 58, 75, 19, 48, 47]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 6, 2, 4, 5, 3, 0, 10, 8, 12, 7, 13, 14, 9, 11], [2, 1, 0, 3, 6, 4, 5, 7, 13, 14, 9, 11, 12, 10, 8], [1, 6, 3, 4, 5, 0, 2, 12, 14, 10, 11, 13, 9, 7, 8], [3, 2, 5, 0, 6, 1, 4, 14, 12, 8, 11, 13, 10, 9, 7], [3, 0, 1, 5, 2, 6, 4, 11, 14, 10, 9, 12, 8, 13, 7], [4, 2, 1, 3, 0, 5, 6, 9, 11, 7, 12, 14, 13, 10, 8], [6, 2, 3, 1, 5, 4, 0, 8, 12, 10, 14, 7, 11, 9, 13], [4, 5, 6, 2, 0, 3, 1, 10, 9, 7, 13, 8, 14, 12, 11], [6, 1, 0, 3, 4, 5, 2, 14, 7, 8, 13, 10, 9, 12, 11], [6, 2, 4, 1, 0, 5, 3, 10, 8, 11, 7, 12, 14, 9, 13], [0, 2, 3, 6, 5, 4, 1, 8, 11, 13, 14, 10, 7, 9, 12], [6, 0, 4, 1, 3, 5, 2, 9, 14, 8, 7, 12, 10, 13, 11], [3, 1, 2, 0, 6, 5, 4, 14, 8, 10, 13, 9, 12, 7, 11], [0, 6, 1, 3, 5, 4, 2, 12, 10, 13, 14, 7, 9, 11, 8], [6, 4, 1, 2, 0, 3, 5, 13, 9, 7, 12, 8, 14, 11, 10], [5, 4, 1, 6, 2, 0, 3, 13, 10, 12, 9, 11, 7, 8, 14], [4, 1, 3, 6, 0, 2, 5, 7, 10, 8, 12, 13, 11, 9, 14], [2, 4, 3, 0, 1, 5, 6, 10, 13, 12, 7, 8, 11, 14, 9], [0, 6, 3, 5, 1, 2, 4, 8, 14, 11, 10, 13, 12, 7, 9], [3, 0, 2, 1, 6, 5, 4, 7, 9, 12, 13, 11, 8, 14, 10]]

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
