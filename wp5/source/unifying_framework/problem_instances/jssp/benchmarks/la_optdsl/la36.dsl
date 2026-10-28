# Job Shop Scheduling instance: la36
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11739

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[53, 21, 34, 55, 21, 95, 71, 26, 52, 16, 12, 42, 31, 39, 98], [55, 77, 66, 77, 83, 79, 19, 64, 34, 37, 92, 54, 43, 62, 79], [93, 87, 87, 69, 60, 77, 41, 38, 24, 83, 44, 49, 98, 17, 25], [96, 75, 43, 79, 95, 77, 7, 35, 76, 28, 61, 9, 95, 35, 10], [46, 91, 59, 16, 28, 59, 52, 27, 50, 43, 87, 45, 39, 41, 9], [20, 54, 71, 14, 78, 43, 28, 37, 26, 33, 33, 89, 8, 66, 42], [69, 74, 94, 27, 96, 84, 78, 45, 69, 81, 20, 31, 17, 87, 76], [24, 18, 32, 81, 58, 25, 72, 23, 99, 28, 45, 76, 86, 90, 97], [42, 46, 17, 48, 98, 27, 67, 62, 27, 48, 80, 12, 50, 19, 28], [94, 63, 98, 50, 75, 80, 41, 50, 55, 14, 61, 37, 18, 79, 72], [47, 71, 14, 96, 75, 57, 60, 65, 79, 22, 33, 31, 69, 32, 58], [44, 34, 47, 58, 62, 51, 44, 17, 29, 8, 97, 15, 40, 66, 38], [57, 39, 58, 50, 63, 20, 21, 57, 32, 87, 84, 85, 90, 61, 56], [20, 67, 70, 30, 82, 15, 23, 45, 38, 84, 18, 29, 21, 50, 41], [52, 52, 38, 54, 54, 16, 62, 74, 57, 37, 81, 61, 30, 68, 57]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 3, 6, 14, 10, 2, 9, 1, 0, 7, 8, 5, 12, 11, 13], [11, 4, 1, 7, 8, 14, 12, 0, 3, 6, 9, 5, 10, 13, 2], [9, 5, 2, 7, 4, 12, 0, 13, 6, 10, 3, 11, 8, 1, 14], [5, 0, 9, 6, 4, 13, 7, 8, 11, 12, 2, 1, 10, 14, 3], [10, 4, 8, 2, 0, 11, 14, 9, 6, 7, 1, 13, 3, 5, 12], [0, 2, 4, 13, 3, 12, 14, 6, 1, 9, 11, 8, 7, 10, 5], [8, 4, 12, 0, 7, 11, 6, 10, 3, 13, 1, 5, 14, 2, 9], [4, 13, 11, 3, 7, 9, 1, 2, 12, 8, 14, 0, 10, 6, 5], [5, 1, 6, 8, 13, 10, 2, 3, 7, 11, 14, 4, 0, 9, 12], [11, 5, 4, 8, 7, 0, 9, 6, 14, 3, 10, 13, 2, 12, 1], [7, 3, 0, 4, 12, 14, 10, 1, 9, 13, 5, 8, 2, 11, 6], [1, 2, 3, 5, 4, 6, 9, 7, 10, 8, 11, 13, 12, 0, 14], [3, 7, 13, 5, 11, 12, 2, 4, 10, 1, 9, 6, 14, 8, 0], [9, 7, 5, 14, 10, 4, 11, 2, 1, 3, 13, 6, 0, 12, 8], [9, 10, 11, 14, 8, 0, 7, 6, 12, 1, 2, 13, 4, 3, 5]]

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
