# Job Shop Scheduling instance: ta10
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11356

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[35, 78, 79, 65, 53, 14, 93, 70, 14, 90, 95, 49, 36, 85, 1], [83, 41, 22, 29, 52, 71, 16, 93, 54, 63, 12, 85, 62, 45, 30], [60, 43, 71, 2, 50, 37, 86, 81, 60, 57, 66, 24, 98, 92, 69], [14, 59, 35, 6, 25, 57, 1, 44, 94, 30, 95, 93, 51, 52, 16], [96, 39, 75, 98, 2, 38, 69, 32, 95, 63, 4, 11, 50, 95, 78], [73, 28, 43, 47, 57, 88, 33, 13, 7, 49, 23, 38, 21, 99, 72], [3, 80, 67, 93, 91, 31, 52, 64, 83, 2, 90, 64, 16, 18, 25], [23, 30, 22, 54, 68, 63, 89, 95, 5, 37, 5, 42, 17, 54, 46], [44, 59, 87, 62, 51, 55, 3, 40, 26, 18, 15, 18, 72, 35, 60], [27, 14, 77, 24, 55, 67, 59, 19, 29, 33, 88, 30, 91, 11, 11], [67, 94, 50, 2, 83, 19, 29, 37, 58, 32, 38, 99, 88, 49, 70], [60, 7, 81, 82, 58, 83, 16, 1, 69, 7, 3, 84, 8, 12, 93], [92, 81, 4, 78, 9, 78, 75, 5, 50, 8, 44, 4, 60, 94, 74], [32, 88, 31, 68, 31, 10, 45, 75, 82, 51, 55, 99, 44, 84, 22], [12, 35, 64, 17, 42, 46, 65, 74, 96, 28, 86, 95, 93, 67, 56]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 2, 7, 14, 12, 0, 4, 3, 13, 5, 9, 10, 6, 1, 11], [2, 8, 6, 4, 11, 0, 9, 7, 5, 3, 1, 10, 13, 14, 12], [5, 11, 8, 14, 12, 1, 4, 9, 10, 6, 13, 0, 2, 3, 7], [9, 13, 8, 6, 12, 5, 10, 2, 1, 0, 14, 11, 3, 4, 7], [8, 10, 3, 13, 14, 5, 4, 0, 12, 11, 9, 6, 2, 1, 7], [7, 2, 9, 5, 10, 4, 3, 1, 11, 8, 6, 14, 13, 0, 12], [2, 10, 1, 12, 14, 3, 0, 4, 9, 5, 11, 13, 7, 8, 6], [13, 6, 11, 12, 8, 7, 14, 5, 3, 4, 0, 10, 2, 1, 9], [8, 4, 6, 7, 0, 11, 13, 12, 2, 3, 10, 1, 5, 14, 9], [2, 6, 12, 9, 8, 11, 1, 3, 13, 4, 10, 5, 0, 7, 14], [0, 9, 4, 8, 10, 2, 11, 12, 14, 6, 3, 7, 5, 1, 13], [8, 1, 12, 5, 7, 10, 9, 4, 11, 6, 13, 2, 14, 0, 3], [13, 14, 2, 9, 7, 8, 12, 4, 10, 6, 1, 0, 5, 11, 3], [1, 0, 12, 2, 13, 8, 3, 14, 4, 7, 6, 9, 11, 10, 5], [3, 13, 2, 5, 9, 6, 7, 4, 8, 0, 12, 10, 14, 1, 11]]

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
