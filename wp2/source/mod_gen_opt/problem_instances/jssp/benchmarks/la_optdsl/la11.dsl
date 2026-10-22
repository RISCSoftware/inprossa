# Job Shop Scheduling instance: la11
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 5
MAX_TIME : int = 5351

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[34, 21, 53, 55, 95], [21, 52, 71, 16, 26], [12, 42, 31, 98, 39], [66, 77, 79, 55, 77], [83, 37, 34, 19, 64], [79, 43, 92, 62, 54], [93, 77, 87, 87, 69], [83, 24, 41, 38, 60], [25, 49, 44, 98, 17], [96, 75, 43, 77, 79], [95, 76, 7, 28, 35], [10, 95, 61, 9, 35], [91, 59, 59, 46, 16], [27, 52, 43, 28, 50], [9, 87, 41, 39, 45], [54, 20, 43, 14, 71], [33, 28, 26, 78, 37], [89, 33, 8, 66, 42], [84, 69, 94, 74, 27], [81, 45, 78, 69, 96]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 1, 0, 3, 4], [0, 3, 1, 4, 2], [0, 1, 2, 4, 3], [2, 3, 4, 0, 1], [0, 4, 3, 1, 2], [4, 2, 0, 3, 1], [0, 4, 2, 1, 3], [4, 3, 1, 2, 0], [4, 1, 0, 2, 3], [0, 1, 2, 4, 3], [0, 3, 1, 4, 2], [4, 2, 0, 1, 3], [1, 2, 4, 0, 3], [2, 1, 4, 0, 3], [4, 0, 3, 2, 1], [1, 0, 4, 3, 2], [4, 1, 3, 0, 2], [1, 0, 2, 3, 4], [4, 0, 2, 1, 3], [4, 2, 1, 3, 0]]

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
