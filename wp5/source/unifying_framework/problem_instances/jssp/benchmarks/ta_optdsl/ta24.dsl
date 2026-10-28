# Job Shop Scheduling instance: ta24
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 20
MAX_TIME : int = 20400

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[25, 30, 35, 18, 34, 67, 51, 52, 29, 43, 49, 38, 46, 20, 53, 92, 29, 98, 80, 96], [8, 68, 68, 3, 73, 89, 80, 64, 43, 68, 59, 30, 14, 15, 98, 63, 20, 88, 72, 41], [16, 6, 89, 90, 72, 25, 32, 69, 88, 63, 88, 92, 55, 51, 63, 7, 36, 83, 71, 18], [83, 86, 50, 35, 79, 69, 57, 40, 88, 43, 42, 28, 4, 73, 18, 37, 25, 82, 64, 58], [31, 13, 96, 50, 80, 76, 49, 38, 90, 36, 75, 72, 41, 66, 45, 2, 96, 29, 50, 66], [87, 65, 93, 15, 38, 55, 49, 31, 24, 89, 24, 6, 45, 75, 23, 44, 19, 16, 72, 75], [80, 58, 12, 22, 85, 93, 94, 54, 54, 10, 92, 99, 48, 79, 36, 34, 2, 4, 2, 33], [53, 16, 20, 60, 60, 68, 57, 11, 71, 54, 60, 36, 97, 2, 65, 59, 7, 19, 68, 42], [57, 92, 82, 62, 29, 32, 60, 19, 59, 12, 80, 16, 84, 91, 24, 43, 20, 82, 99, 20], [3, 82, 7, 78, 78, 85, 78, 53, 23, 76, 99, 80, 42, 30, 58, 6, 13, 62, 84, 22], [65, 94, 92, 7, 10, 33, 23, 87, 78, 88, 9, 94, 83, 88, 85, 35, 72, 6, 84, 18], [44, 52, 81, 9, 11, 39, 28, 25, 93, 43, 82, 69, 48, 75, 28, 44, 53, 67, 33, 67], [32, 25, 21, 41, 44, 36, 21, 72, 5, 96, 19, 6, 73, 46, 82, 61, 58, 24, 14, 30], [17, 97, 8, 26, 35, 87, 2, 40, 28, 65, 93, 42, 78, 10, 91, 77, 93, 56, 33, 64], [17, 79, 79, 24, 15, 22, 73, 64, 92, 59, 45, 39, 3, 65, 88, 73, 95, 38, 11, 96], [69, 83, 3, 28, 93, 42, 17, 17, 45, 51, 47, 7, 69, 40, 91, 83, 82, 43, 71, 59], [68, 80, 9, 67, 70, 30, 95, 34, 84, 62, 80, 69, 44, 72, 78, 37, 15, 39, 82, 32], [98, 4, 27, 37, 13, 73, 92, 99, 26, 12, 96, 70, 89, 35, 20, 8, 75, 83, 98, 68], [55, 65, 70, 35, 38, 35, 16, 97, 8, 1, 34, 58, 78, 75, 73, 1, 9, 38, 6, 51], [39, 64, 4, 27, 29, 90, 4, 20, 21, 6, 98, 32, 84, 36, 94, 41, 50, 34, 50, 49]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 18, 4, 15, 16, 19, 0, 10, 5, 14, 13, 7, 8, 6, 2, 11, 3, 9, 12, 17], [4, 2, 3, 14, 1, 0, 13, 17, 18, 16, 5, 10, 9, 15, 19, 11, 8, 6, 7, 12], [1, 16, 8, 18, 13, 14, 6, 0, 9, 15, 19, 3, 12, 5, 4, 11, 10, 7, 2, 17], [19, 3, 4, 9, 1, 2, 18, 8, 6, 16, 13, 14, 12, 5, 7, 11, 15, 10, 17, 0], [15, 12, 1, 10, 0, 19, 11, 13, 2, 14, 17, 6, 16, 3, 7, 4, 8, 9, 18, 5], [3, 7, 9, 0, 5, 6, 14, 16, 4, 2, 19, 12, 13, 18, 1, 11, 17, 10, 8, 15], [17, 3, 11, 9, 4, 13, 16, 8, 0, 18, 1, 19, 10, 5, 6, 15, 14, 12, 7, 2], [17, 13, 16, 4, 11, 7, 12, 6, 8, 10, 2, 18, 0, 9, 15, 1, 3, 5, 14, 19], [0, 11, 1, 18, 2, 13, 9, 7, 8, 15, 16, 12, 14, 10, 6, 17, 3, 5, 4, 19], [9, 3, 6, 12, 0, 13, 2, 1, 17, 16, 18, 19, 4, 11, 14, 7, 15, 5, 8, 10], [12, 10, 16, 9, 18, 7, 8, 0, 6, 3, 15, 1, 5, 4, 17, 14, 13, 19, 11, 2], [6, 18, 8, 4, 7, 17, 0, 14, 11, 19, 3, 10, 9, 16, 12, 5, 1, 13, 2, 15], [17, 4, 16, 12, 19, 1, 2, 18, 11, 3, 10, 6, 5, 7, 9, 0, 8, 13, 15, 14], [14, 11, 1, 9, 12, 7, 10, 19, 2, 17, 13, 16, 8, 15, 5, 3, 18, 0, 6, 4], [4, 10, 19, 18, 16, 11, 5, 15, 1, 7, 2, 14, 13, 3, 17, 0, 12, 6, 9, 8], [2, 3, 7, 18, 14, 6, 12, 0, 9, 13, 4, 16, 10, 5, 19, 11, 17, 15, 8, 1], [3, 2, 15, 9, 18, 11, 7, 17, 16, 8, 19, 13, 0, 6, 4, 10, 14, 1, 5, 12], [4, 10, 8, 1, 12, 18, 17, 15, 11, 19, 3, 14, 13, 7, 2, 9, 5, 6, 0, 16], [13, 15, 5, 14, 3, 18, 17, 10, 2, 19, 6, 12, 11, 16, 7, 0, 4, 1, 9, 8], [3, 13, 18, 8, 11, 9, 17, 12, 16, 0, 2, 14, 19, 7, 10, 1, 15, 4, 6, 5]]

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
