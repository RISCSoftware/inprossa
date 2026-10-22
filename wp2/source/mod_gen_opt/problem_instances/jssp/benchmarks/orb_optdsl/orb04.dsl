# Job Shop Scheduling instance: orb04
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5628

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 10, 35, 44, 15, 92, 70, 89, 50, 12], [63, 39, 80, 22, 88, 39, 85, 27, 74, 69], [52, 22, 33, 68, 27, 68, 25, 34, 24, 84], [31, 85, 55, 80, 58, 11, 69, 56, 73, 25], [97, 98, 87, 47, 77, 90, 98, 80, 39, 40], [97, 68, 44, 67, 44, 85, 78, 90, 33, 81], [34, 76, 48, 61, 11, 36, 33, 98, 7, 44], [44, 5, 85, 51, 58, 79, 95, 48, 86, 73], [24, 63, 48, 77, 73, 74, 63, 17, 93, 84], [51, 5, 40, 60, 46, 58, 54, 72, 29, 94]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 8, 3, 5, 2, 1, 9, 6, 7, 4], [0, 6, 1, 3, 8, 2, 5, 4, 7, 9], [0, 1, 4, 8, 5, 7, 6, 9, 3, 2], [0, 5, 9, 8, 7, 4, 3, 2, 1, 6], [1, 5, 0, 9, 2, 8, 3, 6, 7, 4], [0, 3, 8, 7, 9, 2, 4, 6, 1, 5], [0, 9, 4, 1, 5, 7, 2, 6, 3, 8], [0, 1, 9, 7, 8, 6, 4, 5, 2, 3], [0, 2, 4, 9, 1, 5, 8, 3, 6, 7]]

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
