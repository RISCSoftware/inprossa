from Translator.Objects.TreeSearchTranslator import TreeSearchTranslator

code = """
class DSList:
    def __init__(self, x, y):
        pass
        
class DSInt:
    def __init__(self, lb = None, ub = None):
        pass
    
BOX_CAPACITIES : DSList(4, DSInt()) = [5, 5, 5, 5]
ITEM_WEIGHTS : DSList(5, DSInt()) = [4, 2, 5, 3, 1]

NBOXES : int = 4
NITEMS : int = 5

assignments: DSList(NITEMS, DSInt(0, NBOXES)) = [1] * (NITEMS)


def not_exceed(assignments: DSList(NITEMS, DSInt(0, NBOXES))):
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_WEIGHTS))) = [0] * (NBOXES)
    #print(assignments)
    objective = 0
    for i in range(0, NBOXES):
        cap[i] = 0
        for j in range(0, NITEMS):
            if assignments[j] == i:
                cap[i] = cap[i] + ITEM_WEIGHTS[j]

        #print(f"  {i}: {cap[i]} < {BOX_CAPACITIES[i]}")
        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            objective = objective + 1

#not_exceed(assignments)
"""

translator = TreeSearchTranslator(code)
model = translator.unroll_translation()
