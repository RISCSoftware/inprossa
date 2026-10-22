# Job Shop Scheduling instance: ta05
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11252

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[40, 96, 59, 95, 76, 75, 23, 65, 65, 16, 71, 52, 84, 99, 24], [2, 88, 99, 52, 68, 13, 38, 35, 57, 37, 93, 38, 68, 94, 71], [87, 46, 14, 87, 30, 79, 62, 37, 54, 1, 97, 16, 2, 51, 96], [19, 15, 42, 8, 72, 15, 76, 25, 78, 84, 62, 70, 81, 16, 97], [68, 71, 3, 68, 91, 37, 73, 21, 85, 79, 51, 50, 21, 30, 64], [14, 1, 29, 72, 6, 31, 98, 50, 83, 2, 86, 33, 33, 98, 59], [21, 80, 99, 70, 80, 71, 47, 96, 56, 78, 53, 10, 92, 1, 33], [29, 85, 89, 10, 30, 38, 38, 48, 16, 65, 90, 73, 88, 46, 47], [37, 9, 49, 23, 1, 78, 39, 15, 9, 41, 35, 83, 8, 61, 60], [1, 73, 47, 46, 10, 37, 60, 84, 26, 11, 37, 79, 75, 49, 51], [22, 49, 33, 2, 24, 3, 73, 68, 21, 61, 69, 94, 43, 39, 48], [81, 46, 21, 23, 86, 19, 64, 52, 22, 50, 11, 73, 77, 16, 75], [21, 80, 30, 32, 22, 23, 85, 92, 14, 13, 68, 60, 45, 32, 90], [29, 95, 52, 59, 33, 12, 73, 96, 75, 12, 83, 3, 90, 57, 6], [94, 18, 54, 42, 70, 29, 43, 50, 75, 70, 40, 48, 1, 27, 12]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[12, 1, 4, 9, 13, 0, 11, 8, 3, 5, 6, 14, 10, 2, 7], [5, 1, 14, 10, 13, 9, 6, 12, 8, 2, 7, 0, 3, 4, 11], [6, 3, 10, 7, 13, 4, 5, 9, 8, 2, 0, 1, 11, 14, 12], [10, 7, 5, 0, 9, 13, 2, 8, 1, 14, 11, 3, 12, 6, 4], [6, 12, 14, 1, 7, 5, 11, 0, 2, 3, 8, 13, 4, 9, 10], [4, 7, 6, 0, 8, 13, 12, 14, 3, 2, 5, 9, 10, 1, 11], [10, 11, 6, 9, 0, 2, 1, 8, 12, 7, 5, 3, 13, 14, 4], [3, 10, 5, 6, 8, 4, 0, 14, 2, 7, 9, 11, 12, 1, 13], [1, 2, 6, 7, 10, 12, 14, 8, 0, 3, 13, 5, 4, 9, 11], [12, 7, 6, 14, 3, 4, 0, 13, 10, 8, 11, 9, 5, 2, 1], [4, 3, 8, 14, 2, 13, 5, 6, 10, 12, 7, 11, 1, 9, 0], [6, 12, 7, 5, 2, 4, 13, 11, 8, 0, 10, 3, 1, 9, 14], [12, 13, 8, 7, 1, 6, 0, 5, 9, 10, 4, 2, 14, 3, 11], [12, 1, 4, 8, 6, 10, 7, 3, 0, 5, 13, 2, 9, 14, 11], [7, 5, 0, 10, 2, 3, 9, 6, 11, 8, 1, 4, 14, 12, 13]]

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
