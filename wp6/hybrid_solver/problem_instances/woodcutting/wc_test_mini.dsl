# Ultra-minimal 0-based woodcutting pipeline model.
#
# The smallest instance that still exercises the real pipeline machines
# (reordering_board -> cutting -> filtering -> reordering_piece -> checking)
# and the real objective, but with the tiny sizes that keep the generated
# MiniZinc small enough to flatten without exhausting memory:
#   - N_BOARDS = 1                 (smallest possible; no board reorder needed)
#   - MAX_N_CUTS_PER_BOARD = 2     (first + last fixed -> N_PIECES = 1)
#   - MAX_N_INTERVALS = 1          (one bad + one curved interval slot)
#   - BEAM_LENGTH small so a single piece can complete a layer exactly
#   - BEAM_DEPTH = 1 (one layer per beam)
#   - MAX_PIECES_PER_BEAM = 1 (one piece per layer -> no nested gap checks)
#   - single forbidden interval
#
# This is intended as a smoke test: it generates a tiny MiniZinc model that
# parses and flattens quickly, useful for validating the toolchain end-to-end
# without running into the MiniZinc 2.10.1 flattener memory/segfault issue
# seen on larger instances.

N_BOARDS : int = 1
MAX_BOARD_LENGTH : int = 10
MAX_N_INTERVALS : int = 1
# Maximum number of bad (or curved) intervals per board
MAX_N_CUTS_PER_BOARD : int = 2
# Maximum number of cuts per board (first + last fixed)
N_PIECES : int = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1)
# Total number of pieces (one interior piece here)
BEAM_LENGTH : int = 6
# Length of the beams to be produced
BEAM_DEPTH : int = 1
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM : int = 1
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES : int = 1
FORBIDDEN_INTERVALS : DSList(1, DSList(2, int)) = [[1, 1]]

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
    Board(length=6,
        bad_intervals=[
            Interval(0, 0)
        ],
        curved_intervals=[
            Interval(0, 0)
        ]
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
        {"quality": 1, "length": 0}
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
        {"length": 0, "bad_intervals": [{"start": 0, "end": 0}], "curved_intervals": [{"start": 0, "end": 0}]}
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
        {"quality": 1, "length": 0}
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
        {"quality": 1, "length": 0}
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
                        if start <= j:
                            if j <= end:
                                s = s + pieces[j].length
                                assert abs(s - length) >= MIN_DIST_BETWEEN_PIECES
            # Check forbidden intervals
            for interval in FORBIDDEN_INTERVALS:
                assert not(interval[0] <= length and length <= interval[1])
