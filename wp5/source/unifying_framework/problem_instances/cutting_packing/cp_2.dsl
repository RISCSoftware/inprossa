# zero-based indexing. Single unified model: works with both example_lns.py (LNS)
# and run_minizinc.py (MiniZinc). Self-contained functions only (no cross-function
# calls, no module-level data flow); objective is bound to a single function call.

LAYER_LENGTH : DSInt() = 17
N_BOARDS : int = 5
ORIGINAL_BOARDS : DSList(N_BOARDS, DSInt()) = [12, 15, 13, 10, 15]
MAX_BOARD_LENGTH : int = 15
MAX_N_LAYERS : int = N_BOARDS * 2

def cutting_constraints(cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))):
    for b in range(N_BOARDS):
        assert cut_positions[b] <= ORIGINAL_BOARDS[b]


def packing_constraints(
    assignments: DSList(N_BOARDS * 2, DSInt(0, MAX_N_LAYERS - 1)),
    cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
    ):
    cut_pieces: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH)) = [0] * (N_BOARDS * 2)
    for b in range(N_BOARDS):
        assert cut_positions[b] <= ORIGINAL_BOARDS[b]
        cut_pieces[2 * b] = ORIGINAL_BOARDS[b] - cut_positions[b]
        cut_pieces[2 * b + 1] = cut_positions[b]
    for n_layer in range(MAX_N_LAYERS):
        used: DSInt(0, sum(ORIGINAL_BOARDS)) = 0
        for n_piece in range(N_BOARDS * 2):
            if assignments[n_piece] == n_layer:
                used = used + cut_pieces[n_piece]
        assert used <= LAYER_LENGTH


def total_cost(
    assignments: DSList(N_BOARDS * 2, DSInt(0, MAX_N_LAYERS - 1)),
    cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
    ):
    cut_pieces: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH)) = [0] * (N_BOARDS * 2)
    cutting_cost: DSInt(0, N_BOARDS) = 0
    for b in range(N_BOARDS):
        cut_pieces[2 * b] = ORIGINAL_BOARDS[b] - cut_positions[b]
        cut_pieces[2 * b + 1] = cut_positions[b]
        if cut_positions[b] != 0:
            cutting_cost = cutting_cost + 1
    use_cost: DSInt(0, N_BOARDS * 6) = 0
    for n_layer in range(MAX_N_LAYERS):
        used: DSInt(0, sum(ORIGINAL_BOARDS)) = 0
        for n_piece in range(N_BOARDS * 2):
            if assignments[n_piece] == n_layer:
                used = used + cut_pieces[n_piece]
        if used > 0:
            use_cost = use_cost + 3
    cost: DSInt(0, N_BOARDS * 7) = cutting_cost + use_cost
    return cost


cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
assignments: DSList(N_BOARDS * 2, DSInt(0, MAX_N_LAYERS - 1))

cutting_constraints(cut_positions)
packing_constraints(assignments, cut_positions)

objective: DSInt(0, N_BOARDS * 7) = total_cost(assignments, cut_positions)

minimize(objective)
