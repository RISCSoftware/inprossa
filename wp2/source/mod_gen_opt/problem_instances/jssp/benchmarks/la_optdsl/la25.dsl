# Job Shop Scheduling instance: la25
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 10
MAX_TIME : int = 7509

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[14, 75, 12, 38, 76, 97, 12, 29, 44, 66], [38, 82, 85, 58, 87, 89, 43, 80, 69, 92], [5, 84, 43, 48, 8, 7, 41, 61, 66, 14], [42, 8, 96, 19, 59, 97, 73, 43, 74, 41], [55, 70, 75, 42, 37, 23, 48, 5, 38, 7], [9, 72, 31, 79, 73, 95, 25, 43, 60, 56], [97, 64, 78, 21, 94, 31, 53, 16, 86, 7], [86, 85, 63, 61, 65, 30, 32, 33, 44, 59], [44, 16, 11, 45, 30, 84, 93, 60, 61, 90], [36, 31, 47, 52, 32, 11, 28, 35, 20, 49], [20, 49, 74, 10, 17, 34, 85, 77, 68, 84], [85, 7, 71, 59, 76, 17, 29, 17, 48, 13], [15, 87, 11, 39, 39, 43, 19, 32, 16, 64], [32, 92, 33, 82, 83, 57, 99, 91, 99, 8], [88, 7, 27, 38, 91, 69, 21, 62, 39, 48]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 4, 3, 2, 0, 5, 9, 1, 7, 6], [5, 3, 2, 4, 6, 9, 0, 1, 7, 8], [9, 1, 0, 6, 4, 7, 3, 5, 8, 2], [2, 1, 0, 5, 4, 7, 9, 8, 3, 6], [6, 2, 3, 8, 4, 7, 1, 5, 9, 0], [8, 2, 7, 0, 5, 3, 4, 6, 9, 1], [0, 2, 3, 5, 4, 9, 8, 6, 7, 1], [3, 7, 9, 0, 2, 4, 5, 1, 8, 6], [2, 3, 4, 6, 1, 9, 8, 0, 5, 7], [7, 8, 4, 6, 0, 5, 2, 9, 3, 1], [8, 6, 7, 4, 5, 3, 0, 2, 9, 1], [1, 5, 8, 6, 4, 0, 3, 2, 7, 9], [2, 6, 7, 1, 4, 8, 0, 3, 9, 5], [6, 2, 5, 8, 1, 7, 9, 4, 3, 0], [4, 7, 8, 1, 3, 2, 6, 9, 5, 0]]

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
