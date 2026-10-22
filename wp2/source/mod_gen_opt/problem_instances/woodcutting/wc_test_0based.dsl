# 0-based indexing translation of wc_test.dsl.
#
# Faithful port of the original 1-based reference model to 0-based indexing so
# it runs under BOTH the LNS evaluator (large_neighborhood_search, --dsl-index-base 0)
# and the MiniZinc translator (run_minizinc.py --dsl-index-base 0).
#
# Indexing changes from the original:
#   - cut positions: cut_list[0..MAX_N_CUTS_PER_BOARD-1]  (was 1..MAX_N_CUTS_PER_BOARD)
#   - forbidden interval entries: FORBIDDEN_INTERVALS[i][0]/[i][1] (was [1]/[2])
#   - piece slot: pieces[board_index * (MAX_N_CUTS_PER_BOARD - 1) + (cut_index - 1)]
#                 (was (board_index - 1) * ...; board_index from enumerate is 0-based here)
#   - quality is a plain 0/1 int (DSInt(0,1)), not a bare DSBool() — the original
#     `quality : DSBool ()` was a bare annotation with no initializer, which the
#     LNS compiler cannot handle (UnboundLocalError on subscript).
#
# Local list-of-record initializers are written as FULL LITERAL LISTS (one record
# dict per element, length = the declared DSList length). Do NOT use
# `[{"quality": 1, "length": 0}] * N_PIECES` style multipliers: the LNS evaluator
# accepts them (compiles to Python), but the MiniZinc translator emits them
# VERBATIM, and MiniZinc has no `array * int` operator for record arrays
# (TypeError). Literal lists translate correctly on both backends.
#
# Objective semantics are preserved EXACTLY from the original: `waste` accumulates
# the full length of every discarded piece (bad ones included). See tools note for
# the alternative GoodCutOut-only objective used by the converter-generated models.
#
# NOTE: `GIVEN_PIECES` from the original (length 2, inconsistent with N_PIECES = 6)
# and the module re-declaration `pieces = GIVEN_PIECES` before `checking_machine`
# are NOT included here. That shadowing construct is invalid in the pipeline model
# (a name bound by a machine call cannot be re-assigned at module level), and the
# length-2 constant breaks MiniZinc's fixed-size array (declared [1..6], assigned
# [1..2]). The pipeline's `pieces` from `cutting_machine` is consumed directly.

N_BOARDS : int = 2
MAX_BOARD_LENGTH : int = 30
MAX_N_INTERVALS : int = 2
# Maximum number of bad (or curved) intervals per board
MAX_N_CUTS_PER_BOARD : int = 4
# Maximum number of cuts per board (including the two fixed cuts at
# the start and end of the board)
N_PIECES : int = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1)
# Total number of pieces to be obtained from all boards
BEAM_LENGTH : int = 10
# Length of the beams to be produced
BEAM_DEPTH : int = 5
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM : int = 2
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES : int = 1
FORBIDDEN_INTERVALS : DSList(2, DSList(2, int)) = [[3, 4], [7, 8]]

Interval = DSRecord({
    "start": DSInt(0, MAX_BOARD_LENGTH),
    "end": DSInt(0, MAX_BOARD_LENGTH)
})

Board = DSRecord({
    "length": DSInt(0, MAX_BOARD_LENGTH),
    "bad_intervals": DSList(MAX_N_INTERVALS, Interval),
    "curved_intervals": DSList(MAX_N_INTERVALS, Interval)
})

Piece = DSRecord({
    "length": DSInt(0, MAX_BOARD_LENGTH),
    "quality": DSInt(0, 1)
})

CutList = DSRecord({
    "position_list": DSList(MAX_N_CUTS_PER_BOARD, DSInt(0, MAX_BOARD_LENGTH))
})

GIVEN_INITIAL_BOARDS : DSList(N_BOARDS, Board) = [
    Board(length=20,
        bad_intervals=[
            Interval(5, 6),
            Interval(15, 16)
        ],
        curved_intervals=[
            Interval(10, 12),
            Interval(18, 20)
        ]
    ),
    Board(length=25,
        bad_intervals=[
            Interval(10, 14),
            Interval(18, 20)
        ],
        curved_intervals=[
            Interval(7, 9),
            Interval(18, 20)
        ],
    )
]

initial_boards : DSList(N_BOARDS, Board) = GIVEN_INITIAL_BOARDS
# Swapping boards
swapping_decisions_boards : DSList(N_BOARDS - 1, bool)
swapped_boards : DSList(N_BOARDS, Board)
swapped_boards = reordering_board_machine(initial_boards, swapping_decisions_boards)
# Cutting boards
cuts_list_list : DSList(N_BOARDS, CutList)
pieces : DSList(N_PIECES, Piece)
pieces = cutting_machine(swapped_boards, cuts_list_list)
# Filtering pieces
keep_decisions : DSList(N_PIECES, bool)
filtered_pieces : DSList(N_PIECES, Piece)
waste : int = 0
filtered_pieces, waste = filtering_machine(pieces, keep_decisions)

# Reordering pieces
swapping_decisions : DSList(N_PIECES - 1, bool)
reordered_pieces : DSList(N_PIECES, Piece)
reordered_pieces = reordering_piece_machine(filtered_pieces, swapping_decisions)

# Checking pieces
checking_machine(reordered_pieces)
minimize(waste)

def reordering_piece_machine(list_to_reorder: DSList(N_PIECES, Piece),
                             swapping_decisions: DSList(N_PIECES - 1, bool),
                             ) -> DSList(N_PIECES, Piece):
    aux_piece : Piece
    new_list : DSList(N_PIECES, Piece) = [
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
    ]
    for i in range(N_PIECES):
        new_list[i] = list_to_reorder[i]
    for i in range(N_PIECES - 1): # Number of swapping decisions
        if swapping_decisions[i]:
            aux_piece = new_list[i]
            new_list[i] = new_list[i + 1]
            new_list[i + 1] = aux_piece
    return new_list

def reordering_board_machine(list_to_reorder: DSList(N_BOARDS, Board),
                             swapping_decisions: DSList(N_BOARDS - 1, bool),
                             ) -> DSList(N_BOARDS, Board):
    aux_board : Board
    new_list : DSList(N_BOARDS, Board) = [
        {"length": 0, "bad_intervals": [{"start": 0, "end": 0}, {"start": 0, "end": 0}], "curved_intervals": [{"start": 0, "end": 0}, {"start": 0, "end": 0}]},
        {"length": 0, "bad_intervals": [{"start": 0, "end": 0}, {"start": 0, "end": 0}], "curved_intervals": [{"start": 0, "end": 0}, {"start": 0, "end": 0}]},
    ]
    for i in range(N_BOARDS):
        new_list[i] = list_to_reorder[i]
    for i in range(N_BOARDS - 1): # Number of swapping decisions
        if swapping_decisions[i]:
            aux_board = new_list[i]
            new_list[i] = new_list[i + 1]
            new_list[i + 1] = aux_board
    return new_list

def cutting_machine(board_list: DSList(N_BOARDS, Board),
                    cuts_list_list: DSList(N_BOARDS, CutList)):
    pieces: DSList(N_PIECES, Piece) = [
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
    ]
    quality : DSInt(0, 1) = 0
    for board_index, board in enumerate(board_list):
        cut_list : DSList(MAX_N_CUTS_PER_BOARD, DSInt(0, MAX_BOARD_LENGTH)) = cuts_list_list[board_index].position_list
        assert cut_list[0] == 0
        assert cut_list[MAX_N_CUTS_PER_BOARD - 1] == board.length
        curved_intervals_board : DSList(MAX_N_INTERVALS, Interval) = board.curved_intervals
        for interval in curved_intervals_board:
            assert any(interval.start <= cut_list[cut] and cut_list[cut] <= interval.end for cut in range(MAX_N_CUTS_PER_BOARD))
        for cut_index in range(1, MAX_N_CUTS_PER_BOARD):
            # Impose ordered cuts
            piece_length = cut_list[cut_index] - cut_list[cut_index - 1]
            assert piece_length >= 0
            if piece_length == 0:
                assert cut_list[cut_index] == board.length
                # No piece of length 0 unless there is no more length to cut
                # This reduces the spaces of solutions
            bad_intervals_board : DSList(MAX_N_INTERVALS, Interval) = board.bad_intervals
            if all(interval.start >= cut_list[cut_index] or cut_list[cut_index - 1] >= interval.end for interval in bad_intervals_board):
                # The piece does not overlap any bad interval
                quality = 1
            else:
                quality = 0
            pieces[board_index * (MAX_N_CUTS_PER_BOARD - 1) + (cut_index - 1)] = {"quality": quality, "length": piece_length}
    return pieces

def filtering_machine(list_to_filter: DSList(N_PIECES, Piece),
                      keep_decisions: DSList(N_PIECES, bool)):
    waste : int = 0
    # Initialize filtered list with empty pieces
    filtered_list : DSList(N_PIECES, Piece) = [
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
        {"quality": 1, "length": 0},
    ]
    for i in range(N_PIECES):
        if keep_decisions[i]:
            assert list_to_filter[i].quality == 1
            filtered_list[i] = list_to_filter[i]
        else:
            waste = waste + list_to_filter[i].length
            filtered_list[i] = {"quality": 1, "length": 0}
    return filtered_list, waste

def checking_machine(pieces: DSList(N_PIECES, Piece)):
    depth = 0
    length = 0
    n_length = 0
    n_prev_layer = 0
    new_beam = 1
    current_index = 0
    for piece in pieces:
        current_index = current_index + 1
        length = length + piece.length
        n_length = n_length + 1
        assert length <= BEAM_LENGTH
        if length == BEAM_LENGTH:
            depth = depth + 1
            n_prev_layer = n_length
            n_length = 0
            length = 0
            if depth == BEAM_DEPTH:
                new_beam = 1
                depth = 0
        else:
            new_beam = 0
            for i in range(1, MAX_PIECES_PER_BEAM):
                if i < n_prev_layer:
                    start = current_index - n_length - n_prev_layer + 1
                    end = start + i - 1
                    s = 0
                    for j in range(1, MAX_PIECES_PER_BEAM):
                        # the language can be made more elegant taking in for from i to j, and automatically translating into this if lower and upper bounds are known
                        if start <= j:
                            if j <= end:
                                s = s + pieces[j].length
                                assert abs(s - length) >= MIN_DIST_BETWEEN_PIECES
            # Check forbidden intervals
            for interval in FORBIDDEN_INTERVALS:
                assert not(interval[0] <= length and length <= interval[1])
