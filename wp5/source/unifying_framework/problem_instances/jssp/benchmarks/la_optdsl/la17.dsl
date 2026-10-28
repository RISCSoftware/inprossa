# Job Shop Scheduling instance: la17
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 4676

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[82, 23, 45, 38, 18, 84, 29, 21, 50, 41], [52, 52, 38, 54, 54, 16, 62, 74, 57, 37], [81, 61, 30, 68, 79, 57, 89, 89, 11, 81], [91, 66, 20, 33, 32, 20, 84, 55, 8, 24], [7, 39, 64, 54, 19, 56, 83, 8, 7, 40], [63, 6, 64, 91, 74, 40, 42, 98, 61, 15], [26, 80, 87, 75, 75, 6, 44, 39, 24, 22], [12, 15, 20, 79, 80, 8, 61, 43, 26, 22], [63, 36, 62, 96, 22, 40, 33, 10, 18, 5], [89, 96, 64, 95, 8, 64, 38, 18, 15, 23]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 7, 9, 2, 3, 8, 5, 6, 1, 0], [8, 5, 1, 7, 2, 3, 6, 9, 4, 0], [2, 4, 3, 1, 8, 6, 7, 0, 9, 5], [0, 8, 3, 7, 5, 2, 4, 6, 1, 9], [9, 0, 4, 8, 6, 2, 5, 3, 7, 1], [3, 2, 5, 0, 7, 4, 8, 1, 6, 9], [1, 7, 8, 3, 4, 5, 6, 0, 2, 9], [1, 7, 2, 0, 8, 6, 3, 9, 5, 4], [2, 3, 4, 9, 0, 6, 7, 8, 1, 5], [1, 0, 5, 3, 9, 7, 8, 2, 6, 4]]

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
