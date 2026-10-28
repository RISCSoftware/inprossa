# Job Shop Scheduling instance: orb08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 4560

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[55, 74, 45, 23, 76, 19, 18, 61, 44, 11], [63, 43, 51, 18, 42, 52, 29, 11, 88, 29], [47, 31, 88, 62, 10, 60, 58, 29, 52, 92], [55, 71, 16, 9, 55, 54, 83, 49, 57, 7], [41, 7, 46, 94, 92, 34, 79, 18, 8, 38], [5, 25, 14, 94, 89, 20, 94, 39, 44, 23], [40, 24, 21, 94, 47, 97, 71, 89, 15, 75], [28, 5, 7, 72, 74, 61, 97, 9, 53, 32], [34, 94, 52, 37, 6, 5, 6, 56, 16, 41], [77, 29, 74, 82, 10, 15, 21, 51, 65, 37]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 1, 2, 3, 4, 7, 6, 5, 9, 8], [2, 1, 0, 4, 3, 5, 6, 7, 8, 9], [2, 1, 0, 4, 3, 7, 6, 5, 9, 8], [1, 0, 4, 3, 2, 6, 5, 9, 8, 7], [1, 0, 4, 3, 2, 6, 5, 9, 8, 7], [1, 2, 4, 0, 3, 6, 7, 9, 5, 8], [1, 2, 4, 0, 3, 5, 7, 8, 9, 6], [0, 2, 3, 4, 1, 6, 7, 9, 5, 8], [0, 2, 3, 4, 1, 5, 7, 8, 9, 6]]

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
