# Job Shop Scheduling instance: la39
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11554

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[51, 43, 80, 18, 38, 24, 67, 15, 24, 72, 45, 80, 64, 44, 88], [40, 88, 77, 59, 20, 52, 70, 40, 32, 76, 43, 31, 21, 5, 47], [32, 49, 5, 64, 58, 80, 94, 11, 26, 26, 59, 85, 47, 96, 14], [23, 9, 75, 37, 43, 79, 75, 34, 20, 10, 83, 68, 52, 66, 9], [69, 59, 28, 62, 36, 26, 84, 16, 54, 42, 54, 6, 40, 88, 79], [78, 53, 17, 29, 82, 23, 12, 64, 86, 59, 5, 68, 59, 13, 56], [83, 46, 7, 65, 69, 62, 16, 58, 66, 83, 90, 42, 81, 69, 85], [73, 71, 64, 10, 20, 99, 24, 65, 82, 72, 43, 82, 27, 24, 33], [82, 34, 92, 8, 38, 45, 21, 35, 52, 35, 15, 23, 6, 83, 30], [84, 7, 66, 6, 28, 27, 79, 70, 85, 94, 60, 80, 39, 66, 29], [44, 58, 14, 65, 72, 14, 52, 21, 25, 5, 51, 61, 55, 42, 36], [43, 72, 78, 12, 17, 46, 27, 51, 63, 79, 79, 91, 49, 26, 93], [49, 49, 71, 78, 44, 41, 91, 84, 91, 21, 47, 28, 61, 70, 93], [25, 85, 66, 45, 95, 21, 84, 24, 53, 67, 91, 11, 32, 30, 89], [92, 93, 99, 40, 37, 69, 66, 57, 22, 44, 73, 97, 18, 69, 41]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[10, 14, 7, 4, 6, 3, 2, 12, 11, 13, 8, 5, 9, 1, 0], [6, 9, 10, 5, 11, 3, 8, 0, 4, 13, 12, 7, 2, 14, 1], [0, 3, 10, 5, 7, 8, 6, 11, 1, 13, 14, 9, 4, 12, 2], [5, 6, 0, 12, 11, 2, 4, 3, 7, 13, 14, 10, 9, 8, 1], [12, 9, 3, 14, 13, 1, 6, 11, 8, 5, 2, 0, 10, 7, 4], [13, 12, 11, 5, 4, 2, 9, 8, 1, 7, 6, 3, 14, 10, 0], [10, 13, 9, 12, 11, 6, 0, 2, 8, 5, 7, 14, 4, 3, 1], [7, 10, 8, 6, 9, 11, 4, 14, 5, 3, 12, 1, 13, 2, 0], [4, 1, 3, 2, 0, 8, 6, 5, 12, 9, 11, 14, 10, 13, 7], [2, 5, 9, 10, 4, 13, 6, 7, 0, 1, 3, 14, 12, 8, 11], [3, 6, 13, 8, 1, 5, 12, 4, 9, 0, 11, 7, 14, 10, 2], [14, 10, 5, 11, 12, 0, 9, 6, 2, 1, 8, 7, 4, 13, 3], [7, 0, 4, 5, 9, 10, 12, 13, 8, 6, 11, 14, 3, 2, 1], [3, 4, 0, 2, 10, 12, 8, 5, 9, 7, 6, 11, 13, 1, 14], [3, 7, 0, 1, 10, 12, 5, 6, 14, 9, 8, 13, 11, 2, 4]]

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
