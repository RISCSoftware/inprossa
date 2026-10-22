# Job Shop Scheduling instance: la20
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5445

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 81, 55, 40, 32, 37, 6, 19, 81, 40], [21, 70, 65, 64, 46, 65, 25, 77, 55, 15], [85, 37, 40, 24, 44, 83, 89, 31, 84, 29], [80, 77, 56, 8, 30, 59, 38, 80, 41, 97], [91, 40, 88, 17, 71, 50, 59, 80, 56, 7], [8, 9, 58, 77, 29, 96, 45, 10, 54, 36], [70, 92, 98, 87, 99, 27, 86, 96, 28, 73], [95, 92, 85, 52, 81, 32, 39, 59, 41, 56], [60, 45, 88, 12, 7, 22, 93, 49, 69, 27], [21, 61, 68, 26, 82, 71, 44, 99, 33, 84]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 1, 4, 2, 8, 3, 0, 5, 9, 7], [7, 2, 9, 4, 1, 5, 8, 0, 3, 6], [2, 5, 0, 3, 1, 6, 4, 8, 7, 9], [4, 6, 7, 0, 2, 5, 3, 1, 9, 8], [0, 6, 4, 1, 2, 3, 9, 8, 5, 7], [2, 6, 3, 5, 1, 8, 0, 9, 4, 7], [4, 3, 1, 5, 6, 7, 8, 9, 0, 2], [1, 7, 3, 4, 6, 9, 8, 0, 2, 5], [3, 8, 0, 2, 1, 5, 4, 9, 7, 6], [0, 2, 3, 5, 6, 9, 8, 4, 7, 1]]

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
