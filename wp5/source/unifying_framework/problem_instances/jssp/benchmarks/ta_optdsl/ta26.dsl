# Job Shop Scheduling instance: ta26
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20593

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[93, 4, 61, 13, 33, 59, 57, 52, 7, 7, 47, 58, 60, 84, 7, 74, 45, 46, 83, 56], [97, 48, 18, 36, 64, 15, 94, 20, 37, 74, 42, 73, 13, 96, 15, 69, 71, 6, 26, 5], [68, 28, 78, 2, 47, 71, 25, 89, 87, 79, 92, 94, 81, 94, 67, 14, 26, 36, 53, 28], [9, 53, 67, 30, 66, 16, 52, 4, 47, 20, 99, 10, 9, 54, 29, 65, 55, 33, 10, 69], [48, 85, 76, 95, 81, 42, 69, 91, 14, 60, 33, 74, 36, 14, 95, 77, 17, 37, 64, 68], [57, 74, 22, 86, 26, 22, 26, 53, 36, 34, 58, 83, 16, 71, 89, 68, 53, 80, 1, 79], [11, 98, 4, 18, 84, 16, 26, 83, 54, 88, 41, 16, 17, 55, 62, 67, 61, 31, 3, 54], [57, 70, 41, 71, 15, 54, 16, 99, 71, 86, 27, 9, 16, 14, 95, 7, 83, 46, 46, 40], [42, 62, 75, 55, 41, 53, 68, 95, 30, 54, 84, 57, 24, 55, 28, 88, 3, 83, 11, 23], [68, 33, 77, 92, 35, 21, 89, 29, 49, 53, 64, 75, 33, 91, 63, 4, 58, 78, 47, 18], [87, 56, 25, 15, 88, 41, 28, 43, 25, 55, 49, 77, 52, 55, 68, 23, 80, 86, 75, 94], [9, 76, 9, 83, 70, 46, 70, 19, 49, 27, 29, 8, 38, 70, 77, 10, 62, 68, 67, 40], [72, 78, 22, 11, 88, 43, 21, 36, 46, 67, 53, 17, 12, 98, 60, 22, 82, 98, 97, 79], [69, 77, 33, 12, 54, 43, 31, 60, 51, 65, 3, 44, 77, 32, 35, 98, 18, 31, 40, 10], [63, 20, 50, 77, 2, 72, 67, 95, 84, 82, 42, 39, 86, 50, 81, 89, 40, 42, 45, 44], [18, 71, 13, 40, 62, 60, 88, 69, 92, 80, 89, 86, 89, 6, 11, 56, 75, 66, 46, 75], [70, 83, 53, 66, 70, 43, 94, 57, 51, 83, 80, 22, 3, 82, 96, 16, 60, 94, 46, 38], [24, 43, 44, 88, 90, 6, 27, 91, 72, 3, 86, 71, 9, 41, 37, 80, 84, 16, 36, 28], [68, 27, 61, 17, 14, 63, 66, 43, 10, 74, 46, 27, 46, 33, 89, 5, 10, 64, 67, 95], [83, 51, 99, 24, 97, 37, 31, 77, 44, 35, 34, 29, 15, 88, 56, 98, 39, 50, 23, 88]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[10, 2, 9, 3, 7, 4, 18, 12, 6, 14, 15, 0, 5, 17, 8, 13, 19, 11, 16, 1], [0, 14, 2, 11, 8, 6, 7, 15, 12, 18, 1, 16, 13, 19, 10, 5, 4, 3, 17, 9], [8, 7, 1, 12, 4, 18, 14, 2, 15, 10, 11, 16, 0, 17, 9, 5, 13, 19, 6, 3], [10, 15, 0, 6, 18, 16, 9, 2, 19, 5, 11, 13, 8, 7, 4, 17, 12, 1, 3, 14], [10, 18, 16, 4, 5, 9, 8, 3, 12, 14, 17, 1, 0, 11, 2, 19, 15, 13, 7, 6], [3, 12, 9, 11, 19, 14, 2, 1, 10, 13, 5, 8, 7, 17, 16, 18, 0, 15, 4, 6], [2, 7, 6, 19, 5, 9, 11, 16, 10, 8, 1, 18, 4, 0, 13, 3, 15, 14, 12, 17], [12, 7, 18, 19, 5, 10, 8, 14, 11, 17, 0, 9, 15, 6, 1, 4, 3, 2, 16, 13], [8, 12, 7, 4, 5, 10, 3, 9, 0, 2, 13, 11, 1, 19, 14, 16, 17, 15, 18, 6], [17, 14, 5, 10, 13, 11, 9, 4, 2, 7, 0, 3, 6, 8, 18, 1, 15, 16, 19, 12], [2, 17, 9, 14, 1, 7, 15, 3, 4, 6, 5, 0, 18, 11, 10, 12, 16, 8, 19, 13], [19, 10, 9, 4, 1, 7, 18, 2, 15, 11, 3, 8, 13, 16, 6, 12, 17, 5, 14, 0], [0, 16, 1, 12, 17, 13, 8, 19, 4, 3, 7, 9, 18, 15, 10, 6, 2, 11, 5, 14], [7, 12, 13, 8, 17, 9, 16, 10, 6, 3, 14, 4, 11, 19, 5, 1, 18, 15, 0, 2], [5, 10, 1, 4, 2, 6, 14, 7, 11, 18, 9, 13, 15, 3, 0, 19, 17, 16, 12, 8], [4, 13, 18, 3, 19, 10, 14, 2, 12, 1, 7, 11, 5, 8, 15, 6, 9, 0, 16, 17], [8, 15, 16, 19, 5, 6, 12, 2, 10, 14, 0, 3, 9, 13, 1, 4, 11, 17, 18, 7], [5, 19, 11, 12, 6, 3, 4, 8, 1, 17, 18, 2, 13, 14, 15, 16, 10, 7, 0, 9], [7, 1, 10, 18, 14, 16, 5, 13, 4, 19, 2, 6, 0, 12, 11, 15, 3, 17, 8, 9], [0, 9, 16, 4, 2, 7, 15, 13, 1, 6, 19, 3, 10, 8, 11, 5, 18, 12, 17, 14]]

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
