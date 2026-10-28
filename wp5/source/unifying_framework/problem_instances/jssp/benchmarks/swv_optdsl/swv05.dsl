# Job Shop Scheduling instance: swv05
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 10
MAX_TIME : int = 10097

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[84, 30, 19, 80, 14, 73, 91, 81, 51, 71], [7, 39, 74, 66, 79, 93, 21, 76, 76, 6], [61, 38, 73, 33, 90, 86, 35, 76, 61, 28], [77, 33, 1, 22, 1, 4, 98, 68, 8, 27], [7, 95, 63, 50, 5, 60, 70, 34, 46, 28], [98, 73, 32, 21, 15, 7, 34, 24, 24, 9], [51, 16, 30, 51, 47, 41, 79, 79, 72, 3], [53, 59, 19, 20, 3, 96, 20, 90, 18, 16], [93, 34, 55, 97, 90, 63, 1, 81, 41, 51], [45, 92, 83, 87, 77, 93, 75, 75, 33, 60], [31, 58, 66, 94, 17, 63, 78, 80, 52, 61], [89, 25, 75, 41, 70, 73, 28, 100, 94, 88], [62, 67, 55, 12, 62, 58, 55, 73, 66, 1], [37, 2, 17, 39, 81, 42, 71, 74, 61, 5], [31, 5, 31, 62, 63, 3, 34, 77, 34, 7], [5, 82, 55, 62, 80, 80, 6, 29, 7, 89], [22, 50, 58, 26, 68, 90, 9, 12, 87, 34], [50, 64, 28, 63, 34, 2, 63, 9, 61, 48], [47, 23, 23, 98, 82, 32, 78, 66, 100, 79], [90, 13, 77, 80, 14, 36, 51, 31, 69, 30]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[2, 1, 3, 0, 4, 8, 5, 6, 7, 9], [2, 4, 1, 0, 3, 9, 5, 8, 6, 7], [4, 3, 1, 2, 0, 8, 7, 5, 9, 6], [4, 3, 2, 0, 1, 6, 5, 9, 8, 7], [2, 4, 1, 0, 3, 8, 9, 6, 5, 7], [0, 1, 4, 3, 2, 7, 9, 8, 5, 6], [3, 4, 2, 1, 0, 5, 6, 7, 9, 8], [4, 1, 0, 3, 2, 6, 9, 7, 5, 8], [1, 2, 3, 0, 4, 7, 5, 8, 6, 9], [4, 3, 1, 2, 0, 7, 9, 6, 5, 8], [0, 2, 1, 4, 3, 5, 7, 9, 6, 8], [4, 1, 2, 0, 3, 7, 5, 6, 8, 9], [1, 4, 3, 2, 0, 5, 8, 7, 6, 9], [4, 0, 1, 3, 2, 7, 6, 8, 5, 9], [3, 0, 4, 2, 1, 9, 7, 8, 6, 5], [0, 2, 3, 1, 4, 6, 8, 7, 5, 9], [3, 1, 2, 0, 4, 7, 6, 9, 5, 8], [0, 2, 1, 4, 3, 7, 9, 6, 8, 5], [0, 2, 1, 4, 3, 7, 6, 8, 9, 5], [1, 4, 0, 2, 3, 9, 7, 5, 6, 8]]

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
