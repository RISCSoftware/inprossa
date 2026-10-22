# Job Shop Scheduling instance: ta18
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 14919

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[70, 6, 29, 55, 14, 33, 66, 14, 7, 57, 55, 18, 62, 46, 92], [30, 53, 19, 1, 98, 81, 63, 62, 10, 15, 73, 75, 80, 84, 97], [42, 61, 6, 60, 24, 70, 78, 11, 35, 38, 61, 90, 74, 1, 60], [76, 84, 72, 17, 27, 86, 84, 71, 90, 27, 13, 98, 3, 57, 66], [38, 58, 80, 24, 50, 76, 6, 12, 26, 14, 35, 38, 55, 33, 42], [77, 87, 59, 19, 84, 85, 63, 51, 18, 29, 2, 13, 1, 25, 54], [19, 83, 71, 22, 4, 68, 68, 88, 80, 55, 11, 19, 39, 68, 37], [38, 98, 11, 3, 33, 43, 19, 90, 56, 83, 76, 97, 2, 76, 1], [25, 65, 88, 56, 75, 48, 40, 19, 39, 40, 43, 99, 23, 74, 39], [97, 66, 54, 29, 23, 9, 74, 46, 85, 98, 74, 12, 71, 65, 25], [3, 40, 81, 74, 67, 93, 76, 16, 12, 67, 52, 20, 24, 71, 90], [13, 59, 95, 79, 46, 16, 67, 67, 64, 85, 85, 27, 26, 56, 1], [64, 1, 29, 66, 32, 35, 8, 26, 94, 94, 62, 42, 60, 56, 7], [3, 7, 40, 93, 55, 75, 25, 21, 30, 82, 1, 58, 53, 88, 19], [66, 88, 48, 77, 38, 78, 16, 41, 93, 38, 25, 51, 14, 98, 61], [33, 23, 7, 60, 74, 54, 2, 22, 32, 15, 79, 83, 69, 41, 19], [61, 26, 66, 85, 34, 15, 59, 75, 3, 80, 39, 69, 6, 73, 65], [96, 6, 52, 22, 35, 79, 16, 72, 29, 26, 52, 58, 57, 31, 74], [42, 79, 84, 25, 70, 90, 8, 60, 81, 88, 11, 71, 61, 49, 81], [52, 3, 57, 66, 88, 42, 23, 72, 97, 91, 50, 43, 82, 62, 27]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 6, 10, 14, 7, 5, 13, 4, 3, 8, 0, 9, 12, 2, 11], [0, 9, 3, 2, 8, 5, 14, 12, 6, 11, 10, 7, 4, 1, 13], [1, 6, 2, 11, 3, 4, 10, 9, 12, 8, 7, 5, 0, 14, 13], [12, 14, 8, 9, 5, 3, 0, 1, 13, 10, 6, 11, 4, 7, 2], [14, 10, 8, 6, 0, 4, 5, 9, 11, 3, 7, 13, 1, 12, 2], [8, 2, 9, 12, 3, 0, 13, 14, 5, 11, 7, 1, 4, 6, 10], [5, 3, 8, 7, 0, 12, 4, 2, 14, 6, 10, 11, 9, 1, 13], [5, 8, 12, 1, 7, 4, 2, 9, 6, 14, 13, 0, 3, 10, 11], [14, 8, 7, 12, 6, 10, 0, 1, 11, 9, 5, 4, 2, 3, 13], [0, 14, 2, 5, 10, 4, 9, 7, 11, 6, 3, 13, 1, 12, 8], [1, 3, 11, 0, 9, 5, 2, 14, 6, 7, 8, 12, 13, 10, 4], [12, 8, 3, 10, 2, 0, 7, 9, 14, 5, 4, 1, 11, 13, 6], [1, 6, 14, 2, 11, 4, 8, 3, 13, 10, 0, 9, 12, 7, 5], [1, 4, 9, 3, 11, 14, 8, 0, 13, 10, 2, 6, 5, 7, 12], [2, 7, 3, 1, 8, 4, 14, 11, 12, 5, 10, 0, 13, 6, 9], [10, 2, 4, 6, 1, 9, 7, 12, 3, 11, 13, 14, 5, 8, 0], [2, 0, 5, 14, 4, 6, 11, 10, 8, 7, 13, 1, 3, 9, 12], [3, 0, 11, 14, 5, 10, 4, 13, 9, 6, 8, 1, 7, 2, 12], [1, 0, 7, 5, 9, 8, 14, 13, 2, 10, 4, 3, 12, 11, 6], [1, 12, 14, 4, 7, 9, 8, 3, 6, 0, 10, 2, 11, 13, 5]]

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
