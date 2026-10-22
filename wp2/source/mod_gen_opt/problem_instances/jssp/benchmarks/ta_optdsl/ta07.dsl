# Job Shop Scheduling instance: ta07
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11553

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[52, 19, 6, 20, 1, 26, 90, 44, 27, 18, 51, 80, 10, 51, 41], [44, 85, 2, 78, 86, 88, 61, 20, 56, 12, 69, 34, 55, 34, 84], [62, 72, 74, 63, 95, 29, 24, 34, 89, 83, 90, 26, 98, 65, 31], [10, 15, 93, 79, 77, 61, 1, 48, 22, 27, 21, 17, 45, 96, 11], [83, 52, 70, 78, 7, 28, 97, 52, 29, 81, 60, 91, 80, 54, 35], [3, 31, 98, 97, 77, 39, 41, 10, 9, 93, 7, 49, 20, 45, 59], [28, 93, 4, 51, 67, 5, 18, 52, 47, 21, 49, 63, 96, 85, 90], [25, 82, 58, 15, 67, 50, 66, 92, 56, 82, 57, 16, 34, 99, 61], [82, 31, 22, 16, 87, 48, 59, 63, 29, 99, 48, 36, 91, 61, 59], [28, 25, 69, 65, 62, 57, 97, 31, 15, 25, 83, 98, 55, 66, 31], [20, 99, 13, 88, 25, 75, 90, 84, 70, 41, 17, 54, 63, 1, 95], [59, 22, 46, 10, 1, 21, 3, 84, 93, 59, 78, 73, 59, 42, 63], [72, 80, 12, 56, 22, 8, 93, 27, 17, 38, 26, 51, 43, 80, 94], [72, 78, 29, 90, 46, 46, 43, 75, 90, 29, 8, 92, 16, 62, 6], [89, 44, 41, 32, 10, 85, 16, 23, 91, 46, 35, 17, 93, 45, 93]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[13, 12, 7, 0, 5, 11, 9, 10, 1, 2, 3, 14, 4, 6, 8], [2, 1, 8, 14, 13, 0, 5, 11, 9, 12, 10, 7, 3, 4, 6], [0, 3, 1, 7, 4, 8, 14, 5, 6, 2, 13, 12, 9, 10, 11], [9, 11, 0, 7, 12, 14, 6, 1, 13, 10, 4, 5, 3, 2, 8], [8, 13, 5, 10, 9, 14, 12, 2, 3, 0, 6, 11, 7, 4, 1], [12, 13, 14, 9, 5, 1, 6, 7, 0, 3, 8, 10, 4, 11, 2], [9, 0, 5, 4, 12, 14, 6, 1, 3, 8, 13, 11, 2, 10, 7], [12, 1, 9, 14, 6, 10, 2, 7, 4, 11, 13, 5, 3, 8, 0], [6, 5, 12, 4, 1, 14, 9, 0, 7, 8, 10, 13, 2, 11, 3], [8, 3, 5, 4, 1, 10, 7, 9, 13, 2, 0, 11, 6, 12, 14], [4, 2, 1, 0, 14, 10, 9, 6, 11, 12, 3, 8, 7, 13, 5], [8, 3, 13, 14, 2, 11, 5, 4, 9, 12, 10, 7, 1, 0, 6], [7, 1, 10, 4, 0, 8, 12, 6, 13, 2, 3, 9, 11, 14, 5], [8, 11, 3, 7, 1, 12, 6, 4, 10, 13, 2, 5, 14, 9, 0], [5, 13, 14, 6, 9, 11, 7, 2, 12, 8, 3, 4, 10, 1, 0]]

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
