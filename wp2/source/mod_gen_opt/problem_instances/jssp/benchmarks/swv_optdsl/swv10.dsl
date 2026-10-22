# Job Shop Scheduling instance: swv10
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15737

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 73, 79, 95, 69, 9, 5, 85, 52, 43, 32, 91, 24, 89, 38], [45, 70, 84, 24, 18, 20, 71, 21, 60, 98, 70, 52, 34, 23, 52], [16, 68, 85, 39, 40, 98, 61, 77, 60, 73, 66, 84, 16, 43, 88], [72, 17, 68, 89, 94, 98, 56, 88, 27, 60, 61, 8, 88, 48, 65], [78, 24, 28, 73, 21, 69, 52, 32, 83, 48, 29, 48, 92, 43, 82], [54, 31, 14, 47, 82, 75, 4, 31, 72, 58, 45, 91, 31, 61, 27], [88, 28, 92, 62, 93, 14, 65, 33, 44, 31, 32, 72, 47, 61, 34], [52, 59, 98, 6, 19, 53, 39, 74, 48, 33, 49, 92, 22, 41, 37], [2, 85, 34, 51, 97, 95, 73, 61, 28, 73, 21, 85, 75, 42, 7], [94, 28, 77, 56, 79, 2, 82, 88, 93, 44, 5, 96, 34, 56, 41], [15, 88, 18, 14, 82, 58, 33, 19, 42, 36, 57, 85, 3, 62, 36], [30, 33, 13, 4, 74, 37, 78, 2, 56, 21, 61, 81, 18, 59, 62], [40, 75, 45, 41, 97, 65, 92, 11, 44, 40, 100, 91, 66, 53, 27], [83, 52, 84, 66, 3, 5, 71, 41, 42, 63, 50, 43, 3, 35, 18], [44, 26, 59, 81, 84, 81, 91, 41, 42, 53, 63, 89, 15, 64, 40], [46, 97, 67, 97, 71, 88, 69, 44, 20, 52, 34, 74, 79, 10, 87], [71, 13, 100, 67, 57, 24, 36, 88, 79, 21, 86, 60, 28, 14, 3], [97, 24, 41, 40, 51, 73, 19, 27, 70, 98, 11, 83, 76, 60, 12], [88, 48, 33, 96, 10, 49, 52, 38, 49, 31, 94, 23, 7, 5, 4], [85, 100, 51, 91, 21, 83, 30, 23, 48, 19, 47, 95, 23, 78, 22]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 2, 1, 0, 6, 4, 5, 8, 9, 11, 14, 7, 10, 13, 12], [6, 1, 4, 3, 5, 0, 2, 8, 7, 9, 10, 13, 12, 11, 14], [6, 4, 1, 0, 5, 2, 3, 10, 7, 11, 9, 14, 8, 13, 12], [0, 1, 3, 4, 2, 6, 5, 10, 13, 9, 12, 8, 7, 11, 14], [6, 2, 5, 0, 4, 1, 3, 14, 8, 11, 10, 13, 12, 9, 7], [4, 6, 5, 3, 0, 1, 2, 8, 12, 7, 9, 13, 14, 11, 10], [4, 1, 5, 6, 3, 0, 2, 7, 9, 8, 14, 11, 13, 12, 10], [0, 1, 5, 3, 2, 6, 4, 8, 12, 10, 13, 11, 7, 14, 9], [0, 6, 3, 2, 4, 5, 1, 14, 9, 12, 8, 11, 7, 13, 10], [5, 1, 0, 2, 6, 4, 3, 9, 10, 12, 14, 8, 7, 13, 11], [2, 5, 6, 3, 1, 0, 4, 13, 10, 9, 14, 12, 7, 11, 8], [3, 6, 0, 4, 2, 1, 5, 14, 13, 9, 10, 11, 7, 8, 12], [5, 1, 6, 0, 3, 2, 4, 7, 12, 8, 9, 11, 14, 13, 10], [1, 2, 0, 3, 5, 6, 4, 13, 10, 11, 12, 14, 8, 9, 7], [4, 0, 1, 6, 2, 5, 3, 13, 7, 11, 8, 14, 9, 10, 12], [1, 0, 5, 4, 3, 6, 2, 14, 12, 11, 13, 10, 8, 7, 9], [3, 6, 4, 2, 1, 5, 0, 7, 14, 8, 9, 12, 11, 10, 13], [0, 6, 2, 4, 1, 5, 3, 9, 12, 13, 10, 11, 7, 8, 14], [5, 3, 1, 4, 6, 0, 2, 10, 13, 7, 12, 14, 9, 11, 8], [2, 0, 5, 6, 1, 3, 4, 12, 9, 8, 11, 10, 7, 14, 13]]

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
