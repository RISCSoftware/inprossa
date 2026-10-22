# Job Shop Scheduling instance: orb02
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5255

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[72, 54, 33, 86, 75, 16, 96, 7, 99, 76], [16, 88, 48, 52, 60, 29, 18, 89, 80, 76], [47, 11, 14, 56, 16, 83, 10, 61, 24, 58], [49, 31, 17, 50, 63, 35, 65, 23, 50, 29], [55, 6, 28, 96, 86, 99, 14, 70, 64, 24], [46, 23, 70, 19, 54, 22, 85, 87, 79, 93], [76, 60, 76, 98, 76, 50, 86, 14, 27, 57], [93, 27, 57, 87, 86, 54, 24, 49, 20, 47], [28, 11, 78, 85, 63, 81, 10, 9, 46, 32], [22, 76, 89, 13, 88, 10, 75, 98, 78, 17]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 3, 4, 8, 9, 6, 7, 5, 2, 1], [0, 7, 3, 2, 6, 4, 1, 5, 8, 9], [0, 1, 3, 8, 5, 2, 4, 7, 6, 9], [0, 6, 1, 3, 5, 2, 9, 7, 8, 4], [4, 0, 6, 8, 2, 3, 9, 7, 5, 1], [4, 3, 0, 9, 2, 1, 8, 7, 6, 5], [4, 6, 9, 3, 8, 2, 7, 5, 0, 1], [2, 6, 8, 7, 4, 9, 3, 1, 5, 0], [2, 9, 5, 8, 6, 3, 7, 4, 1, 0]]

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
