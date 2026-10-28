# Auto-generated from one_beam_no_faults.json by Tools/convert_cutting_packing.py
# Unified cutting & packing model: runs under example_lns.py AND run_minizinc.py.
# Preprocessing: 4 input board(s) -> 4 usable segment(s)
#   (Quality-1 parts kept; Quality-2 discarded; Quality-3 removed with +-50 margin;
#    board edges [10, 10] skipped; segments < 10 dropped).
# Demand: 1 beam(s) x 5 layer(s) of length 500.
# Volume lower bound on waste: 20 (usable 2520 vs demand 2500).
# Not modeled: seam positions, static forbidden zones, staggered joints, width/height.

LAYER_LENGTH : DSInt() = 500
N_LAYERS : int = 5
MIN_PIECE_LENGTH : int = 10
N_SEGMENTS : int = 4
MAX_SEGMENT_LENGTH : int = 630
N_CUTS_PER_SEGMENT : int = 2
N_PIECES_PER_SEGMENT : int = 3
N_CUTS : int = 8
N_PIECES : int = 12
TOTAL_USABLE : int = 2520
WASTE_WEIGHT : int = 1
CUT_WEIGHT : int = 1
MAX_COST : int = 2528
SEGMENT_LENGTHS : DSList(N_SEGMENTS, DSInt()) = [
    630, 630, 630, 630
]


def cutting_constraints(cut_positions: DSList(N_CUTS, DSInt(0, MAX_SEGMENT_LENGTH))):
    for s in range(N_SEGMENTS):
        for j in range(N_CUTS_PER_SEGMENT):
            assert cut_positions[s * N_CUTS_PER_SEGMENT + j] <= SEGMENT_LENGTHS[s]
        for j in range(N_CUTS_PER_SEGMENT - 1):
            assert cut_positions[s * N_CUTS_PER_SEGMENT + j] <= cut_positions[s * N_CUTS_PER_SEGMENT + j + 1]


def packing_constraints(
    piece_assignments: DSList(N_PIECES, DSInt(0, N_LAYERS)),
    cut_positions: DSList(N_CUTS, DSInt(0, MAX_SEGMENT_LENGTH))
    ):
    pieces: DSList(N_PIECES, DSInt(0, MAX_SEGMENT_LENGTH)) = [0] * N_PIECES
    for s in range(N_SEGMENTS):
        prev: DSInt(0, MAX_SEGMENT_LENGTH) = 0
        for j in range(N_CUTS_PER_SEGMENT):
            pieces[s * N_PIECES_PER_SEGMENT + j] = cut_positions[s * N_CUTS_PER_SEGMENT + j] - prev
            prev = cut_positions[s * N_CUTS_PER_SEGMENT + j]
        pieces[s * N_PIECES_PER_SEGMENT + N_CUTS_PER_SEGMENT] = SEGMENT_LENGTHS[s] - prev
    for p in range(N_PIECES):
        if piece_assignments[p] != N_LAYERS:
            assert pieces[p] >= MIN_PIECE_LENGTH
    for l in range(N_LAYERS):
        used: DSInt(0, LAYER_LENGTH) = 0
        for p in range(N_PIECES):
            if piece_assignments[p] == l:
                used = used + pieces[p]
        ok: DSInt(0, 1) = 0
        if used == LAYER_LENGTH:
            ok = 1
        if used == 0:
            ok = 1
        assert ok == 1


def total_cost(
    piece_assignments: DSList(N_PIECES, DSInt(0, N_LAYERS)),
    cut_positions: DSList(N_CUTS, DSInt(0, MAX_SEGMENT_LENGTH))
    ):
    pieces: DSList(N_PIECES, DSInt(0, MAX_SEGMENT_LENGTH)) = [0] * N_PIECES
    for s in range(N_SEGMENTS):
        prev: DSInt(0, MAX_SEGMENT_LENGTH) = 0
        for j in range(N_CUTS_PER_SEGMENT):
            pieces[s * N_PIECES_PER_SEGMENT + j] = cut_positions[s * N_CUTS_PER_SEGMENT + j] - prev
            prev = cut_positions[s * N_CUTS_PER_SEGMENT + j]
        pieces[s * N_PIECES_PER_SEGMENT + N_CUTS_PER_SEGMENT] = SEGMENT_LENGTHS[s] - prev
    waste: DSInt(0, TOTAL_USABLE) = 0
    for p in range(N_PIECES):
        if piece_assignments[p] == N_LAYERS:
            waste = waste + pieces[p]
    n_cuts: DSInt(0, N_CUTS) = 0
    for s in range(N_SEGMENTS):
        prev: DSInt(0, MAX_SEGMENT_LENGTH) = 0
        for j in range(N_CUTS_PER_SEGMENT):
            if cut_positions[s * N_CUTS_PER_SEGMENT + j] > prev:
                n_cuts = n_cuts + 1
            prev = cut_positions[s * N_CUTS_PER_SEGMENT + j]
    cost: DSInt(0, MAX_COST) = WASTE_WEIGHT * waste + CUT_WEIGHT * n_cuts
    return cost


cut_positions: DSList(N_CUTS, DSInt(0, MAX_SEGMENT_LENGTH))
piece_assignments: DSList(N_PIECES, DSInt(0, N_LAYERS))

cutting_constraints(cut_positions)
packing_constraints(piece_assignments, cut_positions)

objective: DSInt(0, MAX_COST) = total_cost(piece_assignments, cut_positions)

minimize(objective)
