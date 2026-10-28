# Job Shop Scheduling instance: ta04
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 10949

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[70, 85, 50, 72, 33, 88, 42, 51, 46, 61, 27, 70, 56, 25, 31], [79, 19, 61, 43, 19, 47, 56, 91, 40, 84, 65, 79, 30, 67, 68], [60, 8, 91, 7, 82, 44, 7, 94, 2, 76, 85, 95, 72, 36, 2], [40, 94, 19, 19, 41, 84, 58, 88, 25, 98, 74, 67, 96, 34, 74], [30, 45, 71, 28, 17, 29, 8, 42, 32, 4, 43, 60, 25, 93, 79], [84, 93, 56, 15, 77, 55, 40, 54, 31, 4, 39, 84, 46, 15, 66], [47, 7, 11, 72, 38, 63, 22, 91, 68, 62, 22, 17, 77, 47, 65], [53, 53, 60, 83, 21, 42, 25, 12, 32, 29, 56, 84, 52, 60, 22], [4, 24, 54, 68, 28, 95, 57, 48, 92, 85, 26, 84, 47, 19, 70], [41, 37, 36, 64, 13, 41, 30, 32, 94, 74, 65, 6, 34, 44, 53], [13, 94, 60, 89, 23, 46, 28, 37, 72, 9, 85, 62, 79, 18, 11], [74, 43, 97, 11, 61, 70, 78, 62, 42, 26, 60, 62, 8, 40, 21], [22, 63, 54, 12, 9, 42, 9, 41, 98, 92, 8, 2, 63, 76, 32], [47, 92, 52, 11, 4, 67, 56, 87, 1, 82, 7, 8, 35, 91, 39], [24, 95, 24, 60, 14, 57, 4, 22, 69, 30, 64, 44, 14, 61, 34]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 7, 6, 14, 9, 8, 5, 4, 10, 1, 0, 12, 11, 2, 13], [1, 11, 0, 5, 8, 13, 3, 10, 9, 2, 12, 6, 4, 7, 14], [7, 3, 8, 11, 0, 4, 9, 13, 1, 10, 6, 5, 14, 12, 2], [6, 11, 5, 13, 3, 2, 1, 4, 9, 12, 8, 0, 14, 7, 10], [1, 11, 6, 5, 8, 7, 12, 9, 2, 14, 13, 3, 0, 4, 10], [11, 2, 12, 1, 14, 0, 6, 9, 3, 13, 7, 10, 4, 5, 8], [14, 7, 11, 0, 12, 8, 9, 10, 3, 13, 4, 1, 2, 6, 5], [7, 4, 13, 5, 14, 11, 2, 12, 6, 1, 0, 10, 9, 3, 8], [7, 4, 14, 10, 3, 0, 13, 8, 1, 2, 6, 12, 11, 9, 5], [2, 12, 10, 3, 6, 5, 14, 9, 13, 4, 0, 11, 7, 8, 1], [11, 9, 3, 7, 6, 4, 0, 2, 5, 1, 10, 8, 13, 12, 14], [0, 4, 1, 9, 2, 11, 13, 10, 7, 6, 8, 12, 14, 3, 5], [6, 0, 4, 10, 2, 14, 9, 13, 11, 12, 1, 8, 5, 3, 7], [5, 10, 13, 2, 7, 4, 8, 6, 9, 0, 12, 11, 1, 14, 3], [11, 2, 0, 4, 14, 5, 9, 10, 6, 12, 8, 1, 7, 3, 13]]

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
