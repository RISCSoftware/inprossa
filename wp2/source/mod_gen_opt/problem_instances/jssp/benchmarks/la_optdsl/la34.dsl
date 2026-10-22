# Job Shop Scheduling instance: la34
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 10
MAX_TIME : int = 15341

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[51, 59, 35, 73, 65, 27, 13, 81, 32, 74], [64, 33, 75, 33, 10, 28, 38, 53, 49, 55], [83, 23, 72, 7, 72, 6, 39, 52, 90, 21], [82, 23, 93, 78, 88, 53, 28, 65, 21, 61], [41, 12, 12, 77, 70, 24, 81, 73, 62, 6], [98, 28, 42, 72, 15, 15, 94, 33, 51, 99], [32, 22, 96, 15, 78, 31, 7, 94, 23, 86], [93, 97, 43, 73, 24, 68, 88, 42, 35, 72], [14, 44, 13, 67, 63, 49, 5, 17, 85, 66], [82, 15, 72, 26, 8, 68, 21, 45, 99, 27], [93, 23, 51, 54, 49, 96, 56, 36, 53, 52], [60, 14, 70, 55, 23, 83, 38, 24, 37, 48], [62, 15, 69, 23, 82, 26, 45, 33, 12, 37], [72, 9, 15, 28, 92, 12, 59, 64, 87, 73], [50, 14, 90, 46, 71, 48, 80, 61, 24, 44], [22, 94, 16, 73, 54, 54, 46, 97, 61, 75], [55, 67, 77, 30, 6, 32, 47, 93, 6, 40], [30, 98, 79, 22, 79, 7, 36, 36, 9, 92], [37, 72, 52, 31, 82, 54, 7, 82, 73, 49], [73, 83, 45, 76, 43, 29, 35, 92, 39, 28], [58, 26, 48, 52, 34, 96, 70, 98, 80, 94], [70, 23, 26, 14, 90, 93, 21, 42, 18, 36], [28, 76, 25, 17, 84, 67, 87, 43, 88, 84], [30, 91, 52, 80, 21, 8, 37, 15, 12, 92], [28, 7, 46, 92, 77, 15, 69, 54, 47, 39], [50, 44, 64, 38, 93, 33, 75, 41, 24, 5], [94, 17, 87, 21, 92, 28, 61, 63, 34, 77], [72, 98, 5, 28, 9, 95, 64, 43, 50, 96], [85, 85, 39, 98, 24, 71, 60, 55, 22, 35], [78, 49, 46, 11, 90, 20, 34, 6, 70, 74]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 7, 1, 5, 9, 0, 6, 3, 8, 4], [4, 7, 5, 2, 8, 0, 3, 6, 9, 1], [6, 1, 2, 3, 9, 0, 4, 5, 8, 7], [3, 1, 2, 4, 6, 7, 9, 8, 5, 0], [4, 6, 9, 3, 1, 7, 0, 5, 2, 8], [4, 3, 6, 9, 0, 8, 5, 2, 1, 7], [0, 8, 9, 4, 6, 3, 5, 1, 2, 7], [7, 2, 3, 5, 0, 8, 9, 1, 4, 6], [2, 0, 8, 5, 1, 3, 7, 4, 6, 9], [7, 9, 3, 4, 0, 1, 6, 8, 2, 5], [4, 6, 0, 8, 3, 1, 2, 9, 5, 7], [8, 0, 4, 9, 1, 5, 3, 2, 7, 6], [0, 7, 8, 9, 1, 6, 4, 5, 3, 2], [6, 1, 7, 5, 8, 9, 0, 3, 4, 2], [0, 1, 7, 5, 3, 4, 2, 9, 8, 6], [0, 9, 5, 3, 2, 8, 4, 1, 6, 7], [9, 3, 6, 4, 7, 1, 8, 5, 2, 0], [1, 3, 7, 0, 6, 2, 8, 9, 5, 4], [8, 7, 2, 4, 1, 9, 5, 6, 3, 0], [1, 3, 7, 2, 4, 9, 0, 5, 8, 6], [2, 0, 1, 8, 7, 6, 5, 4, 3, 9], [1, 8, 5, 4, 6, 2, 3, 0, 7, 9], [4, 6, 7, 0, 1, 2, 8, 3, 9, 5], [7, 3, 8, 4, 0, 5, 9, 2, 6, 1], [1, 4, 7, 6, 2, 3, 9, 8, 0, 5], [9, 5, 2, 8, 4, 6, 7, 0, 1, 3], [7, 0, 6, 2, 8, 9, 1, 4, 3, 5], [3, 8, 9, 4, 2, 5, 6, 1, 0, 7], [0, 2, 8, 1, 7, 3, 5, 4, 9, 6], [3, 6, 2, 1, 0, 5, 9, 7, 4, 8]]

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
