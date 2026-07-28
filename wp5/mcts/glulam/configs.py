"""Example environment configurations (sets of constants) to try.

`FORBIDDEN_INTERVALS` keep a fixed absolute width per config (2 or 4 length units) and are
centered at 0.2, 0.5 and 0.8 of `LAYER_LEN`. The widths are deliberately *not* a percentage of
`LAYER_LEN`: layers are twice as long as they used to be, and the intervals were kept at their
old width, so they now cover about 5% of a layer each instead of 10%.

`BOARD_LEN_SPREAD` (a generation knob, not a spec constant) draws each board length from the top
of its feasible interval — a window of roughly 10% of `MAX_BOARD_LEN` — so boards come out within
90–100% of `MAX_BOARD_LEN` and the hidden stack reads as rows of similar width. It only bites if
every board can hold enough pieces to reach `MAX_BOARD_LEN`, hence the `INI_PIECES` values below.
"""

from mcts.glulam.env import EnvConfig

EXAMPLE_CONFIGS: dict[str, EnvConfig] = {
    "small": EnvConfig(
        LAYER_LEN=40,
        NUM_LAYERS=3,
        MIN_PIECE_LEN=3,
        MAX_PIECE_LEN=12,
        MIN_BOARD_LEN=15,
        MAX_BOARD_LEN=30,
        INI_BOARDS=6,
        INI_PIECES=18,  # 3 per board: fewer would keep boards short of MAX_BOARD_LEN (needs 30/12 -> 3)
        OBSERVABLE_BOARDS=2,
        # L=40: centers 8,20,32, width 2 → (7,9),(19,21),(31,33)
        FORBIDDEN_INTERVALS=((7, 9), (19, 21), (31, 33)),
        PREV_MEET_FORBIDDEN_HALF=1,
        BOARD_LEN_SPREAD=3,
        seed=0,
    ),
    "medium": EnvConfig(
        LAYER_LEN=80,
        NUM_LAYERS=4,
        MIN_PIECE_LEN=4,
        MAX_PIECE_LEN=20,
        MIN_BOARD_LEN=25,
        MAX_BOARD_LEN=50,
        INI_BOARDS=8,
        INI_PIECES=24,
        OBSERVABLE_BOARDS=3,
        # L=80: centers 16,40,64, width 4 → (14,18),(38,42),(62,66)
        FORBIDDEN_INTERVALS=((14, 18), (38, 42), (62, 66)),
        PREV_MEET_FORBIDDEN_HALF=2,
        BOARD_LEN_SPREAD=5,
        seed=7,
    ),
    "narrow_window": EnvConfig(
        LAYER_LEN=60,
        NUM_LAYERS=2,
        MIN_PIECE_LEN=5,
        MAX_PIECE_LEN=15,
        MIN_BOARD_LEN=20,
        MAX_BOARD_LEN=35,
        INI_BOARDS=5,
        INI_PIECES=15,  # 3 per board: fewer would keep boards short of MAX_BOARD_LEN (needs 35/15 -> 3)
        OBSERVABLE_BOARDS=1,
        # L=60: centers 12,30,48, width 2 → (11,13),(29,31),(47,49)
        FORBIDDEN_INTERVALS=((11, 13), (29, 31), (47, 49)),
        PREV_MEET_FORBIDDEN_HALF=1,
        BOARD_LEN_SPREAD=4,
        seed=42,
    ),
    # Larger instances with the `medium` constants (same piece/board bounds).
    "large_50": EnvConfig(
        LAYER_LEN=80,
        NUM_LAYERS=4,
        MIN_PIECE_LEN=4,
        MAX_PIECE_LEN=20,
        MIN_BOARD_LEN=25,
        MAX_BOARD_LEN=50,
        INI_BOARDS=50,
        INI_PIECES=150,
        OBSERVABLE_BOARDS=3,
        FORBIDDEN_INTERVALS=((14, 18), (38, 42), (62, 66)),
        PREV_MEET_FORBIDDEN_HALF=2,
        BOARD_LEN_SPREAD=5,
        seed=7,
    ),
    "xlarge_200": EnvConfig(
        LAYER_LEN=80,
        NUM_LAYERS=4,
        MIN_PIECE_LEN=4,
        MAX_PIECE_LEN=20,
        MIN_BOARD_LEN=25,
        MAX_BOARD_LEN=50,
        INI_BOARDS=200,
        INI_PIECES=600,
        OBSERVABLE_BOARDS=3,
        FORBIDDEN_INTERVALS=((14, 18), (38, 42), (62, 66)),
        PREV_MEET_FORBIDDEN_HALF=2,
        BOARD_LEN_SPREAD=5,
        seed=7,
    ),
}
