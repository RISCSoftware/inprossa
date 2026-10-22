# Job Shop Scheduling instance: la27
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10832

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[60, 48, 95, 87, 72, 5, 35, 39, 54, 66], [37, 34, 97, 55, 21, 20, 59, 46, 19, 46], [45, 73, 24, 28, 28, 25, 23, 83, 5, 78], [53, 12, 12, 37, 33, 71, 55, 29, 87, 38], [90, 49, 27, 65, 7, 23, 48, 83, 17, 40], [85, 25, 84, 64, 13, 66, 46, 59, 62, 19], [88, 67, 14, 41, 73, 57, 53, 80, 47, 74], [78, 64, 63, 46, 84, 84, 28, 52, 26, 41], [11, 64, 97, 38, 17, 85, 73, 10, 95, 67], [93, 95, 43, 65, 32, 59, 85, 46, 85, 60], [61, 41, 49, 23, 66, 49, 70, 99, 90, 17], [13, 7, 98, 57, 73, 73, 68, 40, 98, 9], [86, 76, 14, 41, 85, 37, 19, 17, 54, 79], [40, 53, 97, 87, 96, 84, 16, 66, 52, 95], [33, 33, 87, 18, 55, 13, 77, 60, 42, 74], [92, 91, 79, 54, 69, 79, 33, 61, 39, 16], [82, 41, 28, 64, 78, 76, 6, 49, 47, 58], [52, 42, 24, 91, 47, 88, 91, 52, 28, 35], [82, 76, 86, 93, 84, 38, 95, 37, 21, 23], [77, 8, 42, 64, 70, 45, 45, 28, 67, 86]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 4, 5, 0, 1, 9, 8, 7, 6, 2], [7, 6, 0, 5, 2, 3, 4, 9, 8, 1], [4, 2, 1, 8, 0, 3, 5, 7, 9, 6], [0, 2, 9, 1, 8, 3, 6, 5, 7, 4], [4, 2, 9, 7, 5, 6, 0, 3, 8, 1], [3, 4, 2, 6, 9, 1, 7, 8, 0, 5], [5, 6, 4, 0, 1, 7, 2, 3, 9, 8], [1, 5, 4, 6, 3, 0, 8, 9, 7, 2], [1, 0, 6, 9, 2, 4, 5, 3, 8, 7], [3, 2, 7, 1, 8, 0, 6, 5, 9, 4], [2, 3, 5, 4, 0, 7, 8, 9, 1, 6], [4, 7, 1, 8, 0, 3, 2, 5, 9, 6], [9, 6, 4, 3, 1, 0, 8, 2, 7, 5], [1, 2, 7, 5, 8, 4, 3, 6, 9, 0], [6, 1, 3, 0, 2, 8, 4, 7, 9, 5], [7, 5, 8, 2, 4, 6, 3, 1, 9, 0], [6, 1, 4, 5, 2, 3, 7, 8, 9, 0], [0, 5, 8, 9, 3, 6, 4, 7, 2, 1], [5, 2, 3, 6, 4, 7, 8, 9, 1, 0], [9, 4, 6, 7, 0, 2, 8, 5, 3, 1]]

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
