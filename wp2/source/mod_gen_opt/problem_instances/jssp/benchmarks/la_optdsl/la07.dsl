# Job Shop Scheduling instance: la07
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 5
MAX_TIME : int = 3745

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[47, 57, 71, 96, 14], [75, 60, 22, 79, 65], [32, 33, 69, 31, 58], [44, 34, 51, 58, 47], [29, 44, 62, 17, 8], [15, 40, 97, 38, 66], [58, 39, 57, 20, 50], [57, 32, 87, 63, 21], [56, 84, 90, 85, 61], [15, 20, 67, 30, 70], [84, 82, 23, 45, 38], [50, 21, 18, 41, 29], [16, 52, 52, 38, 54], [37, 54, 57, 74, 62], [57, 61, 81, 30, 68]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 4, 1, 3, 2], [0, 1, 4, 3, 2], [3, 0, 2, 1, 4], [0, 1, 4, 3, 2], [3, 1, 0, 2, 4], [1, 2, 0, 4, 3], [2, 1, 0, 4, 3], [2, 3, 4, 0, 1], [4, 0, 2, 1, 3], [4, 0, 1, 3, 2], [4, 0, 1, 2, 3], [3, 2, 0, 4, 1], [4, 1, 0, 2, 3], [4, 0, 3, 2, 1], [4, 1, 0, 2, 3]]

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
