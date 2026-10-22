# Job Shop Scheduling instance: la06
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 5
MAX_TIME : int = 3992

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[21, 34, 95, 53, 55], [52, 16, 71, 26, 21], [31, 12, 42, 39, 98], [77, 77, 79, 55, 66], [37, 34, 64, 19, 83], [43, 54, 92, 62, 79], [93, 69, 87, 77, 87], [60, 41, 38, 83, 24], [98, 17, 25, 44, 49], [96, 77, 79, 75, 43], [28, 35, 95, 76, 7], [61, 10, 95, 9, 35], [59, 16, 91, 59, 46], [43, 52, 28, 27, 50], [87, 45, 39, 9, 41]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 2, 4, 0, 3], [3, 4, 1, 2, 0], [2, 0, 1, 3, 4], [3, 1, 4, 0, 2], [4, 3, 2, 1, 0], [2, 1, 0, 3, 4], [0, 3, 1, 4, 2], [0, 1, 2, 4, 3], [2, 3, 4, 0, 1], [0, 4, 3, 1, 2], [4, 2, 0, 3, 1], [0, 4, 2, 1, 3], [4, 3, 1, 2, 0], [4, 1, 0, 2, 3], [0, 1, 2, 4, 3]]

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
