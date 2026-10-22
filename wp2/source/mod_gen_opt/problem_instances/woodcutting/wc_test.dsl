N_BOARDS : int = 2
MAX_BOARD_LENGTH : int = 30
MAX_N_INTERVALS : int = 2
# Maximum number of bad (or curved) intervals per board
MAX_N_CUTS_PER_BOARD : int = 4
# Maximum number of cuts per board ( including the two fixed cuts at
the start and end of the board)
N_PIECES : int = N_BOARDS * ( MAX_N_CUTS_PER_BOARD - 1)
# Total number of pieces to be obtained from all boards
BEAM_LENGTH : int = 10
# Length of the beams to be produced
BEAM_DEPTH : int = 5
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM : int = 2
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES : int = 1
FORBIDDEN_INTERVALS : DSList (2, DSList (2, int)) = [[3 ,4] , [7 ,8]]

initial_boards : DSList(N_BOARDS , Board) = GIVEN_INITIAL_BOARDS
# Swapping boards
swapping_decisions_boards : DSList( N_BOARDS - 1, bool)
swapped_boards : DSList(N_BOARDS , Board)
swapped_boards = reordering_board_machine ( initial_boards, swapping_decisions_boards )
# Cutting boards
cuts_list_list : DSList(N_BOARDS, CutList)
pieces : DSList(N_PIECES, Piece)
pieces = cutting_machine(swapped_boards, cuts_list_list )
# Filtering pieces
keep_decisions: DSList(N_PIECES, bool)
filtered_pieces: DSList(N_PIECES, Piece)
waste: int
filtered_pieces, waste = filtering_machine(pieces, keep_decisions)

# Reordering pieces
swapping_decisions: DSList(N_PIECES - 1, bool)
reordered_pieces: DSList(N_PIECES, Piece)
reordered_pieces = reordering_piece_machine(filtered_pieces, swapping_decisions)

# Checking pieces
pieces : DSList(N_PIECES , Piece) = GIVEN_PIECES
checking_machine(reordered_pieces)
minimize (waste)

Interval = DSRecord ({
    "start": DSInt (0, MAX_BOARD_LENGTH),
    "end": DSInt (0, MAX_BOARD_LENGTH)
})

Board = DSRecord ({
    "length": DSInt (0, MAX_BOARD_LENGTH ),
    "bad_intervals": DSList( MAX_N_INTERVALS , Interval ),
    "curved_intervals": DSList( MAX_N_INTERVALS , Interval )
})

Piece = DSRecord ({
    "length": DSInt (0, MAX_BOARD_LENGTH ),
    "quality": DSInt (0, 1)
})

CutList = DSRecord ({
    "position_list": DSList( MAX_N_CUTS_PER_BOARD , DSInt (0, MAX_BOARD_LENGTH ))
})

GIVEN_INITIAL_BOARDS : DSList(N_BOARDS , Board) = [
    Board(length =20,
        bad_intervals =[
            Interval (5 ,6) ,
            Interval (15 ,16)
        ],
        curved_intervals =[
            Interval (10 ,12) ,
            Interval (18 ,20)
        ]
    ),
    Board(length =25,
        bad_intervals =[
            Interval (10 ,14) ,
            Interval (18 ,20)
        ],
        curved_intervals =[
            Interval (7 ,9) ,
            Interval (18 ,20)
        ],
    )
]

GIVEN_PIECES : DSList(N_PIECES, Piece) = [
    Piece(length =5, quality =1),
    Piece(length =10, quality =1),
]

def reordering_piece_machine( list_to_reorder: DSList(N_PIECES, Piece), swapping_decisions: DSList(N_PIECES - 1, bool),) -> DSList(N_PIECES, Piece):
    aux_piece : Piece
    new_list : DSList(N_PIECES , Piece) = list_to_reorder
    for i in range( N_PIECES - 1): # Number of swapping decisions
        if swapping_decisions [i]:
            aux_piece = new_list [i]
            new_list [i] = new_list [i + 1]
            new_list [i + 1] = aux_piece
    return new_list

def reordering_board_machine ( list_to_reorder : DSList(N_BOARDS , Board), swapping_decisions : DSList( N_BOARDS - 1,bool),) -> DSList(N_BOARDS , Board):
    aux_board : Board
    new_list : DSList(N_BOARDS , Board) = list_to_reorder
    for i in range( N_BOARDS - 1): # Number of swapping decisions
        if swapping_decisions [i]:
            aux_board = new_list [i]
            new_list [i] = new_list [i + 1]
            new_list [i + 1] = aux_board
    return new_list

def cutting_machine ( board_list: DSList(N_BOARDS , Board), cuts_list_list: DSList(N_BOARDS , CutList )):
    pieces: DSList(N_PIECES , Piece)
    quality : DSBool ()
    for board_index, board in enumerate(board_list):
        cut_list : DSList(MAX_N_CUTS_PER_BOARD, DSInt (0, MAX_BOARD_LENGTH)) = cuts_list_list[board_index].position_list
        assert cut_list [1] == 0
        assert cut_list [ MAX_N_CUTS_PER_BOARD ] == board.length
        curved_intervals_board: DSList(MAX_N_INTERVALS, Interval ) = board.curved_intervals
        for interval in curved_intervals_board:
            assert any(interval.start <= cut_list [cut] and cut_list [cut] <= interval.end for cut in range (1, MAX_N_CUTS_PER_BOARD + 1))
        for cut_index in range (2, MAX_N_CUTS_PER_BOARD + 1):
            # Impose ordered cuts
            piece_length = cut_list [ cut_index ]- cut_list [cut_index -1]
            assert piece_length >= 0
            if piece_length == 0:
                assert cut_list[cut_index ] == board.length
                # No piece of length 0 unless there is no more length to cut
                # This reduces the spaces of solutions
                # But also removes valid solutions if there is more than one reordering machine (unless the filtering machine puts all the empty pieces at the end, instead of just replacing discarded pieces with empty pieces)
            bad_intervals_board: DSList(MAX_N_INTERVALS, Interval ) = board.bad_intervals
            if all(interval.start >= cut_list[cut_index] or cut_list[cut_index - 1] >= interval.end for interval in bad_intervals_board):
                # The piece does not overlap any bad interval
                quality = 1
            else:
                quality = 0
            pieces[(board_index - 1) * (MAX_N_CUTS_PER_BOARD - 1) + (cut_index - 1)] = {" quality ": quality , "length": piece_length }
    return pieces


def filtering_machine ( list_to_filter : DSList(N_PIECES , Piece), keep_decisions : DSList(N_PIECES , bool),):
    waste: int = 0
    # Initialize filtered list with empty pieces
    filtered_list: DSList(N_PIECES, Piece)
    for i in range( N_PIECES ):
        if keep_decisions [i]:
            assert list_to_filter [i]. quality == 1
            filtered_list [i] = list_to_filter [i]
        else:
            waste = waste + list_to_filter [i]. length
            filtered_list [i] = {" quality ": 1, "length": 0}
    return filtered_list, waste

def checking_machine (pieces: DSList(N_PIECES, elem_type = Piece)):
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
        if length == BEAM_LENGTH :
            depth = depth + 1
            n_prev_layer = n_length
            n_length = 0
            length = 0
            if depth == BEAM_DEPTH:
                new_beam = 1
                depth = 0
        else:
            new_beam = 0
            for i in range (1, MAX_PIECES_PER_BEAM ):
                if i < n_prev_layer :
                    start = current_index - n_length - n_prev_layer + 1
                    end = start + i - 1
                    s = 0
                    for j in range (1, MAX_PIECES_PER_BEAM ):
                        # the language can be made more elegant taking in for from i to j, and automatically translating into this if lower and upper bounds are known
                        if start <= j:
                            if j <= end:
                                s = s + pieces[j].length
                                assert abs(s - length) >= MIN_DIST_BETWEEN_PIECES
            # Check forbidden intervals
            for interval in FORBIDDEN_INTERVALS:
                assert not(interval [1] <= length and length <= interval[2])