# Job Shop Scheduling instance: ta13
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14541

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[87, 41, 95, 1, 14, 17, 22, 67, 4, 63, 80, 17, 91, 30, 85], [9, 8, 77, 12, 24, 77, 71, 6, 76, 95, 77, 6, 8, 64, 13], [99, 30, 3, 92, 54, 58, 12, 7, 23, 27, 78, 88, 66, 33, 96], [2, 3, 32, 78, 22, 65, 25, 24, 31, 19, 30, 9, 49, 30, 45], [16, 44, 26, 84, 41, 85, 35, 76, 61, 97, 96, 2, 13, 37, 51], [52, 97, 13, 85, 81, 59, 22, 85, 55, 95, 64, 65, 52, 2, 8], [4, 26, 94, 63, 98, 32, 13, 28, 2, 97, 14, 64, 20, 23, 62], [38, 96, 63, 98, 56, 27, 94, 6, 1, 63, 77, 28, 56, 41, 81], [37, 88, 8, 11, 72, 63, 13, 64, 98, 99, 57, 96, 89, 96, 28], [60, 82, 87, 71, 72, 85, 17, 14, 33, 80, 66, 27, 44, 63, 2], [42, 20, 65, 90, 61, 86, 47, 11, 65, 10, 9, 47, 96, 5, 17], [66, 89, 90, 37, 8, 98, 91, 37, 99, 17, 40, 16, 8, 87, 33], [65, 10, 99, 13, 30, 22, 39, 56, 25, 2, 44, 25, 12, 44, 62], [37, 45, 90, 69, 84, 54, 50, 62, 30, 64, 52, 35, 70, 38, 2], [50, 16, 46, 58, 82, 12, 2, 30, 73, 10, 16, 48, 21, 40, 37], [75, 79, 91, 81, 70, 19, 91, 40, 51, 6, 48, 21, 51, 65, 76], [51, 15, 25, 86, 47, 84, 26, 59, 49, 40, 32, 74, 70, 5, 75], [64, 83, 49, 21, 31, 6, 25, 85, 11, 30, 56, 60, 52, 31, 18], [72, 11, 35, 72, 55, 43, 42, 44, 83, 67, 35, 64, 90, 88, 8], [89, 53, 27, 56, 80, 21, 89, 34, 28, 79, 74, 15, 50, 19, 83]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[12, 11, 8, 9, 7, 13, 0, 10, 2, 4, 5, 6, 3, 14, 1], [2, 5, 0, 10, 4, 1, 13, 11, 3, 14, 6, 8, 9, 12, 7], [3, 2, 6, 9, 5, 12, 0, 13, 7, 10, 14, 1, 4, 8, 11], [9, 14, 5, 7, 13, 10, 12, 2, 3, 8, 1, 6, 11, 0, 4], [3, 8, 6, 1, 13, 0, 9, 5, 14, 2, 12, 7, 4, 11, 10], [3, 8, 13, 11, 12, 1, 4, 14, 6, 5, 9, 0, 7, 10, 2], [11, 2, 0, 6, 4, 1, 5, 12, 9, 7, 3, 8, 13, 10, 14], [12, 3, 4, 11, 8, 1, 5, 0, 13, 6, 10, 9, 2, 14, 7], [5, 8, 7, 0, 12, 13, 1, 6, 4, 14, 10, 9, 3, 2, 11], [6, 3, 9, 8, 2, 1, 12, 7, 5, 14, 0, 4, 11, 13, 10], [6, 0, 4, 14, 8, 13, 12, 11, 10, 1, 9, 7, 5, 3, 2], [0, 6, 4, 3, 8, 2, 11, 1, 9, 5, 13, 12, 10, 14, 7], [2, 9, 5, 12, 3, 14, 4, 13, 11, 7, 1, 10, 8, 6, 0], [11, 7, 10, 4, 8, 14, 6, 3, 9, 5, 1, 13, 2, 12, 0], [8, 13, 10, 12, 0, 9, 2, 6, 11, 1, 3, 14, 5, 7, 4], [14, 7, 11, 6, 10, 9, 2, 0, 1, 12, 8, 3, 4, 13, 5], [8, 13, 7, 9, 11, 12, 5, 4, 2, 3, 14, 6, 0, 10, 1], [8, 14, 5, 11, 1, 0, 7, 3, 12, 2, 9, 10, 13, 6, 4], [8, 6, 1, 11, 7, 12, 14, 10, 0, 9, 3, 4, 5, 13, 2], [13, 1, 4, 0, 5, 7, 3, 6, 12, 8, 11, 2, 10, 14, 9]]

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
