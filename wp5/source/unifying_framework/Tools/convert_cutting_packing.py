"""Convert cutting/packing benchmark JSON instances into unified OptDSL models.

Reads the raw benchmark format (BeamConfiguration + InputBoards, see
``problem_instances/cutting_packing/benchmarks/*.json``) and emits a
simplified length-based cutting & packing model in the unified ``wc_2.dsl``
style that runs under BOTH backends:

  * ``python run_lns.py <out.dsl>``
  * ``python run_minizinc.py <out.dsl>``

Model semantics
---------------
* Boards are preprocessed like the reference simulator
  (``benchmarks/process_instance.py``): Quality-1 scan parts are usable,
  Quality-2 parts are discarded, Quality-3 (curved) parts are removed together
  with a MaxShiftCurvedCut safety margin on both sides, the board edges
  BeamSkipStart/End are skipped, and remaining segments shorter than
  MinLengthOfBoardInLayer are dropped. Each surviving usable segment becomes
  one cutting subject (SEGMENT_LENGTHS).
* Decisions:
  - ``cut_positions``: up to N_CUTS_PER_SEGMENT ascending cut positions per
    segment (0 = no cut). The cuts partition each segment into
    N_CUTS_PER_SEGMENT + 1 pieces whose lengths sum to the segment length.
  - ``piece_assignments``: piece -> layer 0..N_LAYERS-1, or N_LAYERS = waste
    bucket (leftover good material).
* Layers: N_LAYERS = NumberOfBeams * NumberOfLayers layers of capacity
  BeamLength. Every layer must be filled EXACTLY or left completely empty
  (a partially filled layer is invalid).
* Objective: WASTE_WEIGHT * wasted good length + CUT_WEIGHT * number of cuts.

Not modeled (length-only abstraction): seam positions, static forbidden
zones, staggered joints between layers, board width/height.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for begin, end in sorted(intervals):
        if begin >= end:
            continue
        if not merged or begin > merged[-1][1]:
            merged.append([begin, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(a, b) for a, b in merged]


def _subtract_intervals(
    source: list[tuple[int, int]], forbidden: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    if not source:
        return []
    if not forbidden:
        return source

    result: list[tuple[int, int]] = []
    merged_forbidden = _merge_intervals(forbidden)
    for s_begin, s_end in source:
        cur = s_begin
        for f_begin, f_end in merged_forbidden:
            if f_end <= cur:
                continue
            if f_begin >= s_end:
                break
            if cur < f_begin:
                result.append((cur, min(f_begin, s_end)))
            cur = max(cur, f_end)
            if cur >= s_end:
                break
        if cur < s_end:
            result.append((cur, s_end))
    return [(a, b) for a, b in result if b > a]


def _usable_segment_lengths(
    board: dict,
    skip_start: int,
    skip_end: int,
    max_shift_curved: int,
    min_len: int,
) -> list[int]:
    raw = board["RawBoard"]
    board_length = int(raw["Length"])

    good_intervals: list[tuple[int, int]] = []
    curved_forbidden: list[tuple[int, int]] = []
    for part in raw.get("ScanBoardParts", []):
        quality = int(part.get("Quality", 1))
        start = int(part["StartPosition"])
        end = int(part["EndPosition"])
        if quality == 1:
            good_intervals.append((start, end))
        elif quality == 3:
            left = max(0, start - max_shift_curved)
            right = min(board_length, end + max_shift_curved)
            curved_forbidden.append((left, right))
        # quality 2 (bad) and unknown qualities are unusable material.

    usable = _subtract_intervals(good_intervals, curved_forbidden)

    interior_start = max(0, skip_start)
    interior_end = min(board_length, board_length - max(0, skip_end))

    segments: list[int] = []
    for begin, end in usable:
        clipped_begin = max(begin, interior_start)
        clipped_end = min(end, interior_end)
        if clipped_end - clipped_begin >= min_len:
            segments.append(clipped_end - clipped_begin)
    return segments


MODEL_TEMPLATE = '''# Auto-generated from {source_name} by Tools/convert_cutting_packing.py
# Unified cutting & packing model: runs under run_lns.py AND run_minizinc.py.
# Preprocessing: {n_boards} input board(s) -> {n_segments} usable segment(s)
#   (Quality-1 parts kept; Quality-2 discarded; Quality-3 removed with +-{max_shift} margin;
#    board edges [{skip_start}, {skip_end}] skipped; segments < {min_seg_len} dropped).
# Demand: {n_beams} beam(s) x {n_layers_per_beam} layer(s) of length {layer_length}.
# Volume lower bound on waste: {min_waste} (usable {total_usable} vs demand {demand}).
# Not modeled: seam positions, static forbidden zones, staggered joints, width/height.

LAYER_LENGTH : DSInt() = {layer_length}
N_LAYERS : int = {n_layers}
MIN_PIECE_LENGTH : int = {min_piece_length}
N_SEGMENTS : int = {n_segments}
MAX_SEGMENT_LENGTH : int = {max_segment_length}
N_CUTS_PER_SEGMENT : int = {n_cuts_per_segment}
N_PIECES_PER_SEGMENT : int = {n_pieces_per_segment}
N_CUTS : int = {n_cuts}
N_PIECES : int = {n_pieces}
TOTAL_USABLE : int = {total_usable}
WASTE_WEIGHT : int = {waste_weight}
CUT_WEIGHT : int = {cut_weight}
MAX_COST : int = {max_cost}
SEGMENT_LENGTHS : DSList(N_SEGMENTS, DSInt()) = {segment_lengths}


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
'''


def _format_int_list(values: list[int], per_line: int = 10) -> str:
    lines: list[str] = []
    for i in range(0, len(values), per_line):
        chunk = values[i : i + per_line]
        lines.append(", ".join(str(v) for v in chunk))
    return "[\n    " + ",\n    ".join(lines) + "\n]"


def build_model(
    data: dict,
    source_name: str,
    cuts_per_segment: int,
    waste_weight: int,
    cut_weight: int,
    min_piece_length: int | None,
) -> tuple[str, dict]:
    bc = data["BeamConfiguration"]
    beam_length = int(bc["BeamLength"])
    n_beams = int(bc.get("NumberOfBeams", 1))
    n_layers_per_beam = int(bc.get("NumberOfLayers", 1))
    n_layers = n_beams * n_layers_per_beam
    min_len = int(bc.get("MinLengthOfBoardInLayer", 0))
    skip_start = int(bc.get("BeamSkipStart", 0))
    skip_end = int(bc.get("BeamSkipEnd", 0))
    max_shift = int(bc.get("MaxShiftCurvedCut", 0))

    boards = data.get("InputBoards", [])
    segments: list[int] = []
    for board in boards:
        segments.extend(
            _usable_segment_lengths(
                board,
                skip_start=skip_start,
                skip_end=skip_end,
                max_shift_curved=max_shift,
                min_len=min_len,
            )
        )
    if not segments:
        raise ValueError("no usable segments after preprocessing")

    if min_piece_length is None:
        min_piece_length = min_len

    n_segments = len(segments)
    max_segment_length = max(segments)
    total_usable = sum(segments)
    n_pieces_per_segment = cuts_per_segment + 1
    n_pieces = n_segments * n_pieces_per_segment
    n_cuts = n_segments * cuts_per_segment
    demand = n_layers * beam_length
    min_waste = max(0, total_usable - demand)
    max_cost = waste_weight * total_usable + cut_weight * n_cuts

    model = MODEL_TEMPLATE.format(
        source_name=source_name,
        n_boards=len(boards),
        n_segments=n_segments,
        max_shift=max_shift,
        skip_start=skip_start,
        skip_end=skip_end,
        min_seg_len=min_len,
        n_beams=n_beams,
        n_layers_per_beam=n_layers_per_beam,
        layer_length=beam_length,
        min_waste=min_waste,
        total_usable=total_usable,
        demand=demand,
        n_layers=n_layers,
        min_piece_length=min_piece_length,
        max_segment_length=max_segment_length,
        n_cuts_per_segment=cuts_per_segment,
        n_pieces_per_segment=n_pieces_per_segment,
        n_cuts=n_cuts,
        n_pieces=n_pieces,
        waste_weight=waste_weight,
        cut_weight=cut_weight,
        max_cost=max_cost,
        segment_lengths=_format_int_list(segments),
    )

    summary = dict(
        boards=len(boards),
        segments=n_segments,
        pieces=n_pieces,
        decisions=n_cuts + n_pieces,
        layers=n_layers,
        total_usable=total_usable,
        demand=demand,
        min_waste=min_waste,
    )
    return model, summary


def convert_file(
    json_path: Path,
    out_dir: Path,
    cuts_per_segment: int,
    waste_weight: int,
    cut_weight: int,
    min_piece_length: int | None,
) -> tuple[Path, dict]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    model, summary = build_model(
        data,
        source_name=json_path.name,
        cuts_per_segment=cuts_per_segment,
        waste_weight=waste_weight,
        cut_weight=cut_weight,
        min_piece_length=min_piece_length,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (json_path.stem + ".dsl")
    out_path.write_text(model, encoding="utf-8")
    return out_path, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="JSON benchmark file(s) or a directory to glob *.json")
    parser.add_argument(
        "-o",
        "--outdir",
        default="problem_instances/cutting_packing/benchmarks/generated_cp",
        help="Directory to write the generated .dsl files",
    )
    parser.add_argument(
        "--cuts-per-segment",
        type=int,
        default=2,
        help="Maximum cuts per usable segment (>=2 recommended; 1 can make exact fill infeasible)",
    )
    parser.add_argument("--waste-weight", type=int, default=1)
    parser.add_argument("--cut-weight", type=int, default=1)
    parser.add_argument(
        "--min-piece-length",
        type=int,
        default=None,
        help="Minimum length of a piece used in a layer (default: MinLengthOfBoardInLayer from the JSON; 0 disables)",
    )
    args = parser.parse_args()

    json_files: list[Path] = []
    for path in args.inputs:
        p = Path(path)
        if p.is_dir():
            json_files.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            json_files.append(p)

    out_dir = Path(args.outdir)
    for jf in json_files:
        try:
            out, summary = convert_file(
                jf,
                out_dir,
                cuts_per_segment=args.cuts_per_segment,
                waste_weight=args.waste_weight,
                cut_weight=args.cut_weight,
                min_piece_length=args.min_piece_length,
            )
        except ValueError as exc:
            print(f"{jf.name}: SKIPPED ({exc})")
            continue
        print(
            f"{jf.name} -> {out} | "
            f"boards={summary['boards']} segments={summary['segments']} "
            f"pieces={summary['pieces']} decisions={summary['decisions']} "
            f"layers={summary['layers']} usable={summary['total_usable']} "
            f"demand={summary['demand']} min_waste={summary['min_waste']}"
        )


if __name__ == "__main__":
    main()
