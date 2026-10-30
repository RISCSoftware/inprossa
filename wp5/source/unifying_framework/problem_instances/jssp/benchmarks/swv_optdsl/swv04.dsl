# Job Shop Scheduling instance: swv04
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10240

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[59, 64, 16, 95, 10, 73, 17, 3, 92, 56], [96, 5, 14, 30, 64, 12, 93, 35, 73, 11], [54, 30, 83, 35, 75, 39, 90, 38, 29, 20], [52, 20, 93, 21, 29, 5, 98, 11, 53, 56], [17, 78, 100, 16, 41, 55, 2, 87, 27, 55], [38, 32, 71, 97, 84, 5, 41, 16, 41, 64], [64, 57, 92, 41, 37, 21, 19, 94, 79, 47], [23, 39, 63, 67, 98, 45, 89, 44, 83, 81], [59, 88, 63, 39, 91, 44, 45, 12, 36, 43], [6, 17, 29, 74, 51, 56, 2, 49, 14, 14], [35, 99, 10, 75, 1, 95, 53, 56, 82, 78], [75, 21, 96, 90, 55, 45, 23, 40, 55, 76], [72, 59, 33, 90, 64, 85, 74, 51, 38, 76], [68, 84, 87, 57, 2, 77, 37, 37, 4, 94], [77, 16, 23, 46, 34, 37, 99, 68, 14, 54], [43, 73, 92, 42, 24, 81, 5, 99, 88, 80], [3, 56, 51, 25, 87, 62, 68, 11, 88, 29], [49, 79, 85, 3, 21, 37, 18, 18, 38, 72], [2, 31, 29, 55, 98, 92, 43, 67, 99, 41], [61, 13, 31, 64, 69, 6, 54, 32, 84, 94]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 0, 4, 3, 1, 8, 9, 7, 5, 6], [1, 4, 3, 2, 0, 9, 8, 7, 6, 5], [3, 4, 0, 1, 2, 9, 8, 7, 6, 5], [4, 3, 0, 2, 1, 5, 7, 8, 9, 6], [0, 3, 4, 1, 2, 5, 8, 6, 7, 9], [3, 1, 4, 2, 0, 9, 7, 5, 6, 8], [3, 1, 4, 0, 2, 6, 9, 7, 8, 5], [0, 3, 1, 4, 2, 8, 5, 6, 9, 7], [1, 0, 3, 2, 4, 8, 5, 6, 9, 7], [2, 1, 0, 3, 4, 9, 6, 5, 7, 8], [3, 2, 4, 0, 1, 7, 5, 9, 6, 8], [0, 2, 1, 3, 4, 6, 7, 9, 8, 5], [3, 4, 0, 2, 1, 7, 6, 5, 9, 8], [3, 1, 2, 4, 0, 8, 5, 6, 7, 9], [1, 3, 4, 2, 0, 7, 8, 9, 5, 6], [4, 1, 2, 0, 3, 5, 7, 8, 9, 6], [1, 2, 0, 4, 3, 5, 7, 8, 6, 9], [2, 3, 4, 0, 1, 8, 5, 9, 7, 6], [0, 3, 1, 2, 4, 5, 6, 8, 7, 9], [4, 3, 0, 1, 2, 5, 8, 9, 7, 6]]

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
