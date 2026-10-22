# Job Shop Scheduling instance: abz6
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5946

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[62, 24, 25, 84, 47, 38, 82, 93, 24, 66], [47, 97, 92, 22, 93, 29, 56, 80, 78, 67], [45, 46, 22, 26, 38, 69, 40, 33, 75, 96], [85, 76, 68, 88, 36, 75, 56, 35, 77, 85], [60, 20, 25, 63, 81, 52, 30, 98, 54, 86], [87, 73, 51, 95, 65, 86, 22, 58, 80, 65], [81, 53, 57, 71, 81, 43, 26, 54, 58, 69], [20, 86, 21, 79, 62, 34, 27, 81, 30, 46], [68, 66, 98, 86, 66, 56, 82, 95, 47, 78], [30, 50, 34, 58, 77, 34, 84, 40, 46, 44]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[7, 8, 5, 3, 4, 6, 2, 0, 9, 1], [5, 2, 8, 9, 1, 4, 7, 3, 0, 6], [1, 7, 6, 2, 9, 0, 4, 3, 8, 5], [4, 8, 5, 9, 3, 6, 2, 1, 0, 7], [8, 9, 7, 3, 4, 0, 1, 5, 6, 2], [3, 9, 5, 2, 4, 1, 6, 8, 0, 7], [5, 2, 7, 6, 9, 0, 4, 8, 3, 1], [4, 6, 5, 8, 9, 2, 0, 1, 7, 3], [9, 6, 5, 8, 7, 0, 3, 1, 4, 2], [0, 3, 7, 2, 1, 5, 8, 4, 9, 6]]

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
