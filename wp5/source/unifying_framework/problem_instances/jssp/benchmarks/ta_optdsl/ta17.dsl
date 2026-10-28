# Job Shop Scheduling instance: ta17
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15544

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[33, 29, 39, 92, 86, 36, 40, 3, 57, 55, 80, 95, 72, 31, 72], [20, 68, 71, 97, 95, 35, 49, 56, 52, 56, 83, 90, 94, 58, 32], [31, 85, 63, 5, 24, 16, 23, 89, 98, 97, 5, 65, 75, 50, 19], [94, 58, 63, 42, 36, 80, 38, 41, 73, 3, 34, 75, 79, 8, 60], [54, 94, 71, 7, 86, 86, 26, 59, 69, 65, 43, 99, 35, 86, 99], [22, 58, 74, 70, 70, 82, 30, 43, 37, 53, 50, 9, 98, 90, 94], [31, 61, 17, 64, 97, 5, 39, 63, 71, 15, 2, 67, 65, 68, 93], [90, 62, 92, 32, 81, 36, 65, 10, 21, 5, 5, 63, 49, 7, 85], [77, 9, 52, 69, 63, 37, 4, 66, 67, 82, 49, 24, 62, 66, 31], [73, 73, 18, 87, 73, 43, 8, 20, 13, 13, 64, 69, 97, 67, 28], [13, 42, 55, 58, 72, 30, 18, 17, 72, 80, 85, 66, 17, 64, 28], [82, 56, 49, 23, 66, 79, 30, 72, 57, 36, 27, 17, 4, 87, 87], [16, 53, 43, 69, 49, 6, 18, 78, 78, 62, 62, 20, 66, 17, 4], [85, 5, 12, 57, 55, 61, 23, 69, 59, 34, 36, 89, 16, 82, 50], [85, 96, 19, 88, 52, 9, 9, 22, 29, 29, 71, 68, 10, 65, 3], [73, 1, 34, 15, 7, 40, 7, 51, 63, 43, 85, 91, 23, 73, 34], [40, 32, 46, 11, 49, 68, 62, 51, 18, 42, 71, 99, 97, 4, 92], [43, 11, 39, 47, 12, 93, 56, 43, 84, 23, 77, 22, 46, 82, 1], [63, 26, 38, 72, 84, 47, 92, 98, 78, 32, 14, 95, 59, 84, 70], [87, 34, 31, 30, 9, 89, 35, 53, 52, 73, 80, 34, 97, 72, 68]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 8, 11, 0, 14, 13, 9, 5, 3, 12, 10, 2, 7, 4, 1], [0, 9, 1, 6, 5, 13, 11, 8, 3, 4, 12, 14, 7, 2, 10], [8, 3, 9, 1, 0, 10, 5, 14, 12, 13, 6, 2, 7, 11, 4], [5, 1, 7, 10, 0, 2, 13, 11, 14, 3, 6, 9, 8, 12, 4], [2, 9, 6, 7, 0, 8, 13, 5, 10, 3, 12, 4, 14, 1, 11], [5, 3, 9, 2, 1, 4, 10, 8, 13, 0, 11, 12, 6, 14, 7], [8, 7, 12, 9, 6, 14, 4, 11, 5, 1, 3, 13, 10, 0, 2], [13, 7, 6, 11, 2, 0, 14, 4, 3, 1, 10, 8, 9, 12, 5], [1, 14, 0, 10, 11, 8, 7, 5, 9, 3, 4, 6, 12, 2, 13], [13, 1, 3, 14, 5, 9, 2, 0, 11, 7, 12, 4, 10, 6, 8], [10, 5, 9, 13, 6, 8, 11, 4, 14, 0, 7, 2, 12, 1, 3], [13, 9, 14, 10, 3, 7, 2, 5, 6, 11, 8, 1, 0, 12, 4], [5, 9, 7, 8, 10, 13, 2, 6, 1, 0, 12, 11, 3, 4, 14], [9, 11, 6, 7, 2, 8, 14, 3, 0, 12, 4, 13, 5, 1, 10], [10, 2, 1, 5, 0, 3, 14, 11, 4, 8, 9, 7, 12, 6, 13], [12, 14, 0, 2, 10, 5, 13, 3, 7, 11, 1, 9, 6, 8, 4], [8, 6, 12, 4, 13, 10, 5, 7, 9, 0, 1, 14, 3, 2, 11], [14, 5, 12, 4, 1, 13, 6, 2, 8, 7, 10, 11, 9, 3, 0], [7, 2, 6, 3, 8, 14, 5, 9, 4, 13, 0, 11, 12, 1, 10], [10, 7, 13, 4, 5, 3, 6, 1, 8, 0, 12, 11, 9, 14, 2]]

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
