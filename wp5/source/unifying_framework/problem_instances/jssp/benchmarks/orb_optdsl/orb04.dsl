# Job Shop Scheduling instance: orb04
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5628

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 10, 35, 44, 15, 92, 70, 89, 50, 12], [63, 39, 88, 80, 69, 22, 27, 74, 39, 85], [52, 33, 68, 68, 34, 25, 22, 24, 27, 84], [31, 85, 25, 73, 55, 58, 69, 11, 80, 56], [97, 39, 80, 98, 90, 98, 40, 77, 47, 87], [44, 97, 44, 78, 81, 68, 90, 33, 85, 67], [34, 7, 36, 76, 33, 44, 98, 61, 48, 11], [44, 51, 95, 86, 85, 58, 48, 79, 73, 5], [24, 63, 93, 84, 63, 17, 74, 77, 73, 48], [51, 46, 5, 72, 40, 58, 29, 94, 54, 60]]
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
