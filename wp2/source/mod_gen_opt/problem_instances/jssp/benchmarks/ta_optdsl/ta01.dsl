# Job Shop Scheduling instance: ta01
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 15
MAX_TIME : int = 11671

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[94, 66, 10, 53, 26, 15, 65, 82, 10, 27, 93, 92, 96, 70, 83], [74, 31, 88, 51, 57, 78, 8, 7, 91, 79, 18, 51, 18, 99, 33], [4, 82, 40, 86, 50, 54, 21, 6, 54, 68, 82, 20, 39, 35, 68], [73, 23, 30, 30, 53, 94, 58, 93, 32, 91, 30, 56, 27, 92, 9], [78, 23, 21, 60, 36, 29, 95, 99, 79, 76, 93, 42, 52, 42, 96], [29, 61, 88, 70, 16, 31, 65, 83, 78, 26, 50, 87, 62, 14, 30], [18, 75, 20, 4, 91, 68, 19, 54, 85, 73, 43, 24, 37, 87, 66], [32, 52, 9, 49, 61, 35, 99, 62, 6, 62, 7, 80, 3, 57, 7], [85, 30, 96, 91, 13, 87, 82, 83, 78, 56, 85, 8, 66, 88, 15], [5, 59, 30, 60, 41, 17, 66, 89, 78, 88, 69, 45, 82, 6, 13], [90, 27, 1, 8, 91, 80, 89, 49, 32, 28, 90, 93, 6, 35, 73], [47, 43, 75, 8, 51, 3, 84, 34, 28, 60, 69, 45, 67, 58, 87], [65, 62, 97, 20, 31, 33, 33, 77, 50, 80, 48, 90, 75, 96, 44], [28, 21, 51, 75, 17, 89, 59, 56, 63, 18, 17, 30, 16, 7, 35], [57, 16, 42, 34, 37, 26, 68, 73, 5, 8, 12, 87, 83, 20, 97]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 12, 4, 7, 3, 2, 10, 11, 8, 14, 9, 13, 5, 0, 1], [4, 5, 7, 14, 13, 8, 11, 9, 6, 10, 0, 3, 12, 1, 2], [1, 8, 9, 12, 6, 11, 13, 5, 0, 2, 7, 10, 4, 3, 14], [5, 2, 9, 6, 10, 0, 13, 4, 7, 14, 11, 8, 12, 1, 3], [7, 8, 6, 10, 4, 9, 2, 14, 12, 5, 1, 13, 11, 0, 3], [5, 3, 12, 13, 11, 4, 14, 7, 2, 1, 10, 0, 9, 6, 8], [12, 3, 7, 8, 14, 6, 1, 11, 4, 5, 2, 10, 0, 13, 9], [11, 5, 0, 7, 12, 13, 14, 1, 2, 8, 4, 3, 9, 6, 10], [10, 11, 6, 14, 0, 1, 2, 5, 12, 4, 8, 7, 9, 13, 3], [6, 11, 9, 2, 8, 0, 13, 3, 10, 7, 1, 12, 14, 4, 5], [4, 7, 13, 0, 5, 12, 6, 8, 14, 10, 3, 1, 11, 9, 2], [2, 14, 0, 12, 6, 10, 7, 5, 8, 9, 13, 1, 3, 11, 4], [5, 8, 10, 2, 3, 6, 9, 0, 13, 4, 1, 11, 12, 7, 14], [8, 14, 4, 13, 5, 6, 9, 1, 12, 7, 11, 10, 3, 2, 0], [10, 8, 12, 6, 4, 1, 13, 14, 11, 0, 7, 3, 2, 9, 5]]

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
