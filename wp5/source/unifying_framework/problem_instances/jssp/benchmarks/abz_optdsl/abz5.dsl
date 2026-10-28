# Job Shop Scheduling instance: abz5
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 7773

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[86, 67, 89, 92, 88, 99, 94, 99, 68, 77], [92, 82, 94, 50, 75, 72, 69, 94, 66, 63], [83, 65, 55, 77, 85, 85, 64, 78, 61, 83], [76, 61, 68, 54, 99, 66, 75, 94, 67, 63], [99, 86, 67, 69, 88, 68, 95, 67, 95, 82], [88, 99, 80, 79, 81, 64, 66, 69, 80, 62], [95, 86, 66, 96, 97, 99, 52, 50, 97, 71], [62, 71, 51, 82, 98, 94, 73, 85, 95, 79], [94, 66, 90, 81, 76, 58, 71, 85, 93, 97], [59, 82, 96, 50, 81, 59, 58, 56, 67, 96]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 8, 6, 5, 1, 2, 9, 7, 0, 3], [5, 3, 6, 4, 2, 8, 0, 1, 7, 9], [9, 8, 0, 1, 6, 5, 7, 4, 2, 3], [7, 2, 1, 4, 3, 6, 5, 0, 9, 8], [3, 4, 9, 8, 0, 2, 6, 5, 7, 1], [1, 4, 5, 6, 8, 2, 7, 9, 3, 0], [7, 1, 4, 3, 0, 8, 2, 5, 6, 9], [4, 6, 3, 2, 1, 5, 7, 0, 8, 9], [0, 6, 3, 7, 1, 2, 4, 5, 8, 9], [3, 0, 1, 8, 7, 9, 6, 4, 5, 2]]

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
