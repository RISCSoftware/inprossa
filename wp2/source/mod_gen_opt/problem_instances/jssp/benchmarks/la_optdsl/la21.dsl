# Job Shop Scheduling instance: la21
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 10
MAX_TIME : int = 7994

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[34, 55, 95, 16, 21, 71, 53, 52, 21, 26], [39, 31, 12, 42, 79, 77, 77, 98, 55, 66], [19, 83, 34, 92, 54, 79, 62, 37, 64, 43], [60, 87, 24, 77, 69, 38, 87, 41, 83, 93], [79, 77, 98, 96, 17, 44, 43, 75, 49, 25], [35, 95, 9, 10, 35, 7, 28, 61, 95, 76], [28, 59, 16, 43, 46, 50, 52, 27, 59, 91], [9, 20, 39, 54, 45, 71, 87, 41, 43, 14], [28, 33, 78, 26, 37, 8, 66, 89, 42, 33], [94, 84, 78, 81, 74, 27, 69, 69, 45, 96], [31, 24, 20, 17, 25, 81, 76, 87, 32, 18], [28, 97, 58, 45, 76, 99, 23, 72, 90, 86], [27, 48, 27, 62, 98, 67, 48, 42, 46, 17], [12, 50, 80, 50, 80, 19, 28, 63, 94, 98], [61, 55, 37, 14, 50, 79, 41, 72, 18, 75]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 3, 5, 9, 4, 6, 0, 8, 1, 7], [3, 2, 0, 1, 9, 8, 6, 5, 4, 7], [1, 0, 3, 4, 6, 9, 8, 5, 2, 7], [4, 2, 8, 5, 3, 7, 1, 6, 9, 0], [8, 9, 2, 4, 3, 0, 7, 6, 1, 5], [8, 7, 6, 9, 2, 1, 5, 4, 0, 3], [4, 5, 3, 9, 0, 8, 6, 7, 2, 1], [5, 4, 2, 6, 1, 7, 0, 3, 9, 8], [1, 5, 0, 3, 2, 7, 8, 6, 9, 4], [2, 5, 6, 9, 1, 3, 8, 0, 7, 4], [1, 4, 0, 2, 9, 8, 5, 3, 7, 6], [5, 9, 0, 4, 6, 3, 2, 1, 8, 7], [5, 9, 8, 7, 4, 6, 3, 0, 1, 2], [1, 8, 0, 2, 9, 3, 5, 6, 4, 7], [4, 3, 6, 5, 2, 8, 1, 9, 7, 0]]

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
