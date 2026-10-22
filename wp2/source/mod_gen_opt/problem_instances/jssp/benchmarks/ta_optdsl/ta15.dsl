# Job Shop Scheduling instance: ta15
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14591

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[15, 89, 49, 95, 40, 79, 44, 59, 87, 88, 48, 44, 43, 11, 75], [6, 46, 18, 4, 56, 44, 15, 40, 44, 79, 1, 32, 5, 92, 76], [78, 45, 61, 49, 26, 36, 94, 80, 49, 53, 4, 51, 82, 36, 76], [58, 34, 70, 19, 85, 69, 87, 38, 5, 88, 66, 3, 10, 28, 18], [78, 7, 83, 75, 39, 24, 10, 13, 42, 2, 61, 26, 11, 89, 39], [80, 88, 13, 92, 11, 62, 42, 3, 6, 36, 49, 98, 40, 59, 15], [83, 12, 48, 1, 76, 32, 1, 81, 53, 70, 78, 75, 7, 82, 31], [75, 13, 9, 11, 49, 15, 57, 84, 77, 80, 41, 82, 68, 64, 50], [39, 64, 88, 9, 97, 99, 27, 48, 18, 49, 50, 26, 54, 80, 77], [66, 87, 27, 47, 68, 75, 31, 25, 49, 85, 86, 12, 26, 82, 78], [93, 87, 74, 26, 60, 76, 3, 98, 72, 52, 73, 75, 28, 1, 51], [79, 13, 14, 27, 14, 5, 58, 32, 38, 67, 70, 86, 28, 94, 33], [83, 67, 18, 20, 4, 84, 22, 8, 91, 89, 25, 8, 69, 85, 46], [64, 18, 12, 43, 78, 65, 20, 53, 32, 49, 25, 10, 43, 30, 3], [99, 29, 50, 99, 53, 65, 23, 49, 91, 1, 86, 7, 68, 71, 89], [13, 19, 31, 94, 78, 43, 16, 56, 76, 1, 11, 24, 13, 62, 55], [43, 24, 85, 20, 6, 44, 49, 41, 67, 47, 25, 86, 6, 6, 30], [68, 92, 15, 80, 29, 72, 22, 41, 49, 36, 97, 80, 23, 77, 4], [51, 34, 10, 96, 74, 80, 65, 75, 14, 83, 13, 78, 61, 43, 58], [69, 56, 15, 89, 22, 21, 89, 16, 59, 83, 20, 33, 11, 67, 90]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 12, 6, 3, 8, 5, 0, 9, 1, 10, 2, 4, 13, 14, 11], [8, 3, 12, 5, 6, 9, 1, 14, 4, 2, 11, 0, 10, 13, 7], [1, 0, 8, 4, 11, 14, 12, 6, 13, 9, 2, 5, 7, 10, 3], [11, 13, 10, 0, 4, 7, 14, 5, 3, 2, 9, 1, 12, 8, 6], [14, 6, 2, 10, 11, 5, 12, 9, 3, 1, 13, 4, 0, 7, 8], [7, 5, 12, 13, 9, 11, 1, 4, 3, 6, 2, 8, 0, 14, 10], [14, 13, 8, 9, 1, 0, 11, 4, 2, 3, 10, 6, 7, 12, 5], [7, 13, 4, 11, 0, 10, 5, 2, 6, 1, 8, 12, 3, 9, 14], [5, 11, 4, 1, 12, 14, 13, 7, 8, 6, 9, 2, 0, 3, 10], [9, 4, 3, 8, 14, 5, 6, 13, 11, 10, 12, 7, 1, 2, 0], [11, 13, 6, 5, 10, 3, 12, 8, 2, 4, 9, 1, 0, 14, 7], [11, 1, 4, 7, 12, 3, 5, 10, 14, 2, 13, 0, 6, 9, 8], [1, 5, 7, 12, 13, 6, 11, 4, 8, 3, 14, 10, 0, 9, 2], [4, 10, 7, 8, 3, 13, 0, 14, 11, 12, 9, 6, 1, 2, 5], [8, 4, 11, 13, 1, 9, 0, 6, 12, 5, 2, 10, 3, 7, 14], [13, 8, 10, 5, 6, 14, 11, 7, 12, 0, 1, 4, 9, 2, 3], [5, 8, 13, 11, 9, 14, 10, 1, 12, 6, 4, 7, 3, 0, 2], [2, 9, 4, 0, 5, 7, 8, 10, 12, 11, 3, 13, 6, 1, 14], [1, 4, 8, 10, 6, 11, 9, 5, 13, 0, 7, 12, 3, 14, 2], [1, 10, 13, 12, 5, 4, 6, 14, 11, 7, 8, 2, 9, 0, 3]]

# Decision variable: completion time of operation op for each job.
completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))


def precedence_constraint(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))):
    # Each job's operations must respect sequence order with processing times.
    for j in range(N_JOBS):
        first_machine = MACHINE_SEQUENCE[j][0]
        assert completion[j][0] >= PROCESSING_TIMES[j][first_machine]
        for op in range(1, N_MACHINES):
            machine = MACHINE_SEQUENCE[j][op]
            assert completion[j][op] >= completion[j][op - 1] + PROCESSING_TIMES[j][machine]


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
