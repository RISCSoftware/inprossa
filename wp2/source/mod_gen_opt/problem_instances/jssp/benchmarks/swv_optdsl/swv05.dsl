# Job Shop Scheduling instance: swv05
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10097

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[19, 30, 80, 84, 14, 51, 73, 91, 81, 71], [74, 79, 39, 7, 66, 6, 93, 76, 21, 76], [90, 33, 38, 73, 61, 61, 76, 86, 28, 35], [1, 22, 1, 77, 33, 98, 4, 27, 8, 68], [63, 5, 95, 7, 50, 46, 28, 70, 60, 34], [98, 73, 15, 21, 32, 24, 9, 24, 7, 34], [51, 47, 30, 16, 51, 41, 79, 79, 3, 72], [3, 59, 53, 20, 19, 20, 16, 90, 96, 18], [34, 55, 97, 93, 90, 81, 63, 41, 1, 51], [77, 87, 92, 83, 45, 75, 60, 75, 93, 33], [31, 66, 58, 17, 94, 63, 80, 61, 78, 52], [70, 25, 75, 89, 41, 100, 73, 28, 94, 88], [67, 62, 12, 55, 62, 58, 66, 73, 55, 1], [81, 37, 2, 39, 17, 74, 71, 61, 42, 5], [62, 31, 63, 31, 5, 7, 77, 34, 34, 3], [5, 55, 62, 82, 80, 6, 7, 29, 80, 89], [26, 50, 58, 22, 68, 12, 9, 34, 90, 87], [50, 28, 64, 34, 63, 9, 48, 63, 61, 2], [47, 23, 23, 82, 98, 66, 78, 100, 79, 32], [13, 14, 90, 77, 80, 30, 31, 36, 51, 69]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 1, 3, 0, 4, 8, 5, 6, 7, 9], [2, 4, 1, 0, 3, 9, 5, 8, 6, 7], [4, 3, 1, 2, 0, 8, 7, 5, 9, 6], [4, 3, 2, 0, 1, 6, 5, 9, 8, 7], [2, 4, 1, 0, 3, 8, 9, 6, 5, 7], [0, 1, 4, 3, 2, 7, 9, 8, 5, 6], [3, 4, 2, 1, 0, 5, 6, 7, 9, 8], [4, 1, 0, 3, 2, 6, 9, 7, 5, 8], [1, 2, 3, 0, 4, 7, 5, 8, 6, 9], [4, 3, 1, 2, 0, 7, 9, 6, 5, 8], [0, 2, 1, 4, 3, 5, 7, 9, 6, 8], [4, 1, 2, 0, 3, 7, 5, 6, 8, 9], [1, 4, 3, 2, 0, 5, 8, 7, 6, 9], [4, 0, 1, 3, 2, 7, 6, 8, 5, 9], [3, 0, 4, 2, 1, 9, 7, 8, 6, 5], [0, 2, 3, 1, 4, 6, 8, 7, 5, 9], [3, 1, 2, 0, 4, 7, 6, 9, 5, 8], [0, 2, 1, 4, 3, 7, 9, 6, 8, 5], [0, 2, 1, 4, 3, 7, 6, 8, 9, 5], [1, 4, 0, 2, 3, 9, 7, 5, 6, 8]]

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
