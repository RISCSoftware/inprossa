# Job Shop Scheduling instance: ta03
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11181

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[69, 81, 81, 62, 80, 3, 38, 62, 54, 66, 88, 82, 3, 12, 88], [83, 51, 47, 15, 89, 76, 52, 18, 22, 85, 26, 30, 5, 89, 22], [62, 47, 93, 54, 38, 78, 71, 96, 19, 33, 44, 71, 90, 9, 21], [33, 82, 80, 30, 96, 31, 11, 26, 41, 55, 12, 10, 92, 3, 75], [36, 49, 10, 43, 69, 72, 19, 65, 37, 57, 32, 11, 73, 89, 12], [83, 32, 6, 13, 87, 94, 36, 76, 46, 30, 56, 62, 32, 52, 72], [29, 78, 21, 27, 17, 43, 14, 15, 16, 49, 72, 19, 99, 38, 64], [12, 74, 4, 3, 15, 62, 50, 38, 49, 25, 18, 55, 5, 71, 27], [69, 13, 33, 47, 86, 31, 97, 48, 25, 40, 94, 22, 61, 59, 16], [27, 4, 35, 80, 49, 46, 84, 46, 96, 72, 18, 23, 96, 74, 23], [36, 17, 81, 67, 47, 5, 51, 23, 82, 35, 96, 7, 54, 92, 38], [78, 58, 62, 43, 1, 56, 76, 49, 80, 26, 79, 9, 24, 24, 42], [38, 86, 38, 38, 83, 36, 11, 17, 99, 14, 57, 64, 58, 96, 17], [10, 86, 93, 63, 61, 62, 75, 90, 40, 77, 8, 27, 96, 69, 64], [73, 12, 14, 71, 3, 47, 84, 84, 53, 58, 95, 87, 90, 68, 75]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 11, 8, 3, 12, 1, 13, 0, 14, 6, 9, 4, 2, 10, 5], [12, 1, 11, 9, 6, 3, 2, 4, 5, 8, 13, 14, 10, 0, 7], [1, 2, 9, 0, 3, 5, 8, 4, 14, 10, 12, 13, 7, 6, 11], [13, 10, 6, 2, 14, 7, 4, 11, 0, 5, 9, 3, 8, 1, 12], [1, 8, 4, 14, 6, 5, 3, 2, 9, 10, 13, 7, 11, 0, 12], [5, 14, 2, 12, 10, 1, 11, 4, 6, 9, 0, 13, 8, 3, 7], [5, 2, 0, 1, 8, 14, 11, 10, 7, 9, 6, 12, 4, 13, 3], [4, 7, 10, 1, 9, 8, 2, 14, 11, 3, 5, 6, 13, 12, 0], [14, 11, 0, 9, 10, 5, 3, 12, 8, 13, 6, 1, 7, 2, 4], [9, 0, 3, 10, 12, 13, 5, 1, 6, 14, 8, 11, 2, 7, 4], [7, 2, 1, 12, 3, 14, 4, 6, 5, 9, 8, 13, 10, 0, 11], [0, 8, 14, 12, 9, 5, 6, 10, 7, 11, 3, 4, 1, 13, 2], [8, 12, 10, 11, 14, 3, 6, 1, 4, 5, 0, 9, 13, 2, 7], [13, 2, 11, 0, 14, 10, 3, 1, 12, 4, 5, 6, 7, 9, 8], [1, 13, 0, 11, 2, 10, 4, 8, 3, 5, 7, 6, 9, 12, 14]]

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
