code_constants = f"""
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


BEAM_LENGTH = 10
# Length of the beams to be produced
BEAM_DEPTH = 5
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM = 5
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES = 1
FORBIDDEN_INTERVALS = [[3,4], [7,8]]
"""