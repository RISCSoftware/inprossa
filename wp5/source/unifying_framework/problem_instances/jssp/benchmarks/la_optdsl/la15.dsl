# Job Shop Scheduling instance: la15
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 20
N_MACHINES : int = 5
MAX_TIME : int = 5445

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[6, 81, 40, 37, 19], [55, 9, 40, 32, 81], [77, 46, 70, 55, 65], [64, 15, 21, 25, 65], [40, 44, 85, 24, 37], [89, 83, 84, 31, 29], [8, 80, 30, 38, 59], [80, 77, 56, 97, 41], [91, 17, 71, 50, 56], [88, 40, 7, 80, 59], [45, 29, 8, 58, 77], [54, 9, 36, 96, 10], [28, 98, 73, 92, 87], [70, 99, 27, 86, 96], [59, 95, 41, 85, 56], [52, 81, 92, 39, 32], [88, 7, 12, 60, 22], [93, 27, 69, 45, 49], [21, 84, 61, 68, 26], [99, 82, 33, 44, 71]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[0, 2, 1, 3, 4], [2, 3, 0, 4, 1], [1, 4, 2, 3, 0], [2, 4, 0, 3, 1], [2, 0, 1, 3, 4], [0, 4, 1, 3, 2], [4, 3, 1, 2, 0], [0, 2, 1, 4, 3], [4, 0, 3, 2, 1], [1, 0, 4, 2, 3], [0, 1, 2, 4, 3], [2, 0, 3, 1, 4], [0, 2, 1, 3, 4], [0, 3, 2, 1, 4], [1, 0, 4, 3, 2], [1, 2, 4, 0, 3], [1, 4, 2, 0, 3], [3, 0, 2, 4, 1], [0, 1, 2, 3, 4], [1, 2, 4, 0, 3]]

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
