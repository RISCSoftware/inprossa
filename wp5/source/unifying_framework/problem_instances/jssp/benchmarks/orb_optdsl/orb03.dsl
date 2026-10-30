# Job Shop Scheduling instance: orb03
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5292

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[96, 69, 25, 5, 55, 15, 88, 11, 17, 82], [11, 48, 67, 38, 18, 92, 62, 24, 81, 96], [93, 63, 67, 25, 85, 72, 51, 81, 58, 15], [27, 35, 30, 44, 82, 49, 25, 92, 77, 28], [83, 53, 77, 26, 73, 92, 33, 38, 38, 99], [44, 20, 66, 88, 81, 91, 70, 96, 55, 37], [56, 21, 93, 34, 22, 29, 40, 53, 63, 46], [26, 32, 63, 17, 36, 85, 82, 15, 55, 16], [73, 99, 46, 89, 24, 19, 92, 7, 14, 51], [52, 23, 20, 70, 98, 15, 81, 81, 71, 24]]
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
