"""Convert woodcutting benchmark JSON instances into OptDSL files, WITHOUT the
board-reordering step.

This is a variant of ``convert_woodcutting_benchmarks.py`` that omits the
``reordering_board_machine`` (and its ``swapping_decisions_boards`` /
``swapped_boards`` variables).  The board-reordering machine is the construct
that makes MiniZinc 2.10.1 crash / hit a memory violation on the woodcutting
pipeline models (see repo notes), so cutting feeds directly on
``initial_boards``:

    initial_boards : DSList(N_BOARDS, Board) = GIVEN_INITIAL_BOARDS
    pieces = cutting_machine(initial_boards, cuts_list_list)

(Piece reordering is retained: it models the simulator's single-piece buffer
and is not the source of the MiniZinc crash.)

The emitted model is the **0-based** variant (matches ``run_minizinc.py``'s
default ``--dsl-index-base 0``) and, unlike the plain converter, it is written
to be **MiniZinc 2.10.1 compatible by construction**:

* ``MAX_N_INTERVALS`` is clamped to a minimum of 1.  Empty ``bad_intervals`` /
  ``curved_intervals`` (``array[1..0]``) become the MiniZinc empty-set
  ``array[{}]`` record fields, which 2.10.1 cannot type-check in
  record/predicate position ("not an array expression").  The clamp emits
  exactly one inert ``Interval(0, 0)`` sentinel instead (the curved-coverage
  assert guards ``start < end`` and the bad-interval check is trivially true
  for cuts > 0), matching the hand-written ``wc_test_mini.dsl``.
* ``FORBIDDEN_INTERVALS`` is clamped to a minimum of one entry.  An empty
  ``[[ ]]`` list would translate to ``array[1..0]``; a single inert ``[0, 0]``
  entry keeps the list non-empty and is never triggered (checked running
  lengths are > 0).

Mapping (JSON -> DSL)
---------------------
BeamConfiguration
    BeamLength                  -> BEAM_LENGTH
    NumberOfLayers              -> BEAM_DEPTH
    NumberOfBeams               -> N_BEAMS
    StaticForbiddenZones        -> FORBIDDEN_INTERVALS  (list of [Begin, End])
InputBoards
    len(InputBoards)            -> N_BOARDS
    max(RawBoard.Length)        -> MAX_BOARD_LENGTH
    RawBoard.Length             -> Board.length
    ScanBoardParts with
      Quality != 1              -> Board.bad_intervals (Interval(start, end))
      (all parts)               -> Board.curved_intervals

Documented assumptions (override with CLI flags if needed):
  * bad_intervals   = the defective scan parts (Quality != 1).
  * curved_intervals = empty by default (the JSON carries no explicit curved-cut
    segments distinct from the static forbidden zones); pass
    --curves-from-parts to fill them from every scan part instead.
  * Each board's interval lists are padded with degenerate Interval(0,0) entries
    to the fixed length MAX_N_INTERVALS (DSList(MAX_N_INTERVALS, Interval)).
  * MAX_N_CUTS_PER_BOARD and MAX_PIECES_PER_BEAM default to 4 and 2 (as in wc_1)
    but are configurable.
  * Values are emitted as-is; pass --scale to divide all lengths by a factor.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


# --------------------------------------------------------------------------
# Model template.  The data-dependent header + record definitions + boards are
# regenerated per instance; the machine bodies are shared verbatim.
# 0-based, objective variable minimised via minimize(objective).
# The board-reordering machine is OMITTED.
# --------------------------------------------------------------------------

MODEL_RECORDS = '''

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
'''

# NOTE: no swapping_decisions_boards / swapped_boards / reordering_board_machine
# unless reorder_boards=True.
def _model_body(reorder_pieces: bool, reorder_boards: bool = False) -> str:
    """Pipeline body of the generated DSL.

    ``reorder_pieces=False`` removes the piece-reordering machine entirely:
    ``checking_machine`` consumes ``filtered_pieces`` directly.  (The reorder
    machine is a no-op for identity ``swapping_decisions`` anyway, and dropping
    it shrinks the MiniZinc model and avoids the single-hold reorder SSA path.)
    """
    body = """
initial_boards: DSList(N_BOARDS, Board) = GIVEN_INITIAL_BOARDS
"""
    if reorder_boards:
        body += """
# Reordering boards (adjacent swaps, applied left to right)

swapping_decisions_boards: DSList(N_BOARDS - 1, bool)
swapped_boards: DSList(N_BOARDS, Board)
swapped_boards = reordering_board_machine(initial_boards, swapping_decisions_boards)

# Cutting boards

cuts_list_list: DSList(N_BOARDS, CutList)
pieces : DSList(N_PIECES, Piece)
pieces = cutting_machine(swapped_boards, cuts_list_list)
"""
    else:
        body += """
# Cutting boards (directly, no board reordering step)

cuts_list_list: DSList(N_BOARDS, CutList)
pieces : DSList(N_PIECES, Piece)
pieces = cutting_machine(initial_boards, cuts_list_list)
"""
    body += """
# Filtering pieces

# Objective: total length of GOOD (quality == 1) piece material that is
# discarded (filtered out) rather than kept.  Bad material can never be used,
# so its length is left out of the objective.
objective: DSInt(0, MAX_BOARD_LENGTH * N_BOARDS) = 0

keep_decisions: DSList(N_PIECES, bool)
filtered_pieces: DSList(N_PIECES, Piece)
filtered_pieces, objective = filtering_machine(pieces, keep_decisions, objective)
"""
    if reorder_pieces:
        body += """
# Reordering pieces (single-held-piece model of the simulator)

swapping_decisions: DSList(N_PIECES - 1, bool)
reordered_pieces: DSList(N_PIECES, Piece)
reordered_pieces = reordering_piece_machine(filtered_pieces, swapping_decisions)

# Checking pieces

checking_machine(reordered_pieces)

minimize(objective)
"""
    else:
        body += """
# Checking pieces (piece-reordering removed: checking reads filtered_pieces)

checking_machine(filtered_pieces)

minimize(objective)
"""
    body += _machine_defs(reorder_pieces, reorder_boards)
    return body


def _machine_defs(reorder_pieces: bool, reorder_boards: bool = False) -> str:
    """Shared machine definitions.  Includes reordering_piece_machine only when
    ``reorder_pieces`` is True and reordering_board_machine only when
    ``reorder_boards`` is True."""
    defs = ""
    if reorder_boards:
        defs += """
# Board reordering: swapping_decisions[i] swaps the boards at positions i and
# i + 1 of the current order (swaps are applied left to right).
def reordering_board_machine(list_to_reorder: DSList(N_BOARDS, Board),
                             swapping_decisions: DSList(N_BOARDS - 1, bool),
                             ) -> DSList(N_BOARDS, Board):
    aux_board : Board
    new_list : DSList(N_BOARDS, Board) = [0] * N_BOARDS
    for i in range(N_BOARDS):
        new_list[i] = list_to_reorder[i]
    for i in range(N_BOARDS - 1):
        if swapping_decisions[i]:
            aux_board = new_list[i]
            new_list[i] = new_list[i + 1]
            new_list[i + 1] = aux_board
    return new_list
"""
    if reorder_pieces:
        defs += """
# Piece reordering is restricted to the SINGLE-held-piece model of the target
# WoodCutter simulator (its piece buffer can hold at most one piece, accessed
# via the pgo/pout/pin vocabulary).  ``swapping_decisions`` is a bit vector over
# the stream: the FIRST ``1`` selects the single piece that is held back
# (simulator "pout"), all later pieces pass it in their original relative order
# (simulator "pgo"), and the held piece is released at the very end
# (simulator "pin").  Any later ``1`` is ignored (only one piece can be held).
#
# The first N_PIECES-1 pieces are processed in a loop that may consult
# swapping_decisions[i]; the last piece (index N_PIECES-1) is handled
# separately so swapping_decisions is NEVER indexed at N_PIECES (which would be
# an out-of-bounds access in the unrolled MiniZinc: swapping_decisions has only
# N_PIECES-1 elements, i.e. a 1..N_PIECES-1 index set).  This mirrors the
# single-held semantics exactly: the last piece is simply appended (after the
# held piece if one was held).
def reordering_piece_machine(list_to_reorder: DSList(N_PIECES, Piece),
                             swapping_decisions: DSList(N_PIECES - 1, bool),
                             ) -> DSList(N_PIECES, Piece):

    new_list : DSList(N_PIECES, Piece) = [0] * N_PIECES
    held : DSInt(0, 2) = 0
    held_piece : Piece = {"quality": 1, "length": 0}
    write_index : DSInt(0, N_PIECES) = 0
    for i in range(N_PIECES - 1):
        if held == 0 and swapping_decisions[i]:
            # First 1: hold this piece aside (simulator pout).
            held = 1
            held_piece = list_to_reorder[i]
        else:
            new_list[write_index] = list_to_reorder[i]
            write_index = write_index + 1
    # Last piece (i == N_PIECES - 1): never consults swapping_decisions.
    if held == 1:
        new_list[write_index] = list_to_reorder[N_PIECES - 1]
        write_index = write_index + 1
        new_list[write_index] = held_piece
        write_index = write_index + 1
    else:
        new_list[write_index] = list_to_reorder[N_PIECES - 1]
        write_index = write_index + 1
    return new_list
"""
    defs += """
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
"""
    defs += """
def checking_machine(pieces: DSList(N_PIECES, Piece)):
    depth = 0
    total_depth = 0
    length = 0
    n_length = 0
    n_prev_layer = 0
    new_beam = 1
    current_index = 0
    # End positions (within a layer, cumulative in the stream) of the pieces in
    # the most recently completed layer.  This lets checking_machine enforce the
    # simulator's "gap to board abut in consecutive layers": no seam of the
    # current layer may be closer than GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS
    # to a seam of the previous layer (within the same beam).  There is no abs()
    # in the subset of the language: the distance is expressed as a disjunction
    # of the two one-sided inequalities.
    prev_layer_lengths : DSList(N_PIECES, DSInt(0, BEAM_LENGTH)) = [0] * N_PIECES
    layer_lengths : DSList(N_PIECES, DSInt(0, BEAM_LENGTH)) = [0] * N_PIECES
    for piece in pieces:
        current_index = current_index + 1
        length = length + piece.length
        # Only kept pieces (length > 0) form a layer's seams; discarded slots
        # are zero-length placeholders in the uncompacted stream and must not
        # count toward n_length / layer_lengths.
        if piece.length > 0:
            layer_lengths[n_length] = length
            n_length = n_length + 1
        assert length <= BEAM_LENGTH
        if length == BEAM_LENGTH:
            depth = depth + 1
            total_depth = total_depth + 1
            # Record this layer's piece end positions for the next layer's gap check.
            for i in range(N_PIECES):
                if i < n_length:
                    prev_layer_lengths[i] = layer_lengths[i]
            n_prev_layer = n_length
            n_length = 0
            length = 0
            if depth == BEAM_DEPTH:
                new_beam = 1
                depth = 0
        else:
            new_beam = 0
            # Only a kept piece (length > 0) creates a seam; discards are
            # zero-length placeholders and are ignored.
            if piece.length > 0:
                # Gap check vs the previous layer's seams (only within the same
                # beam: the simulator's completedLayers reset when a beam
                # completes, and a new beam restarts from position 0).
                if depth >= 1:
                    for i in range(N_PIECES):
                        if i < n_prev_layer:
                            s = prev_layer_lengths[i]
                            assert s - length >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS or length - s >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS
                # Check forbidden intervals
                for interval in FORBIDDEN_INTERVALS:
                    assert not (interval[0] <= length and length <= interval[1])
                # Check beam skip zones: no seam may lie in the start/end margins.
                assert length > BEAM_SKIP_START
                assert length < BEAM_LENGTH - BEAM_SKIP_END
    # Every piece must be either used (contributes to a layer) or discarded
    # (zero length).  After the whole stream, no dangling partial layer may
    # remain (length == 0) and the exact number of layers/beams must be built.
    assert length == 0
    assert depth == 0
    assert total_depth == N_BEAMS * BEAM_DEPTH
"""
    return defs


def _scale(value, scale):
    if scale in (None, 1):
        return value
    return int(value) // scale


def _interval_list(pairs, max_intervals):
    """Build a fixed-length list of Interval(...) entries padded with (0,0).

    ``max_intervals`` is >= 1 (see generate_dsl), so an empty ``pairs`` list
    still emits a single inert ``Interval(0, 0)`` -> keeps MiniZinc's record
    field arrays non-empty.
    """
    entries = [f"            Interval({s}, {e})," for (s, e) in pairs[:max_intervals]]
    entries += ["            Interval(0, 0),"] * (max_intervals - len(entries))
    return entries


def build_boards_json(data, scale, max_intervals, curves_from_parts):
    boards = data.get("InputBoards", [])
    board_blocks = []
    for item in boards:
        board = item.get("RawBoard", {})
        length = _scale(board.get("Length", 0), scale)
        parts = board.get("ScanBoardParts", [])

        if curves_from_parts:
            curved_pairs = [
                (_scale(p["StartPosition"], scale), _scale(p["EndPosition"], scale))
                for p in parts
            ]
        else:
            curved_pairs = []

        bad_pairs = [
            (_scale(p["StartPosition"], scale), _scale(p["EndPosition"], scale))
            for p in parts
            if p.get("Quality", 1) != 1
        ]

        lines = [f"    Board(length={length},"]
        lines.append("          bad_intervals=[")
        lines.extend(_interval_list(bad_pairs, max_intervals))
        lines.append("          ],")
        lines.append("          curved_intervals=[")
        lines.extend(_interval_list(curved_pairs, max_intervals))
        lines.append("          ]")
        lines.append("    ),")
        board_blocks.append("\n".join(lines))

    return board_blocks


def generate_dsl(data, scale=None, max_cuts_per_board=4, max_pieces_per_beam=2,
                 min_dist_between_pieces=1, curves_from_parts=False,
                 min_intervals=1, reorder_pieces=True, reorder_boards=False) -> str:
    cfg = data.get("BeamConfiguration", {})
    boards = data.get("InputBoards", [])

    n_boards = len(boards)
    beam_count = cfg.get("NumberOfBeams", n_boards)
    board_lengths = [b.get("RawBoard", {}).get("Length", 0) for b in boards]
    max_board_length = _scale(max(board_lengths, default=0), scale)
    layer_length = _scale(cfg.get("BeamLength", 0), scale)
    beam_depth = cfg.get("NumberOfLayers", 0)
    beam_skip_start = cfg.get("BeamSkipStart", 0)
    beam_skip_end = cfg.get("BeamSkipEnd", 0)
    min_length_of_board_in_layer = cfg.get("MinLengthOfBoardInLayer", 0)
    gap_to_board_abut = cfg.get("GapToBoardAbutInConsecutiveLayers", min_dist_between_pieces)
    max_shift_curved_cut = cfg.get("MaxShiftCurvedCut", 0)
    forbidden = cfg.get("StaticForbiddenZones", [])
    forbidden_pairs = [
        (_scale(z.get("Begin", 0), scale), _scale(z.get("End", 0), scale))
        for z in forbidden
    ]
    # MiniZinc compatibility: never emit an empty FORBIDDEN_INTERVALS list.
    if not forbidden_pairs:
        forbidden_pairs = [(0, 0)]

    # Maximum number of bad/curved intervals across all boards (bounded below
    # by min_intervals which defaults to 1 so the record field is never empty).
    if curves_from_parts:
        part_counts = [len(b.get("RawBoard", {}).get("ScanBoardParts", [])) for b in boards]
    else:
        part_counts = [
            sum(1 for p in b.get("RawBoard", {}).get("ScanBoardParts", [])
                if p.get("Quality", 1) != 1)
            for b in boards
        ]
    max_intervals = max([min_intervals] + part_counts) if part_counts else min_intervals
    max_intervals = max(max_intervals, 1)

    forbidden_literal = "[" + ", ".join(f"[{s}, {e}]" for (s, e) in forbidden_pairs) + "]"

    board_blocks = build_boards_json(data, scale, max_intervals, curves_from_parts)

    header = f"""# Auto-converted from: {data.get('_source_file', '<json>')}
# Header is generated from the beam/board data; the model body is shared.
# 0-based indexing variant (matches run_minizinc.py --dsl-index-base 0).
# {'WITH board-reordering machine.' if reorder_boards else 'NO board-reordering machine.'}

# The following can be deduced from GIVEN_INITIAL_BOARDS
N_BOARDS : int = {n_boards}
N_BEAMS : int = {beam_count}
# Number of beams to produce (may differ from N_BOARDS: more raw boards than beams)
MAX_BOARD_LENGTH : int = {max_board_length}
MAX_N_INTERVALS : int = {max_intervals}
# Maximum number of bad (or curved) intervals per board (>= 1: empty interval
# lists would translate to MiniZinc's empty-set array[{{}}] and break 2.10.1;
# entries are (0,0)-padded to this length and the (0,0)s are inert)
MAX_N_CUTS_PER_BOARD : int = {max_cuts_per_board}
# Maximum number of cuts per board (including the two fixed cuts at the start and end of the board)

N_PIECES : int = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1)
# Total number of pieces to be obtained from all boards
BEAM_LENGTH : int = {layer_length}
# Length of the beams to be produced
BEAM_DEPTH : int = {beam_depth}
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM : int = {max_pieces_per_beam}
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES : int = {min_dist_between_pieces}
BEAM_SKIP_START : int = {beam_skip_start}
# Unusable margin at the start of each beam (no seam may lie here)
BEAM_SKIP_END : int = {beam_skip_end}
# Unusable margin at the end of each beam (no seam may lie here)
MIN_LENGTH_OF_BOARD_IN_LAYER : int = {min_length_of_board_in_layer}
# Minimum length of a board piece used in a layer
GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS : int = {gap_to_board_abut}
# Minimum distance between seams in consecutive layers
MAX_SHIFT_CURVED_CUT : int = {max_shift_curved_cut}
# Safety margin around curved cuts where a cut may shift
FORBIDDEN_INTERVALS : DSList({max(len(forbidden_pairs), 1)}, DSList(2, int)) = {forbidden_literal}
"""

    # Record definitions must precede GIVEN_INITIAL_BOARDS (which references
    # Board / Interval), so they are emitted between the header and the boards.
    boards_block = f"""
GIVEN_INITIAL_BOARDS : DSList(N_BOARDS, Board) = [
{chr(10).join(board_blocks)}
]
"""

    return header + MODEL_RECORDS + boards_block + _model_body(reorder_pieces, reorder_boards)


def convert_file(json_path: Path, out_dir: Path, **kwargs) -> Path:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data.setdefault("_source_file", json_path.name)
    dsl_text = generate_dsl(data, **kwargs)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (json_path.stem + ".dsl")
    out_path.write_text(dsl_text, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="JSON benchmark file(s) or a directory to glob *.json")
    parser.add_argument("-o", "--outdir", default="problem_instances/woodcutting/benchmarks/generated_noreorder",
                        help="Directory to write the generated .dsl files")
    parser.add_argument("--scale", type=int, default=None,
                        help="Divide all lengths by this factor (e.g. 10) to shrink values")
    parser.add_argument("--max-cuts-per-board", type=int, default=4)
    parser.add_argument("--max-pieces-per-beam", type=int, default=2)
    parser.add_argument("--min-dist-between-pieces", type=int, default=1)
    parser.add_argument("--min-intervals", type=int, default=1,
                        help="Lower bound on the fixed interval-list length (MAX_N_INTERVALS); "
                             "clamped to >= 1 for MiniZinc compatibility")
    parser.add_argument("--curves-from-parts", action="store_true",
                        help="Treat every scan part as a curved interval; otherwise curved_intervals is empty")
    parser.add_argument("--no-piece-reorder", action="store_true",
                        help="Omit the piece-reordering machine entirely (checking_machine reads "
                             "filtered_pieces directly).  Removes swapping_decisions/reordered_pieces "
                             "and shrinks the MiniZinc model.")
    parser.add_argument("--reorder-boards", action="store_true",
                        help="Insert the board-reordering machine (swapping_decisions_boards) "
                             "between initial_boards and cutting.")
    args = parser.parse_args()

    json_files: list[Path] = []
    for path in args.inputs:
        p = Path(path)
        if p.is_dir():
            json_files.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            json_files.append(p)

    out_dir = Path(args.outdir)
    kwargs = dict(
        scale=args.scale,
        max_cuts_per_board=args.max_cuts_per_board,
        max_pieces_per_beam=args.max_pieces_per_beam,
        min_dist_between_pieces=args.min_dist_between_pieces,
        min_intervals=args.min_intervals,
        curves_from_parts=args.curves_from_parts,
        reorder_pieces=not args.no_piece_reorder,
        reorder_boards=args.reorder_boards,
    )

    for jf in json_files:
        out = convert_file(jf, out_dir, **kwargs)
        print(f"{jf.name} -> {out}")


if __name__ == "__main__":
    main()
