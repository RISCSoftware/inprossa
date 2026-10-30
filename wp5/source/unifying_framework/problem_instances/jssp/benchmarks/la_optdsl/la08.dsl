# Job Shop Scheduling instance: la08
# Minimize makespan (total completion time for all jobs).

N_JOBS : int = 15
N_MACHINES : int = 5
MAX_TIME : int = 3825

# PROCESSING_TIMES[j][m] = time job j needs on machine m (MACHINE-indexed).
# MACHINE_SEQUENCE[j][op] = machine used by operation op of job j.
# The processing time of operation op of job j is
#   PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[12, 7, 94, 92, 91], [87, 19, 21, 11, 66], [75, 14, 20, 13, 16], [7, 77, 95, 7, 66], [15, 45, 34, 6, 89], [76, 53, 20, 77, 88], [52, 88, 74, 27, 9], [62, 88, 52, 69, 98], [62, 52, 61, 90, 9], [88, 15, 54, 59, 5], [41, 50, 23, 53, 78], [38, 71, 91, 68, 72], [45, 6, 25, 95, 52], [23, 66, 17, 30, 36], [71, 8, 95, 76, 88]]
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [[3, 2, 0, 4, 1], [2, 1, 0, 3, 4], [1, 3, 0, 4, 2], [2, 4, 0, 1, 3], [2, 4, 3, 1, 0], [4, 3, 2, 1, 0], [4, 3, 0, 1, 2], [3, 2, 0, 1, 4], [3, 0, 4, 2, 1], [4, 2, 3, 0, 1], [0, 1, 4, 3, 2], [0, 4, 2, 3, 1], [0, 3, 4, 2, 1], [3, 1, 0, 4, 2], [2, 0, 3, 1, 4]]

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
