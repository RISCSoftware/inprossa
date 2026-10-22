# Job Shop Scheduling instance: orb08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 4560

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[55, 74, 45, 23, 76, 19, 18, 61, 44, 11], [63, 43, 51, 18, 42, 11, 29, 52, 29, 88], [88, 31, 47, 10, 62, 60, 58, 29, 52, 92], [16, 71, 55, 55, 9, 49, 83, 54, 7, 57], [7, 41, 92, 94, 46, 79, 34, 38, 8, 18], [25, 5, 89, 94, 14, 94, 20, 23, 44, 39], [24, 21, 47, 40, 94, 71, 89, 75, 97, 15], [5, 7, 74, 28, 72, 61, 9, 53, 32, 97], [34, 52, 37, 6, 94, 6, 56, 41, 5, 16], [77, 74, 82, 10, 29, 15, 51, 65, 37, 21]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 1, 2, 3, 4, 7, 6, 5, 9, 8], [2, 1, 0, 4, 3, 5, 6, 7, 8, 9], [2, 1, 0, 4, 3, 7, 6, 5, 9, 8], [1, 0, 4, 3, 2, 6, 5, 9, 8, 7], [1, 0, 4, 3, 2, 6, 5, 9, 8, 7], [1, 2, 4, 0, 3, 6, 7, 9, 5, 8], [1, 2, 4, 0, 3, 5, 7, 8, 9, 6], [0, 2, 3, 4, 1, 6, 7, 9, 5, 8], [0, 2, 3, 4, 1, 5, 7, 8, 9, 6]]

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
