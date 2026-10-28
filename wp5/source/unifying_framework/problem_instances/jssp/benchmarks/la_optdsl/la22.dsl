# Job Shop Scheduling instance: la22
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 10
MAX_TIME : int = 7322

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[12, 7, 94, 92, 87, 91, 19, 21, 11, 66], [75, 14, 20, 13, 7, 16, 77, 95, 7, 66], [15, 45, 34, 6, 76, 89, 53, 20, 77, 88], [52, 88, 74, 27, 62, 9, 88, 52, 69, 98], [62, 52, 61, 90, 88, 9, 15, 54, 59, 5], [41, 50, 23, 53, 38, 78, 71, 91, 68, 72], [45, 6, 25, 95, 23, 52, 66, 17, 30, 36], [71, 8, 95, 76, 65, 88, 28, 65, 85, 27], [73, 37, 9, 51, 28, 90, 55, 51, 86, 37], [16, 25, 15, 39, 46, 24, 83, 53, 82, 44], [87, 72, 66, 60, 48, 95, 54, 39, 35, 5], [97, 46, 21, 20, 59, 55, 34, 37, 19, 46], [28, 24, 73, 25, 45, 23, 78, 83, 28, 5], [53, 37, 12, 71, 38, 29, 55, 87, 33, 12], [48, 40, 49, 83, 90, 7, 23, 65, 17, 27]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 5, 4, 2, 7, 3, 1, 0, 8, 6], [3, 2, 4, 1, 9, 0, 6, 5, 7, 8], [8, 7, 2, 0, 9, 5, 6, 3, 1, 4], [3, 2, 6, 4, 7, 8, 5, 9, 0, 1], [4, 6, 1, 2, 7, 0, 8, 5, 3, 9], [6, 0, 4, 3, 7, 8, 1, 5, 2, 9], [3, 9, 6, 5, 0, 8, 4, 2, 7, 1], [4, 1, 8, 0, 7, 6, 5, 3, 9, 2], [9, 1, 4, 3, 8, 2, 6, 0, 7, 5], [3, 2, 6, 9, 7, 0, 4, 5, 1, 8], [1, 4, 0, 2, 9, 6, 7, 8, 5, 3], [1, 3, 0, 2, 9, 7, 8, 4, 6, 5], [5, 3, 6, 1, 0, 7, 8, 9, 2, 4], [1, 0, 7, 4, 3, 5, 9, 8, 6, 2], [4, 8, 2, 3, 1, 6, 7, 9, 5, 0]]

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
