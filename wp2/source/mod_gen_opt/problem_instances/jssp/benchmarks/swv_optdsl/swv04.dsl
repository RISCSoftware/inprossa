# Job Shop Scheduling instance: swv04
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10240

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[16, 59, 10, 95, 64, 92, 56, 3, 73, 17], [5, 64, 30, 14, 96, 11, 73, 35, 93, 12], [35, 75, 54, 30, 83, 20, 29, 38, 90, 39], [29, 21, 52, 93, 20, 5, 11, 53, 56, 98], [17, 16, 41, 78, 100, 55, 27, 2, 87, 55], [97, 32, 84, 71, 38, 64, 16, 5, 41, 41], [41, 57, 37, 64, 92, 19, 47, 94, 79, 21], [23, 67, 39, 98, 63, 83, 45, 89, 81, 44], [88, 59, 39, 63, 91, 36, 44, 45, 43, 12], [29, 17, 6, 74, 51, 14, 2, 56, 49, 14], [75, 10, 1, 35, 99, 56, 95, 78, 53, 82], [75, 96, 21, 90, 55, 23, 40, 76, 55, 45], [90, 64, 72, 33, 59, 51, 74, 85, 76, 38], [57, 84, 87, 2, 68, 4, 77, 37, 37, 94], [16, 46, 34, 23, 77, 68, 14, 54, 37, 99], [24, 73, 92, 43, 42, 81, 99, 88, 80, 5], [56, 51, 3, 87, 25, 62, 11, 88, 68, 29], [85, 3, 21, 49, 79, 38, 37, 72, 18, 18], [2, 55, 31, 29, 98, 92, 43, 99, 67, 41], [69, 64, 61, 13, 31, 6, 84, 94, 32, 54]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 0, 4, 3, 1, 8, 9, 7, 5, 6], [1, 4, 3, 2, 0, 9, 8, 7, 6, 5], [3, 4, 0, 1, 2, 9, 8, 7, 6, 5], [4, 3, 0, 2, 1, 5, 7, 8, 9, 6], [0, 3, 4, 1, 2, 5, 8, 6, 7, 9], [3, 1, 4, 2, 0, 9, 7, 5, 6, 8], [3, 1, 4, 0, 2, 6, 9, 7, 8, 5], [0, 3, 1, 4, 2, 8, 5, 6, 9, 7], [1, 0, 3, 2, 4, 8, 5, 6, 9, 7], [2, 1, 0, 3, 4, 9, 6, 5, 7, 8], [3, 2, 4, 0, 1, 7, 5, 9, 6, 8], [0, 2, 1, 3, 4, 6, 7, 9, 8, 5], [3, 4, 0, 2, 1, 7, 6, 5, 9, 8], [3, 1, 2, 4, 0, 8, 5, 6, 7, 9], [1, 3, 4, 2, 0, 7, 8, 9, 5, 6], [4, 1, 2, 0, 3, 5, 7, 8, 9, 6], [1, 2, 0, 4, 3, 5, 7, 8, 6, 9], [2, 3, 4, 0, 1, 8, 5, 9, 7, 6], [0, 3, 1, 2, 4, 5, 6, 8, 7, 9], [4, 3, 0, 1, 2, 5, 8, 9, 7, 6]]

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
