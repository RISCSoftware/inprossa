# Job Shop Scheduling instance: la25
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 10
MAX_TIME : int = 7509

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[76, 29, 38, 12, 75, 97, 66, 44, 14, 12], [43, 80, 85, 82, 58, 38, 87, 69, 92, 89], [43, 84, 14, 41, 8, 61, 48, 7, 66, 5], [96, 8, 42, 74, 59, 19, 41, 97, 43, 73], [7, 48, 70, 75, 37, 5, 55, 23, 42, 38], [79, 56, 72, 95, 25, 73, 43, 31, 9, 60], [97, 7, 64, 78, 94, 21, 16, 86, 53, 31], [61, 33, 65, 86, 30, 32, 59, 85, 44, 63], [60, 30, 44, 16, 11, 61, 45, 90, 93, 84], [32, 49, 28, 20, 47, 11, 52, 36, 31, 35], [85, 84, 77, 34, 10, 17, 49, 74, 20, 68], [17, 85, 17, 29, 76, 7, 59, 48, 71, 13], [19, 39, 15, 32, 39, 64, 87, 11, 43, 16], [8, 83, 92, 99, 91, 33, 32, 57, 82, 99], [48, 38, 69, 91, 88, 39, 21, 7, 27, 62]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 4, 3, 2, 0, 5, 9, 1, 7, 6], [5, 3, 2, 4, 6, 9, 0, 1, 7, 8], [9, 1, 0, 6, 4, 7, 3, 5, 8, 2], [2, 1, 0, 5, 4, 7, 9, 8, 3, 6], [6, 2, 3, 8, 4, 7, 1, 5, 9, 0], [8, 2, 7, 0, 5, 3, 4, 6, 9, 1], [0, 2, 3, 5, 4, 9, 8, 6, 7, 1], [3, 7, 9, 0, 2, 4, 5, 1, 8, 6], [2, 3, 4, 6, 1, 9, 8, 0, 5, 7], [7, 8, 4, 6, 0, 5, 2, 9, 3, 1], [8, 6, 7, 4, 5, 3, 0, 2, 9, 1], [1, 5, 8, 6, 4, 0, 3, 2, 7, 9], [2, 6, 7, 1, 4, 8, 0, 3, 9, 5], [6, 2, 5, 8, 1, 7, 9, 4, 3, 0], [4, 7, 8, 1, 3, 2, 6, 9, 5, 0]]

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
