# Job Shop Scheduling instance: orb05
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 4908

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[11, 93, 48, 76, 13, 71, 59, 90, 10, 65], [52, 76, 84, 73, 56, 10, 26, 43, 39, 49], [28, 44, 26, 66, 68, 74, 27, 14, 6, 21], [18, 58, 62, 46, 25, 6, 60, 28, 80, 30], [78, 47, 29, 16, 29, 57, 78, 87, 39, 73], [66, 51, 12, 64, 67, 15, 66, 26, 20, 98], [23, 76, 45, 75, 24, 18, 83, 15, 88, 17], [56, 83, 80, 16, 31, 93, 30, 29, 66, 28], [79, 69, 82, 16, 62, 41, 91, 35, 34, 75], [5, 19, 20, 12, 94, 60, 99, 31, 96, 63]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 8, 0, 7, 6, 5, 3, 2, 4, 1], [8, 9, 0, 7, 5, 4, 6, 2, 3, 1], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [0, 1, 3, 2, 6, 4, 5, 7, 8, 9], [0, 1, 7, 5, 4, 6, 3, 2, 8, 9], [9, 8, 3, 7, 5, 4, 6, 2, 1, 0], [8, 9, 6, 7, 5, 3, 4, 2, 1, 0], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [9, 8, 2, 4, 5, 3, 6, 7, 0, 1], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]

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
