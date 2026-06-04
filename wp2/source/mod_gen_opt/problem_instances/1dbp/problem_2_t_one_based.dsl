BOX_CAPACITIES : DSList(4, DSInt()) = [5, 5, 5, 5]
ITEM_WEIGHTS : DSList(5, DSInt()) = [3, 2, 5, 3, 1]

NBOXES : int = 4
NITEMS : int = 5

assignments: DSList(NITEMS, DSInt(1, NBOXES))

def all_assigned(assignments: DSList(NITEMS, DSInt(1, NBOXES))):
    assigned: DSList(NITEMS, DSInt())
    for i in range(1, NBOXES + 1):
        for j in range(1, NITEMS + 1):
            if assignments[j] == i:
                assigned[j] = 1
    for k in range(1, NITEMS + 1):
        assert assigned[k] != 0

def not_exceed(assignments: DSList(NITEMS, DSInt(1, NBOXES))):
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_WEIGHTS)))
    obj = 0
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + ITEM_WEIGHTS[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            obj = obj + 1
    return obj

all_assigned(assignments)
objective: DSInt(0, NBOXES) = not_exceed(assignments)

minimize(objective)


# A : DSList(4, DSInt()) = [5, 5, 5, 5]
# B : DSList(5, DSInt()) = [3, 2, 5, 3, 1]
# 
# NA : int = 4
# NB : int = 5
# 
# variables: DSList(NB, DSInt(1, NA)) 
# 
# 
# def not_exceed(variables: DSList(NB, DSInt(1, NA))):
#     c: DSList(NA, DSInt(0, sum(B))) 
#     #= [1] * (NA)
#     obj = 0
#     for i in range(1, NA):
#         c[i] = 0
#         for j in range(1, NB):
#             if variables[j] == i:
#                 c[i] = c[i] + B[j]
# 
#         assert c[i] <= A[i]
#         if c[i] > 0:
#             obj = obj + 1
#     return obj
# 
# objective: DSInt(0, NA) = not_exceed(variables)
# 
# minimize(objective)