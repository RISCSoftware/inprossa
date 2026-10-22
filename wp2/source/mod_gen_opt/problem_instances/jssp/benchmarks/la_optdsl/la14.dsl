# Job Shop Scheduling instance: la14
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 5
MAX_TIME : int = 5346

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[5, 58, 44, 9, 58], [89, 96, 97, 84, 77], [81, 85, 87, 39, 77], [15, 57, 73, 21, 31], [48, 71, 70, 40, 49], [10, 82, 34, 80, 22], [17, 55, 91, 75, 7], [47, 62, 72, 35, 11], [90, 94, 50, 64, 75], [15, 67, 12, 20, 71], [93, 29, 52, 57, 68], [77, 93, 58, 70, 7], [63, 27, 95, 6, 82], [36, 26, 48, 56, 87], [36, 8, 15, 76, 36], [78, 84, 41, 30, 76], [78, 75, 88, 13, 81], [54, 40, 13, 82, 29], [26, 82, 52, 6, 6], [54, 64, 54, 32, 88]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 4, 2, 0, 1], [1, 4, 0, 2, 3], [2, 3, 1, 4, 0], [0, 3, 4, 1, 2], [2, 4, 3, 0, 1], [0, 4, 3, 2, 1], [2, 0, 1, 4, 3], [3, 2, 1, 4, 0], [1, 2, 4, 0, 3], [3, 2, 0, 4, 1], [4, 2, 0, 1, 3], [3, 1, 0, 2, 4], [1, 3, 0, 4, 2], [4, 0, 3, 2, 1], [2, 1, 4, 3, 0], [4, 1, 3, 0, 2], [1, 0, 4, 3, 2], [0, 4, 2, 1, 3], [1, 4, 0, 3, 2], [3, 1, 0, 2, 4]]

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
