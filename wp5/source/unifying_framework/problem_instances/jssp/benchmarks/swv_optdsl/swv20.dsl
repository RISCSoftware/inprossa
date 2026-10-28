# Job Shop Scheduling instance: swv20
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 50
N_MACHINES : int = 10
MAX_TIME : int = 24617

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 71, 31, 55, 42, 41, 94, 30, 100, 11], [90, 86, 64, 96, 81, 47, 20, 39, 29, 61], [56, 88, 68, 44, 22, 80, 80, 19, 95, 60], [88, 54, 15, 25, 86, 33, 70, 50, 89, 88], [48, 57, 11, 78, 86, 4, 25, 40, 60, 60], [51, 90, 52, 83, 1, 30, 23, 9, 25, 14], [1, 30, 41, 28, 75, 76, 50, 54, 75, 100], [8, 37, 46, 78, 50, 39, 56, 12, 66, 72], [32, 24, 99, 6, 63, 52, 90, 81, 12, 22], [66, 32, 4, 9, 41, 29, 62, 79, 59, 84], [51, 64, 99, 17, 14, 99, 2, 10, 27, 57], [67, 29, 30, 7, 1, 25, 87, 81, 93, 83], [60, 5, 22, 98, 28, 65, 77, 74, 53, 48], [71, 97, 31, 17, 38, 37, 51, 49, 28, 67], [20, 27, 57, 39, 8, 42, 73, 26, 94, 63], [86, 68, 65, 35, 1, 77, 17, 100, 77, 20], [10, 60, 30, 56, 79, 60, 62, 84, 68, 86], [8, 56, 74, 69, 71, 4, 6, 89, 50, 78], [46, 59, 48, 96, 91, 5, 21, 53, 29, 82], [73, 39, 19, 50, 65, 54, 78, 60, 50, 96], [13, 93, 26, 26, 15, 96, 27, 68, 70, 13], [3, 31, 92, 78, 66, 41, 41, 9, 18, 53], [64, 43, 15, 32, 12, 9, 73, 69, 89, 22], [72, 26, 94, 74, 53, 93, 19, 7, 81, 19], [98, 38, 29, 48, 58, 51, 32, 35, 72, 54], [94, 62, 53, 68, 41, 49, 53, 27, 84, 23], [66, 4, 29, 23, 4, 2, 86, 90, 46, 78], [15, 12, 97, 78, 12, 61, 77, 68, 92, 22], [100, 2, 70, 23, 72, 78, 71, 89, 89, 37], [91, 80, 36, 74, 72, 47, 62, 77, 80, 20], [67, 44, 38, 40, 66, 5, 59, 15, 99, 19], [7, 69, 35, 86, 89, 32, 66, 52, 63, 35], [45, 66, 40, 3, 68, 2, 41, 27, 39, 77], [55, 55, 1, 42, 66, 6, 98, 79, 73, 44], [65, 27, 27, 80, 17, 42, 6, 74, 18, 94], [84, 97, 73, 68, 70, 51, 89, 28, 29, 95], [43, 8, 50, 76, 17, 54, 56, 93, 65, 85], [40, 1, 61, 17, 71, 38, 41, 18, 74, 94], [93, 1, 21, 30, 74, 3, 39, 64, 22, 56], [17, 18, 63, 85, 89, 38, 88, 5, 8, 20], [42, 34, 12, 71, 88, 44, 32, 13, 87, 11], [48, 73, 39, 94, 68, 23, 43, 66, 48, 77], [30, 98, 43, 69, 70, 87, 5, 19, 85, 19], [75, 60, 45, 75, 30, 35, 41, 37, 67, 71], [66, 46, 16, 63, 51, 20, 57, 39, 40, 69], [24, 21, 7, 60, 22, 68, 17, 73, 2, 36], [7, 20, 75, 38, 17, 28, 57, 22, 12, 29], [53, 11, 100, 18, 7, 53, 48, 5, 27, 38], [20, 49, 63, 15, 81, 5, 1, 47, 9, 10], [42, 34, 30, 97, 49, 64, 27, 17, 56, 82]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 7, 4, 9, 2, 1, 5, 0, 3, 6], [4, 6, 3, 7, 8, 0, 9, 2, 1, 5], [5, 0, 1, 7, 2, 8, 3, 4, 9, 6], [4, 6, 0, 2, 7, 1, 9, 3, 8, 5], [0, 1, 4, 8, 3, 5, 9, 7, 2, 6], [6, 7, 1, 0, 2, 9, 5, 4, 8, 3], [1, 4, 5, 9, 7, 2, 6, 8, 0, 3], [2, 3, 1, 7, 6, 4, 8, 5, 0, 9], [1, 6, 0, 3, 2, 9, 8, 4, 7, 5], [6, 3, 8, 0, 4, 1, 5, 7, 9, 2], [9, 5, 6, 3, 0, 7, 4, 1, 2, 8], [7, 0, 9, 2, 5, 6, 1, 3, 8, 4], [5, 8, 9, 4, 7, 0, 6, 2, 1, 3], [1, 5, 0, 7, 6, 3, 4, 9, 8, 2], [0, 8, 3, 6, 9, 4, 2, 1, 7, 5], [8, 1, 9, 7, 4, 5, 6, 3, 2, 0], [8, 6, 4, 7, 1, 3, 0, 9, 5, 2], [4, 2, 6, 1, 3, 0, 8, 9, 5, 7], [8, 5, 1, 3, 0, 4, 2, 7, 6, 9], [2, 9, 0, 1, 5, 8, 7, 3, 4, 6], [7, 4, 2, 3, 0, 9, 5, 8, 6, 1], [6, 8, 4, 7, 1, 2, 0, 3, 5, 9], [5, 0, 2, 6, 4, 1, 8, 7, 3, 9], [5, 6, 3, 8, 0, 2, 9, 1, 4, 7], [3, 2, 5, 8, 7, 6, 1, 0, 4, 9], [0, 9, 4, 6, 2, 7, 1, 3, 8, 5], [4, 1, 0, 7, 9, 2, 5, 6, 3, 8], [3, 5, 2, 7, 8, 0, 4, 6, 1, 9], [0, 7, 6, 2, 8, 4, 5, 3, 9, 1], [0, 3, 2, 4, 6, 1, 9, 7, 5, 8], [1, 0, 4, 8, 6, 5, 7, 2, 3, 9], [1, 9, 3, 0, 2, 5, 6, 4, 8, 7], [3, 4, 1, 7, 6, 5, 9, 0, 2, 8], [4, 3, 7, 0, 6, 9, 5, 8, 1, 2], [3, 8, 9, 2, 5, 4, 7, 0, 6, 1], [2, 4, 5, 0, 8, 9, 1, 7, 3, 6], [9, 6, 5, 3, 2, 0, 1, 7, 4, 8], [1, 3, 2, 5, 4, 7, 0, 9, 6, 8], [3, 8, 6, 9, 5, 7, 4, 2, 0, 1], [0, 8, 9, 5, 3, 7, 2, 1, 4, 6], [8, 5, 0, 1, 9, 7, 3, 4, 6, 2], [2, 1, 6, 0, 9, 8, 5, 7, 3, 4], [1, 7, 3, 6, 8, 9, 0, 2, 5, 4], [2, 1, 4, 9, 5, 0, 3, 6, 8, 7], [3, 7, 2, 9, 1, 5, 6, 4, 0, 8], [2, 7, 6, 1, 0, 8, 5, 4, 9, 3], [1, 4, 8, 9, 5, 0, 3, 6, 7, 2], [5, 4, 7, 8, 9, 2, 6, 0, 1, 3], [1, 7, 4, 8, 0, 2, 3, 6, 9, 5], [4, 6, 7, 5, 2, 8, 0, 3, 9, 1]]

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
