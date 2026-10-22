# Job Shop Scheduling instance: la12
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 5
MAX_TIME : int = 4676

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[23, 82, 84, 45, 38], [50, 41, 29, 18, 21], [16, 54, 52, 38, 52], [62, 57, 37, 74, 54], [68, 61, 30, 81, 57], [89, 89, 11, 79, 81], [66, 91, 33, 20, 20], [8, 24, 55, 32, 84], [7, 64, 39, 56, 54], [19, 40, 7, 8, 83], [63, 64, 91, 40, 6], [42, 61, 15, 98, 74], [80, 26, 75, 6, 87], [39, 22, 75, 24, 44], [15, 79, 8, 12, 20], [26, 43, 80, 22, 61], [62, 36, 63, 96, 40], [33, 18, 22, 5, 10], [64, 64, 89, 96, 95], [18, 23, 15, 38, 8]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[1, 0, 4, 2, 3], [3, 4, 1, 0, 2], [4, 3, 1, 2, 0], [1, 3, 4, 2, 0], [3, 1, 2, 0, 4], [1, 2, 3, 0, 4], [1, 0, 3, 4, 2], [3, 4, 2, 0, 1], [0, 2, 1, 4, 3], [0, 4, 3, 2, 1], [0, 2, 3, 4, 1], [1, 3, 4, 2, 0], [1, 0, 3, 4, 2], [2, 4, 0, 3, 1], [1, 3, 4, 0, 2], [3, 2, 0, 4, 1], [2, 1, 0, 3, 4], [1, 3, 0, 4, 2], [2, 4, 0, 1, 3], [2, 4, 3, 1, 0]]

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
