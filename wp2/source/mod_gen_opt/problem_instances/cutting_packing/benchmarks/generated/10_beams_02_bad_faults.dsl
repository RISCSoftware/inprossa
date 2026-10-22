# Auto-converted from: 10_beams_02_bad_faults.json
# Header is generated from the beam/board data; the model body is shared.
# 0-based indexing variant (matches run_minizinc.py --dsl-index-base 0).

# The following can be deduced from GIVEN_INITIAL_BOARDS
N_BOARDS : int = 100
N_BEAMS : int = 10
# Number of beams to produce (may differ from N_BOARDS: more raw boards than beams)
MAX_BOARD_LENGTH : int = 650
MAX_N_INTERVALS : int = 5
# Maximum number of bad (or curved) intervals per board
MAX_N_CUTS_PER_BOARD : int = 4
# Maximum number of cuts per board (including the two fixed cuts at the start and end of the board)

N_PIECES : int = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1)
# Total number of pieces to be obtained from all boards
BEAM_LENGTH : int = 500
# Length of the beams to be produced
BEAM_DEPTH : int = 5
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM : int = 2
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES : int = 1
BEAM_SKIP_START : int = 10
# Unusable margin at the start of each beam (no seam may lie here)
BEAM_SKIP_END : int = 10
# Unusable margin at the end of each beam (no seam may lie here)
MIN_LENGTH_OF_BOARD_IN_LAYER : int = 10
# Minimum length of a board piece used in a layer
GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS : int = 10
# Minimum distance between seams in consecutive layers
MAX_SHIFT_CURVED_CUT : int = 50
# Safety margin around curved cuts where a cut may shift
FORBIDDEN_INTERVALS : DSList(4, DSList(2, int)) = [[90, 110], [190, 210], [290, 310], [390, 410]]


Interval = DSRecord({
    "start": DSInt(0, MAX_BOARD_LENGTH),
    "end": DSInt(0, MAX_BOARD_LENGTH)
})

Board = DSRecord({
    "length": DSInt(0, MAX_BOARD_LENGTH),
    "bad_intervals": DSList(MAX_N_INTERVALS, Interval),
    "curved_intervals": DSList(MAX_N_INTERVALS, Interval)
})

# "quality" is a 0/1 flag (1 = good piece). DSInt(0, 1) instead of DSBool()
# so the 0/1 literals used below stay type-correct in MiniZinc.
Piece = DSRecord({
    "length": DSInt(0, MAX_BOARD_LENGTH),
    "quality": DSInt(0, 1)
})

CutList = DSRecord({
    "position_list": DSList(MAX_N_CUTS_PER_BOARD, DSInt(0, MAX_BOARD_LENGTH))
})

GIVEN_INITIAL_BOARDS : DSList(N_BOARDS, Board) = [
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(156, 176),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(204, 224),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(113, 126),
            Interval(149, 160),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(276, 289),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(266, 283),
            Interval(299, 311),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(249, 268),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(43, 58),
            Interval(236, 249),
            Interval(317, 336),
            Interval(491, 510),
            Interval(616, 627),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(23, 34),
            Interval(312, 328),
            Interval(482, 497),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(76, 87),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(67, 81),
            Interval(166, 178),
            Interval(250, 268),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(117, 128),
            Interval(189, 206),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(42, 54),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(265, 277),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(83, 97),
            Interval(304, 320),
            Interval(401, 412),
            Interval(585, 601),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(270, 289),
            Interval(372, 385),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(101, 121),
            Interval(178, 189),
            Interval(355, 375),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(174, 188),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(89, 108),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(170, 185),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(74, 88),
            Interval(210, 220),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(246, 263),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(63, 79),
            Interval(166, 178),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(191, 204),
            Interval(254, 272),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(359, 369),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(53, 73),
            Interval(100, 119),
            Interval(167, 182),
            Interval(306, 318),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(382, 397),
            Interval(462, 481),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(444, 454),
            Interval(492, 502),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(265, 284),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(519, 538),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(38, 54),
            Interval(176, 190),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(77, 88),
            Interval(193, 203),
            Interval(280, 290),
            Interval(370, 385),
            Interval(429, 442),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(159, 173),
            Interval(377, 391),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(227, 242),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(5, 22),
            Interval(167, 186),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(432, 443),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(187, 197),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(176, 191),
            Interval(220, 235),
            Interval(261, 271),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(47, 57),
            Interval(301, 316),
            Interval(487, 504),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(315, 327),
            Interval(384, 399),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(84, 94),
            Interval(307, 319),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(328, 345),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(44, 61),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(77, 95),
            Interval(213, 231),
            Interval(251, 261),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(72, 92),
            Interval(248, 266),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(74, 88),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(97, 113),
            Interval(203, 223),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(253, 263),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(404, 414),
            Interval(483, 503),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(169, 185),
            Interval(272, 288),
            Interval(306, 324),
            Interval(523, 539),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(300, 310),
            Interval(357, 372),
            Interval(394, 407),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(3, 17),
            Interval(191, 204),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(81, 96),
            Interval(541, 559),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(56, 66),
            Interval(489, 501),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(201, 211),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(312, 330),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(364, 375),
            Interval(402, 416),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(54, 64),
            Interval(79, 98),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(141, 159),
            Interval(361, 373),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(100, 117),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(539, 558),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(83, 103),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(51, 64),
            Interval(435, 448),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(321, 331),
            Interval(359, 379),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(229, 245),
            Interval(328, 343),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(136, 154),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(43, 53),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(22, 35),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(363, 375),
            Interval(563, 579),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(4, 21),
            Interval(40, 57),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(17, 31),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(578, 590),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(11, 28),
            Interval(120, 137),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
    Board(length=650,
          bad_intervals=[
            Interval(35, 47),
            Interval(195, 206),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ],
          curved_intervals=[
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
            Interval(0, 0),
          ]
    ),
]


initial_boards: DSList(N_BOARDS, Board) = GIVEN_INITIAL_BOARDS


# Swapping boards

swapping_decisions_boards: DSList(N_BOARDS - 1, bool)
swapped_boards: DSList(N_BOARDS, Board)
swapped_boards = reordering_board_machine(initial_boards, swapping_decisions_boards)


# Cutting boards

cuts_list_list: DSList(N_BOARDS, CutList)
pieces : DSList(N_PIECES, Piece)
pieces = cutting_machine(swapped_boards, cuts_list_list)


# Filtering pieces

# Objective: total length of GOOD (quality == 1) piece material that is
# discarded (filtered out) rather than kept.  Bad material can never be used,
# so its length is left out of the objective.
objective: DSInt(0, MAX_BOARD_LENGTH * N_BOARDS) = 0

keep_decisions: DSList(N_PIECES, bool)
filtered_pieces: DSList(N_PIECES, Piece)
filtered_pieces, objective = filtering_machine(pieces, keep_decisions, objective)

# Reordering pieces

swapping_decisions: DSList(N_PIECES - 1, bool)
reordered_pieces: DSList(N_PIECES, Piece)
reordered_pieces = reordering_piece_machine(filtered_pieces, swapping_decisions)


# Checking pieces

checking_machine(reordered_pieces)

minimize(objective)

def reordering_piece_machine(list_to_reorder: DSList(N_PIECES, Piece),
                             swapping_decisions: DSList(N_PIECES - 1, bool),
                             ) -> DSList(N_PIECES, Piece):

    new_list : DSList(N_PIECES, Piece) = list_to_reorder
    for i in range(N_PIECES - 1): # Number of swapping decisions
        if swapping_decisions[i]:
            aux_piece : Piece = new_list[i]
            new_list[i] = new_list[i + 1]
            new_list[i + 1] = aux_piece
    return new_list




def reordering_board_machine(list_to_reorder: DSList(N_BOARDS, Board),
                             swapping_decisions: DSList(N_BOARDS - 1, bool),
                             ) -> DSList(N_BOARDS, Board):
    new_list : DSList(N_BOARDS, Board) = list_to_reorder
    for i in range(N_BOARDS - 1): # Number of swapping decisions
        if swapping_decisions[i]:
            aux_board : Board = new_list[i]
            new_list[i] = new_list[i + 1]
            new_list[i + 1] = aux_board
    return new_list

def cutting_machine(board_list: DSList(N_BOARDS, Board),
                    cuts_list_list: DSList(N_BOARDS, CutList)):
    pieces: DSList(N_PIECES, Piece) = [0] * N_PIECES
    quality: DSInt(0, 1) = 0
    for board_index, board in enumerate(board_list):
        cut_list : DSList(MAX_N_CUTS_PER_BOARD, DSInt(0, MAX_BOARD_LENGTH)) = cuts_list_list[board_index].position_list
        assert cut_list[0] == BEAM_SKIP_START
        assert cut_list[MAX_N_CUTS_PER_BOARD - 1] == board.length - BEAM_SKIP_END
        curved_intervals_board : DSList(MAX_N_INTERVALS, Interval) = board.curved_intervals
        for interval in curved_intervals_board:
            if interval.start < interval.end:
                assert any(interval.start <= cut_list[cut] and cut_list[cut] <= interval.end for cut in range(MAX_N_CUTS_PER_BOARD))
        for cut_index in range(1, MAX_N_CUTS_PER_BOARD):
            # Impose ordered cuts
            piece_length = cut_list[cut_index] - cut_list[cut_index - 1]
            assert piece_length >= 0
            if piece_length == 0:
                assert cut_list[cut_index] == board.length - BEAM_SKIP_END
                # No piece of length 0 unless there is no more length to cut
                # This reduces the spaces of solutions
                # But also removes valid solutions if there is more than one reordering machine (unless the filtering machine puts all the empty pieces at the end, instead of just replacing discarded pieces with empty pieces)
            bad_intervals_board : DSList(MAX_N_INTERVALS, Interval) = board.bad_intervals
            if all(
                interval.start >= cut_list[cut_index] or
                cut_list[cut_index - 1] >= interval.end
                for interval in bad_intervals_board
                ):
                # The piece does not overlap any bad interval
                quality = 1
            else:
                quality = 0
            pieces[board_index * (MAX_N_CUTS_PER_BOARD - 1) + (cut_index - 1)] = {"quality": quality, "length": piece_length}
    return pieces

def filtering_machine(list_to_filter: DSList(N_PIECES, Piece),
                      keep_decisions: DSList(N_PIECES, bool),
                      objective: DSInt(0, MAX_BOARD_LENGTH * N_BOARDS),
                      ):
    # Initialize filtered list with empty pieces
    filtered_list : DSList(N_PIECES, Piece) = [0] * N_PIECES
    for i in range(N_PIECES):
        if keep_decisions[i]:
            assert list_to_filter[i].quality == 1
            filtered_list[i] = list_to_filter[i]
        else:
            if list_to_filter[i].quality == 1:
                # Only good material that we choose to discard counts as waste
                # (bad material cannot be used at all, so its length is not
                # part of the objective).
                objective = objective + list_to_filter[i].length
            filtered_list[i] = {"quality": 1, "length": 0}

    return filtered_list, objective

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
                assert not (interval[0] <= length and length <= interval[1])
            # Check beam skip zones: no seam may lie in the start/end margins.
            if length > 0:
                assert length > BEAM_SKIP_START
                assert length < BEAM_LENGTH - BEAM_SKIP_END
