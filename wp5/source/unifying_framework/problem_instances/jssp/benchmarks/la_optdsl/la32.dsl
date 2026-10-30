# Job Shop Scheduling instance: la32
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 10
MAX_TIME : int = 16569

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 58, 44, 5, 97, 58, 89, 84, 77, 96], [77, 87, 81, 85, 15, 39, 21, 31, 57, 73], [40, 49, 48, 70, 10, 71, 22, 80, 34, 82], [55, 91, 17, 7, 11, 75, 72, 62, 47, 35], [64, 90, 94, 75, 12, 50, 71, 67, 15, 20], [52, 57, 29, 68, 58, 93, 93, 70, 77, 7], [95, 63, 82, 27, 26, 6, 87, 56, 48, 36], [36, 8, 36, 76, 30, 15, 84, 76, 41, 78], [75, 78, 81, 13, 54, 88, 82, 13, 29, 40], [52, 26, 6, 6, 54, 82, 64, 32, 54, 88], [62, 35, 67, 61, 72, 32, 93, 69, 62, 5], [85, 72, 78, 11, 7, 88, 63, 82, 64, 90], [44, 66, 27, 35, 28, 31, 88, 50, 49, 11], [76, 7, 14, 97, 62, 39, 56, 69, 47, 66], [64, 18, 41, 69, 79, 53, 47, 58, 93, 57], [76, 58, 74, 78, 77, 22, 61, 76, 26, 81], [65, 16, 99, 43, 92, 95, 30, 64, 72, 29], [7, 35, 81, 74, 85, 16, 86, 34, 61, 35], [43, 97, 42, 64, 72, 17, 88, 43, 94, 22], [92, 20, 84, 74, 89, 98, 31, 99, 99, 23], [6, 81, 40, 37, 55, 19, 9, 40, 32, 81], [77, 46, 70, 55, 64, 65, 15, 21, 25, 65], [40, 44, 85, 24, 89, 37, 83, 84, 31, 29], [8, 80, 30, 38, 80, 59, 77, 56, 97, 41], [91, 17, 71, 50, 88, 56, 40, 7, 80, 59], [45, 29, 8, 58, 54, 77, 9, 36, 96, 10], [28, 98, 73, 92, 70, 87, 99, 27, 86, 96], [59, 95, 41, 85, 52, 56, 81, 92, 39, 32], [88, 7, 12, 60, 93, 22, 27, 69, 45, 49], [21, 84, 61, 68, 99, 26, 82, 33, 44, 71]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 1, 4, 2, 8, 3, 0, 5, 9, 7], [7, 2, 9, 4, 1, 5, 8, 0, 3, 6], [2, 5, 0, 3, 1, 6, 4, 8, 7, 9], [4, 6, 7, 0, 2, 5, 3, 1, 9, 8], [0, 6, 4, 1, 2, 3, 9, 8, 5, 7], [2, 6, 3, 5, 1, 8, 0, 9, 4, 7], [4, 3, 1, 5, 6, 7, 8, 9, 0, 2], [1, 7, 3, 4, 6, 9, 8, 0, 2, 5], [3, 8, 0, 2, 1, 5, 4, 9, 7, 6], [0, 2, 3, 5, 6, 9, 8, 4, 7, 1], [8, 1, 4, 7, 0, 5, 9, 3, 2, 6], [2, 3, 7, 4, 1, 8, 9, 0, 5, 6], [7, 4, 3, 1, 2, 8, 9, 6, 5, 0], [4, 5, 0, 2, 6, 3, 1, 7, 9, 8], [6, 2, 0, 7, 9, 8, 3, 5, 1, 4], [7, 9, 0, 6, 4, 8, 2, 5, 1, 3], [6, 8, 3, 0, 1, 4, 5, 9, 2, 7], [1, 3, 5, 4, 0, 2, 6, 8, 9, 7], [1, 7, 4, 6, 5, 0, 8, 3, 9, 2], [7, 2, 8, 5, 1, 6, 3, 0, 9, 4], [8, 0, 4, 5, 9, 1, 7, 6, 3, 2], [6, 2, 8, 1, 9, 4, 7, 0, 5, 3], [8, 7, 5, 3, 2, 4, 9, 1, 0, 6], [4, 0, 9, 5, 7, 3, 2, 8, 6, 1], [9, 0, 3, 8, 1, 6, 2, 5, 4, 7], [7, 3, 4, 5, 2, 6, 0, 9, 1, 8], [0, 3, 2, 7, 8, 5, 9, 1, 6, 4], [9, 1, 3, 6, 2, 8, 7, 0, 5, 4], [4, 2, 5, 6, 8, 7, 3, 1, 0, 9], [2, 5, 9, 8, 0, 6, 3, 7, 1, 4]]

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
