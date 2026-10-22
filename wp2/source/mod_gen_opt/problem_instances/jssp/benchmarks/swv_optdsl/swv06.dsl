# Job Shop Scheduling instance: swv06
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15239

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[16, 58, 22, 24, 53, 9, 57, 63, 92, 43, 41, 26, 20, 44, 93], [89, 94, 86, 13, 54, 41, 55, 98, 38, 80, 1, 100, 90, 63, 14], [26, 96, 32, 75, 9, 57, 39, 54, 28, 8, 30, 57, 75, 9, 41], [37, 36, 63, 24, 71, 97, 74, 19, 45, 24, 71, 53, 61, 6, 32], [57, 55, 21, 84, 23, 79, 90, 8, 59, 99, 41, 68, 14, 4, 55], [10, 81, 13, 78, 78, 10, 48, 37, 21, 88, 75, 11, 55, 93, 51], [100, 52, 54, 37, 26, 74, 87, 13, 88, 94, 73, 55, 68, 50, 88], [47, 70, 7, 72, 62, 30, 95, 18, 65, 69, 89, 89, 64, 81, 25], [1, 10, 72, 59, 92, 53, 89, 52, 48, 8, 69, 49, 26, 76, 97], [85, 47, 45, 99, 39, 32, 87, 56, 98, 13, 96, 71, 95, 11, 78], [17, 21, 87, 41, 41, 31, 96, 17, 95, 29, 3, 71, 64, 97, 31], [9, 87, 34, 62, 56, 66, 95, 56, 42, 86, 68, 82, 82, 52, 97], [86, 37, 49, 2, 30, 63, 4, 47, 84, 5, 13, 39, 18, 76, 63], [29, 34, 53, 7, 19, 26, 63, 22, 98, 77, 11, 87, 5, 44, 42], [44, 91, 91, 58, 77, 51, 14, 1, 17, 55, 40, 95, 31, 54, 37], [59, 47, 56, 39, 7, 43, 39, 75, 43, 32, 6, 93, 69, 47, 93], [24, 30, 97, 17, 7, 55, 8, 70, 87, 29, 20, 29, 51, 14, 32], [29, 99, 17, 96, 50, 67, 91, 91, 14, 14, 19, 36, 11, 83, 6], [7, 60, 31, 76, 23, 83, 30, 73, 76, 17, 53, 9, 72, 89, 24], [63, 89, 2, 46, 86, 74, 1, 34, 30, 19, 48, 75, 72, 47, 58]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 6, 2, 4, 5, 3, 0, 10, 8, 12, 7, 13, 14, 9, 11], [2, 1, 0, 3, 6, 4, 5, 7, 13, 14, 9, 11, 12, 10, 8], [1, 6, 3, 4, 5, 0, 2, 12, 14, 10, 11, 13, 9, 7, 8], [3, 2, 5, 0, 6, 1, 4, 14, 12, 8, 11, 13, 10, 9, 7], [3, 0, 1, 5, 2, 6, 4, 11, 14, 10, 9, 12, 8, 13, 7], [4, 2, 1, 3, 0, 5, 6, 9, 11, 7, 12, 14, 13, 10, 8], [6, 2, 3, 1, 5, 4, 0, 8, 12, 10, 14, 7, 11, 9, 13], [4, 5, 6, 2, 0, 3, 1, 10, 9, 7, 13, 8, 14, 12, 11], [6, 1, 0, 3, 4, 5, 2, 14, 7, 8, 13, 10, 9, 12, 11], [6, 2, 4, 1, 0, 5, 3, 10, 8, 11, 7, 12, 14, 9, 13], [0, 2, 3, 6, 5, 4, 1, 8, 11, 13, 14, 10, 7, 9, 12], [6, 0, 4, 1, 3, 5, 2, 9, 14, 8, 7, 12, 10, 13, 11], [3, 1, 2, 0, 6, 5, 4, 14, 8, 10, 13, 9, 12, 7, 11], [0, 6, 1, 3, 5, 4, 2, 12, 10, 13, 14, 7, 9, 11, 8], [6, 4, 1, 2, 0, 3, 5, 13, 9, 7, 12, 8, 14, 11, 10], [5, 4, 1, 6, 2, 0, 3, 13, 10, 12, 9, 11, 7, 8, 14], [4, 1, 3, 6, 0, 2, 5, 7, 10, 8, 12, 13, 11, 9, 14], [2, 4, 3, 0, 1, 5, 6, 10, 13, 12, 7, 8, 11, 14, 9], [0, 6, 3, 5, 1, 2, 4, 8, 14, 11, 10, 13, 12, 7, 9], [3, 0, 2, 1, 6, 5, 4, 7, 9, 12, 13, 11, 8, 14, 10]]

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
