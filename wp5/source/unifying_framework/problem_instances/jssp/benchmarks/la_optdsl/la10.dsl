# Job Shop Scheduling instance: la10
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 5
MAX_TIME : int = 4020

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 58, 44, 5, 58], [97, 89, 84, 77, 96], [77, 87, 81, 85, 39], [15, 21, 31, 57, 73], [40, 49, 48, 70, 71], [10, 22, 80, 34, 82], [55, 91, 17, 7, 75], [11, 72, 62, 47, 35], [64, 90, 94, 75, 50], [12, 71, 67, 15, 20], [52, 57, 29, 68, 93], [58, 93, 70, 77, 7], [95, 63, 82, 27, 6], [26, 87, 56, 48, 36], [36, 8, 36, 76, 15]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 2, 3, 0, 4], [1, 0, 4, 3, 2], [0, 1, 2, 4, 3], [3, 1, 2, 0, 4], [2, 0, 1, 3, 4], [3, 4, 2, 0, 1], [1, 4, 0, 2, 3], [2, 3, 1, 4, 0], [0, 3, 4, 1, 2], [2, 4, 3, 0, 1], [0, 4, 3, 2, 1], [2, 0, 1, 4, 3], [3, 2, 1, 4, 0], [1, 2, 4, 0, 3], [3, 2, 0, 4, 1]]

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
