# Job Shop Scheduling instance: orb06
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5614

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[99, 74, 49, 67, 17, 7, 9, 39, 35, 49], [49, 67, 82, 92, 62, 84, 45, 30, 42, 71], [26, 33, 82, 98, 83, 16, 64, 65, 36, 77], [41, 62, 73, 94, 51, 46, 55, 31, 64, 46], [68, 26, 50, 46, 25, 88, 6, 13, 98, 84], [24, 80, 91, 55, 48, 99, 72, 91, 84, 12], [16, 13, 9, 58, 23, 85, 36, 89, 71, 41], [54, 41, 38, 53, 11, 74, 88, 46, 41, 65], [53, 50, 40, 90, 7, 80, 57, 60, 91, 47], [45, 59, 81, 99, 71, 19, 75, 77, 94, 95]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 3, 4, 2, 1, 5, 8, 6, 7, 9], [0, 3, 1, 2, 5, 4, 6, 7, 9, 8], [0, 1, 4, 3, 6, 5, 2, 9, 7, 8], [1, 0, 5, 3, 4, 7, 2, 8, 9, 6], [0, 6, 2, 3, 1, 8, 4, 9, 7, 5], [2, 3, 0, 1, 4, 7, 5, 6, 8, 9], [2, 0, 3, 4, 1, 5, 9, 6, 7, 8], [2, 1, 4, 0, 7, 5, 3, 9, 6, 8], [2, 0, 8, 3, 6, 1, 4, 7, 9, 5]]

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
