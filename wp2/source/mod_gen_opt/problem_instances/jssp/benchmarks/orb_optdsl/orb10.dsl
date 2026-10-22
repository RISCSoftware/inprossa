# Job Shop Scheduling instance: orb10
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5549

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[66, 13, 93, 91, 14, 70, 99, 53, 86, 16], [34, 99, 62, 65, 62, 64, 21, 12, 9, 75], [12, 26, 64, 92, 67, 28, 66, 83, 38, 58], [77, 73, 82, 75, 84, 19, 18, 89, 8, 73], [34, 74, 48, 44, 92, 40, 60, 62, 22, 67], [8, 85, 58, 97, 92, 89, 75, 77, 95, 5], [52, 43, 5, 78, 12, 62, 21, 80, 60, 31], [81, 23, 23, 75, 78, 56, 51, 39, 53, 96], [79, 55, 88, 21, 83, 93, 47, 10, 63, 14], [43, 63, 83, 29, 52, 98, 54, 39, 33, 23]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 8, 0, 7, 6, 5, 3, 2, 4, 1], [8, 9, 0, 7, 5, 4, 6, 2, 3, 1], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [0, 1, 3, 2, 6, 4, 5, 7, 8, 9], [0, 1, 7, 5, 4, 6, 3, 2, 8, 9], [9, 8, 3, 7, 5, 4, 6, 2, 1, 0], [8, 9, 6, 7, 5, 3, 4, 2, 1, 0], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [9, 8, 2, 4, 5, 3, 6, 7, 0, 1], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]

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
