# Job Shop Scheduling instance: la24
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 10
MAX_TIME : int = 7727

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 75, 72, 74, 30, 43, 38, 98, 26, 19], [19, 73, 43, 23, 85, 39, 13, 26, 67, 9], [50, 93, 80, 7, 55, 61, 57, 72, 42, 46], [68, 43, 99, 60, 68, 91, 11, 96, 11, 72], [84, 34, 40, 7, 70, 74, 12, 43, 69, 30], [60, 49, 59, 72, 63, 69, 99, 45, 27, 9], [71, 91, 65, 90, 98, 8, 50, 75, 37, 17], [62, 90, 98, 31, 91, 38, 72, 9, 72, 49], [35, 39, 74, 25, 47, 52, 63, 21, 35, 80], [58, 5, 50, 52, 88, 20, 68, 24, 53, 57], [99, 91, 33, 19, 18, 38, 24, 35, 49, 9], [68, 60, 77, 10, 60, 15, 72, 18, 90, 18], [79, 60, 56, 91, 40, 86, 72, 80, 89, 51], [10, 92, 23, 46, 40, 72, 6, 23, 95, 34], [24, 29, 49, 55, 47, 77, 77, 8, 28, 48]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 9, 0, 6, 4, 8, 2, 5, 1, 3], [6, 8, 3, 0, 1, 4, 5, 9, 2, 7], [1, 3, 5, 4, 0, 2, 6, 8, 9, 7], [1, 7, 4, 6, 5, 0, 8, 3, 9, 2], [7, 2, 8, 5, 1, 6, 3, 0, 9, 4], [8, 0, 4, 5, 9, 1, 7, 6, 3, 2], [6, 2, 8, 1, 9, 4, 7, 0, 5, 3], [8, 7, 5, 3, 2, 4, 9, 1, 0, 6], [4, 0, 9, 5, 7, 3, 2, 8, 6, 1], [9, 0, 3, 8, 1, 6, 2, 5, 4, 7], [7, 3, 4, 5, 2, 6, 0, 9, 1, 8], [0, 3, 2, 7, 8, 5, 9, 1, 6, 4], [9, 1, 3, 6, 2, 8, 7, 0, 5, 4], [4, 2, 5, 6, 8, 7, 3, 1, 0, 9], [2, 5, 9, 8, 0, 6, 3, 7, 1, 4]]

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
