BOX_CAPACITIES : DSList(4, DSInt()) = [5, 5, 5, 5]
ITEM_WEIGHTS : DSList(5, DSInt()) = [3, 2, 5, 3, 1]

NBOXES : int = 4
NITEMS : int = 5

assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))

def all_assigned(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    assigned: DSList(NITEMS, DSInt())
    for i in range(0, NBOXES):
        for j in range(0, NITEMS):
            if assignments[j] == i:
                assigned[j] = 1
    for k in range(0, NITEMS):
        assert assigned[k] != 0

def not_exceed(assignments: DSList(NITEMS, DSInt(0, NBOXES - 1))):
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_WEIGHTS)))
    obj = 0
    for i in range(0, NBOXES):
        cap[i] = 0
        for j in range(0, NITEMS):
            if assignments[j] == i:
                cap[i] = cap[i] + ITEM_WEIGHTS[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            obj = obj + 1
    return obj

all_assigned(assignments)
objective: DSInt(0, NBOXES) = not_exceed(assignments)

minimize(objective)
