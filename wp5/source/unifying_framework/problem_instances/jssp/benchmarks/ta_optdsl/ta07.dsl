# Job Shop Scheduling instance: ta07
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11553

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[20, 27, 18, 51, 10, 1, 51, 6, 41, 90, 44, 26, 19, 52, 80], [88, 85, 44, 55, 34, 61, 84, 34, 2, 56, 69, 20, 12, 86, 78], [62, 74, 83, 72, 95, 34, 89, 63, 29, 98, 65, 31, 26, 90, 24], [93, 48, 96, 45, 21, 17, 1, 79, 11, 10, 27, 15, 77, 22, 61], [81, 35, 52, 29, 54, 70, 60, 80, 83, 7, 78, 91, 97, 52, 28], [9, 39, 59, 93, 20, 77, 41, 10, 7, 97, 49, 45, 3, 31, 98], [93, 52, 96, 47, 51, 4, 18, 90, 21, 28, 85, 63, 67, 49, 5], [61, 82, 66, 34, 56, 16, 67, 92, 99, 58, 50, 82, 25, 57, 15], [63, 87, 91, 59, 16, 31, 82, 29, 99, 59, 48, 61, 22, 36, 48], [83, 62, 25, 25, 65, 69, 55, 97, 28, 31, 57, 98, 66, 15, 31], [88, 13, 99, 17, 20, 95, 84, 63, 54, 90, 75, 70, 41, 1, 25], [42, 59, 1, 22, 84, 3, 63, 73, 59, 93, 78, 21, 59, 46, 10], [22, 80, 38, 26, 56, 94, 27, 72, 8, 51, 12, 43, 93, 17, 80], [6, 46, 8, 29, 75, 92, 43, 90, 72, 62, 90, 78, 46, 29, 16], [93, 45, 23, 35, 17, 89, 32, 16, 46, 10, 93, 85, 91, 44, 41]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[13, 12, 7, 0, 5, 11, 9, 10, 1, 2, 3, 14, 4, 6, 8], [2, 1, 8, 14, 13, 0, 5, 11, 9, 12, 10, 7, 3, 4, 6], [0, 3, 1, 7, 4, 8, 14, 5, 6, 2, 13, 12, 9, 10, 11], [9, 11, 0, 7, 12, 14, 6, 1, 13, 10, 4, 5, 3, 2, 8], [8, 13, 5, 10, 9, 14, 12, 2, 3, 0, 6, 11, 7, 4, 1], [12, 13, 14, 9, 5, 1, 6, 7, 0, 3, 8, 10, 4, 11, 2], [9, 0, 5, 4, 12, 14, 6, 1, 3, 8, 13, 11, 2, 10, 7], [12, 1, 9, 14, 6, 10, 2, 7, 4, 11, 13, 5, 3, 8, 0], [6, 5, 12, 4, 1, 14, 9, 0, 7, 8, 10, 13, 2, 11, 3], [8, 3, 5, 4, 1, 10, 7, 9, 13, 2, 0, 11, 6, 12, 14], [4, 2, 1, 0, 14, 10, 9, 6, 11, 12, 3, 8, 7, 13, 5], [8, 3, 13, 14, 2, 11, 5, 4, 9, 12, 10, 7, 1, 0, 6], [7, 1, 10, 4, 0, 8, 12, 6, 13, 2, 3, 9, 11, 14, 5], [8, 11, 3, 7, 1, 12, 6, 4, 10, 13, 2, 5, 14, 9, 0], [5, 13, 14, 6, 9, 11, 7, 2, 12, 8, 3, 4, 10, 1, 0]]

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
