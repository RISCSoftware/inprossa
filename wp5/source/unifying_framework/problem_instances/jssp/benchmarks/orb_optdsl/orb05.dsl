# Job Shop Scheduling instance: orb05
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 4908

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[48, 65, 90, 59, 10, 71, 13, 76, 93, 11], [84, 49, 43, 39, 10, 56, 26, 73, 52, 76], [21, 6, 14, 27, 68, 74, 66, 26, 44, 28], [18, 58, 46, 62, 6, 60, 25, 28, 80, 30], [78, 47, 87, 78, 29, 16, 57, 29, 39, 73], [98, 20, 26, 12, 15, 67, 66, 64, 51, 66], [17, 88, 15, 18, 83, 24, 45, 75, 23, 76], [28, 66, 29, 30, 31, 93, 16, 80, 83, 56], [34, 75, 82, 41, 16, 62, 91, 35, 69, 79], [5, 19, 20, 12, 94, 60, 99, 31, 96, 63]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 8, 0, 7, 6, 5, 3, 2, 4, 1], [8, 9, 0, 7, 5, 4, 6, 2, 3, 1], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [0, 1, 3, 2, 6, 4, 5, 7, 8, 9], [0, 1, 7, 5, 4, 6, 3, 2, 8, 9], [9, 8, 3, 7, 5, 4, 6, 2, 1, 0], [8, 9, 6, 7, 5, 3, 4, 2, 1, 0], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [9, 8, 2, 4, 5, 3, 6, 7, 0, 1], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]

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
