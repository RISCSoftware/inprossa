# Job Shop Scheduling instance: swv01
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 9739

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[19, 27, 39, 13, 25, 37, 40, 54, 74, 93], [69, 30, 1, 4, 64, 71, 2, 84, 31, 8], [79, 80, 86, 55, 54, 81, 72, 86, 59, 75], [76, 15, 26, 17, 30, 44, 91, 83, 52, 68], [73, 87, 74, 39, 98, 100, 43, 17, 7, 77], [63, 49, 16, 55, 9, 73, 61, 34, 82, 46], [87, 71, 43, 80, 39, 70, 18, 41, 79, 44], [70, 22, 73, 62, 64, 25, 19, 69, 41, 28], [16, 84, 58, 7, 9, 8, 10, 17, 42, 65], [8, 10, 3, 41, 3, 40, 56, 53, 96, 13], [62, 60, 64, 12, 39, 2, 64, 87, 21, 60], [66, 71, 23, 75, 78, 74, 35, 24, 23, 50], [5, 92, 6, 69, 80, 13, 17, 89, 80, 47], [82, 84, 24, 47, 93, 85, 34, 73, 28, 91], [55, 57, 63, 24, 40, 30, 37, 99, 88, 41], [75, 47, 68, 7, 78, 80, 2, 23, 49, 50], [91, 25, 10, 21, 94, 6, 59, 84, 75, 70], [85, 31, 94, 94, 11, 21, 7, 61, 50, 93], [27, 77, 13, 30, 2, 88, 4, 39, 53, 54], [34, 12, 31, 24, 24, 16, 6, 88, 81, 11]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 2, 1, 4, 0, 8, 9, 5, 7, 6], [2, 0, 4, 3, 1, 7, 5, 9, 6, 8], [4, 3, 0, 2, 1, 8, 6, 7, 5, 9], [2, 3, 1, 0, 4, 8, 7, 6, 5, 9], [4, 3, 1, 0, 2, 9, 5, 8, 7, 6], [1, 0, 2, 3, 4, 9, 5, 8, 6, 7], [0, 1, 4, 3, 2, 7, 8, 6, 9, 5], [4, 2, 0, 3, 1, 5, 8, 6, 9, 7], [3, 0, 1, 4, 2, 5, 6, 7, 8, 9], [3, 0, 1, 4, 2, 7, 8, 5, 9, 6], [4, 1, 3, 2, 0, 5, 7, 6, 9, 8], [2, 1, 3, 4, 0, 7, 6, 9, 8, 5], [1, 3, 4, 0, 2, 7, 5, 9, 6, 8], [0, 3, 1, 2, 4, 7, 5, 6, 8, 9], [4, 0, 3, 2, 1, 7, 6, 5, 8, 9], [1, 2, 3, 0, 4, 7, 6, 9, 8, 5], [0, 4, 2, 1, 3, 8, 7, 5, 9, 6], [2, 1, 0, 4, 3, 5, 9, 6, 8, 7], [1, 0, 4, 2, 3, 5, 7, 9, 6, 8], [1, 2, 3, 0, 4, 7, 5, 9, 8, 6]]

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
