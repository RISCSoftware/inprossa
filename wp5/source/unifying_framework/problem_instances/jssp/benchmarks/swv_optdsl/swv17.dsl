# Job Shop Scheduling instance: swv17
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 24459

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[33, 80, 57, 21, 46, 34, 83, 9, 89, 62], [21, 35, 40, 78, 33, 26, 21, 64, 37, 82], [24, 16, 78, 48, 52, 49, 43, 14, 58, 34], [36, 37, 94, 86, 98, 27, 53, 29, 41, 5], [54, 87, 20, 51, 29, 29, 85, 55, 51, 93], [87, 98, 88, 67, 28, 17, 23, 26, 41, 70], [18, 44, 78, 86, 43, 9, 43, 62, 42, 78], [89, 91, 51, 26, 89, 90, 59, 37, 28, 37], [16, 98, 31, 82, 89, 25, 32, 23, 12, 92], [62, 58, 89, 42, 46, 14, 66, 88, 66, 97], [78, 86, 4, 11, 43, 19, 3, 93, 94, 11], [17, 87, 2, 15, 73, 22, 37, 81, 31, 61], [86, 33, 68, 54, 63, 35, 28, 15, 22, 84], [1, 2, 23, 20, 73, 31, 18, 82, 49, 8], [7, 44, 36, 90, 51, 8, 47, 49, 31, 6], [18, 95, 24, 26, 43, 90, 91, 98, 99, 99], [10, 49, 76, 73, 85, 96, 69, 41, 42, 52], [5, 69, 40, 38, 33, 23, 99, 35, 17, 82], [94, 93, 70, 42, 90, 40, 88, 76, 11, 54], [63, 4, 38, 52, 91, 88, 92, 92, 53, 44], [10, 44, 79, 75, 2, 83, 32, 63, 56, 6], [23, 23, 96, 44, 27, 93, 36, 71, 21, 35], [55, 8, 43, 35, 45, 42, 37, 100, 5, 98], [40, 37, 7, 58, 98, 60, 23, 34, 34, 17], [37, 49, 39, 23, 42, 9, 83, 50, 48, 87], [54, 68, 60, 34, 49, 3, 60, 40, 50, 22], [83, 55, 32, 90, 22, 22, 29, 23, 38, 59], [79, 14, 27, 14, 25, 73, 81, 1, 87, 51], [9, 46, 62, 68, 78, 16, 88, 63, 37, 95], [21, 86, 13, 61, 77, 12, 49, 39, 96, 73], [17, 68, 60, 37, 27, 14, 42, 91, 15, 49], [4, 31, 95, 26, 25, 3, 62, 8, 76, 13], [69, 14, 61, 1, 1, 50, 73, 45, 35, 43], [74, 1, 92, 12, 57, 42, 96, 85, 1, 38], [25, 40, 32, 34, 65, 31, 83, 49, 79, 97], [31, 28, 66, 10, 81, 40, 59, 33, 83, 24], [80, 96, 72, 50, 39, 33, 86, 62, 42, 66], [35, 79, 25, 88, 69, 68, 96, 47, 56, 61], [42, 84, 2, 29, 42, 79, 95, 90, 57, 23], [81, 25, 9, 51, 17, 26, 7, 12, 21, 96], [15, 63, 22, 37, 55, 87, 40, 16, 24, 48], [60, 68, 7, 62, 64, 83, 66, 95, 81, 2], [14, 85, 77, 24, 53, 59, 35, 60, 57, 29], [9, 24, 7, 89, 77, 23, 30, 35, 72, 73], [66, 9, 14, 43, 90, 50, 63, 48, 12, 76], [59, 29, 77, 97, 64, 60, 61, 16, 40, 17], [1, 92, 3, 61, 22, 1, 19, 23, 63, 5], [35, 88, 23, 27, 39, 2, 91, 61, 74, 84], [6, 6, 74, 57, 19, 58, 22, 44, 87, 78], [45, 94, 54, 58, 6, 19, 70, 90, 72, 67]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 2, 9, 5, 6, 0, 1, 4, 3, 8], [9, 1, 8, 5, 6, 3, 7, 4, 2, 0], [7, 5, 3, 9, 4, 1, 2, 0, 8, 6], [2, 3, 8, 5, 7, 6, 9, 0, 4, 1], [7, 1, 8, 5, 9, 3, 0, 6, 2, 4], [2, 1, 3, 8, 6, 9, 7, 4, 5, 0], [2, 0, 4, 3, 9, 6, 7, 8, 1, 5], [9, 4, 3, 6, 0, 5, 1, 8, 7, 2], [3, 2, 1, 5, 0, 7, 9, 4, 6, 8], [6, 1, 5, 3, 0, 8, 4, 7, 2, 9], [8, 9, 6, 1, 2, 5, 7, 4, 0, 3], [5, 1, 9, 2, 3, 6, 7, 0, 8, 4], [6, 0, 3, 2, 4, 1, 8, 5, 9, 7], [6, 1, 2, 8, 7, 9, 4, 5, 3, 0], [7, 5, 2, 8, 6, 3, 0, 9, 1, 4], [4, 1, 0, 9, 7, 3, 8, 5, 2, 6], [1, 6, 3, 9, 0, 7, 8, 5, 4, 2], [0, 1, 3, 7, 5, 2, 8, 4, 6, 9], [3, 1, 4, 6, 2, 8, 9, 7, 5, 0], [5, 9, 0, 7, 1, 4, 6, 8, 3, 2], [5, 3, 1, 2, 7, 6, 0, 4, 9, 8], [7, 0, 5, 3, 6, 4, 2, 1, 9, 8], [5, 2, 6, 9, 0, 3, 4, 1, 8, 7], [0, 8, 2, 9, 5, 4, 7, 6, 1, 3], [9, 2, 3, 8, 6, 7, 5, 1, 0, 4], [6, 5, 2, 7, 0, 1, 4, 8, 9, 3], [5, 1, 2, 0, 8, 4, 6, 7, 9, 3], [9, 2, 6, 8, 0, 7, 3, 5, 4, 1], [6, 1, 5, 2, 9, 7, 4, 0, 3, 8], [4, 2, 8, 3, 0, 7, 5, 6, 9, 1], [7, 5, 3, 0, 9, 4, 1, 2, 6, 8], [9, 4, 6, 0, 1, 8, 5, 7, 3, 2], [7, 5, 1, 0, 9, 4, 6, 8, 3, 2], [4, 1, 0, 8, 6, 2, 7, 5, 3, 9], [7, 5, 8, 6, 1, 4, 3, 2, 9, 0], [9, 5, 4, 3, 6, 8, 2, 1, 7, 0], [5, 4, 3, 1, 7, 2, 8, 6, 9, 0], [3, 7, 0, 4, 1, 9, 2, 8, 5, 6], [9, 6, 0, 1, 8, 4, 2, 5, 3, 7], [9, 8, 4, 7, 1, 2, 6, 5, 0, 3], [1, 7, 6, 2, 9, 5, 0, 8, 3, 4], [7, 0, 3, 2, 9, 8, 5, 4, 1, 6], [3, 7, 6, 2, 1, 8, 9, 5, 4, 0], [1, 6, 0, 3, 8, 4, 2, 5, 9, 7], [0, 8, 1, 5, 2, 9, 4, 3, 7, 6], [3, 1, 0, 4, 9, 2, 5, 7, 6, 8], [9, 4, 2, 8, 5, 7, 0, 3, 1, 6], [6, 8, 1, 5, 7, 4, 0, 2, 9, 3], [8, 5, 7, 1, 6, 3, 9, 4, 2, 0], [4, 1, 0, 2, 9, 7, 5, 8, 6, 3]]

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
