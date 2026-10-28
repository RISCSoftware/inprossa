# Job Shop Scheduling instance: la37
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 12569

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[62, 66, 84, 85, 25, 19, 64, 46, 59, 13, 41, 73, 53, 80, 88], [14, 67, 57, 74, 84, 47, 78, 41, 84, 64, 63, 46, 26, 28, 52], [64, 11, 17, 10, 85, 73, 97, 67, 95, 38, 59, 65, 95, 93, 46], [60, 85, 43, 32, 66, 85, 90, 61, 41, 49, 23, 17, 49, 70, 99], [73, 98, 68, 73, 13, 40, 9, 7, 57, 98, 37, 85, 17, 41, 79], [14, 76, 54, 19, 95, 86, 40, 53, 16, 87, 84, 66, 97, 96, 52], [18, 33, 55, 87, 77, 74, 33, 60, 13, 42, 16, 61, 54, 33, 91], [69, 79, 92, 79, 58, 39, 41, 78, 76, 64, 28, 82, 6, 49, 47], [52, 35, 28, 47, 91, 42, 88, 52, 24, 91, 23, 21, 76, 86, 82], [84, 93, 38, 95, 70, 37, 86, 45, 67, 28, 8, 42, 64, 45, 77], [9, 58, 44, 5, 97, 58, 89, 84, 77, 96, 77, 87, 81, 85, 39], [15, 21, 31, 57, 40, 73, 49, 48, 70, 71, 10, 22, 80, 34, 82], [55, 91, 17, 7, 11, 75, 72, 62, 47, 35, 64, 90, 94, 75, 50], [12, 71, 67, 15, 52, 20, 57, 29, 68, 93, 58, 93, 70, 77, 7], [95, 63, 82, 27, 26, 6, 87, 56, 48, 36, 36, 8, 36, 76, 15]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[5, 6, 11, 9, 2, 14, 3, 10, 12, 13, 1, 7, 8, 4, 0], [1, 3, 7, 2, 14, 0, 9, 8, 6, 5, 13, 4, 10, 12, 11], [6, 8, 0, 9, 10, 12, 2, 11, 13, 3, 5, 1, 4, 14, 7], [10, 12, 3, 4, 2, 0, 8, 7, 13, 9, 11, 6, 1, 14, 5], [9, 8, 3, 6, 0, 7, 1, 4, 13, 5, 11, 10, 2, 14, 12], [11, 7, 5, 6, 0, 3, 13, 4, 2, 10, 12, 8, 14, 1, 9], [4, 2, 9, 5, 14, 13, 10, 12, 0, 3, 7, 8, 6, 1, 11], [6, 5, 11, 9, 14, 10, 7, 13, 1, 4, 2, 3, 12, 0, 8], [11, 5, 9, 2, 0, 6, 12, 13, 10, 1, 7, 4, 3, 14, 8], [11, 1, 3, 13, 9, 14, 0, 10, 7, 4, 5, 6, 12, 8, 2], [4, 12, 1, 7, 5, 0, 11, 3, 2, 13, 6, 10, 9, 14, 8], [12, 1, 10, 5, 8, 6, 2, 13, 4, 11, 0, 14, 3, 9, 7], [2, 7, 5, 9, 1, 14, 3, 10, 13, 12, 0, 6, 8, 4, 11], [11, 6, 1, 12, 9, 5, 3, 13, 10, 0, 2, 8, 14, 7, 4], [13, 3, 4, 9, 11, 10, 0, 8, 2, 6, 5, 1, 7, 12, 14]]

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
