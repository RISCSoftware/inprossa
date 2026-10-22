# Job Shop Scheduling instance: la09
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 5
MAX_TIME : int = 4263

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[66, 85, 84, 62, 19], [59, 64, 46, 13, 25], [88, 80, 73, 53, 41], [14, 67, 57, 74, 47], [84, 64, 41, 84, 78], [63, 28, 46, 26, 52], [10, 17, 73, 11, 64], [67, 97, 95, 38, 85], [95, 46, 59, 65, 93], [43, 85, 32, 85, 60], [49, 41, 61, 66, 90], [17, 23, 70, 99, 49], [40, 73, 73, 98, 68], [57, 9, 7, 13, 98], [37, 85, 17, 79, 41]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 3, 2, 0, 4], [3, 1, 2, 4, 0], [4, 3, 1, 2, 0], [0, 1, 2, 3, 4], [0, 4, 2, 3, 1], [0, 3, 1, 2, 4], [3, 2, 4, 1, 0], [2, 1, 3, 4, 0], [2, 4, 0, 1, 3], [2, 4, 3, 1, 0], [4, 3, 2, 0, 1], [1, 0, 3, 4, 2], [4, 3, 0, 1, 2], [3, 1, 2, 0, 4], [0, 1, 2, 4, 3]]

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
