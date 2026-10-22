# Job Shop Scheduling instance: swv03
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 9895

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[19, 30, 68, 55, 24, 34, 72, 32, 62, 45], [63, 11, 65, 16, 67, 95, 23, 82, 52, 53], [19, 17, 79, 49, 12, 41, 67, 40, 25, 42], [42, 71, 27, 95, 19, 48, 100, 31, 25, 38], [1, 100, 68, 94, 89, 86, 35, 29, 56, 55], [93, 53, 4, 48, 57, 99, 67, 86, 80, 60], [82, 95, 12, 60, 80, 88, 5, 81, 52, 69], [79, 31, 63, 28, 64, 63, 29, 75, 18, 33], [9, 64, 31, 13, 33, 82, 79, 30, 84, 20], [14, 56, 95, 34, 13, 16, 44, 45, 62, 86], [66, 9, 66, 46, 12, 10, 58, 6, 62, 17], [89, 52, 37, 74, 7, 43, 96, 89, 21, 66], [73, 68, 5, 49, 67, 23, 7, 44, 30, 29], [21, 68, 88, 75, 64, 6, 72, 66, 66, 56], [24, 25, 69, 27, 51, 60, 26, 45, 77, 93], [19, 17, 82, 75, 34, 67, 89, 91, 13, 35], [2, 21, 83, 19, 65, 65, 8, 68, 60, 7], [63, 49, 4, 2, 50, 99, 27, 68, 46, 89], [48, 45, 100, 66, 30, 58, 73, 94, 36, 5], [36, 53, 56, 57, 77, 7, 59, 8, 15, 23]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 0, 1, 4, 3, 8, 7, 5, 9, 6], [2, 1, 4, 3, 0, 9, 8, 7, 6, 5], [2, 4, 1, 3, 0, 7, 9, 8, 6, 5], [0, 2, 3, 4, 1, 5, 8, 6, 7, 9], [3, 1, 4, 0, 2, 5, 7, 9, 8, 6], [4, 1, 2, 3, 0, 8, 7, 5, 6, 9], [4, 1, 2, 0, 3, 8, 7, 6, 9, 5], [3, 1, 4, 0, 2, 8, 5, 7, 9, 6], [4, 1, 2, 0, 3, 9, 6, 5, 7, 8], [2, 0, 1, 4, 3, 6, 5, 7, 8, 9], [4, 3, 2, 1, 0, 5, 7, 6, 8, 9], [4, 1, 2, 3, 0, 8, 5, 7, 6, 9], [1, 3, 2, 4, 0, 9, 7, 5, 8, 6], [2, 0, 1, 4, 3, 6, 8, 7, 9, 5], [1, 4, 2, 0, 3, 9, 8, 6, 5, 7], [2, 3, 1, 4, 0, 5, 9, 6, 7, 8], [4, 0, 3, 1, 2, 6, 8, 9, 7, 5], [1, 3, 2, 4, 0, 9, 5, 6, 8, 7], [0, 4, 3, 2, 1, 6, 7, 9, 5, 8], [2, 0, 4, 3, 1, 9, 6, 8, 5, 7]]

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
