from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner

code = """
BOX_CAPACITIES : DSList(4, DSInt()) = [5, 5, 5, 5]
ITEM_WEIGHTS : DSList(5, DSInt()) = [4, 2, 5, 3, 1]

NBOXES : int = 4
NITEMS : int = 5

assignments: DSList(NITEMS, DSInt(1, NBOXES))

def not_exceed(assignments: DSList(NITEMS, DSInt(1, NBOXES))):
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_WEIGHTS)))
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + ITEM_WEIGHTS[j]

        assert cap[i] <= BOX_CAPACITIES[i] # + slack
        if cap[i] > 0:
            objective = objective + 1

not_exceed(assignments)
"""

if __name__ == "__main__":
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print("\n")
    print(model)
    print("\n")


    runner = MiniZincRunner()
    result = runner.run(model)
    print(result)
