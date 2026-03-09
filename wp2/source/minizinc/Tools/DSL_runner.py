from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner


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

dsl_code = f"""
LAYER_LENGTH : DSInt() = 17
N_BOARDS : int = 5
ORIGINAL_BOARDS : DSList(N_BOARDS, DSInt()) = [12, 15, 13, 10, 15]
MAX_BOARD_LENGTH : int = 15
MAX_N_LAYERS : int = N_BOARDS * 2

def cutting_stage(
    cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
    ):
    cutting_cost: DSInt(0, N_BOARDS) = 0
    cut_boards: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH))
    for n_board in range(1, N_BOARDS + 1):
        cut_boards[2 * n_board] = ORIGINAL_BOARDS[n_board] - cut_positions[n_board]
        cut_boards[2 * n_board - 1] = cut_positions[n_board]
        if cut_positions[n_board] != 0:
            cutting_cost = cutting_cost + 1
    return cut_boards, cutting_cost

def packing_stage(
    assignments: DSList(N_BOARDS * 2, DSInt(1, MAX_N_LAYERS)),
    cut_boards: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH))
    ):
    use_cost: DSInt(0, N_BOARDS * 6) = 0
    used_length: DSList(MAX_N_LAYERS, DSInt(0, sum(ORIGINAL_BOARDS)))
    for n_layer in range(1, MAX_N_LAYERS + 1):
        used_length[n_layer] = 0
        for n_board in range(1, N_BOARDS * 2 + 1):
            if assignments[n_board] == n_layer:
                used_length[n_layer] = used_length[n_layer] + cut_boards[n_board]
        assert used_length[n_layer] <= LAYER_LENGTH
        if used_length[n_layer] > 0:
            use_cost = use_cost + 3
    return use_cost

cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
cut_boards: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH))
cutting_cost : DSInt(0, N_BOARDS)
cut_boards, cutting_cost = cutting_stage(cut_positions)

assignments: DSList(N_BOARDS * 2, DSInt(1, MAX_N_LAYERS)) 
use_cost: DSInt(0, N_BOARDS * 6) = 0
use_cost = packing_stage(assignments, cut_boards)
total_cost: DSInt(0, N_BOARDS * 7) = cutting_cost + use_cost

minimize(total_cost)
"""

if __name__ == "__main__":
    dsl_runner = DSLRunner(dsl_code)
    result = dsl_runner.run()
    print(result)