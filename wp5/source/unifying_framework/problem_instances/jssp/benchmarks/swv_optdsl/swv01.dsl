# Job Shop Scheduling instance: swv01
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 9739

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[25, 39, 27, 19, 13, 54, 93, 74, 37, 40], [30, 64, 69, 4, 1, 2, 31, 71, 8, 84], [86, 54, 55, 80, 79, 59, 72, 86, 81, 75], [17, 26, 76, 15, 30, 52, 83, 91, 44, 68], [39, 74, 98, 87, 73, 43, 77, 7, 17, 100], [49, 63, 16, 55, 9, 61, 82, 46, 34, 73], [87, 71, 39, 80, 43, 44, 41, 70, 18, 79], [73, 64, 22, 62, 70, 25, 69, 28, 19, 41], [84, 58, 9, 16, 7, 8, 10, 17, 42, 65], [10, 3, 3, 8, 41, 53, 13, 40, 56, 96], [39, 60, 12, 64, 62, 2, 87, 64, 60, 21], [78, 71, 66, 23, 75, 50, 35, 74, 23, 24], [69, 5, 80, 92, 6, 17, 80, 13, 47, 89], [82, 24, 47, 84, 93, 34, 73, 85, 28, 91], [57, 40, 24, 63, 55, 99, 37, 30, 88, 41], [7, 75, 47, 68, 78, 50, 2, 80, 49, 23], [91, 21, 10, 94, 25, 84, 70, 59, 6, 75], [94, 31, 85, 11, 94, 21, 61, 93, 50, 7], [77, 27, 30, 2, 13, 88, 53, 4, 54, 39], [24, 34, 12, 31, 24, 6, 11, 16, 81, 88]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 2, 1, 4, 0, 8, 9, 5, 7, 6], [2, 0, 4, 3, 1, 7, 5, 9, 6, 8], [4, 3, 0, 2, 1, 8, 6, 7, 5, 9], [2, 3, 1, 0, 4, 8, 7, 6, 5, 9], [4, 3, 1, 0, 2, 9, 5, 8, 7, 6], [1, 0, 2, 3, 4, 9, 5, 8, 6, 7], [0, 1, 4, 3, 2, 7, 8, 6, 9, 5], [4, 2, 0, 3, 1, 5, 8, 6, 9, 7], [3, 0, 1, 4, 2, 5, 6, 7, 8, 9], [3, 0, 1, 4, 2, 7, 8, 5, 9, 6], [4, 1, 3, 2, 0, 5, 7, 6, 9, 8], [2, 1, 3, 4, 0, 7, 6, 9, 8, 5], [1, 3, 4, 0, 2, 7, 5, 9, 6, 8], [0, 3, 1, 2, 4, 7, 5, 6, 8, 9], [4, 0, 3, 2, 1, 7, 6, 5, 8, 9], [1, 2, 3, 0, 4, 7, 6, 9, 8, 5], [0, 4, 2, 1, 3, 8, 7, 5, 9, 6], [2, 1, 0, 4, 3, 5, 9, 6, 8, 7], [1, 0, 4, 2, 3, 5, 7, 9, 6, 8], [1, 2, 3, 0, 4, 7, 5, 9, 8, 6]]

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
