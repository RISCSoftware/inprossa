# Job Shop Scheduling instance: la22
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 10
MAX_TIME : int = 7322

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[66, 91, 87, 94, 21, 92, 7, 12, 11, 19], [13, 20, 7, 14, 66, 75, 77, 16, 95, 7], [77, 20, 34, 15, 88, 89, 53, 6, 45, 76], [27, 74, 88, 62, 52, 69, 9, 98, 52, 88], [88, 15, 52, 61, 54, 62, 59, 9, 90, 5], [71, 41, 38, 53, 91, 68, 50, 78, 23, 72], [95, 36, 66, 52, 45, 30, 23, 25, 17, 6], [65, 8, 85, 71, 65, 28, 88, 76, 27, 95], [37, 37, 28, 51, 86, 9, 55, 73, 51, 90], [39, 15, 83, 44, 53, 16, 46, 24, 25, 82], [72, 48, 87, 66, 5, 54, 39, 35, 95, 60], [46, 20, 97, 21, 46, 37, 19, 59, 34, 55], [23, 25, 78, 24, 28, 83, 28, 5, 73, 45], [37, 53, 87, 38, 71, 29, 12, 33, 55, 12], [90, 17, 49, 83, 40, 23, 65, 27, 7, 48]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 5, 4, 2, 7, 3, 1, 0, 8, 6], [3, 2, 4, 1, 9, 0, 6, 5, 7, 8], [8, 7, 2, 0, 9, 5, 6, 3, 1, 4], [3, 2, 6, 4, 7, 8, 5, 9, 0, 1], [4, 6, 1, 2, 7, 0, 8, 5, 3, 9], [6, 0, 4, 3, 7, 8, 1, 5, 2, 9], [3, 9, 6, 5, 0, 8, 4, 2, 7, 1], [4, 1, 8, 0, 7, 6, 5, 3, 9, 2], [9, 1, 4, 3, 8, 2, 6, 0, 7, 5], [3, 2, 6, 9, 7, 0, 4, 5, 1, 8], [1, 4, 0, 2, 9, 6, 7, 8, 5, 3], [1, 3, 0, 2, 9, 7, 8, 4, 6, 5], [5, 3, 6, 1, 0, 7, 8, 9, 2, 4], [1, 0, 7, 4, 3, 5, 9, 8, 6, 2], [4, 8, 2, 3, 1, 6, 7, 9, 5, 0]]

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
