# Job Shop Scheduling instance: la23
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 10
MAX_TIME : int = 8085

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[84, 58, 77, 44, 97, 89, 5, 58, 96, 9], [21, 87, 15, 39, 81, 85, 31, 57, 73, 77], [40, 71, 34, 82, 70, 22, 10, 80, 48, 49], [75, 17, 7, 72, 11, 62, 47, 35, 91, 55], [20, 12, 71, 67, 64, 94, 15, 50, 75, 90], [93, 93, 57, 70, 77, 58, 52, 29, 7, 68], [56, 95, 48, 26, 82, 63, 36, 27, 87, 6], [76, 15, 78, 8, 41, 36, 30, 84, 36, 76], [75, 13, 81, 29, 54, 82, 88, 78, 40, 13], [6, 26, 32, 64, 54, 52, 82, 6, 88, 54], [62, 67, 32, 62, 69, 61, 35, 72, 5, 93], [78, 90, 85, 72, 64, 63, 11, 82, 88, 7], [28, 11, 50, 88, 44, 31, 27, 66, 49, 35], [14, 39, 56, 62, 97, 66, 69, 7, 47, 76], [18, 93, 58, 47, 69, 57, 41, 53, 79, 64]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 5, 8, 2, 4, 6, 3, 1, 9, 0], [6, 1, 4, 5, 2, 3, 7, 8, 9, 0], [0, 5, 8, 9, 3, 6, 4, 7, 2, 1], [5, 2, 3, 6, 4, 7, 8, 9, 1, 0], [9, 4, 6, 7, 0, 2, 8, 5, 3, 1], [6, 5, 1, 7, 8, 4, 0, 2, 9, 3], [7, 0, 8, 4, 2, 1, 9, 3, 6, 5], [3, 5, 9, 1, 8, 2, 4, 6, 0, 7], [0, 7, 2, 8, 4, 6, 5, 1, 9, 3], [2, 1, 7, 6, 4, 0, 5, 3, 9, 8], [8, 2, 5, 0, 7, 3, 1, 4, 9, 6], [2, 9, 0, 1, 8, 6, 3, 7, 5, 4], [4, 9, 7, 6, 0, 5, 2, 1, 8, 3], [2, 5, 6, 4, 3, 9, 7, 1, 8, 0], [1, 8, 7, 6, 3, 9, 2, 5, 4, 0]]

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
