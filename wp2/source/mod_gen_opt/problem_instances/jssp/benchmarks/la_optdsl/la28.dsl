# Job Shop Scheduling instance: la28
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10682

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[32, 81, 55, 40, 6, 19, 81, 37, 40, 9], [70, 55, 21, 64, 46, 25, 65, 77, 65, 15], [84, 89, 24, 44, 85, 31, 29, 83, 37, 40], [80, 59, 8, 30, 77, 38, 80, 56, 41, 97], [40, 71, 91, 7, 59, 80, 50, 56, 17, 88], [36, 10, 45, 9, 54, 96, 8, 77, 29, 58], [99, 86, 92, 28, 98, 70, 87, 96, 73, 27], [95, 85, 56, 52, 59, 41, 81, 39, 32, 92], [7, 69, 93, 27, 22, 88, 45, 60, 49, 12], [33, 61, 44, 26, 84, 82, 68, 21, 71, 99], [43, 72, 30, 98, 75, 26, 8, 74, 19, 38], [19, 67, 73, 85, 26, 39, 9, 23, 13, 43], [72, 46, 80, 93, 61, 7, 42, 50, 55, 57], [99, 91, 11, 68, 43, 96, 72, 11, 60, 68], [69, 43, 12, 40, 70, 74, 34, 7, 30, 84], [99, 27, 59, 72, 9, 45, 49, 63, 69, 60], [75, 17, 91, 50, 65, 37, 98, 90, 71, 8], [72, 9, 31, 49, 91, 62, 90, 72, 98, 38], [35, 63, 25, 35, 21, 47, 52, 80, 39, 74], [68, 24, 58, 52, 5, 20, 50, 57, 88, 53]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 1, 4, 7, 0, 5, 9, 3, 2, 6], [2, 3, 7, 4, 1, 8, 9, 0, 5, 6], [7, 4, 3, 1, 2, 8, 9, 6, 5, 0], [4, 5, 0, 2, 6, 3, 1, 7, 9, 8], [6, 2, 0, 7, 9, 8, 3, 5, 1, 4], [7, 9, 0, 6, 4, 8, 2, 5, 1, 3], [6, 8, 3, 0, 1, 4, 5, 9, 2, 7], [1, 3, 5, 4, 0, 2, 6, 8, 9, 7], [1, 7, 4, 6, 5, 0, 8, 3, 9, 2], [7, 2, 8, 5, 1, 6, 3, 0, 9, 4], [8, 0, 4, 5, 9, 1, 7, 6, 3, 2], [6, 2, 8, 1, 9, 4, 7, 0, 5, 3], [8, 7, 5, 3, 2, 4, 9, 1, 0, 6], [4, 0, 9, 5, 7, 3, 2, 8, 6, 1], [9, 0, 3, 8, 1, 6, 2, 5, 4, 7], [7, 3, 4, 5, 2, 6, 0, 9, 1, 8], [0, 3, 2, 7, 8, 5, 9, 1, 6, 4], [9, 1, 3, 6, 2, 8, 7, 0, 5, 4], [4, 2, 5, 6, 8, 7, 3, 1, 0, 9], [2, 5, 9, 8, 0, 6, 3, 7, 1, 4]]

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
