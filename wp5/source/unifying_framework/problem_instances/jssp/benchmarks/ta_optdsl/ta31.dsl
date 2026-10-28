# Job Shop Scheduling instance: ta31
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 15
MAX_TIME : int = 22600

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[48, 99, 34, 99, 84, 23, 38, 50, 98, 95, 43, 24, 53, 30, 6], [85, 5, 65, 16, 24, 9, 19, 60, 22, 59, 25, 9, 36, 32, 94], [56, 30, 62, 49, 54, 78, 88, 13, 17, 40, 93, 88, 59, 71, 47], [60, 84, 98, 14, 79, 60, 17, 31, 74, 42, 42, 19, 59, 16, 84], [51, 52, 2, 9, 50, 14, 49, 64, 1, 56, 46, 28, 6, 75, 37], [23, 17, 99, 40, 39, 59, 65, 86, 46, 67, 8, 6, 85, 94, 69], [49, 22, 64, 69, 31, 77, 36, 70, 21, 46, 44, 10, 75, 7, 57], [17, 93, 74, 63, 26, 53, 58, 71, 82, 54, 66, 37, 4, 89, 46], [78, 46, 90, 17, 19, 17, 56, 76, 72, 56, 27, 5, 42, 72, 43], [36, 71, 87, 20, 83, 90, 18, 79, 6, 48, 94, 23, 25, 84, 93], [61, 58, 54, 45, 60, 15, 56, 49, 1, 72, 52, 74, 26, 94, 54], [73, 97, 50, 41, 21, 63, 54, 45, 36, 82, 52, 84, 15, 21, 52], [90, 26, 39, 31, 33, 75, 92, 77, 90, 56, 23, 55, 70, 14, 49], [53, 48, 83, 10, 87, 99, 29, 24, 84, 47, 89, 97, 34, 58, 82], [29, 88, 93, 16, 82, 26, 77, 35, 98, 4, 58, 30, 28, 98, 32], [94, 3, 66, 30, 62, 24, 56, 53, 10, 18, 34, 59, 92, 18, 41], [2, 8, 39, 60, 34, 47, 72, 26, 23, 56, 56, 95, 17, 81, 18], [60, 27, 94, 3, 58, 6, 79, 65, 80, 45, 29, 80, 94, 76, 14], [42, 86, 54, 87, 79, 33, 48, 8, 16, 32, 93, 57, 31, 79, 63], [96, 51, 23, 75, 63, 71, 92, 1, 10, 63, 45, 42, 58, 27, 18], [93, 61, 9, 15, 62, 82, 75, 16, 5, 28, 43, 22, 19, 1, 84], [25, 79, 95, 1, 58, 71, 50, 73, 12, 1, 18, 29, 46, 72, 23], [89, 6, 28, 56, 71, 9, 92, 52, 10, 39, 90, 49, 42, 40, 20], [48, 59, 38, 88, 43, 81, 68, 7, 63, 97, 87, 86, 70, 29, 53], [91, 28, 80, 9, 60, 29, 78, 92, 65, 85, 15, 97, 95, 85, 81], [34, 4, 89, 35, 59, 7, 53, 39, 12, 69, 32, 3, 34, 40, 6], [50, 7, 31, 1, 51, 59, 29, 98, 98, 31, 64, 98, 85, 24, 9], [2, 8, 59, 7, 69, 72, 9, 3, 68, 69, 84, 45, 14, 54, 59], [98, 86, 14, 82, 87, 59, 24, 21, 92, 52, 53, 61, 79, 83, 64], [35, 26, 51, 80, 45, 94, 8, 21, 60, 73, 11, 3, 70, 94, 56]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 10, 14, 1, 5, 8, 4, 11, 13, 12, 2, 9, 7, 0, 6], [6, 4, 2, 3, 14, 5, 7, 13, 9, 0, 11, 12, 8, 10, 1], [4, 2, 10, 5, 12, 13, 3, 11, 9, 7, 8, 6, 14, 1, 0], [0, 13, 4, 1, 14, 9, 12, 3, 8, 5, 2, 6, 10, 7, 11], [6, 1, 10, 4, 8, 5, 2, 9, 7, 0, 13, 11, 3, 14, 12], [5, 6, 12, 3, 0, 4, 2, 8, 1, 13, 11, 9, 14, 7, 10], [11, 13, 1, 6, 4, 12, 14, 0, 10, 8, 5, 7, 2, 9, 3], [5, 2, 1, 4, 9, 13, 8, 10, 11, 3, 7, 0, 6, 12, 14], [7, 13, 12, 5, 10, 9, 0, 11, 8, 4, 2, 1, 14, 6, 3], [6, 7, 14, 1, 9, 11, 3, 5, 10, 2, 8, 0, 13, 12, 4], [10, 0, 3, 4, 5, 11, 7, 12, 13, 14, 8, 1, 6, 2, 9], [5, 0, 9, 11, 12, 6, 10, 14, 8, 4, 7, 3, 13, 1, 2], [8, 0, 7, 4, 3, 1, 13, 5, 6, 12, 11, 9, 2, 14, 10], [4, 9, 13, 12, 6, 2, 7, 1, 11, 10, 8, 14, 0, 5, 3], [7, 14, 11, 2, 10, 12, 1, 3, 13, 9, 4, 8, 5, 0, 6], [13, 12, 4, 11, 1, 0, 10, 6, 5, 9, 2, 7, 3, 14, 8], [0, 7, 12, 14, 3, 2, 8, 11, 13, 9, 4, 1, 5, 6, 10], [5, 6, 7, 4, 12, 9, 11, 3, 10, 8, 1, 0, 2, 14, 13], [12, 4, 3, 13, 11, 6, 5, 0, 10, 1, 2, 9, 7, 8, 14], [0, 7, 3, 11, 10, 1, 8, 12, 5, 6, 2, 14, 9, 13, 4], [14, 5, 7, 1, 10, 6, 9, 3, 12, 0, 11, 13, 4, 2, 8], [12, 11, 6, 8, 13, 10, 1, 7, 14, 9, 4, 3, 2, 0, 5], [8, 9, 11, 3, 4, 13, 10, 2, 0, 12, 5, 6, 7, 1, 14], [12, 8, 6, 9, 11, 5, 2, 7, 14, 0, 4, 1, 3, 13, 10], [14, 11, 8, 4, 10, 5, 3, 2, 6, 9, 12, 13, 0, 1, 7], [7, 14, 4, 0, 12, 10, 8, 5, 3, 1, 6, 9, 2, 11, 13], [11, 12, 4, 14, 13, 1, 5, 8, 0, 7, 10, 9, 2, 6, 3], [14, 8, 7, 1, 0, 6, 9, 12, 5, 10, 4, 13, 11, 2, 3], [8, 7, 10, 14, 5, 12, 9, 2, 11, 1, 3, 0, 13, 6, 4], [2, 12, 13, 3, 0, 14, 6, 5, 10, 11, 8, 9, 1, 7, 4]]

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
