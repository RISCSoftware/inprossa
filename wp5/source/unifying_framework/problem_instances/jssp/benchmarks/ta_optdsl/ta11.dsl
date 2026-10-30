# Job Shop Scheduling instance: ta11
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14447

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[14, 76, 62, 25, 38, 46, 57, 59, 3, 31, 38, 75, 13, 92, 75], [5, 34, 55, 11, 40, 67, 35, 96, 11, 21, 22, 16, 77, 29, 42], [35, 29, 22, 98, 46, 13, 70, 52, 18, 59, 22, 19, 31, 64, 8], [27, 2, 21, 11, 92, 56, 19, 43, 99, 97, 42, 17, 23, 35, 88], [39, 59, 71, 52, 35, 2, 12, 35, 5, 39, 47, 65, 82, 42, 50], [64, 5, 34, 48, 54, 2, 60, 3, 86, 63, 57, 51, 45, 26, 39], [99, 50, 40, 54, 67, 29, 34, 67, 46, 30, 43, 60, 71, 95, 6], [3, 59, 85, 82, 6, 71, 48, 46, 65, 62, 76, 5, 18, 49, 79], [87, 69, 97, 89, 65, 55, 52, 32, 22, 81, 15, 63, 82, 69, 71], [81, 70, 50, 52, 74, 67, 24, 18, 39, 77, 94, 32, 59, 14, 14], [53, 96, 64, 18, 14, 89, 18, 90, 99, 35, 6, 48, 81, 80, 39], [93, 30, 44, 74, 75, 59, 12, 75, 13, 26, 30, 91, 93, 84, 71], [39, 48, 46, 7, 22, 17, 55, 56, 29, 26, 69, 50, 55, 96, 13], [53, 95, 90, 14, 13, 92, 24, 43, 75, 8, 78, 94, 57, 87, 68], [83, 56, 97, 93, 48, 28, 18, 15, 78, 40, 53, 39, 51, 27, 92], [59, 92, 11, 20, 30, 47, 42, 19, 11, 14, 28, 10, 28, 4, 34], [27, 27, 68, 69, 18, 56, 98, 82, 82, 43, 64, 43, 20, 17, 40], [44, 20, 87, 89, 12, 51, 23, 84, 26, 49, 84, 61, 3, 95, 88], [73, 70, 54, 43, 59, 22, 28, 45, 36, 85, 29, 13, 18, 72, 20], [40, 95, 34, 23, 66, 4, 22, 8, 14, 45, 74, 7, 79, 62, 97]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 11, 14, 1, 10, 2, 4, 7, 0, 12, 5, 9, 6, 13, 8], [5, 0, 3, 8, 4, 1, 12, 14, 6, 7, 10, 2, 9, 13, 11], [2, 3, 14, 0, 9, 12, 5, 4, 7, 10, 8, 11, 13, 1, 6], [8, 10, 1, 13, 3, 4, 14, 9, 2, 5, 11, 7, 0, 6, 12], [14, 8, 1, 2, 10, 9, 12, 4, 6, 5, 0, 13, 3, 11, 7], [3, 10, 1, 5, 6, 0, 8, 7, 11, 13, 2, 14, 12, 9, 4], [2, 10, 1, 12, 8, 0, 7, 6, 14, 13, 4, 3, 5, 9, 11], [1, 0, 2, 4, 7, 13, 11, 3, 12, 5, 6, 14, 9, 8, 10], [4, 5, 9, 10, 7, 6, 2, 1, 12, 3, 13, 0, 8, 14, 11], [1, 4, 3, 10, 14, 0, 6, 13, 11, 8, 5, 12, 7, 9, 2], [3, 10, 1, 0, 9, 8, 14, 6, 4, 7, 2, 12, 5, 11, 13], [2, 7, 6, 8, 3, 5, 14, 4, 1, 0, 9, 10, 13, 11, 12], [0, 7, 14, 8, 12, 10, 9, 3, 6, 1, 4, 2, 11, 13, 5], [12, 3, 9, 4, 1, 0, 10, 6, 5, 2, 14, 13, 7, 8, 11], [3, 14, 6, 5, 13, 9, 1, 0, 12, 7, 2, 4, 10, 8, 11], [5, 14, 6, 12, 8, 2, 4, 9, 11, 13, 3, 1, 7, 0, 10], [3, 7, 10, 14, 0, 8, 1, 11, 5, 13, 4, 12, 6, 9, 2], [10, 8, 2, 11, 13, 6, 14, 3, 9, 7, 4, 5, 12, 0, 1], [3, 2, 12, 13, 1, 6, 14, 5, 4, 8, 9, 11, 0, 10, 7], [11, 14, 5, 6, 10, 9, 13, 1, 4, 8, 0, 3, 12, 2, 7]]

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
