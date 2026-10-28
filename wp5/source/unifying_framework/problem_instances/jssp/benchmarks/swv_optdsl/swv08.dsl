# Job Shop Scheduling instance: swv08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 15
MAX_TIME : int = 15807

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[23, 68, 49, 8, 73, 24, 81, 70, 74, 25, 45, 4, 69, 68, 59], [38, 69, 33, 34, 54, 7, 18, 81, 28, 81, 66, 66, 12, 91, 50], [8, 68, 82, 52, 83, 18, 20, 50, 93, 20, 73, 6, 99, 48, 54], [72, 91, 41, 1, 52, 30, 92, 76, 41, 45, 64, 71, 97, 52, 43], [48, 44, 29, 29, 88, 49, 92, 68, 22, 93, 99, 63, 69, 79, 14], [56, 80, 42, 93, 54, 94, 42, 64, 85, 28, 95, 39, 80, 12, 69], [90, 46, 91, 93, 75, 93, 9, 72, 67, 63, 76, 50, 82, 74, 77], [55, 23, 90, 60, 75, 74, 11, 97, 100, 55, 15, 54, 32, 67, 48], [32, 59, 40, 92, 69, 64, 71, 82, 28, 94, 1, 58, 71, 68, 34], [3, 50, 94, 33, 46, 87, 36, 50, 38, 1, 22, 45, 39, 84, 60], [34, 53, 28, 95, 32, 56, 97, 54, 84, 77, 46, 94, 98, 65, 48], [77, 18, 1, 74, 82, 97, 14, 81, 34, 35, 6, 14, 93, 84, 52], [86, 62, 57, 94, 77, 37, 80, 72, 56, 26, 7, 41, 47, 98, 67], [57, 61, 34, 30, 2, 45, 68, 57, 89, 10, 93, 43, 85, 96, 42], [17, 51, 4, 31, 53, 21, 49, 23, 4, 63, 45, 21, 1, 45, 90], [87, 40, 9, 6, 13, 18, 68, 95, 83, 66, 94, 22, 27, 28, 68], [67, 14, 80, 97, 23, 15, 14, 34, 45, 98, 1, 5, 12, 35, 87], [90, 37, 20, 74, 33, 3, 20, 97, 7, 100, 6, 41, 38, 56, 84], [28, 41, 99, 1, 63, 45, 47, 25, 59, 39, 76, 89, 5, 2, 60], [22, 2, 46, 25, 8, 22, 67, 82, 71, 24, 87, 79, 99, 64, 19]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 4, 2, 5, 6, 1, 0, 12, 8, 10, 11, 14, 9, 7, 13], [3, 2, 5, 1, 4, 6, 0, 8, 12, 14, 10, 7, 9, 13, 11], [0, 6, 3, 4, 5, 2, 1, 7, 14, 11, 10, 13, 9, 8, 12], [2, 0, 1, 4, 5, 3, 6, 13, 8, 9, 14, 12, 10, 11, 7], [0, 1, 5, 6, 3, 2, 4, 14, 10, 8, 13, 9, 12, 11, 7], [0, 6, 2, 3, 1, 4, 5, 12, 14, 11, 8, 10, 13, 9, 7], [0, 4, 6, 1, 2, 3, 5, 14, 9, 11, 12, 13, 8, 7, 10], [0, 2, 6, 3, 4, 1, 5, 11, 7, 12, 13, 10, 14, 8, 9], [6, 5, 2, 0, 3, 1, 4, 13, 14, 12, 8, 9, 7, 10, 11], [6, 4, 1, 5, 3, 2, 0, 14, 11, 13, 9, 8, 10, 12, 7], [1, 0, 5, 6, 3, 4, 2, 14, 7, 12, 8, 9, 10, 13, 11], [2, 5, 0, 4, 6, 1, 3, 14, 11, 12, 9, 8, 13, 10, 7], [1, 0, 2, 6, 5, 3, 4, 7, 9, 11, 10, 8, 13, 14, 12], [5, 3, 0, 6, 1, 2, 4, 7, 13, 9, 12, 14, 10, 8, 11], [6, 4, 1, 2, 0, 5, 3, 10, 13, 9, 11, 8, 7, 14, 12], [6, 5, 0, 3, 4, 2, 1, 8, 7, 12, 10, 14, 11, 13, 9], [2, 6, 0, 5, 1, 3, 4, 8, 10, 11, 14, 7, 12, 9, 13], [4, 2, 3, 6, 5, 0, 1, 13, 12, 8, 14, 9, 11, 10, 7], [6, 4, 3, 0, 2, 1, 5, 14, 13, 7, 8, 9, 10, 11, 12], [6, 2, 3, 1, 5, 4, 0, 13, 7, 12, 11, 10, 8, 9, 14]]

# Decision variable: completion time of operation op for each job.
completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))


def precedence_constraint(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, MAX_TIME)))):
    # Each job's operations must respect sequence order with processing times.
    for j in range(N_JOBS):
        assert completion[j][0] >= PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][0]]
        for op in range(1, N_MACHINES):
            assert completion[j][op] >= completion[j][op - 1] + PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]


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
