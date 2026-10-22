# Job Shop Scheduling instance: la17
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 4676

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[18, 21, 41, 45, 38, 50, 84, 29, 23, 82], [57, 16, 52, 74, 38, 54, 62, 37, 54, 52], [30, 79, 68, 61, 11, 89, 89, 81, 81, 57], [91, 8, 33, 55, 20, 20, 32, 84, 66, 24], [40, 7, 19, 7, 83, 64, 56, 54, 8, 39], [91, 64, 40, 63, 98, 74, 61, 6, 42, 15], [80, 39, 24, 75, 75, 6, 44, 26, 87, 22], [15, 43, 20, 12, 26, 61, 79, 22, 8, 80], [62, 96, 22, 5, 63, 33, 10, 18, 36, 40], [96, 89, 64, 95, 23, 18, 15, 64, 38, 8]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 7, 9, 2, 3, 8, 5, 6, 1, 0], [8, 5, 1, 7, 2, 3, 6, 9, 4, 0], [2, 4, 3, 1, 8, 6, 7, 0, 9, 5], [0, 8, 3, 7, 5, 2, 4, 6, 1, 9], [9, 0, 4, 8, 6, 2, 5, 3, 7, 1], [3, 2, 5, 0, 7, 4, 8, 1, 6, 9], [1, 7, 8, 3, 4, 5, 6, 0, 2, 9], [1, 7, 2, 0, 8, 6, 3, 9, 5, 4], [2, 3, 4, 9, 0, 6, 7, 8, 1, 5], [1, 0, 5, 3, 9, 7, 8, 2, 6, 4]]

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
