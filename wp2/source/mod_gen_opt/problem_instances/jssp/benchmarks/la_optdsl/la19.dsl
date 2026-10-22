# Job Shop Scheduling instance: la19
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5346

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[44, 5, 58, 97, 9, 84, 77, 96, 58, 89], [15, 31, 87, 57, 77, 85, 81, 39, 73, 21], [82, 22, 10, 70, 49, 40, 34, 48, 80, 71], [91, 17, 62, 75, 47, 11, 7, 72, 35, 55], [71, 90, 75, 64, 94, 15, 12, 67, 20, 50], [70, 93, 77, 29, 58, 93, 68, 57, 7, 52], [87, 63, 26, 6, 82, 27, 56, 48, 36, 95], [36, 15, 41, 78, 76, 84, 30, 76, 36, 8], [88, 81, 13, 82, 54, 13, 29, 40, 78, 75], [88, 54, 64, 32, 52, 6, 54, 82, 6, 26]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 3, 5, 4, 0, 7, 8, 9, 1, 6], [4, 7, 1, 8, 0, 3, 2, 5, 9, 6], [9, 6, 4, 3, 1, 0, 8, 2, 7, 5], [1, 2, 7, 5, 8, 4, 3, 6, 9, 0], [6, 1, 3, 0, 2, 8, 4, 7, 9, 5], [7, 5, 8, 2, 4, 6, 3, 1, 9, 0], [6, 1, 4, 5, 2, 3, 7, 8, 9, 0], [0, 5, 8, 9, 3, 6, 4, 7, 2, 1], [5, 2, 3, 6, 4, 7, 8, 9, 1, 0], [9, 4, 6, 7, 0, 2, 8, 5, 3, 1]]

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
