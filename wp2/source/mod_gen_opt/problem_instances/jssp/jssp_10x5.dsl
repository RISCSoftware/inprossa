# Job Shop Scheduling Problem: 10 jobs x 5 machines
# Classic JSSP instance

N_JOBS : int = 10
N_MACHINES : int = 5

# Processing times [job][machine] - time each job needs on each machine
PROCESSING_TIMES : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [
    [4, 3, 5, 2, 3],
    [2, 5, 3, 4, 2],
    [3, 2, 4, 5, 3],
    [5, 4, 2, 3, 4],
    [3, 3, 4, 2, 5],
    [2, 4, 5, 3, 2],
    [5, 2, 3, 4, 3],
    [3, 5, 2, 2, 4],
    [4, 2, 5, 3, 3],
    [2, 3, 3, 5, 4]
]

# Machine sequence for each job: which machine each operation uses
# MACHINE_SEQUENCE[job][op_index] = machine_id
MACHINE_SEQUENCE : DSList(N_JOBS, DSList(N_MACHINES, DSInt())) = [
    [0, 1, 2, 3, 4],
    [1, 0, 3, 2, 4],
    [2, 3, 0, 4, 1],
    [0, 2, 4, 1, 3],
    [3, 1, 2, 0, 4],
    [1, 4, 0, 3, 2],
    [2, 0, 3, 4, 1],
    [4, 2, 1, 0, 3],
    [0, 3, 4, 2, 1],
    [3, 1, 0, 4, 2]
]

# Decision variables: completion time for each operation
completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, 500)))

def precedence_constraint(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, 500)))):
    # Each job's operations must respect sequence order with actual processing times
    for j in range(N_JOBS):
        assert completion[j][0] >= PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][0]]
        for op in range(1, N_MACHINES):
            assert completion[j][op] >= completion[j][op - 1] + PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]

def no_overlap_constraint(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, 500)))):
    # No two jobs can use the same machine at the same time
    for m in range(N_MACHINES):
        for j1 in range(N_JOBS):
            for op1 in range(N_MACHINES):
                if MACHINE_SEQUENCE[j1][op1] == m:
                    for j2 in range(j1 + 1, N_JOBS):
                        for op2 in range(N_MACHINES):
                            if MACHINE_SEQUENCE[j2][op2] == m:
                                # Either j1 starts after j2 finishes, or vice versa
                                assert completion[j1][op1] >= completion[j2][op2] + PROCESSING_TIMES[j1][m] or completion[j2][op2] >= completion[j1][op1] + PROCESSING_TIMES[j2][m]

def makespan(completion: DSList(N_JOBS, DSList(N_MACHINES, DSInt(0, 500)))):
    ms: DSInt() = 0
    for j in range(N_JOBS):
        if completion[j][N_MACHINES - 1] > ms:
            ms = completion[j][N_MACHINES - 1]
    return ms

precedence_constraint(completion)
no_overlap_constraint(completion)

objective: DSInt(0, 500) = makespan(completion)

minimize(objective)