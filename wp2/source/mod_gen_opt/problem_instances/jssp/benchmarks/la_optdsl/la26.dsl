# Job Shop Scheduling instance: la26
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10515

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[52, 26, 71, 16, 34, 21, 95, 21, 53, 55], [55, 98, 39, 79, 12, 77, 77, 66, 31, 42], [37, 92, 64, 54, 19, 43, 83, 34, 79, 62], [87, 77, 93, 69, 87, 38, 24, 41, 83, 60], [98, 25, 75, 77, 49, 17, 79, 44, 43, 96], [7, 61, 95, 35, 10, 35, 28, 76, 95, 9], [59, 43, 46, 28, 52, 16, 59, 91, 50, 27], [9, 43, 14, 71, 20, 54, 41, 87, 45, 39], [28, 66, 78, 37, 42, 26, 33, 89, 33, 8], [96, 27, 78, 84, 94, 69, 74, 81, 45, 69], [24, 32, 25, 17, 87, 81, 76, 18, 31, 20], [90, 28, 72, 86, 23, 99, 76, 97, 45, 58], [17, 98, 48, 46, 27, 67, 62, 42, 48, 27], [80, 50, 19, 98, 28, 50, 94, 63, 12, 80], [72, 75, 61, 79, 37, 50, 14, 55, 18, 41], [96, 14, 57, 47, 65, 75, 79, 71, 60, 22], [31, 47, 58, 32, 44, 58, 34, 33, 69, 51], [44, 40, 17, 62, 66, 15, 29, 38, 8, 97], [58, 50, 63, 87, 57, 21, 57, 32, 39, 20], [85, 84, 56, 61, 15, 70, 30, 90, 67, 20]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 7, 6, 9, 2, 1, 5, 4, 0, 3], [4, 5, 3, 9, 0, 8, 6, 7, 2, 1], [5, 4, 2, 6, 1, 7, 0, 3, 9, 8], [1, 5, 0, 3, 2, 7, 8, 6, 9, 4], [2, 5, 6, 9, 1, 3, 8, 0, 7, 4], [1, 4, 0, 2, 9, 8, 5, 3, 7, 6], [5, 9, 0, 4, 6, 3, 2, 1, 8, 7], [5, 9, 8, 7, 4, 6, 3, 0, 1, 2], [1, 8, 0, 2, 9, 3, 5, 6, 4, 7], [4, 3, 6, 5, 2, 8, 1, 9, 7, 0], [4, 7, 9, 2, 3, 8, 5, 6, 1, 0], [8, 5, 1, 7, 2, 3, 6, 9, 4, 0], [2, 4, 3, 1, 8, 6, 7, 0, 9, 5], [0, 8, 3, 7, 5, 2, 4, 6, 1, 9], [9, 0, 4, 8, 6, 2, 5, 3, 7, 1], [3, 2, 5, 0, 7, 4, 8, 1, 6, 9], [1, 7, 8, 3, 4, 5, 6, 0, 2, 9], [1, 7, 2, 0, 8, 6, 3, 9, 5, 4], [2, 3, 4, 9, 0, 6, 7, 8, 1, 5], [1, 0, 5, 3, 9, 7, 8, 2, 6, 4]]

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
