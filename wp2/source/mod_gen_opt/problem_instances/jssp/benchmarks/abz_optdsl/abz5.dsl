# Job Shop Scheduling instance: abz5
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 7773

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[88, 68, 94, 99, 67, 89, 77, 99, 86, 92], [72, 50, 69, 75, 94, 66, 92, 82, 94, 63], [83, 61, 83, 65, 64, 85, 78, 85, 55, 77], [94, 68, 61, 99, 54, 75, 66, 76, 63, 67], [69, 88, 82, 95, 99, 67, 95, 68, 67, 86], [99, 81, 64, 66, 80, 80, 69, 62, 79, 88], [50, 86, 97, 96, 95, 97, 66, 99, 52, 71], [98, 73, 82, 51, 71, 94, 85, 62, 95, 79], [94, 71, 81, 85, 66, 90, 76, 58, 93, 97], [50, 59, 82, 67, 56, 96, 58, 81, 59, 96]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[4, 8, 6, 5, 1, 2, 9, 7, 0, 3], [5, 3, 6, 4, 2, 8, 0, 1, 7, 9], [9, 8, 0, 1, 6, 5, 7, 4, 2, 3], [7, 2, 1, 4, 3, 6, 5, 0, 9, 8], [3, 4, 9, 8, 0, 2, 6, 5, 7, 1], [1, 4, 5, 6, 8, 2, 7, 9, 3, 0], [7, 1, 4, 3, 0, 8, 2, 5, 6, 9], [4, 6, 3, 2, 1, 5, 7, 0, 8, 9], [0, 6, 3, 7, 1, 2, 4, 5, 8, 9], [3, 0, 1, 8, 7, 9, 6, 4, 5, 2]]

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
