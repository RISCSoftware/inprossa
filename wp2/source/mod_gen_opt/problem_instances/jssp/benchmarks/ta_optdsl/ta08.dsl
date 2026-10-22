# Job Shop Scheduling instance: ta08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11402

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[83, 1, 96, 54, 30, 80, 81, 9, 49, 32, 19, 92, 65, 88, 64], [4, 68, 79, 21, 84, 92, 66, 51, 83, 96, 68, 38, 38, 99, 76], [46, 57, 66, 75, 88, 58, 56, 35, 59, 82, 24, 96, 24, 55, 80], [34, 69, 53, 98, 8, 81, 81, 38, 39, 3, 59, 81, 30, 76, 71], [85, 80, 36, 57, 96, 34, 14, 3, 90, 99, 9, 42, 95, 27, 27], [28, 11, 66, 2, 35, 69, 61, 84, 73, 56, 98, 81, 72, 92, 23], [21, 5, 95, 5, 22, 16, 77, 85, 76, 46, 36, 89, 99, 44, 37], [49, 80, 61, 87, 41, 6, 83, 79, 44, 83, 9, 84, 99, 38, 68], [77, 51, 68, 69, 6, 26, 99, 6, 34, 27, 51, 82, 5, 90, 1], [85, 64, 55, 76, 89, 68, 34, 14, 52, 33, 91, 4, 18, 95, 76], [40, 8, 36, 5, 1, 51, 33, 80, 90, 75, 47, 65, 42, 16, 11], [38, 83, 48, 74, 15, 10, 89, 41, 97, 97, 16, 47, 21, 95, 20], [89, 22, 11, 15, 37, 65, 28, 39, 88, 14, 28, 6, 24, 4, 23], [14, 66, 4, 58, 7, 6, 5, 48, 54, 59, 2, 1, 4, 82, 75], [24, 66, 4, 20, 79, 50, 23, 15, 14, 91, 86, 96, 63, 16, 3]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 6, 7, 13, 4, 1, 12, 10, 8, 14, 0, 9, 5, 2, 11], [2, 12, 1, 13, 3, 4, 8, 14, 0, 10, 7, 5, 9, 11, 6], [8, 14, 3, 0, 10, 5, 9, 13, 2, 11, 6, 4, 7, 1, 12], [5, 13, 11, 4, 14, 2, 9, 8, 10, 3, 6, 7, 1, 0, 12], [13, 5, 2, 14, 1, 8, 4, 3, 11, 6, 7, 12, 9, 0, 10], [14, 11, 2, 5, 8, 10, 0, 4, 9, 7, 13, 3, 1, 6, 12], [8, 12, 5, 10, 7, 11, 2, 13, 0, 14, 6, 9, 1, 4, 3], [9, 7, 12, 3, 6, 2, 10, 13, 1, 8, 14, 4, 0, 5, 11], [0, 4, 5, 1, 11, 7, 6, 2, 14, 13, 8, 9, 3, 10, 12], [8, 11, 7, 1, 14, 13, 12, 4, 6, 9, 10, 0, 5, 2, 3], [12, 4, 5, 13, 6, 0, 1, 7, 9, 8, 11, 10, 14, 2, 3], [3, 14, 4, 13, 5, 9, 8, 0, 7, 12, 6, 1, 10, 11, 2], [10, 8, 4, 1, 2, 0, 7, 14, 12, 13, 9, 6, 3, 11, 5], [6, 2, 0, 14, 1, 4, 12, 3, 10, 7, 8, 9, 5, 13, 11], [10, 2, 9, 13, 5, 0, 6, 7, 1, 14, 11, 4, 12, 3, 8]]

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
