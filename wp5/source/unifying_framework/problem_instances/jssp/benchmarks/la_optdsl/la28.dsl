# Job Shop Scheduling instance: la28
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10682

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 81, 40, 37, 55, 19, 9, 40, 32, 81], [77, 46, 70, 55, 64, 65, 15, 21, 25, 65], [40, 44, 85, 24, 89, 37, 83, 84, 31, 29], [8, 80, 30, 38, 80, 59, 77, 56, 97, 41], [91, 17, 71, 50, 88, 56, 40, 7, 80, 59], [45, 29, 8, 58, 54, 77, 9, 36, 96, 10], [28, 98, 73, 92, 70, 87, 99, 27, 86, 96], [59, 95, 41, 85, 52, 56, 81, 92, 39, 32], [88, 7, 12, 60, 93, 22, 27, 69, 45, 49], [21, 84, 61, 68, 99, 26, 82, 33, 44, 71], [72, 26, 38, 19, 30, 98, 74, 8, 43, 75], [23, 85, 67, 43, 39, 13, 19, 9, 73, 26], [55, 50, 61, 93, 7, 80, 57, 46, 72, 42], [91, 68, 72, 96, 99, 68, 60, 43, 11, 11], [43, 70, 34, 12, 30, 7, 74, 84, 40, 69], [49, 69, 9, 27, 59, 72, 45, 99, 60, 63], [75, 90, 91, 17, 8, 37, 71, 50, 65, 98], [72, 9, 91, 31, 38, 98, 49, 90, 62, 72], [39, 80, 63, 52, 35, 25, 35, 47, 21, 74], [5, 88, 68, 50, 53, 24, 20, 57, 52, 58]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 1, 4, 7, 0, 5, 9, 3, 2, 6], [2, 3, 7, 4, 1, 8, 9, 0, 5, 6], [7, 4, 3, 1, 2, 8, 9, 6, 5, 0], [4, 5, 0, 2, 6, 3, 1, 7, 9, 8], [6, 2, 0, 7, 9, 8, 3, 5, 1, 4], [7, 9, 0, 6, 4, 8, 2, 5, 1, 3], [6, 8, 3, 0, 1, 4, 5, 9, 2, 7], [1, 3, 5, 4, 0, 2, 6, 8, 9, 7], [1, 7, 4, 6, 5, 0, 8, 3, 9, 2], [7, 2, 8, 5, 1, 6, 3, 0, 9, 4], [8, 0, 4, 5, 9, 1, 7, 6, 3, 2], [6, 2, 8, 1, 9, 4, 7, 0, 5, 3], [8, 7, 5, 3, 2, 4, 9, 1, 0, 6], [4, 0, 9, 5, 7, 3, 2, 8, 6, 1], [9, 0, 3, 8, 1, 6, 2, 5, 4, 7], [7, 3, 4, 5, 2, 6, 0, 9, 1, 8], [0, 3, 2, 7, 8, 5, 9, 1, 6, 4], [9, 1, 3, 6, 2, 8, 7, 0, 5, 4], [4, 2, 5, 6, 8, 7, 3, 1, 0, 9], [2, 5, 9, 8, 0, 6, 3, 7, 1, 4]]

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
