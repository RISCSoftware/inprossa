# Job Shop Scheduling instance: orb09
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5181

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[36, 96, 86, 7, 20, 9, 39, 79, 82, 24], [16, 24, 87, 67, 16, 63, 49, 92, 95, 62], [65, 9, 48, 67, 66, 49, 71, 5, 70, 96], [50, 31, 83, 34, 6, 98, 93, 97, 13, 30], [99, 66, 75, 90, 81, 7, 40, 68, 78, 55], [5, 42, 10, 39, 51, 11, 50, 20, 30, 39], [38, 43, 89, 68, 37, 89, 53, 77, 86, 32], [19, 41, 52, 68, 37, 72, 31, 7, 10, 11], [83, 21, 74, 23, 74, 29, 89, 87, 58, 23], [44, 65, 57, 58, 69, 69, 89, 13, 60, 50]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 8, 3, 5, 2, 1, 9, 6, 7, 4], [0, 6, 1, 3, 8, 2, 5, 4, 7, 9], [0, 1, 4, 8, 5, 7, 6, 9, 3, 2], [0, 5, 9, 8, 7, 4, 3, 2, 1, 6], [1, 5, 0, 9, 2, 8, 3, 6, 7, 4], [0, 3, 8, 7, 9, 2, 4, 6, 1, 5], [0, 9, 4, 1, 5, 7, 2, 6, 3, 8], [0, 1, 9, 7, 8, 6, 4, 5, 2, 3], [0, 2, 4, 9, 1, 5, 8, 3, 6, 7]]

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
