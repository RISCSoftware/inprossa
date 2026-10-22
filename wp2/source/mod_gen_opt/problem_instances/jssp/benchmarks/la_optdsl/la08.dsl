# Job Shop Scheduling instance: la08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 5
MAX_TIME : int = 3825

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[92, 94, 12, 91, 7], [21, 19, 87, 11, 66], [14, 13, 75, 16, 20], [95, 66, 7, 77, 7], [34, 89, 6, 45, 15], [88, 77, 20, 53, 76], [9, 27, 52, 88, 74], [69, 52, 62, 88, 98], [90, 62, 9, 61, 52], [5, 54, 59, 88, 15], [41, 50, 78, 53, 23], [38, 72, 91, 68, 71], [45, 95, 52, 25, 6], [30, 66, 23, 36, 17], [95, 71, 76, 8, 88]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 2, 0, 4, 1], [2, 1, 0, 3, 4], [1, 3, 0, 4, 2], [2, 4, 0, 1, 3], [2, 4, 3, 1, 0], [4, 3, 2, 1, 0], [4, 3, 0, 1, 2], [3, 2, 0, 1, 4], [3, 0, 4, 2, 1], [4, 2, 3, 0, 1], [0, 1, 4, 3, 2], [0, 4, 2, 3, 1], [0, 3, 4, 2, 1], [3, 1, 0, 4, 2], [2, 0, 3, 1, 4]]

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
