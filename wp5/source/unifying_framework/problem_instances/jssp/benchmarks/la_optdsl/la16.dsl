# Job Shop Scheduling instance: la16
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5351

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[53, 21, 34, 55, 21, 95, 71, 26, 52, 16], [12, 42, 31, 39, 55, 98, 77, 66, 77, 79], [83, 19, 64, 34, 92, 37, 54, 43, 62, 79], [93, 87, 87, 69, 60, 77, 41, 38, 24, 83], [44, 49, 98, 17, 96, 25, 75, 43, 79, 77], [95, 7, 35, 76, 61, 28, 9, 95, 35, 10], [46, 91, 59, 16, 28, 59, 52, 27, 50, 43], [87, 45, 39, 41, 20, 9, 54, 71, 14, 43], [78, 28, 37, 26, 33, 33, 89, 8, 66, 42], [69, 74, 94, 27, 96, 84, 78, 45, 69, 81]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 6, 9, 8, 7, 2, 0, 4, 3, 5], [4, 2, 5, 9, 0, 7, 1, 8, 6, 3], [3, 2, 8, 1, 4, 9, 7, 6, 0, 5], [1, 3, 2, 7, 8, 9, 6, 0, 5, 4], [2, 0, 5, 6, 7, 1, 4, 9, 3, 8], [2, 3, 5, 9, 4, 6, 0, 8, 1, 7], [3, 2, 0, 1, 9, 8, 6, 5, 4, 7], [1, 0, 3, 4, 6, 9, 8, 5, 2, 7], [4, 2, 8, 5, 3, 7, 1, 6, 9, 0], [8, 9, 2, 4, 3, 0, 7, 6, 1, 5]]

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
