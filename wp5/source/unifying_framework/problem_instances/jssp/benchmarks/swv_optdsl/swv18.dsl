# Job Shop Scheduling instance: swv18
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 24671

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[86, 90, 92, 30, 5, 40, 23, 35, 8, 35], [12, 75, 60, 97, 3, 45, 69, 82, 21, 70], [61, 55, 38, 4, 31, 48, 12, 96, 29, 79], [95, 43, 18, 29, 83, 4, 92, 82, 97, 67], [32, 40, 38, 46, 95, 1, 64, 89, 66, 80], [90, 6, 94, 98, 80, 45, 57, 27, 68, 59], [91, 18, 97, 48, 4, 50, 100, 52, 96, 63], [31, 88, 76, 25, 13, 44, 43, 23, 83, 41], [81, 27, 20, 90, 42, 46, 40, 34, 72, 20], [42, 10, 49, 71, 71, 97, 14, 80, 98, 10], [96, 58, 79, 29, 47, 76, 59, 66, 31, 88], [60, 7, 66, 27, 97, 66, 3, 23, 93, 55], [26, 28, 98, 31, 77, 79, 38, 58, 39, 12], [19, 87, 28, 38, 4, 83, 8, 82, 10, 48], [55, 85, 86, 26, 30, 6, 19, 79, 33, 13], [45, 58, 28, 37, 15, 17, 74, 29, 26, 43], [37, 42, 90, 37, 7, 47, 21, 15, 62, 33], [75, 28, 57, 21, 46, 32, 41, 18, 49, 3], [40, 30, 9, 4, 91, 49, 98, 25, 24, 73], [17, 21, 90, 94, 94, 29, 33, 85, 90, 86], [54, 66, 5, 84, 85, 70, 3, 61, 57, 40], [18, 98, 45, 30, 98, 82, 65, 81, 84, 1], [59, 97, 26, 72, 21, 39, 40, 77, 42, 90], [51, 14, 54, 63, 64, 57, 23, 96, 78, 100], [32, 55, 87, 41, 35, 61, 73, 96, 91, 60], [45, 61, 84, 66, 100, 90, 84, 3, 91, 19], [39, 88, 33, 59, 54, 29, 27, 20, 14, 72], [18, 46, 26, 73, 45, 77, 22, 27, 55, 43], [32, 71, 57, 41, 9, 71, 58, 50, 25, 16], [42, 56, 44, 73, 15, 66, 3, 53, 48, 32], [50, 2, 31, 38, 70, 55, 69, 14, 40, 90], [55, 68, 5, 83, 79, 12, 89, 78, 14, 100], [18, 84, 2, 38, 26, 44, 27, 64, 39, 98], [20, 57, 10, 98, 7, 89, 12, 87, 50, 99], [64, 30, 34, 11, 89, 31, 62, 98, 63, 31], [37, 10, 51, 26, 69, 29, 43, 27, 92, 21], [64, 13, 23, 27, 21, 98, 38, 89, 21, 89], [33, 67, 43, 42, 39, 16, 62, 32, 90, 70], [45, 98, 61, 37, 5, 15, 25, 73, 58, 45], [17, 2, 35, 62, 40, 81, 15, 94, 16, 64], [25, 37, 76, 87, 56, 32, 37, 52, 21, 11], [33, 6, 40, 23, 4, 25, 25, 31, 29, 98], [62, 95, 22, 2, 30, 99, 3, 1, 96, 30], [78, 30, 43, 96, 1, 3, 90, 88, 97, 54], [42, 94, 67, 80, 86, 29, 60, 75, 17, 27], [57, 17, 25, 73, 90, 62, 62, 80, 81, 19], [27, 19, 34, 54, 4, 28, 46, 60, 64, 31], [80, 45, 43, 6, 7, 13, 1, 1, 66, 95], [87, 65, 21, 20, 37, 32, 64, 82, 61, 16], [49, 21, 31, 54, 66, 2, 73, 82, 69, 35]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 6, 2, 4, 5, 1, 3, 9, 8, 0], [2, 3, 8, 9, 7, 0, 4, 5, 1, 6], [7, 2, 0, 1, 4, 5, 9, 3, 6, 8], [4, 7, 8, 1, 0, 6, 2, 3, 5, 9], [3, 9, 8, 2, 4, 1, 7, 0, 6, 5], [6, 4, 8, 7, 0, 5, 3, 9, 1, 2], [5, 0, 2, 9, 7, 3, 4, 8, 1, 6], [7, 6, 3, 8, 2, 9, 1, 0, 5, 4], [2, 3, 9, 4, 8, 5, 1, 0, 6, 7], [7, 5, 0, 2, 9, 1, 3, 4, 6, 8], [2, 3, 0, 7, 1, 8, 4, 5, 6, 9], [8, 6, 1, 3, 5, 7, 0, 4, 2, 9], [9, 8, 4, 5, 0, 7, 2, 6, 3, 1], [6, 9, 4, 1, 3, 2, 8, 0, 7, 5], [5, 9, 2, 6, 3, 7, 0, 1, 8, 4], [3, 8, 7, 6, 9, 5, 0, 2, 1, 4], [7, 3, 6, 5, 2, 0, 9, 1, 4, 8], [8, 4, 1, 7, 6, 2, 0, 3, 9, 5], [6, 1, 8, 4, 9, 7, 5, 0, 2, 3], [6, 3, 1, 2, 9, 7, 5, 0, 4, 8], [6, 4, 1, 7, 8, 3, 2, 9, 0, 5], [7, 1, 2, 0, 6, 9, 4, 3, 8, 5], [6, 7, 3, 1, 5, 4, 0, 8, 9, 2], [5, 3, 1, 4, 6, 8, 2, 0, 9, 7], [5, 1, 6, 2, 4, 3, 7, 0, 8, 9], [9, 5, 8, 0, 3, 2, 1, 7, 6, 4], [2, 9, 6, 8, 3, 0, 7, 5, 4, 1], [4, 0, 3, 2, 8, 6, 7, 1, 9, 5], [2, 9, 1, 8, 7, 3, 6, 5, 4, 0], [8, 9, 0, 3, 1, 7, 6, 5, 4, 2], [6, 7, 1, 8, 4, 9, 3, 2, 5, 0], [9, 8, 0, 2, 5, 4, 1, 3, 6, 7], [4, 5, 8, 1, 7, 9, 3, 2, 6, 0], [3, 2, 9, 8, 0, 6, 4, 1, 7, 5], [0, 8, 7, 5, 1, 6, 3, 4, 9, 2], [3, 6, 4, 7, 8, 2, 1, 5, 9, 0], [8, 5, 0, 6, 2, 1, 7, 9, 4, 3], [4, 7, 1, 0, 5, 2, 6, 3, 9, 8], [7, 9, 3, 0, 2, 6, 5, 4, 8, 1], [7, 0, 6, 5, 9, 3, 1, 8, 2, 4], [5, 6, 9, 0, 1, 8, 2, 7, 4, 3], [3, 2, 1, 7, 6, 9, 8, 4, 5, 0], [8, 9, 1, 3, 6, 2, 0, 4, 7, 5], [9, 5, 0, 2, 6, 7, 4, 8, 1, 3], [5, 6, 3, 1, 2, 0, 8, 9, 7, 4], [1, 5, 2, 7, 6, 9, 8, 3, 0, 4], [9, 3, 5, 1, 4, 2, 8, 6, 7, 0], [9, 7, 2, 3, 4, 8, 1, 5, 0, 6], [3, 7, 0, 1, 6, 8, 2, 5, 9, 4], [0, 3, 2, 8, 1, 5, 6, 9, 4, 7]]

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
