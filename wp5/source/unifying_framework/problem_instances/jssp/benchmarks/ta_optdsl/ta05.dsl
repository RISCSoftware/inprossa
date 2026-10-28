# Job Shop Scheduling instance: ta05
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11252

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[75, 96, 99, 65, 59, 16, 71, 24, 65, 95, 84, 23, 40, 76, 52], [38, 88, 37, 68, 94, 2, 38, 93, 57, 13, 52, 71, 35, 68, 99], [97, 16, 1, 46, 79, 62, 87, 87, 54, 37, 14, 2, 96, 30, 51], [8, 78, 76, 70, 97, 42, 16, 15, 25, 72, 19, 62, 81, 15, 84], [21, 68, 85, 79, 21, 37, 68, 91, 51, 30, 64, 73, 71, 50, 3], [72, 98, 2, 83, 14, 86, 29, 1, 6, 33, 33, 59, 98, 31, 50], [80, 47, 71, 10, 33, 53, 99, 78, 96, 70, 21, 80, 56, 92, 1], [38, 46, 16, 29, 38, 89, 10, 65, 30, 90, 85, 73, 88, 47, 48], [9, 37, 9, 41, 8, 83, 49, 23, 15, 61, 1, 60, 78, 35, 39], [60, 51, 49, 10, 37, 75, 47, 73, 11, 79, 26, 37, 1, 84, 46], [48, 43, 24, 49, 22, 73, 68, 69, 33, 39, 21, 94, 61, 3, 2], [50, 77, 86, 73, 19, 23, 81, 21, 22, 16, 11, 52, 46, 64, 75], [85, 22, 60, 32, 68, 92, 23, 32, 30, 14, 13, 90, 21, 80, 45], [75, 95, 3, 96, 52, 12, 33, 73, 59, 90, 12, 6, 29, 83, 57], [54, 40, 70, 29, 48, 18, 50, 94, 70, 43, 42, 75, 27, 12, 1]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[12, 1, 4, 9, 13, 0, 11, 8, 3, 5, 6, 14, 10, 2, 7], [5, 1, 14, 10, 13, 9, 6, 12, 8, 2, 7, 0, 3, 4, 11], [6, 3, 10, 7, 13, 4, 5, 9, 8, 2, 0, 1, 11, 14, 12], [10, 7, 5, 0, 9, 13, 2, 8, 1, 14, 11, 3, 12, 6, 4], [6, 12, 14, 1, 7, 5, 11, 0, 2, 3, 8, 13, 4, 9, 10], [4, 7, 6, 0, 8, 13, 12, 14, 3, 2, 5, 9, 10, 1, 11], [10, 11, 6, 9, 0, 2, 1, 8, 12, 7, 5, 3, 13, 14, 4], [3, 10, 5, 6, 8, 4, 0, 14, 2, 7, 9, 11, 12, 1, 13], [1, 2, 6, 7, 10, 12, 14, 8, 0, 3, 13, 5, 4, 9, 11], [12, 7, 6, 14, 3, 4, 0, 13, 10, 8, 11, 9, 5, 2, 1], [4, 3, 8, 14, 2, 13, 5, 6, 10, 12, 7, 11, 1, 9, 0], [6, 12, 7, 5, 2, 4, 13, 11, 8, 0, 10, 3, 1, 9, 14], [12, 13, 8, 7, 1, 6, 0, 5, 9, 10, 4, 2, 14, 3, 11], [12, 1, 4, 8, 6, 10, 7, 3, 0, 5, 13, 2, 9, 14, 11], [7, 5, 0, 10, 2, 3, 9, 6, 11, 8, 1, 4, 14, 12, 13]]

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
