import io
from contextlib import redirect_stdout

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner


dsl_code = f"""
BOX_CAPACITIES : DSList(10, DSInt()) = [5,5,5,5, 5,5,5,5, 5,5]
ITEM_LENGTHS : DSList(12, DSInt()) = [2,3,4,5,4,3,2,1,5,4,3,2]
MAX_ITEM_LENGTH : int = 5

NBOXES : int = 10
NITEMS : int = 12
 
assignments: DSList(NITEMS * 2, DSInt(1, NBOXES))
cut_positions: DSList(NITEMS, DSInt(0, MAX_ITEM_LENGTH))
cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))

def cutting_machine(
    cut_positions: DSList(NITEMS, DSInt(0, MAX_ITEM_LENGTH))
    ):
    cutting_cost: DSInt(0, NITEMS) = 0
    cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))
    for n_item in range(1, NITEMS + 1):
        cut_items[2 * n_item] = ITEM_LENGTHS[n_item] - cut_positions[n_item]
        cut_items[2 * n_item - 1] = cut_positions[n_item]
        if cut_positions[n_item] != 0:
            # A cut is made
            cutting_cost = cutting_cost + 1

    return cut_items, cutting_cost


def not_exceed(
    assignments: DSList(NITEMS * 2, DSInt(1, NBOXES)),
    cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))
    ):
    use_cost: DSInt(0, NITEMS * 3) = 0
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_LENGTHS)))
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS * 2 + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + cut_items[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            use_cost = use_cost + 3
    return use_cost

cutting_cost : DSInt(0, NITEMS)
cut_items, cutting_cost = cutting_machine(cut_positions)
use_cost: DSInt(0, NITEMS * 3) = 0
use_cost = not_exceed(assignments, cut_items)
total_cost: DSInt(0, NITEMS * 4) = cutting_cost + use_cost
minimize(total_cost)
"""

class DSLRunner:
    def __init__(self,
                 code: str,
                 solver_name="chuffed",
                 timelimit: float = 10):
        self.code = code
        self.solver_name = solver_name
        self.timelimit = timelimit

    def run(self):
        translator = MiniZincTranslator(self.code)
        model = translator.unroll_translation()

        runner = MiniZincRunner(
            solver_name=self.solver_name,
            timelimit=self.timelimit
            )
        result = runner.run(model)
        return result
    

if __name__ == "__main__":
    dsl_runner = DSLRunner(dsl_code)
    result = dsl_runner.run()
    print(result)