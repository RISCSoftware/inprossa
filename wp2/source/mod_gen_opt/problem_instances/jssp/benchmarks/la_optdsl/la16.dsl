# Job Shop Scheduling instance: la16
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5351

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[21, 71, 16, 52, 26, 34, 53, 21, 55, 95], [55, 31, 98, 79, 12, 66, 42, 77, 77, 39], [34, 64, 62, 19, 92, 79, 43, 54, 83, 37], [87, 69, 87, 38, 24, 83, 41, 93, 77, 60], [98, 44, 25, 75, 43, 49, 96, 77, 17, 79], [35, 76, 28, 10, 61, 9, 95, 35, 7, 95], [16, 59, 46, 91, 43, 50, 52, 59, 28, 27], [45, 87, 41, 20, 54, 43, 14, 9, 39, 71], [33, 37, 66, 33, 26, 8, 28, 89, 42, 78], [69, 81, 94, 96, 27, 69, 45, 78, 74, 84]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 6, 9, 8, 7, 2, 0, 4, 3, 5], [4, 2, 5, 9, 0, 7, 1, 8, 6, 3], [3, 2, 8, 1, 4, 9, 7, 6, 0, 5], [1, 3, 2, 7, 8, 9, 6, 0, 5, 4], [2, 0, 5, 6, 7, 1, 4, 9, 3, 8], [2, 3, 5, 9, 4, 6, 0, 8, 1, 7], [3, 2, 0, 1, 9, 8, 6, 5, 4, 7], [1, 0, 3, 4, 6, 9, 8, 5, 2, 7], [4, 2, 8, 5, 3, 7, 1, 6, 9, 0], [8, 9, 2, 4, 3, 0, 7, 6, 1, 5]]

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
