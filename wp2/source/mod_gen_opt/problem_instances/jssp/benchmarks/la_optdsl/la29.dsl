# Job Shop Scheduling instance: la29
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 9929

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[14, 38, 44, 76, 97, 12, 75, 66, 12, 29], [43, 85, 82, 38, 58, 89, 92, 87, 69, 80], [41, 7, 5, 43, 14, 8, 61, 84, 66, 48], [42, 74, 59, 41, 8, 73, 43, 96, 19, 97], [23, 42, 37, 55, 7, 5, 70, 38, 75, 48], [9, 43, 31, 25, 73, 95, 79, 72, 60, 56], [7, 21, 53, 16, 94, 97, 78, 64, 86, 31], [65, 59, 85, 33, 30, 44, 61, 86, 63, 32], [45, 44, 61, 93, 30, 90, 84, 11, 16, 60], [47, 36, 31, 49, 20, 28, 52, 35, 11, 32], [77, 10, 68, 17, 85, 84, 20, 49, 74, 34], [17, 7, 85, 29, 17, 76, 59, 71, 13, 48], [87, 39, 43, 11, 15, 32, 64, 19, 39, 16], [33, 99, 32, 91, 82, 92, 99, 57, 83, 8], [91, 39, 69, 27, 7, 21, 38, 62, 88, 48], [67, 80, 24, 88, 18, 44, 45, 64, 80, 38], [59, 72, 47, 40, 21, 43, 51, 52, 24, 15], [70, 31, 20, 76, 40, 43, 32, 88, 5, 77], [47, 64, 85, 49, 58, 26, 32, 80, 14, 94], [59, 96, 5, 79, 34, 75, 26, 9, 23, 11]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 2, 7, 0, 5, 3, 4, 6, 9, 1], [0, 2, 3, 5, 4, 9, 8, 6, 7, 1], [3, 7, 9, 0, 2, 4, 5, 1, 8, 6], [2, 3, 4, 6, 1, 9, 8, 0, 5, 7], [7, 8, 4, 6, 0, 5, 2, 9, 3, 1], [8, 6, 7, 4, 5, 3, 0, 2, 9, 1], [1, 5, 8, 6, 4, 0, 3, 2, 7, 9], [2, 6, 7, 1, 4, 8, 0, 3, 9, 5], [6, 2, 5, 8, 1, 7, 9, 4, 3, 0], [4, 7, 8, 1, 3, 2, 6, 9, 5, 0], [2, 4, 9, 5, 0, 1, 8, 6, 7, 3], [0, 5, 1, 3, 2, 4, 6, 8, 9, 7], [6, 4, 8, 7, 2, 3, 5, 0, 1, 9], [5, 3, 6, 4, 8, 2, 9, 7, 1, 0], [3, 5, 2, 8, 7, 6, 1, 9, 4, 0], [2, 7, 3, 0, 4, 1, 8, 9, 5, 6], [9, 3, 6, 4, 7, 5, 0, 8, 1, 2], [3, 2, 6, 8, 1, 7, 0, 5, 9, 4], [4, 5, 9, 3, 7, 1, 0, 8, 2, 6], [5, 2, 0, 7, 8, 4, 3, 6, 9, 1]]

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
