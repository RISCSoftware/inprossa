# Job Shop Scheduling instance: ta16
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15540

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[58, 90, 76, 90, 74, 68, 87, 35, 77, 63, 28, 17, 60, 26, 64], [88, 71, 24, 42, 37, 5, 97, 62, 79, 71, 47, 86, 87, 20, 47], [3, 42, 67, 76, 25, 2, 46, 38, 28, 23, 76, 89, 94, 66, 98], [36, 32, 55, 87, 19, 37, 18, 45, 96, 3, 79, 6, 15, 9, 12], [41, 17, 43, 77, 66, 71, 46, 52, 71, 21, 37, 73, 22, 88, 59], [6, 29, 54, 12, 79, 78, 16, 4, 60, 22, 21, 19, 27, 87, 41], [64, 74, 68, 39, 92, 22, 60, 37, 10, 47, 15, 82, 29, 96, 68], [74, 9, 94, 60, 77, 28, 71, 59, 3, 74, 98, 21, 19, 19, 57], [93, 66, 90, 13, 76, 6, 56, 69, 38, 63, 2, 53, 7, 58, 60], [90, 74, 20, 51, 34, 85, 67, 60, 94, 50, 33, 75, 28, 4, 46], [23, 35, 14, 12, 21, 37, 12, 85, 88, 11, 88, 76, 87, 98, 33], [97, 73, 71, 16, 2, 91, 3, 89, 15, 30, 65, 98, 19, 89, 71], [79, 32, 61, 76, 78, 31, 84, 34, 59, 88, 50, 25, 71, 86, 75], [59, 67, 65, 9, 11, 24, 96, 61, 38, 93, 74, 25, 41, 69, 68], [21, 71, 91, 5, 52, 77, 86, 72, 72, 68, 45, 25, 65, 50, 68], [23, 36, 50, 80, 2, 19, 37, 26, 27, 45, 65, 20, 35, 61, 27], [7, 70, 57, 46, 47, 63, 88, 77, 95, 23, 88, 49, 36, 5, 42], [83, 85, 49, 20, 33, 23, 65, 64, 63, 3, 92, 42, 78, 29, 80], [29, 63, 47, 70, 63, 1, 85, 84, 93, 67, 48, 57, 87, 90, 48], [93, 81, 85, 25, 14, 6, 10, 22, 19, 62, 70, 41, 73, 80, 62]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 11, 0, 13, 1, 8, 9, 6, 4, 7, 12, 3, 14, 5, 10], [5, 8, 9, 3, 1, 13, 11, 0, 14, 7, 4, 12, 10, 6, 2], [5, 2, 8, 14, 13, 1, 6, 9, 12, 4, 11, 0, 7, 3, 10], [8, 10, 4, 0, 3, 11, 13, 6, 1, 5, 2, 9, 12, 14, 7], [8, 11, 1, 0, 5, 13, 2, 14, 10, 12, 9, 3, 4, 6, 7], [11, 3, 13, 9, 14, 1, 0, 7, 4, 5, 10, 12, 6, 2, 8], [13, 3, 11, 10, 5, 12, 0, 4, 14, 6, 7, 8, 9, 2, 1], [5, 8, 6, 7, 2, 3, 10, 4, 1, 14, 11, 9, 13, 0, 12], [12, 8, 9, 7, 3, 6, 11, 13, 10, 0, 2, 5, 1, 4, 14], [5, 14, 11, 4, 10, 8, 9, 2, 13, 12, 7, 1, 0, 3, 6], [10, 9, 1, 12, 2, 7, 3, 4, 0, 5, 6, 8, 13, 14, 11], [9, 7, 5, 6, 0, 14, 1, 3, 8, 11, 2, 12, 10, 13, 4], [2, 13, 12, 3, 9, 1, 5, 10, 11, 6, 0, 7, 8, 14, 4], [3, 0, 9, 13, 8, 2, 6, 1, 10, 12, 7, 14, 4, 5, 11], [6, 5, 0, 13, 8, 14, 2, 7, 12, 4, 10, 3, 1, 9, 11], [6, 8, 0, 7, 4, 1, 11, 10, 13, 14, 12, 2, 9, 3, 5], [13, 2, 1, 8, 3, 12, 6, 14, 11, 9, 5, 7, 4, 10, 0], [13, 7, 5, 11, 4, 6, 10, 14, 2, 9, 0, 3, 8, 12, 1], [9, 2, 10, 11, 7, 1, 14, 3, 6, 8, 5, 4, 12, 0, 13], [13, 4, 11, 12, 7, 0, 5, 1, 8, 14, 9, 2, 3, 10, 6]]

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
