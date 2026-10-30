# Job Shop Scheduling instance: la30
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10680

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[82, 33, 20, 16, 10, 88, 32, 70, 12, 75], [86, 45, 36, 91, 81, 56, 59, 68, 39, 69], [88, 5, 57, 84, 81, 73, 83, 41, 38, 17], [94, 30, 15, 18, 20, 6, 45, 17, 19, 88], [45, 25, 15, 60, 11, 16, 49, 5, 63, 24], [93, 86, 77, 32, 71, 45, 54, 92, 50, 48], [32, 39, 57, 78, 71, 86, 90, 57, 86, 88], [54, 69, 59, 18, 41, 83, 94, 20, 65, 31], [59, 72, 8, 47, 79, 73, 76, 57, 84, 30], [59, 62, 89, 8, 10, 54, 88, 45, 20, 7], [82, 24, 5, 37, 77, 63, 9, 10, 13, 79], [74, 32, 61, 5, 92, 23, 45, 53, 10, 20], [61, 98, 85, 33, 37, 99, 94, 75, 65, 51], [51, 81, 7, 24, 17, 8, 30, 12, 23, 35], [93, 71, 31, 63, 65, 42, 29, 27, 68, 70], [72, 28, 33, 90, 51, 38, 54, 70, 78, 45], [18, 81, 90, 59, 25, 35, 92, 29, 85, 80], [97, 38, 96, 94, 86, 67, 35, 86, 45, 82], [33, 75, 92, 54, 59, 8, 52, 60, 51, 70], [82, 69, 7, 98, 51, 78, 62, 80, 79, 89]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 3, 1, 8, 7, 4, 9, 0, 5, 2], [8, 4, 3, 5, 9, 1, 6, 0, 2, 7], [3, 2, 7, 5, 4, 0, 8, 9, 6, 1], [4, 5, 2, 8, 1, 0, 6, 7, 3, 9], [9, 6, 5, 4, 3, 7, 8, 1, 2, 0], [1, 8, 2, 6, 9, 0, 3, 7, 5, 4], [5, 6, 3, 9, 2, 0, 7, 8, 4, 1], [2, 3, 9, 4, 7, 5, 8, 0, 6, 1], [3, 4, 6, 0, 1, 2, 9, 5, 7, 8], [0, 2, 4, 7, 3, 5, 6, 8, 9, 1], [5, 6, 4, 3, 2, 8, 9, 1, 7, 0], [0, 1, 2, 7, 4, 9, 8, 3, 6, 5], [2, 9, 0, 5, 4, 6, 1, 8, 3, 7], [0, 3, 5, 6, 7, 8, 2, 4, 9, 1], [1, 5, 8, 2, 6, 3, 4, 9, 7, 0], [1, 5, 4, 7, 2, 8, 9, 3, 6, 0], [0, 2, 4, 6, 8, 5, 7, 1, 9, 3], [5, 2, 1, 4, 0, 3, 7, 6, 9, 8], [2, 8, 4, 6, 5, 9, 1, 3, 7, 0], [3, 7, 5, 0, 2, 9, 1, 4, 8, 6]]

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
