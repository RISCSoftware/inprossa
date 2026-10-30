# Job Shop Scheduling instance: swv02
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10001

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[22, 58, 16, 53, 24, 92, 43, 63, 9, 57], [66, 48, 24, 6, 14, 99, 73, 2, 19, 85], [63, 14, 90, 31, 100, 27, 51, 33, 1, 15], [12, 96, 98, 84, 52, 45, 74, 49, 93, 60], [54, 30, 28, 8, 39, 9, 75, 41, 57, 19], [8, 13, 89, 94, 37, 71, 63, 97, 36, 24], [65, 25, 69, 90, 15, 86, 56, 52, 83, 91], [68, 99, 14, 59, 41, 15, 48, 4, 13, 55], [16, 51, 17, 54, 36, 50, 68, 98, 45, 82], [11, 75, 93, 51, 55, 55, 61, 19, 24, 40], [73, 51, 38, 59, 56, 7, 99, 72, 29, 53], [33, 88, 88, 68, 50, 47, 26, 68, 52, 74], [45, 57, 3, 42, 28, 14, 44, 38, 22, 31], [73, 9, 49, 89, 12, 11, 10, 41, 15, 37], [25, 92, 97, 76, 100, 8, 58, 51, 65, 92], [54, 47, 45, 85, 50, 32, 99, 56, 87, 39], [70, 85, 58, 33, 25, 44, 52, 65, 5, 20], [66, 22, 5, 45, 60, 14, 73, 61, 44, 60], [97, 4, 31, 43, 64, 10, 100, 93, 51, 47], [62, 56, 34, 9, 87, 66, 86, 56, 95, 42]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 1, 0, 4, 3, 8, 9, 7, 5, 6], [3, 1, 4, 0, 2, 7, 9, 6, 8, 5], [4, 2, 0, 1, 3, 5, 9, 8, 6, 7], [2, 3, 4, 0, 1, 9, 6, 8, 5, 7], [4, 0, 2, 3, 1, 8, 6, 5, 7, 9], [3, 0, 2, 1, 4, 8, 6, 9, 5, 7], [3, 2, 1, 4, 0, 7, 6, 9, 8, 5], [3, 1, 4, 0, 2, 7, 9, 6, 8, 5], [4, 2, 1, 0, 3, 8, 5, 7, 6, 9], [1, 0, 4, 2, 3, 6, 9, 7, 8, 5], [4, 0, 3, 2, 1, 6, 8, 9, 5, 7], [3, 4, 1, 2, 0, 5, 8, 6, 9, 7], [2, 3, 0, 1, 4, 5, 8, 9, 6, 7], [3, 0, 4, 1, 2, 5, 8, 7, 9, 6], [3, 2, 4, 1, 0, 5, 9, 7, 6, 8], [4, 0, 3, 1, 2, 6, 9, 5, 8, 7], [0, 2, 3, 1, 4, 8, 7, 9, 6, 5], [1, 3, 4, 0, 2, 7, 6, 9, 5, 8], [4, 0, 2, 1, 3, 9, 7, 6, 5, 8], [3, 4, 2, 0, 1, 5, 8, 7, 9, 6]]

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
