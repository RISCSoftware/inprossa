# Job Shop Scheduling instance: swv03
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 9895

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[30, 68, 19, 24, 55, 32, 45, 72, 34, 62], [67, 11, 63, 16, 65, 53, 52, 82, 23, 95], [12, 79, 19, 49, 17, 42, 25, 41, 40, 67], [42, 19, 71, 27, 95, 48, 31, 25, 100, 38], [94, 100, 89, 1, 68, 86, 55, 35, 56, 29], [57, 53, 4, 48, 93, 86, 80, 67, 99, 60], [60, 95, 12, 80, 82, 69, 81, 5, 88, 52], [28, 31, 64, 79, 63, 29, 33, 75, 63, 18], [13, 64, 31, 33, 9, 30, 79, 84, 20, 82], [56, 95, 14, 13, 34, 44, 16, 45, 62, 86], [12, 46, 66, 9, 66, 10, 6, 58, 62, 17], [7, 52, 37, 74, 89, 96, 21, 89, 43, 66], [67, 73, 5, 68, 49, 44, 29, 7, 30, 23], [68, 88, 21, 64, 75, 56, 6, 66, 72, 66], [27, 24, 69, 51, 25, 77, 45, 93, 26, 60], [34, 82, 19, 17, 75, 67, 91, 13, 35, 89], [21, 19, 65, 83, 2, 7, 65, 60, 8, 68], [50, 63, 4, 49, 2, 27, 68, 89, 46, 99], [48, 30, 66, 100, 45, 36, 58, 73, 5, 94], [53, 77, 36, 57, 56, 15, 59, 23, 8, 7]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 0, 1, 4, 3, 8, 7, 5, 9, 6], [2, 1, 4, 3, 0, 9, 8, 7, 6, 5], [2, 4, 1, 3, 0, 7, 9, 8, 6, 5], [0, 2, 3, 4, 1, 5, 8, 6, 7, 9], [3, 1, 4, 0, 2, 5, 7, 9, 8, 6], [4, 1, 2, 3, 0, 8, 7, 5, 6, 9], [4, 1, 2, 0, 3, 8, 7, 6, 9, 5], [3, 1, 4, 0, 2, 8, 5, 7, 9, 6], [4, 1, 2, 0, 3, 9, 6, 5, 7, 8], [2, 0, 1, 4, 3, 6, 5, 7, 8, 9], [4, 3, 2, 1, 0, 5, 7, 6, 8, 9], [4, 1, 2, 3, 0, 8, 5, 7, 6, 9], [1, 3, 2, 4, 0, 9, 7, 5, 8, 6], [2, 0, 1, 4, 3, 6, 8, 7, 9, 5], [1, 4, 2, 0, 3, 9, 8, 6, 5, 7], [2, 3, 1, 4, 0, 5, 9, 6, 7, 8], [4, 0, 3, 1, 2, 6, 8, 9, 7, 5], [1, 3, 2, 4, 0, 9, 5, 6, 8, 7], [0, 4, 3, 2, 1, 6, 7, 9, 5, 8], [2, 0, 4, 3, 1, 9, 6, 8, 5, 7]]

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
