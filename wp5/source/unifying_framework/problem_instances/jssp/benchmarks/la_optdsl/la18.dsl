# Job Shop Scheduling instance: la18
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5186

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[87, 72, 66, 60, 48, 95, 54, 39, 35, 5], [97, 46, 21, 20, 59, 55, 34, 37, 19, 46], [28, 24, 73, 25, 45, 23, 78, 83, 28, 5], [53, 37, 12, 71, 38, 29, 55, 87, 33, 12], [48, 40, 49, 83, 90, 7, 23, 65, 17, 27], [62, 66, 84, 85, 25, 19, 64, 46, 59, 13], [41, 73, 53, 80, 14, 88, 67, 57, 74, 47], [84, 78, 41, 84, 63, 64, 46, 26, 28, 52], [64, 11, 17, 10, 85, 73, 97, 67, 95, 38], [59, 65, 95, 93, 60, 46, 85, 43, 32, 85]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 0, 4, 3, 7, 8, 1, 5, 2, 9], [3, 9, 6, 5, 0, 8, 4, 2, 7, 1], [4, 1, 8, 0, 7, 6, 5, 3, 9, 2], [9, 1, 4, 3, 8, 2, 6, 0, 7, 5], [3, 2, 6, 9, 7, 0, 4, 5, 1, 8], [1, 4, 0, 2, 9, 6, 7, 8, 5, 3], [1, 3, 0, 2, 9, 7, 8, 4, 6, 5], [5, 3, 6, 1, 0, 7, 8, 9, 2, 4], [1, 0, 7, 4, 3, 5, 9, 8, 6, 2], [4, 8, 2, 3, 1, 6, 7, 9, 5, 0]]

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
