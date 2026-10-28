# Job Shop Scheduling instance: ta29
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20982

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[91, 70, 79, 49, 5, 9, 25, 36, 81, 45, 84, 80, 24, 83, 39, 89, 53, 9, 48, 50], [97, 65, 68, 91, 75, 6, 32, 23, 74, 42, 51, 13, 21, 31, 62, 66, 44, 96, 26, 48], [64, 78, 72, 26, 4, 83, 31, 59, 65, 70, 49, 76, 82, 68, 35, 16, 55, 92, 75, 64], [31, 55, 8, 20, 94, 85, 37, 20, 58, 49, 65, 32, 65, 50, 30, 94, 31, 37, 47, 22], [11, 93, 94, 95, 7, 79, 98, 38, 79, 9, 69, 17, 21, 81, 81, 38, 68, 65, 2, 76], [74, 69, 78, 57, 75, 64, 87, 7, 66, 73, 8, 26, 50, 93, 80, 94, 85, 77, 29, 29], [3, 63, 71, 59, 31, 2, 41, 67, 59, 25, 49, 89, 91, 33, 54, 15, 44, 79, 82, 50], [8, 18, 21, 33, 4, 72, 54, 44, 56, 57, 20, 23, 43, 93, 20, 18, 65, 93, 23, 18], [51, 69, 35, 12, 25, 89, 35, 34, 58, 54, 92, 4, 25, 74, 78, 33, 81, 72, 10, 89], [33, 75, 67, 65, 66, 93, 77, 22, 87, 98, 45, 33, 75, 44, 67, 37, 66, 44, 49, 84], [17, 54, 24, 34, 69, 92, 47, 80, 29, 72, 68, 84, 34, 92, 96, 75, 94, 26, 25, 84], [66, 22, 72, 75, 81, 74, 97, 30, 67, 71, 79, 99, 43, 44, 75, 50, 11, 61, 47, 54], [23, 13, 19, 66, 99, 91, 90, 49, 58, 70, 26, 19, 45, 75, 82, 38, 35, 82, 92, 72], [33, 39, 18, 44, 40, 69, 91, 9, 73, 10, 1, 26, 33, 74, 89, 11, 41, 82, 96, 2], [25, 21, 98, 4, 85, 14, 94, 2, 1, 67, 32, 72, 25, 84, 57, 92, 41, 42, 89, 91], [16, 98, 13, 2, 41, 97, 43, 29, 19, 22, 22, 34, 9, 87, 79, 91, 52, 13, 73, 50], [98, 29, 36, 92, 23, 25, 17, 63, 41, 62, 5, 90, 42, 8, 91, 66, 19, 61, 47, 31], [40, 71, 37, 75, 37, 40, 32, 52, 69, 78, 69, 79, 48, 81, 93, 61, 10, 7, 61, 4], [81, 10, 61, 31, 16, 68, 72, 7, 96, 78, 27, 69, 38, 40, 32, 68, 90, 84, 42, 52], [42, 50, 75, 90, 91, 87, 10, 45, 17, 69, 62, 2, 9, 32, 7, 44, 88, 78, 93, 21]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[10, 9, 16, 18, 17, 5, 14, 2, 13, 19, 12, 3, 8, 4, 1, 15, 0, 6, 11, 7], [4, 19, 5, 6, 2, 7, 16, 12, 9, 11, 8, 13, 14, 3, 1, 15, 18, 17, 0, 10], [10, 3, 14, 0, 16, 1, 2, 5, 7, 15, 17, 13, 19, 4, 11, 12, 9, 18, 8, 6], [1, 8, 17, 11, 0, 10, 12, 5, 13, 4, 6, 3, 15, 7, 16, 14, 9, 2, 19, 18], [13, 16, 18, 10, 15, 4, 14, 5, 19, 2, 17, 0, 6, 7, 3, 1, 9, 12, 11, 8], [5, 7, 15, 19, 17, 4, 12, 2, 3, 18, 8, 13, 0, 9, 14, 10, 11, 6, 1, 16], [10, 3, 12, 8, 9, 16, 19, 6, 13, 11, 17, 0, 14, 18, 1, 4, 15, 5, 7, 2], [4, 14, 18, 3, 16, 7, 9, 10, 17, 11, 15, 0, 5, 6, 19, 13, 12, 1, 8, 2], [8, 4, 7, 5, 9, 19, 3, 0, 13, 14, 11, 17, 16, 10, 1, 2, 12, 6, 18, 15], [11, 19, 12, 4, 18, 6, 8, 13, 15, 2, 0, 1, 3, 17, 16, 10, 5, 9, 7, 14], [0, 17, 1, 18, 13, 12, 6, 7, 2, 5, 15, 10, 11, 9, 19, 16, 4, 14, 3, 8], [0, 10, 5, 8, 2, 1, 15, 7, 18, 3, 12, 13, 9, 17, 19, 11, 16, 6, 14, 4], [16, 13, 4, 19, 18, 6, 10, 5, 9, 17, 1, 12, 14, 8, 15, 11, 3, 0, 7, 2], [17, 13, 4, 12, 7, 0, 11, 3, 2, 8, 16, 18, 1, 6, 14, 15, 10, 19, 5, 9], [12, 10, 16, 5, 9, 0, 6, 18, 1, 2, 15, 11, 14, 3, 8, 7, 13, 19, 17, 4], [7, 1, 4, 13, 16, 12, 9, 3, 14, 18, 0, 10, 5, 17, 8, 2, 19, 6, 15, 11], [14, 8, 18, 17, 15, 19, 3, 12, 16, 0, 2, 1, 13, 5, 10, 11, 9, 7, 6, 4], [8, 9, 15, 7, 5, 1, 0, 18, 14, 2, 6, 12, 17, 4, 10, 19, 11, 13, 16, 3], [16, 4, 15, 14, 8, 7, 18, 19, 12, 5, 6, 9, 1, 2, 13, 3, 0, 11, 17, 10], [4, 8, 2, 14, 15, 6, 13, 17, 12, 9, 7, 5, 3, 1, 0, 11, 19, 10, 18, 16]]

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
