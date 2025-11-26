minicutter = """
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
    "quality": DSBool
})

CutList = DSRecord({
    "position_list": DSList(MAX_N_CUTS_PER_BOARD, DSInt(0, MAX_BOARD_LENGTH))
})

GIVEN_INITIAL_BOARDS = [
    Board(length=20,
          bad_intervals=[Interval(5,6), Interval(15,16)],
          curved_intervals=[Interval(10,12)]
    ),
    Board(length=15,
          bad_intervals=[Interval(3,4)],
          curved_intervals=[Interval(7,9)],
    ),
    Board(length=25,
          bad_intervals=[Interval(8,10), Interval(18,20)],
          curved_intervals=[Interval(5,7), Interval(12,14)]
    )
]

# The following can be deduced from GIVEN_INITIAL_BOARDS
N_BOARDS = 3
MAX_BOARD_LENGTH = 30
MAX_N_INTERVALS = 5
# Maximum number of bad (or curved) intervals per board
MAX_N_CUTS_PER_BOARD = 10
# Maximum number of cuts per board (including the two fixed cuts at the start and end of the board)


initial_boards: list[Board] = GIVEN_INITIAL_BOARDS
N_BOARDS = len(initial_boards)
N_PIECES = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1) # First and last cuts are fixed


cuts_list_list: DSList(N_BOARDS, CutList(MAX_N_CUTS_PER_BOARD))
pieces = cutting_machine(initial_boards, cuts_list_list)

def cutting_machine(board_list: DSList(N_BOARDS, Board),
                    cuts_list_list: DSList(N_BOARDS, CutList)):
    pieces: DSList(N_PIECES, Piece)
    for board_index, board in enumerate(board_list):
        cut_list = cuts_list_list[board_index]
        assert cut_list[0] == 0
        assert cut_list[MAX_N_CUTS_PER_BOARD] == board.length
        for interval in board.curved_intervals:
            assert any(interval.start <= cut and cut <= interval.end for cut in cut_list)
        for cut_index in range(len(cut_list)):
            # Impose ordered cuts
            if cut_index > 1:
                piece_length = cut_list[cut_index - 1] - cut_list[cut_index]
                assert piece_length >= 0
                if piece_length == 0:
                    assert cut_list[cut_index] == board.length
                    # No piece of length 0 unless it is the last piece
                    # This reduces the spaces of solutions
                    # But also removes valid solutions if there is more than one reordering machine (unless the filtering machine puts all the empty pieces at the end, instead of just replacing discarded pieces with empty pieces)
                quality = all(
                   interval.start <= cut_list[cut_index] and
                   cut_list[cut_index - 1] <= interval.end
                   for interval in board.bad_intervals
                   )
                pieces[(board_index - 1) * (MAX_N_CUTS_PER_BOARD - 1) + cut_index - 1] = Piece(piece_length, quality)
    return pieces
"""