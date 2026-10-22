# Job Shop Scheduling instance: ta20
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15133

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[84, 58, 71, 26, 98, 36, 12, 30, 87, 95, 45, 28, 73, 73, 45], [29, 22, 47, 75, 94, 15, 4, 82, 14, 35, 79, 34, 57, 23, 56], [73, 36, 48, 26, 49, 60, 15, 66, 90, 39, 8, 74, 63, 94, 91], [1, 35, 23, 93, 75, 50, 40, 60, 41, 7, 57, 72, 40, 75, 7], [13, 15, 17, 14, 67, 94, 18, 52, 53, 16, 33, 61, 47, 65, 39], [54, 80, 87, 36, 54, 72, 17, 44, 37, 88, 77, 84, 17, 82, 90], [4, 62, 33, 62, 86, 30, 39, 67, 42, 31, 83, 39, 67, 67, 31], [29, 29, 69, 26, 55, 46, 53, 65, 97, 24, 69, 22, 17, 39, 13], [12, 73, 36, 70, 12, 80, 99, 70, 51, 14, 71, 28, 35, 58, 35], [61, 49, 74, 90, 60, 88, 3, 60, 59, 94, 91, 34, 26, 4, 26], [89, 90, 95, 32, 18, 73, 9, 19, 97, 58, 36, 62, 13, 16, 1], [71, 47, 95, 7, 63, 49, 24, 46, 72, 73, 19, 96, 41, 15, 81], [45, 9, 97, 62, 77, 78, 70, 19, 86, 15, 23, 46, 32, 6, 70], [74, 46, 98, 1, 53, 59, 86, 98, 76, 12, 91, 98, 98, 11, 27], [73, 70, 14, 32, 19, 57, 17, 96, 56, 73, 32, 7, 79, 10, 91], [39, 87, 11, 81, 7, 79, 24, 9, 58, 42, 67, 27, 20, 19, 67], [76, 89, 64, 14, 11, 14, 99, 85, 81, 3, 46, 47, 40, 81, 27], [55, 71, 5, 83, 16, 4, 20, 15, 60, 8, 93, 33, 63, 71, 29], [92, 25, 8, 86, 22, 79, 23, 96, 24, 94, 97, 17, 48, 67, 47], [5, 77, 74, 59, 13, 57, 62, 37, 54, 69, 80, 35, 88, 47, 98]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 0, 12, 4, 1, 9, 2, 11, 10, 14, 5, 6, 13, 3, 8], [4, 8, 7, 3, 9, 13, 12, 0, 11, 10, 1, 6, 5, 14, 2], [1, 4, 7, 13, 3, 8, 10, 5, 12, 14, 9, 6, 2, 0, 11], [5, 11, 9, 12, 7, 1, 6, 13, 8, 2, 0, 14, 3, 4, 10], [4, 11, 12, 1, 0, 9, 6, 13, 2, 14, 5, 10, 3, 8, 7], [2, 6, 3, 8, 14, 0, 4, 10, 11, 1, 7, 13, 12, 5, 9], [4, 14, 5, 10, 8, 7, 6, 1, 0, 12, 9, 13, 11, 3, 2], [7, 10, 11, 14, 3, 2, 4, 5, 1, 12, 9, 6, 13, 0, 8], [14, 11, 0, 13, 3, 2, 1, 8, 5, 7, 4, 12, 6, 10, 9], [0, 5, 12, 1, 13, 10, 9, 4, 2, 8, 14, 11, 7, 6, 3], [4, 3, 8, 12, 9, 11, 2, 14, 5, 7, 13, 6, 10, 1, 0], [9, 6, 1, 0, 14, 7, 13, 12, 2, 11, 5, 8, 10, 3, 4], [4, 3, 0, 14, 13, 9, 7, 2, 11, 8, 10, 1, 6, 12, 5], [12, 10, 3, 6, 4, 5, 0, 7, 2, 8, 13, 11, 14, 9, 1], [14, 7, 5, 8, 11, 0, 2, 13, 12, 4, 6, 1, 10, 9, 3], [6, 14, 12, 2, 7, 5, 8, 13, 11, 9, 0, 3, 4, 1, 10], [9, 5, 14, 10, 12, 1, 4, 13, 0, 11, 3, 2, 7, 6, 8], [9, 12, 4, 14, 11, 8, 0, 7, 5, 3, 1, 10, 6, 13, 2], [12, 2, 3, 14, 5, 1, 6, 11, 13, 9, 7, 10, 8, 0, 4], [3, 12, 10, 5, 14, 0, 9, 8, 13, 6, 11, 1, 7, 2, 4]]

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
