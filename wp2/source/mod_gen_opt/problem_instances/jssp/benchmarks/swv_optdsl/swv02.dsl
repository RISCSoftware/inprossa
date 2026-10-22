# Job Shop Scheduling instance: swv02
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10001

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[16, 58, 22, 24, 53, 9, 57, 63, 92, 43], [6, 48, 14, 66, 24, 2, 85, 73, 19, 99], [100, 90, 63, 14, 31, 27, 15, 1, 51, 33], [98, 84, 52, 12, 96, 60, 74, 93, 45, 49], [39, 54, 28, 8, 30, 57, 75, 9, 41, 19], [94, 8, 89, 13, 37, 36, 63, 24, 71, 97], [90, 69, 25, 15, 65, 52, 56, 91, 83, 86], [59, 99, 41, 68, 14, 4, 55, 48, 13, 15], [36, 17, 51, 16, 54, 45, 50, 98, 68, 82], [75, 11, 55, 93, 51, 61, 40, 19, 24, 55], [56, 73, 59, 38, 51, 99, 29, 53, 7, 72], [68, 50, 88, 88, 33, 47, 52, 26, 74, 68], [3, 42, 45, 57, 28, 14, 22, 31, 44, 38], [89, 73, 12, 9, 49, 11, 15, 41, 37, 10], [76, 97, 100, 92, 25, 8, 92, 51, 58, 65], [50, 54, 85, 47, 45, 99, 39, 32, 87, 56], [70, 58, 33, 85, 25, 5, 65, 20, 52, 44], [22, 45, 60, 66, 5, 61, 73, 60, 14, 44], [64, 97, 31, 4, 43, 47, 93, 100, 10, 51], [9, 87, 34, 62, 56, 66, 95, 56, 42, 86]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 1, 0, 4, 3, 8, 9, 7, 5, 6], [3, 1, 4, 0, 2, 7, 9, 6, 8, 5], [4, 2, 0, 1, 3, 5, 9, 8, 6, 7], [2, 3, 4, 0, 1, 9, 6, 8, 5, 7], [4, 0, 2, 3, 1, 8, 6, 5, 7, 9], [3, 0, 2, 1, 4, 8, 6, 9, 5, 7], [3, 2, 1, 4, 0, 7, 6, 9, 8, 5], [3, 1, 4, 0, 2, 7, 9, 6, 8, 5], [4, 2, 1, 0, 3, 8, 5, 7, 6, 9], [1, 0, 4, 2, 3, 6, 9, 7, 8, 5], [4, 0, 3, 2, 1, 6, 8, 9, 5, 7], [3, 4, 1, 2, 0, 5, 8, 6, 9, 7], [2, 3, 0, 1, 4, 5, 8, 9, 6, 7], [3, 0, 4, 1, 2, 5, 8, 7, 9, 6], [3, 2, 4, 1, 0, 5, 9, 7, 6, 8], [4, 0, 3, 1, 2, 6, 9, 5, 8, 7], [0, 2, 3, 1, 4, 8, 7, 9, 6, 5], [1, 3, 4, 0, 2, 7, 6, 9, 5, 8], [4, 0, 2, 1, 3, 9, 7, 6, 5, 8], [3, 4, 2, 0, 1, 5, 8, 7, 9, 6]]

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
