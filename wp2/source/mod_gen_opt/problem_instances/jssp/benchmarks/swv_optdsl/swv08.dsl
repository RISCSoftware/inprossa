# Job Shop Scheduling instance: swv08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15807

# PROCESSING_TIMES[j][op] and MACHINE_SEQUENCE[j][op] define each job route.
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[8, 73, 49, 24, 81, 68, 23, 69, 74, 45, 4, 59, 25, 70, 68], [34, 33, 7, 69, 54, 18, 38, 28, 12, 50, 66, 81, 81, 91, 66], [8, 20, 52, 83, 18, 82, 68, 50, 54, 6, 73, 48, 20, 93, 99], [41, 72, 91, 52, 30, 1, 92, 52, 41, 45, 43, 97, 64, 71, 76], [48, 44, 49, 92, 29, 29, 88, 14, 99, 22, 79, 93, 69, 63, 68], [56, 42, 42, 93, 80, 54, 94, 80, 69, 39, 85, 95, 12, 28, 64], [90, 75, 9, 46, 91, 93, 93, 77, 63, 50, 82, 74, 67, 72, 76], [55, 90, 11, 60, 75, 23, 74, 54, 97, 32, 67, 15, 48, 100, 55], [71, 64, 40, 32, 92, 59, 69, 68, 34, 71, 28, 94, 82, 1, 58], [36, 46, 50, 87, 33, 94, 3, 60, 45, 84, 1, 38, 22, 39, 50], [53, 34, 56, 97, 95, 32, 28, 48, 54, 98, 84, 77, 46, 65, 94], [1, 97, 77, 82, 14, 18, 74, 52, 14, 93, 35, 34, 84, 6, 81], [62, 86, 57, 80, 37, 94, 77, 72, 26, 41, 7, 56, 98, 67, 47], [45, 30, 57, 68, 61, 34, 2, 57, 96, 10, 85, 42, 93, 89, 43], [49, 53, 51, 4, 17, 21, 31, 45, 45, 63, 21, 4, 23, 90, 1], [68, 18, 87, 6, 13, 9, 40, 83, 95, 27, 94, 68, 22, 28, 66], [80, 14, 67, 15, 14, 97, 23, 45, 1, 5, 87, 34, 12, 98, 35], [33, 20, 74, 20, 3, 90, 37, 56, 38, 7, 84, 100, 41, 6, 97], [47, 63, 1, 28, 99, 41, 45, 60, 2, 25, 59, 39, 76, 89, 5], [67, 46, 25, 2, 22, 8, 22, 64, 82, 99, 79, 87, 71, 24, 19]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 4, 2, 5, 6, 1, 0, 12, 8, 10, 11, 14, 9, 7, 13], [3, 2, 5, 1, 4, 6, 0, 8, 12, 14, 10, 7, 9, 13, 11], [0, 6, 3, 4, 5, 2, 1, 7, 14, 11, 10, 13, 9, 8, 12], [2, 0, 1, 4, 5, 3, 6, 13, 8, 9, 14, 12, 10, 11, 7], [0, 1, 5, 6, 3, 2, 4, 14, 10, 8, 13, 9, 12, 11, 7], [0, 6, 2, 3, 1, 4, 5, 12, 14, 11, 8, 10, 13, 9, 7], [0, 4, 6, 1, 2, 3, 5, 14, 9, 11, 12, 13, 8, 7, 10], [0, 2, 6, 3, 4, 1, 5, 11, 7, 12, 13, 10, 14, 8, 9], [6, 5, 2, 0, 3, 1, 4, 13, 14, 12, 8, 9, 7, 10, 11], [6, 4, 1, 5, 3, 2, 0, 14, 11, 13, 9, 8, 10, 12, 7], [1, 0, 5, 6, 3, 4, 2, 14, 7, 12, 8, 9, 10, 13, 11], [2, 5, 0, 4, 6, 1, 3, 14, 11, 12, 9, 8, 13, 10, 7], [1, 0, 2, 6, 5, 3, 4, 7, 9, 11, 10, 8, 13, 14, 12], [5, 3, 0, 6, 1, 2, 4, 7, 13, 9, 12, 14, 10, 8, 11], [6, 4, 1, 2, 0, 5, 3, 10, 13, 9, 11, 8, 7, 14, 12], [6, 5, 0, 3, 4, 2, 1, 8, 7, 12, 10, 14, 11, 13, 9], [2, 6, 0, 5, 1, 3, 4, 8, 10, 11, 14, 7, 12, 9, 13], [4, 2, 3, 6, 5, 0, 1, 13, 12, 8, 14, 9, 11, 10, 7], [6, 4, 3, 0, 2, 1, 5, 14, 13, 7, 8, 9, 10, 11, 12], [6, 2, 3, 1, 5, 4, 0, 13, 7, 12, 11, 10, 8, 9, 14]]

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
