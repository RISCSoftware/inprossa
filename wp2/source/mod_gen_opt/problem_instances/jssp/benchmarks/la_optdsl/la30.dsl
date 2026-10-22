# Job Shop Scheduling instance: la30
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10680

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[32, 16, 33, 12, 70, 10, 75, 82, 88, 20], [39, 81, 91, 56, 69, 45, 59, 86, 36, 68], [84, 57, 41, 73, 81, 88, 38, 17, 83, 5], [20, 6, 15, 19, 30, 94, 45, 17, 18, 88], [24, 49, 16, 11, 60, 5, 63, 25, 15, 45], [86, 50, 77, 54, 48, 93, 32, 92, 45, 71], [86, 90, 78, 88, 57, 32, 57, 86, 71, 39], [59, 18, 31, 41, 20, 83, 65, 54, 94, 69], [47, 79, 76, 59, 72, 8, 30, 73, 57, 84], [59, 89, 10, 45, 8, 54, 88, 20, 7, 62], [63, 9, 77, 37, 5, 13, 79, 24, 10, 82], [74, 32, 61, 53, 92, 20, 10, 5, 45, 23], [85, 51, 61, 99, 37, 94, 98, 65, 33, 75], [51, 24, 8, 30, 12, 23, 7, 17, 35, 81], [71, 42, 68, 31, 29, 63, 65, 70, 27, 93], [28, 38, 51, 70, 33, 78, 45, 90, 54, 72], [18, 90, 25, 92, 85, 35, 29, 81, 80, 59], [67, 96, 38, 86, 97, 94, 86, 35, 82, 45], [92, 51, 59, 52, 8, 70, 75, 54, 60, 33], [98, 80, 78, 82, 7, 89, 69, 51, 79, 62]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 3, 1, 8, 7, 4, 9, 0, 5, 2], [8, 4, 3, 5, 9, 1, 6, 0, 2, 7], [3, 2, 7, 5, 4, 0, 8, 9, 6, 1], [4, 5, 2, 8, 1, 0, 6, 7, 3, 9], [9, 6, 5, 4, 3, 7, 8, 1, 2, 0], [1, 8, 2, 6, 9, 0, 3, 7, 5, 4], [5, 6, 3, 9, 2, 0, 7, 8, 4, 1], [2, 3, 9, 4, 7, 5, 8, 0, 6, 1], [3, 4, 6, 0, 1, 2, 9, 5, 7, 8], [0, 2, 4, 7, 3, 5, 6, 8, 9, 1], [5, 6, 4, 3, 2, 8, 9, 1, 7, 0], [0, 1, 2, 7, 4, 9, 8, 3, 6, 5], [2, 9, 0, 5, 4, 6, 1, 8, 3, 7], [0, 3, 5, 6, 7, 8, 2, 4, 9, 1], [1, 5, 8, 2, 6, 3, 4, 9, 7, 0], [1, 5, 4, 7, 2, 8, 9, 3, 6, 0], [0, 2, 4, 6, 8, 5, 7, 1, 9, 3], [5, 2, 1, 4, 0, 3, 7, 6, 9, 8], [2, 8, 4, 6, 5, 9, 1, 3, 7, 0], [3, 7, 5, 0, 2, 9, 1, 4, 8, 6]]

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
