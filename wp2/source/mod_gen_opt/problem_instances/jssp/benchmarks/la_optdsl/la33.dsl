# Job Shop Scheduling instance: la33
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 30
N_MACHINES : int = 10
MAX_TIME : int = 14969

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[38, 75, 12, 97, 76, 29, 14, 66, 44, 12], [43, 38, 80, 82, 85, 58, 87, 92, 89, 69], [48, 8, 66, 7, 14, 41, 61, 43, 84, 5], [19, 74, 41, 59, 43, 42, 73, 97, 8, 96], [75, 5, 70, 42, 23, 55, 48, 38, 37, 7], [72, 31, 95, 79, 25, 56, 9, 60, 73, 43], [31, 78, 16, 94, 86, 21, 97, 53, 7, 64], [86, 65, 59, 44, 33, 85, 61, 32, 63, 30], [11, 61, 84, 16, 90, 30, 60, 93, 44, 45], [11, 28, 32, 36, 31, 47, 20, 52, 35, 49], [17, 34, 49, 84, 85, 20, 74, 68, 10, 77], [71, 7, 29, 85, 76, 59, 17, 17, 13, 48], [39, 16, 39, 87, 11, 32, 15, 19, 64, 43], [33, 82, 92, 83, 32, 99, 99, 91, 8, 57], [7, 48, 62, 88, 21, 39, 27, 91, 38, 69], [64, 45, 24, 80, 67, 18, 38, 88, 80, 44], [15, 72, 40, 21, 52, 51, 59, 24, 47, 43], [77, 43, 40, 31, 76, 20, 88, 70, 5, 32], [14, 58, 85, 64, 26, 94, 32, 49, 80, 47], [23, 11, 34, 75, 79, 26, 96, 5, 9, 59], [75, 20, 10, 66, 43, 37, 9, 83, 68, 52], [54, 26, 79, 88, 84, 6, 54, 59, 28, 42], [56, 29, 36, 40, 86, 68, 69, 23, 62, 16], [53, 5, 17, 59, 59, 78, 64, 82, 13, 12], [7, 62, 90, 83, 85, 69, 16, 81, 58, 66], [24, 65, 69, 42, 82, 82, 83, 46, 72, 33], [10, 27, 43, 20, 71, 65, 73, 99, 24, 64], [35, 92, 38, 35, 30, 45, 8, 82, 34, 21], [23, 84, 7, 85, 60, 15, 52, 94, 83, 6], [70, 29, 27, 80, 6, 39, 79, 28, 66, 66]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 4, 9, 5, 0, 1, 8, 6, 7, 3], [0, 5, 1, 3, 2, 4, 6, 8, 9, 7], [6, 4, 8, 7, 2, 3, 5, 0, 1, 9], [5, 3, 6, 4, 8, 2, 9, 7, 1, 0], [3, 5, 2, 8, 7, 6, 1, 9, 4, 0], [2, 7, 3, 0, 4, 1, 8, 9, 5, 6], [9, 3, 6, 4, 7, 5, 0, 8, 1, 2], [3, 2, 6, 8, 1, 7, 0, 5, 9, 4], [4, 5, 9, 3, 7, 1, 0, 8, 2, 6], [5, 2, 0, 7, 8, 4, 3, 6, 9, 1], [5, 3, 6, 1, 0, 8, 7, 9, 4, 2], [8, 5, 3, 1, 4, 6, 2, 0, 9, 7], [1, 9, 4, 6, 7, 3, 2, 0, 5, 8], [5, 8, 2, 1, 6, 3, 9, 4, 0, 7], [7, 0, 9, 4, 6, 5, 8, 3, 1, 2], [9, 8, 3, 7, 2, 4, 6, 0, 5, 1], [2, 3, 4, 7, 8, 0, 9, 1, 6, 5], [4, 7, 1, 2, 8, 6, 5, 3, 9, 0], [2, 7, 9, 5, 1, 6, 0, 3, 8, 4], [9, 1, 8, 4, 7, 3, 2, 0, 6, 5], [0, 2, 8, 3, 6, 7, 1, 9, 4, 5], [8, 1, 4, 7, 6, 0, 2, 9, 3, 5], [4, 9, 3, 0, 6, 8, 2, 7, 5, 1], [7, 1, 6, 9, 2, 8, 3, 0, 4, 5], [9, 6, 7, 5, 1, 3, 0, 4, 2, 8], [7, 2, 1, 5, 9, 6, 0, 3, 8, 4], [1, 8, 7, 5, 4, 9, 2, 6, 0, 3], [9, 3, 0, 5, 7, 8, 2, 4, 1, 6], [5, 7, 9, 4, 8, 1, 2, 6, 3, 0], [2, 6, 8, 9, 4, 7, 1, 0, 3, 5]]

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
