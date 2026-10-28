# Job Shop Scheduling instance: orb06
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5614

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[99, 74, 49, 67, 17, 7, 9, 39, 35, 49], [49, 62, 92, 67, 82, 84, 30, 42, 45, 71], [26, 82, 98, 33, 16, 83, 64, 65, 77, 36], [41, 62, 55, 94, 73, 46, 51, 64, 46, 31], [26, 68, 6, 46, 25, 50, 84, 88, 13, 98], [24, 48, 91, 55, 72, 12, 80, 84, 99, 91], [9, 58, 16, 13, 23, 36, 89, 85, 71, 41], [41, 11, 54, 38, 53, 74, 46, 41, 65, 88], [90, 50, 53, 57, 40, 80, 91, 7, 47, 60], [59, 19, 45, 99, 75, 95, 71, 77, 81, 94]]
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
