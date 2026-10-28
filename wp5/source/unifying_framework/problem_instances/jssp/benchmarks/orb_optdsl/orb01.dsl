# Job Shop Scheduling instance: orb01
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5409

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[72, 64, 55, 31, 53, 95, 11, 52, 6, 84], [61, 49, 78, 27, 88, 83, 74, 29, 91, 87], [86, 35, 37, 32, 48, 18, 91, 52, 30, 60], [8, 82, 33, 99, 27, 9, 74, 59, 98, 20], [94, 50, 5, 62, 55, 43, 36, 48, 36, 47], [53, 68, 7, 12, 28, 7, 30, 45, 87, 70], [99, 14, 29, 96, 34, 7, 76, 14, 57, 76], [19, 84, 90, 87, 51, 45, 58, 81, 96, 84], [38, 99, 97, 40, 93, 96, 32, 13, 45, 64], [60, 85, 44, 5, 34, 47, 74, 95, 29, 51]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 3, 4, 2, 1, 5, 8, 6, 7, 9], [0, 3, 1, 2, 5, 4, 6, 7, 9, 8], [0, 1, 4, 3, 6, 5, 2, 9, 7, 8], [1, 0, 5, 3, 4, 7, 2, 8, 9, 6], [0, 6, 2, 3, 1, 8, 4, 9, 7, 5], [2, 3, 0, 1, 4, 7, 5, 6, 8, 9], [2, 0, 3, 4, 1, 5, 9, 6, 7, 8], [2, 1, 4, 0, 7, 5, 3, 9, 6, 8], [2, 0, 8, 3, 6, 1, 4, 7, 9, 5]]

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
