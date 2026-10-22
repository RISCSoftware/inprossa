# Job Shop Scheduling instance: la15
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 5
MAX_TIME : int = 5445

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 40, 81, 37, 19], [40, 32, 55, 81, 9], [46, 65, 70, 55, 77], [21, 65, 64, 25, 15], [85, 40, 44, 24, 37], [89, 29, 83, 31, 84], [59, 38, 80, 30, 8], [80, 56, 77, 41, 97], [56, 91, 50, 71, 17], [40, 88, 59, 7, 80], [45, 29, 8, 77, 58], [36, 54, 96, 9, 10], [28, 73, 98, 92, 87], [70, 86, 27, 99, 96], [95, 59, 56, 85, 41], [81, 92, 32, 52, 39], [7, 22, 12, 88, 60], [45, 93, 69, 49, 27], [21, 84, 61, 68, 26], [82, 33, 71, 99, 44]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 2, 1, 3, 4], [2, 3, 0, 4, 1], [1, 4, 2, 3, 0], [2, 4, 0, 3, 1], [2, 0, 1, 3, 4], [0, 4, 1, 3, 2], [4, 3, 1, 2, 0], [0, 2, 1, 4, 3], [4, 0, 3, 2, 1], [1, 0, 4, 2, 3], [0, 1, 2, 4, 3], [2, 0, 3, 1, 4], [0, 2, 1, 3, 4], [0, 3, 2, 1, 4], [1, 0, 4, 3, 2], [1, 2, 4, 0, 3], [1, 4, 2, 0, 3], [3, 0, 2, 4, 1], [0, 1, 2, 3, 4], [1, 2, 4, 0, 3]]

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
