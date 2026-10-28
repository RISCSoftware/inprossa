# Job Shop Scheduling instance: orb10
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 10
N_MACHINES : int = 10
MAX_TIME : int = 5549

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[93, 16, 53, 99, 86, 70, 14, 91, 13, 66], [62, 75, 12, 9, 64, 62, 21, 65, 34, 99], [58, 38, 83, 66, 67, 28, 92, 64, 26, 12], [77, 73, 75, 82, 19, 18, 84, 89, 8, 73], [34, 74, 62, 60, 92, 44, 40, 48, 22, 67], [5, 95, 77, 58, 89, 92, 75, 97, 85, 8], [31, 60, 80, 62, 21, 12, 5, 78, 52, 43], [96, 53, 39, 51, 78, 56, 75, 23, 23, 81], [63, 14, 88, 93, 21, 83, 47, 10, 55, 79], [43, 63, 83, 29, 52, 98, 54, 39, 33, 23]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[9, 8, 0, 7, 6, 5, 3, 2, 4, 1], [8, 9, 0, 7, 5, 4, 6, 2, 3, 1], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [0, 1, 3, 2, 6, 4, 5, 7, 8, 9], [0, 1, 7, 5, 4, 6, 3, 2, 8, 9], [9, 8, 3, 7, 5, 4, 6, 2, 1, 0], [8, 9, 6, 7, 5, 3, 4, 2, 1, 0], [9, 8, 7, 6, 4, 5, 3, 2, 1, 0], [9, 8, 2, 4, 5, 3, 6, 7, 0, 1], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]

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
