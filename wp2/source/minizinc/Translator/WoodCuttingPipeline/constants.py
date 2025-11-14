code_constants = f"""

# The following can be deduced from GIVEN_INITIAL_BOARDS
N_BOARDS : int = 2
MAX_BOARD_LENGTH : int = 30
MAX_N_INTERVALS : int = 2
# Maximum number of bad (or curved) intervals per board
MAX_N_CUTS_PER_BOARD : int = 2
# Maximum number of cuts per board (including the two fixed cuts at the start and end of the board)

N_PIECES : int = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1)
# Total number of pieces to be obtained from all boards
BEAM_LENGTH : int = 10
# Length of the beams to be produced
BEAM_DEPTH : int = 5
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM : int = 2
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES : int = 1
FORBIDDEN_INTERVALS : DSList(2, DSList(2, int)) = [[3,4], [7,8]]

BEAM_LENGTH : int = 10
BEAM_DEPTH : int = 3
"""