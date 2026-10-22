# Job Shop Scheduling instance: ta04
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 10949

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[72, 51, 42, 31, 61, 46, 88, 33, 27, 85, 70, 56, 70, 50, 25], [19, 79, 79, 47, 40, 67, 43, 65, 84, 61, 30, 56, 19, 91, 68], [94, 7, 2, 95, 60, 82, 76, 36, 8, 85, 7, 44, 2, 72, 91], [58, 67, 84, 34, 19, 19, 94, 41, 98, 96, 25, 40, 74, 88, 74], [45, 60, 8, 29, 32, 42, 25, 4, 71, 79, 93, 28, 30, 17, 43], [84, 56, 46, 93, 66, 84, 40, 4, 15, 15, 54, 39, 77, 55, 31], [65, 91, 17, 47, 77, 68, 62, 22, 72, 47, 38, 7, 11, 22, 63], [12, 21, 60, 42, 22, 84, 60, 52, 25, 53, 53, 56, 29, 83, 32], [48, 28, 70, 26, 68, 4, 19, 92, 24, 54, 57, 47, 84, 85, 95], [36, 34, 65, 64, 30, 41, 53, 74, 44, 13, 41, 6, 32, 94, 37], [62, 9, 89, 37, 28, 23, 13, 60, 46, 94, 85, 72, 18, 79, 11], [74, 61, 43, 26, 97, 62, 40, 60, 62, 78, 42, 8, 21, 11, 70], [9, 22, 9, 8, 54, 32, 92, 76, 2, 63, 63, 98, 42, 12, 41], [67, 7, 91, 52, 87, 4, 1, 56, 82, 47, 35, 8, 92, 39, 11], [44, 24, 24, 14, 34, 57, 30, 64, 4, 14, 69, 95, 22, 60, 61]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 7, 6, 14, 9, 8, 5, 4, 10, 1, 0, 12, 11, 2, 13], [1, 11, 0, 5, 8, 13, 3, 10, 9, 2, 12, 6, 4, 7, 14], [7, 3, 8, 11, 0, 4, 9, 13, 1, 10, 6, 5, 14, 12, 2], [6, 11, 5, 13, 3, 2, 1, 4, 9, 12, 8, 0, 14, 7, 10], [1, 11, 6, 5, 8, 7, 12, 9, 2, 14, 13, 3, 0, 4, 10], [11, 2, 12, 1, 14, 0, 6, 9, 3, 13, 7, 10, 4, 5, 8], [14, 7, 11, 0, 12, 8, 9, 10, 3, 13, 4, 1, 2, 6, 5], [7, 4, 13, 5, 14, 11, 2, 12, 6, 1, 0, 10, 9, 3, 8], [7, 4, 14, 10, 3, 0, 13, 8, 1, 2, 6, 12, 11, 9, 5], [2, 12, 10, 3, 6, 5, 14, 9, 13, 4, 0, 11, 7, 8, 1], [11, 9, 3, 7, 6, 4, 0, 2, 5, 1, 10, 8, 13, 12, 14], [0, 4, 1, 9, 2, 11, 13, 10, 7, 6, 8, 12, 14, 3, 5], [6, 0, 4, 10, 2, 14, 9, 13, 11, 12, 1, 8, 5, 3, 7], [5, 10, 13, 2, 7, 4, 8, 6, 9, 0, 12, 11, 1, 14, 3], [11, 2, 0, 4, 14, 5, 9, 10, 6, 12, 8, 1, 7, 3, 13]]

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
