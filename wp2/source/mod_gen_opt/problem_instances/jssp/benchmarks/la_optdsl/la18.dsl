# Job Shop Scheduling instance: la18
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5186

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[54, 87, 48, 60, 39, 35, 72, 95, 66, 5], [20, 46, 34, 55, 97, 19, 59, 21, 37, 46], [45, 24, 28, 28, 83, 78, 23, 25, 5, 73], [12, 37, 38, 71, 33, 12, 55, 53, 87, 29], [83, 49, 23, 27, 65, 48, 90, 7, 40, 17], [66, 25, 62, 84, 13, 64, 46, 59, 19, 85], [73, 80, 41, 53, 47, 57, 74, 14, 67, 88], [64, 84, 46, 78, 84, 26, 28, 52, 41, 63], [11, 64, 67, 85, 10, 73, 38, 95, 97, 17], [60, 32, 95, 93, 65, 85, 43, 85, 46, 59]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 0, 4, 3, 7, 8, 1, 5, 2, 9], [3, 9, 6, 5, 0, 8, 4, 2, 7, 1], [4, 1, 8, 0, 7, 6, 5, 3, 9, 2], [9, 1, 4, 3, 8, 2, 6, 0, 7, 5], [3, 2, 6, 9, 7, 0, 4, 5, 1, 8], [1, 4, 0, 2, 9, 6, 7, 8, 5, 3], [1, 3, 0, 2, 9, 7, 8, 4, 6, 5], [5, 3, 6, 1, 0, 7, 8, 9, 2, 4], [1, 0, 7, 4, 3, 5, 9, 8, 6, 2], [4, 8, 2, 3, 1, 6, 7, 9, 5, 0]]

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
