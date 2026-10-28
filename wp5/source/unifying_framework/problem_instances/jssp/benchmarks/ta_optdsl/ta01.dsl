# Job Shop Scheduling instance: ta01
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11671

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[70, 83, 15, 26, 10, 96, 94, 53, 10, 93, 65, 82, 66, 92, 27], [18, 99, 33, 51, 74, 31, 91, 88, 78, 7, 79, 8, 18, 57, 51], [54, 4, 68, 35, 39, 6, 50, 82, 82, 40, 20, 54, 86, 21, 68], [94, 92, 23, 9, 93, 73, 30, 32, 56, 30, 53, 30, 27, 58, 91], [42, 93, 95, 96, 36, 76, 21, 78, 23, 29, 60, 52, 79, 42, 99], [87, 26, 78, 61, 31, 29, 14, 83, 30, 62, 50, 16, 88, 70, 65], [37, 19, 43, 75, 85, 73, 68, 20, 4, 66, 24, 54, 18, 87, 91], [9, 62, 6, 80, 7, 52, 57, 49, 62, 3, 7, 32, 61, 35, 99], [13, 87, 82, 15, 56, 83, 96, 8, 85, 66, 85, 30, 78, 88, 91], [17, 69, 60, 89, 6, 13, 5, 88, 41, 30, 78, 59, 45, 66, 82], [8, 93, 73, 90, 90, 91, 89, 27, 49, 35, 28, 6, 80, 1, 32], [75, 45, 47, 67, 87, 34, 51, 84, 28, 60, 3, 58, 8, 69, 43], [77, 48, 20, 31, 80, 65, 33, 96, 62, 33, 97, 90, 75, 50, 44], [35, 56, 7, 16, 51, 17, 89, 18, 28, 59, 30, 17, 63, 75, 21], [8, 26, 83, 87, 37, 97, 34, 12, 16, 20, 57, 5, 42, 68, 73]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 12, 4, 7, 3, 2, 10, 11, 8, 14, 9, 13, 5, 0, 1], [4, 5, 7, 14, 13, 8, 11, 9, 6, 10, 0, 3, 12, 1, 2], [1, 8, 9, 12, 6, 11, 13, 5, 0, 2, 7, 10, 4, 3, 14], [5, 2, 9, 6, 10, 0, 13, 4, 7, 14, 11, 8, 12, 1, 3], [7, 8, 6, 10, 4, 9, 2, 14, 12, 5, 1, 13, 11, 0, 3], [5, 3, 12, 13, 11, 4, 14, 7, 2, 1, 10, 0, 9, 6, 8], [12, 3, 7, 8, 14, 6, 1, 11, 4, 5, 2, 10, 0, 13, 9], [11, 5, 0, 7, 12, 13, 14, 1, 2, 8, 4, 3, 9, 6, 10], [10, 11, 6, 14, 0, 1, 2, 5, 12, 4, 8, 7, 9, 13, 3], [6, 11, 9, 2, 8, 0, 13, 3, 10, 7, 1, 12, 14, 4, 5], [4, 7, 13, 0, 5, 12, 6, 8, 14, 10, 3, 1, 11, 9, 2], [2, 14, 0, 12, 6, 10, 7, 5, 8, 9, 13, 1, 3, 11, 4], [5, 8, 10, 2, 3, 6, 9, 0, 13, 4, 1, 11, 12, 7, 14], [8, 14, 4, 13, 5, 6, 9, 1, 12, 7, 11, 10, 3, 2, 0], [10, 8, 12, 6, 4, 1, 13, 14, 11, 0, 7, 3, 2, 9, 5]]

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
