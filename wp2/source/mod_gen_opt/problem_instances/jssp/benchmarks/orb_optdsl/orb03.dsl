# Job Shop Scheduling instance: orb03
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5292

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[96, 69, 25, 5, 55, 15, 88, 11, 17, 82], [11, 48, 67, 38, 18, 24, 62, 92, 96, 81], [67, 63, 93, 85, 25, 72, 51, 81, 58, 15], [30, 35, 27, 82, 44, 92, 25, 49, 28, 77], [53, 83, 73, 26, 77, 33, 92, 99, 38, 38], [20, 44, 81, 88, 66, 70, 91, 37, 55, 96], [21, 93, 22, 56, 34, 40, 53, 46, 29, 63], [32, 63, 36, 26, 17, 85, 15, 55, 16, 82], [73, 46, 89, 24, 99, 92, 7, 51, 19, 14], [52, 20, 70, 98, 23, 15, 81, 71, 24, 81]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 1, 2, 3, 4, 7, 6, 5, 9, 8], [2, 1, 0, 4, 3, 5, 6, 7, 8, 9], [2, 1, 0, 4, 3, 7, 6, 5, 9, 8], [1, 0, 4, 3, 2, 6, 5, 9, 8, 7], [1, 0, 4, 3, 2, 6, 5, 9, 8, 7], [1, 2, 4, 0, 3, 6, 7, 9, 5, 8], [1, 2, 4, 0, 3, 5, 7, 8, 9, 6], [0, 2, 3, 4, 1, 6, 7, 9, 5, 8], [0, 2, 3, 4, 1, 5, 7, 8, 9, 6]]

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
