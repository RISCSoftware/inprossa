# Job Shop Scheduling instance: la27
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10832

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[87, 72, 66, 60, 48, 95, 54, 39, 35, 5], [97, 46, 21, 20, 59, 55, 34, 37, 19, 46], [28, 24, 73, 25, 45, 23, 78, 83, 28, 5], [53, 37, 12, 71, 38, 29, 55, 87, 33, 12], [48, 40, 49, 83, 90, 7, 23, 65, 17, 27], [62, 66, 84, 85, 25, 19, 64, 46, 59, 13], [41, 73, 53, 80, 14, 88, 67, 57, 74, 47], [84, 78, 41, 84, 63, 64, 46, 26, 28, 52], [64, 11, 17, 10, 85, 73, 97, 67, 95, 38], [59, 65, 95, 93, 60, 46, 85, 43, 32, 85], [66, 90, 61, 41, 23, 49, 17, 49, 70, 99], [73, 98, 68, 73, 13, 40, 9, 7, 57, 98], [37, 85, 17, 41, 14, 79, 76, 54, 19, 86], [95, 40, 53, 16, 84, 87, 66, 97, 96, 52], [18, 33, 55, 87, 77, 74, 33, 60, 13, 42], [16, 61, 54, 33, 69, 91, 79, 92, 79, 39], [58, 41, 78, 76, 28, 64, 82, 6, 49, 47], [52, 35, 28, 47, 91, 42, 88, 52, 24, 91], [23, 21, 76, 86, 84, 82, 93, 38, 95, 37], [70, 86, 45, 67, 8, 28, 42, 64, 45, 77]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 4, 5, 0, 1, 9, 8, 7, 6, 2], [7, 6, 0, 5, 2, 3, 4, 9, 8, 1], [4, 2, 1, 8, 0, 3, 5, 7, 9, 6], [0, 2, 9, 1, 8, 3, 6, 5, 7, 4], [4, 2, 9, 7, 5, 6, 0, 3, 8, 1], [3, 4, 2, 6, 9, 1, 7, 8, 0, 5], [5, 6, 4, 0, 1, 7, 2, 3, 9, 8], [1, 5, 4, 6, 3, 0, 8, 9, 7, 2], [1, 0, 6, 9, 2, 4, 5, 3, 8, 7], [3, 2, 7, 1, 8, 0, 6, 5, 9, 4], [2, 3, 5, 4, 0, 7, 8, 9, 1, 6], [4, 7, 1, 8, 0, 3, 2, 5, 9, 6], [9, 6, 4, 3, 1, 0, 8, 2, 7, 5], [1, 2, 7, 5, 8, 4, 3, 6, 9, 0], [6, 1, 3, 0, 2, 8, 4, 7, 9, 5], [7, 5, 8, 2, 4, 6, 3, 1, 9, 0], [6, 1, 4, 5, 2, 3, 7, 8, 9, 0], [0, 5, 8, 9, 3, 6, 4, 7, 2, 1], [5, 2, 3, 6, 4, 7, 8, 9, 1, 0], [9, 4, 6, 7, 0, 2, 8, 5, 3, 1]]

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
