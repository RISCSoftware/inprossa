# Job Shop Scheduling instance: la13
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 5
MAX_TIME : int = 5186

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[60, 87, 72, 95, 66], [54, 48, 39, 35, 5], [20, 46, 97, 21, 55], [37, 59, 19, 34, 46], [73, 25, 24, 28, 23], [78, 28, 83, 45, 5], [71, 37, 12, 29, 53], [12, 33, 55, 87, 38], [48, 40, 49, 83, 7], [90, 27, 65, 17, 23], [62, 85, 66, 84, 19], [59, 46, 13, 64, 25], [53, 73, 80, 88, 41], [57, 47, 14, 67, 74], [41, 64, 84, 78, 84], [52, 28, 26, 63, 46], [11, 64, 10, 73, 17], [38, 95, 85, 97, 67], [93, 65, 95, 59, 46], [60, 85, 43, 85, 32]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 0, 1, 4, 2], [1, 0, 2, 3, 4], [3, 1, 0, 2, 4], [2, 0, 3, 1, 4], [2, 3, 1, 0, 4], [1, 3, 2, 0, 4], [3, 1, 2, 4, 0], [4, 3, 1, 2, 0], [0, 1, 2, 3, 4], [0, 4, 2, 3, 1], [0, 3, 1, 2, 4], [3, 2, 4, 1, 0], [2, 1, 3, 4, 0], [2, 4, 0, 1, 3], [2, 4, 3, 1, 0], [4, 3, 2, 0, 1], [1, 0, 3, 4, 2], [4, 3, 0, 1, 2], [3, 1, 2, 0, 4], [0, 1, 2, 4, 3]]

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
