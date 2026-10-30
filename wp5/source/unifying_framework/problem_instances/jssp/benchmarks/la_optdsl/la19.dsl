# Job Shop Scheduling instance: la19
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5346

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 58, 44, 5, 97, 58, 89, 84, 77, 96], [77, 87, 81, 85, 15, 39, 21, 31, 57, 73], [40, 49, 48, 70, 10, 71, 22, 80, 34, 82], [55, 91, 17, 7, 11, 75, 72, 62, 47, 35], [64, 90, 94, 75, 12, 50, 71, 67, 15, 20], [52, 57, 29, 68, 58, 93, 93, 70, 77, 7], [95, 63, 82, 27, 26, 6, 87, 56, 48, 36], [36, 8, 36, 76, 30, 15, 84, 76, 41, 78], [75, 78, 81, 13, 54, 88, 82, 13, 29, 40], [52, 26, 6, 6, 54, 82, 64, 32, 54, 88]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 3, 5, 4, 0, 7, 8, 9, 1, 6], [4, 7, 1, 8, 0, 3, 2, 5, 9, 6], [9, 6, 4, 3, 1, 0, 8, 2, 7, 5], [1, 2, 7, 5, 8, 4, 3, 6, 9, 0], [6, 1, 3, 0, 2, 8, 4, 7, 9, 5], [7, 5, 8, 2, 4, 6, 3, 1, 9, 0], [6, 1, 4, 5, 2, 3, 7, 8, 9, 0], [0, 5, 8, 9, 3, 6, 4, 7, 2, 1], [5, 2, 3, 6, 4, 7, 8, 9, 1, 0], [9, 4, 6, 7, 0, 2, 8, 5, 3, 1]]

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
