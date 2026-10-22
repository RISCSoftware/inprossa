# Job Shop Scheduling instance: abz9
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 7442

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[14, 21, 13, 11, 11, 35, 20, 17, 18, 11, 23, 13, 15, 11, 35], [35, 31, 13, 26, 14, 17, 38, 20, 19, 12, 16, 34, 15, 12, 14], [30, 35, 40, 35, 30, 23, 29, 37, 38, 40, 26, 11, 40, 36, 17], [40, 18, 12, 23, 23, 14, 16, 14, 23, 12, 16, 32, 40, 25, 29], [35, 15, 31, 28, 32, 30, 27, 29, 38, 11, 23, 17, 27, 37, 29], [33, 33, 19, 40, 19, 33, 26, 31, 28, 36, 38, 21, 25, 40, 35], [25, 32, 33, 18, 32, 28, 15, 35, 14, 34, 23, 32, 17, 26, 19], [16, 33, 34, 30, 40, 12, 26, 26, 15, 21, 40, 32, 14, 30, 35], [17, 16, 20, 24, 26, 36, 22, 14, 11, 20, 23, 29, 23, 15, 40], [27, 37, 40, 14, 25, 30, 34, 11, 15, 32, 36, 12, 28, 31, 23], [25, 22, 27, 14, 25, 20, 18, 14, 19, 17, 27, 22, 22, 27, 21], [34, 15, 22, 29, 34, 40, 17, 32, 20, 39, 31, 16, 37, 33, 13], [12, 27, 17, 24, 11, 19, 11, 17, 25, 11, 31, 33, 31, 12, 22], [22, 15, 16, 32, 20, 22, 11, 19, 30, 33, 29, 18, 34, 32, 18], [27, 26, 28, 37, 18, 12, 11, 26, 27, 40, 19, 24, 18, 12, 34], [15, 28, 25, 32, 13, 38, 11, 34, 25, 20, 32, 23, 14, 16, 20], [15, 13, 37, 14, 22, 24, 26, 22, 34, 22, 19, 32, 29, 13, 35], [36, 33, 28, 20, 30, 33, 29, 34, 22, 12, 30, 12, 35, 13, 35], [26, 31, 35, 38, 19, 35, 27, 29, 39, 13, 14, 26, 17, 22, 15], [36, 34, 33, 17, 38, 39, 16, 27, 29, 16, 16, 19, 40, 35, 39]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 5, 8, 4, 1, 14, 13, 11, 10, 12, 2, 3, 0, 7, 9], [1, 5, 0, 3, 6, 9, 7, 12, 10, 13, 8, 4, 11, 14, 2], [0, 4, 2, 10, 6, 14, 8, 13, 7, 3, 9, 12, 1, 11, 5], [7, 5, 4, 8, 0, 9, 13, 12, 10, 3, 6, 14, 1, 11, 2], [2, 3, 12, 11, 6, 4, 10, 7, 0, 13, 1, 14, 5, 9, 8], [5, 3, 6, 12, 10, 0, 13, 2, 11, 7, 4, 1, 14, 9, 8], [13, 0, 11, 12, 4, 6, 5, 3, 9, 2, 7, 10, 1, 14, 8], [2, 12, 9, 11, 13, 8, 14, 5, 6, 3, 1, 4, 0, 7, 10], [2, 10, 14, 6, 8, 3, 12, 0, 13, 9, 7, 1, 11, 4, 5], [4, 9, 3, 11, 13, 7, 0, 2, 5, 12, 1, 10, 14, 8, 6], [13, 0, 3, 8, 5, 6, 14, 7, 1, 2, 4, 9, 12, 11, 10], [14, 10, 0, 3, 13, 6, 7, 2, 12, 5, 4, 11, 1, 8, 9], [6, 12, 4, 2, 8, 5, 14, 3, 9, 1, 11, 13, 7, 10, 0], [5, 14, 0, 8, 7, 4, 9, 13, 1, 12, 6, 11, 3, 10, 2], [5, 3, 10, 6, 4, 12, 11, 13, 7, 9, 14, 1, 2, 0, 8], [8, 5, 9, 6, 1, 7, 11, 2, 4, 0, 10, 3, 12, 14, 13], [1, 4, 8, 3, 10, 5, 12, 7, 9, 14, 11, 13, 0, 2, 6], [7, 5, 13, 9, 10, 4, 14, 0, 3, 11, 6, 8, 1, 2, 12], [14, 11, 5, 2, 13, 10, 4, 8, 3, 9, 6, 7, 0, 1, 12], [1, 7, 11, 8, 14, 6, 5, 3, 13, 2, 0, 4, 9, 12, 10]]

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
