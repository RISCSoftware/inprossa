# Job Shop Scheduling instance: la13
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 5
MAX_TIME : int = 5186

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[87, 72, 66, 60, 95], [48, 54, 39, 35, 5], [97, 46, 21, 20, 55], [59, 34, 37, 19, 46], [28, 24, 73, 25, 23], [45, 78, 83, 28, 5], [53, 37, 12, 71, 29], [38, 55, 87, 33, 12], [48, 40, 49, 83, 7], [90, 23, 65, 17, 27], [62, 66, 84, 85, 19], [25, 64, 46, 59, 13], [41, 73, 53, 80, 88], [14, 67, 57, 74, 47], [84, 78, 41, 84, 64], [63, 46, 26, 28, 52], [64, 11, 17, 10, 73], [85, 97, 67, 95, 38], [59, 65, 95, 93, 46], [60, 85, 43, 32, 85]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 0, 1, 4, 2], [1, 0, 2, 3, 4], [3, 1, 0, 2, 4], [2, 0, 3, 1, 4], [2, 3, 1, 0, 4], [1, 3, 2, 0, 4], [3, 1, 2, 4, 0], [4, 3, 1, 2, 0], [0, 1, 2, 3, 4], [0, 4, 2, 3, 1], [0, 3, 1, 2, 4], [3, 2, 4, 1, 0], [2, 1, 3, 4, 0], [2, 4, 0, 1, 3], [2, 4, 3, 1, 0], [4, 3, 2, 0, 1], [1, 0, 3, 4, 2], [4, 3, 0, 1, 2], [3, 1, 2, 0, 4], [0, 1, 2, 4, 3]]

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
