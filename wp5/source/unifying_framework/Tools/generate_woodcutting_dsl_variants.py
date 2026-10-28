"""Generate LNS and MiniZinc variants of the woodcutting DSL from one source.

The woodcutting model is expressed once as a set of *shared facts* (instance
data, decision-variable domains, constraint/objective logic).  From it we emit:

  * wc_1.dsl — LNS form (run_lns.py):
      - every `def` runs in isolation; only declared decision vars are assigned
      - derived arrays (`cut_pieces`) are rebuilt inline with ``[0] * N``
      - objective is a single function `total_cost(assignments, cut_positions)`

  * wc_2.dsl — MiniZinc form (run_minizinc.py):
      - module-level cross-function flow: `cut_pieces, cutting_cost =
        cutting_stage(cut_positions)` and `use_cost = packing_stage(...)`
      - local arrays are `DSList(...)`-annotated and assigned elementwise
      - objective is the derived scalar `total_cost`

Run:
    python Tools/generate_woodcutting_dsl_variants.py \
        --boards 12 15 13 10 15 --layer-length 17 \
        --outdir problem_instances/cutting_packing
"""

from __future__ import annotations

import argparse
from pathlib import Path

_BOARDS_HEADER = """# Auto-generated via {tool}.  Do not edit by hand — keep the two
# variants in sync by editing the generator.

LAYER_LENGTH : DSInt() = {layer_length}
N_BOARDS : int = {n_boards}
ORIGINAL_BOARDS : DSList(N_BOARDS, DSInt()) = {boards}
MAX_BOARD_LENGTH : int = {max_board_length}
MAX_N_LAYERS : int = N_BOARDS * 2
"""

_LNS_MODEL = """
def cutting_constraints(cut_positions):
    for b in range(N_BOARDS):
        assert cut_positions[b] <= ORIGINAL_BOARDS[b]


def packing_constraints(assignments, cut_positions):
    cut_pieces = [0] * (N_BOARDS * 2)
    for b in range(N_BOARDS):
        assert cut_positions[b] <= ORIGINAL_BOARDS[b]
        cut_pieces[2 * b] = ORIGINAL_BOARDS[b] - cut_positions[b]
        cut_pieces[2 * b + 1] = cut_positions[b]
    for n_layer in range(MAX_N_LAYERS):
        used = 0
        for n_piece in range(N_BOARDS * 2):
            if assignments[n_piece] == n_layer:
                used = used + cut_pieces[n_piece]
        assert used <= LAYER_LENGTH


def total_cost(assignments, cut_positions):
    cut_pieces = [0] * (N_BOARDS * 2)
    cutting_cost = 0
    for b in range(N_BOARDS):
        cut_pieces[2 * b] = ORIGINAL_BOARDS[b] - cut_positions[b]
        cut_pieces[2 * b + 1] = cut_positions[b]
        if cut_positions[b] != 0:
            cutting_cost = cutting_cost + 1
    use_cost = 0
    for n_layer in range(MAX_N_LAYERS):
        used = 0
        for n_piece in range(N_BOARDS * 2):
            if assignments[n_piece] == n_layer:
                used = used + cut_pieces[n_piece]
        if used > 0:
            use_cost = use_cost + 3
    return cutting_cost + use_cost


cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
assignments: DSList(N_BOARDS * 2, DSInt(1, MAX_N_LAYERS))

cutting_constraints(cut_positions)
packing_constraints(assignments, cut_positions)

objective: DSInt(0, N_BOARDS * 7) = total_cost(assignments, cut_positions)

minimize(objective)
"""

_MZN_MODEL = """
def cutting_stage(
    cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
    ):
    cutting_cost: DSInt(0, N_BOARDS) = 0
    cut_pieces: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH))
    for n_board in range(N_BOARDS):
        assert cut_positions[n_board] <= ORIGINAL_BOARDS[n_board]
        cut_pieces[2 * n_board] = ORIGINAL_BOARDS[n_board] - cut_positions[n_board]
        cut_pieces[2 * n_board + 1] = cut_positions[n_board]
        if cut_positions[n_board] != 0:
            cutting_cost = cutting_cost + 1
    return cut_pieces, cutting_cost

def packing_stage(
    assignments: DSList(N_BOARDS * 2, DSInt(1, MAX_N_LAYERS)),
    cut_pieces: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH))
    ):
    use_cost: DSInt(0, N_BOARDS * 6) = 0
    used_length: DSList(MAX_N_LAYERS, DSInt(0, sum(ORIGINAL_BOARDS)))
    for n_layer in range(MAX_N_LAYERS):
        used_length[n_layer] = 0
        for n_board in range(N_BOARDS * 2):
            if assignments[n_board] == n_layer:
                used_length[n_layer] = used_length[n_layer] + cut_pieces[n_board]
        assert used_length[n_layer] <= LAYER_LENGTH
        if used_length[n_layer] > 0:
            use_cost = use_cost + 3
    return use_cost

cut_positions: DSList(N_BOARDS, DSInt(0, MAX_BOARD_LENGTH))
cut_pieces: DSList(N_BOARDS * 2, DSInt(0, MAX_BOARD_LENGTH))
cutting_cost : DSInt(0, N_BOARDS)
cut_pieces, cutting_cost = cutting_stage(cut_positions)

assignments: DSList(N_BOARDS * 2, DSInt(1, MAX_N_LAYERS)) 
use_cost: DSInt(0, N_BOARDS * 6) = 0
use_cost = packing_stage(assignments, cut_pieces)
total_cost: DSInt(0, N_BOARDS * 7) = cutting_cost + use_cost

minimize(total_cost)
"""


def generate(boards: list[int], layer_length: int, tool: str = __file__) -> tuple[str, str]:
    n_boards = len(boards)
    max_board_length = max(boards)
    header = _BOARDS_HEADER.format(
        tool=Path(tool).name,
        layer_length=layer_length,
        n_boards=n_boards,
        boards=boards,
        max_board_length=max_board_length,
    )
    return header + _LNS_MODEL, header + _MZN_MODEL


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boards", nargs="+", type=int, default=[12, 15, 13, 10, 15])
    parser.add_argument("--layer-length", type=int, default=17)
    parser.add_argument("--outdir", type=Path, default=Path("problem_instances/cutting_packing"))
    parser.add_argument("--lns-filename", default="wc_1.dsl")
    parser.add_argument("--mzn-filename", default="wc_2.dsl")
    args = parser.parse_args()

    lns_text, mzn_text = generate(args.boards, args.layer_length, tool=__file__)
    args.outdir.mkdir(parents=True, exist_ok=True)
    lns_path = args.outdir / args.lns_filename
    mzn_path = args.outdir / args.mzn_filename
    lns_path.write_text(lns_text, encoding="utf-8")
    mzn_path.write_text(mzn_text, encoding="utf-8")
    print(f"Wrote {lns_path}")
    print(f"Wrote {mzn_path}")


if __name__ == "__main__":
    main()
