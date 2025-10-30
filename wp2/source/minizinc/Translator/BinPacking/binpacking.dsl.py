BOX_CAPACITIES = [5, 5, 5, 5]
ITEM_WEIGHTS = [4, 2, 5, 3, 1]

nboxes = len(BOX_CAPACITIES)
nitems = len(ITEM_WEIGHTS)

#BoxAssignments: list = [[-1 for i in ITEM_WEIGHTS] for b in BOX_CAPACITIES]

#assignments: DSList(nboxes, DSList(nitems, DSBool))
# alternative
assignments: DSList(nitems, DSInt(1, nboxes))

# use a slack variable or mark not yet assigned items

# objective: min(objective)

# Functions/Predicates
def check_exact_one(assignments):
    for i in range(nboxes):
        for j in range(nitems):
            t_assignments[j,i] = assignments[i,j]
    
    for j in range(nitems):
        assert sum(t_assignments[j]) == 1

def not_exceed(assignments, objective):
    for i in range(nboxes):
        cap[i] = 0
        for j in range(nitems):
            #if assignments[i,j] == 1:
            if assignments[i] == j:
                cap[i] += ITEM_WEIGHTS[j]

        assert cap[i] <= BOX_CAPACITIES[i] # + slack
        if cap[i] > 0:
            objective += 1
