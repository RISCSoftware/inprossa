"""Convert a woodcutting OptDSL file (wc_0.dsl / wc_1.dsl style) into a raw
benchmark JSON instance (one_beam_no_faults.json / two_beams_02_bad_faults.json
style).

This is the *reverse* of ``Tools/convert_woodcutting_benchmarks.py`` (JSON -> DSL).
Given a DSL file such as ``problem_instances/cutting_packing/wc_0.dsl`` or
``wc_1.dsl``, it reconstructs the JSON problem-data structure:

    {
      "BeamConfiguration": { ... },
      "InputBoards": [ { "Position": 0, "RawBoard": { ... } }, ... ]
    }

Mapping (DSL -> JSON)
---------------------
BeamConfiguration
    BEAM_LENGTH (or LAYER_LENGTH)     -> BeamLength
    BEAM_DEPTH                        -> NumberOfLayers
    N_BEAMS (if declared)             -> NumberOfBeams
      NOTE: the DSL represents the number of beams to produce with the
      dedicated ``N_BEAMS`` constant (emitted by the forward converter when
      NumberOfBeams != N_BOARDS; e.g. one_beam has N_BOARDS=4 but N_BEAMS=1).
      If N_BEAMS is absent the DSL carries no beam-count, so it falls back to
      the raw-board count (N_BOARDS) and can be overridden with
      --number-of-beams.
    FORBIDDEN_INTERVALS               -> StaticForbiddenZones
      (list of {"Begin": .., "End": ..}); degenerate [0,0] entries dropped.
    BEAM_SKIP_START / BEAM_SKIP_END   -> BeamSkipStart / BeamSkipEnd
    MIN_LENGTH_OF_BOARD_IN_LAYER      -> MinLengthOfBoardInLayer
    GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS -> GapToBoardAbutInConsecutiveLayers
    MAX_SHIFT_CURVED_CUT              -> MaxShiftCurvedCut
    defaulted (DSL carries no value), override with CLI flags:
      BeamWidth, BeamHeight                         -> 0
      BeamSkipStart, BeamSkipEnd                    -> 10
      MinLengthOfBoardInLayer                       -> 10
      GapToBoardAbutInConsecutiveLayers             -> 10
      MaxShiftCurvedCut                             -> 50

InputBoards  (one entry per raw board, len == N_BOARDS)
    Board.length                  -> RawBoard.Length
    Board.bad_intervals           -> ScanBoardParts with Quality == 2 (bad)
    Board.curved_intervals        -> ScanBoardParts with Quality == 3 (curved)
    Board.length fallbacks:
      wc_1.x style (no Board records / no GIVEN_INITIAL_BOARDS):
        ORIGINAL_BOARDS[board]    -> RawBoard.Length   (if the list is present)
        MAX_BOARD_LENGTH          -> RawBoard.Length   (fallback)
    RawBoard.Width / Height       -> 0 (defaults), also see --board-width/--board-height

ScanBoardParts reconstruction
    Each board is resynthesised as a single "scan" over [0, length].  The defect
    intervals (bad + curved) are merged and emitted as separate scan parts of
    length > 0 tagged with the matching Quality; the remaining good stretches
    become Quality == 1 parts.  Overlapping intervals of different kinds are
    split so a single position maps to exactly one quality tag (bad dominates
    curved for determinism).  Degenerate Interval(0,0) padding entries (used to
    fill DSList(MAX_N_INTERVALS, Interval)) are ignored.  Adjacent same-quality
    parts are coalesced, and part Ids are 1-based contiguous per board.

Quality convention (matches the existing benchmark data)
    1 -> good part
    2 -> bad defect      (Board.bad_intervals)
    3 -> curved defect   (Board.curved_intervals)

Limitations
    * The DSL does not carry a beam-production count distinct from the raw-board
      count unless a ``N_BEAMS`` constant is declared.  In the reference
      benchmark data NumberOfBeams != len(InputBoards) (e.g. two_beams has
      NumberOfBeams=2 but 6 InputBoards).  The forward converter now emits
      ``N_BEAMS`` so round-trips preserve it; for DSLs without N_BEAMS the
      fallback is the board count, override with --number-of-beams.
    * wc_1.dsl is the simplified LNS model: it has no beam depth / forbidden
      zones / defect data, so those JSON fields fall back to defaults.
    * The array/scalar upper bounds (DSInt(0, MAX..)) are NOT the actual defect
      intervals; the concrete Board.bad_intervals / curved_intervals lists are
      used.

Usage
    python Tools/convert_woodcutting_dsl_to_json.py <dsl_file> [-o dir]
    python Tools/convert_woodcutting_dsl_to_json.py problem_instances/cutting_packing/wc_0.dsl
    python Tools/convert_woodcutting_dsl_to_json.py problem_instances/cutting_packing/wc_1.dsl
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# DSL as data: turn the .dsl (Python-like) text into a Python AST.
# --------------------------------------------------------------------------


class ConstantError(ValueError):
    """Raised when a constant expression cannot be statically evaluated."""


def _eval_expr(node: ast.AST, env: dict[str, int]) -> int:
    """Evaluate a constant integer expression using only parsed int constants."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_expr(node.operand, env)
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Add):
            return _eval_expr(node.left, env) + _eval_expr(node.right, env)
        if isinstance(node.op, ast.Sub):
            return _eval_expr(node.left, env) - _eval_expr(node.right, env)
        if isinstance(node.op, ast.Mult):
            return _eval_expr(node.left, env) * _eval_expr(node.right, env)
        if isinstance(node.op, ast.FloorDiv):
            return _eval_expr(node.left, env) // _eval_expr(node.right, env)
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    raise ConstantError(f"Constant expression not supported: {ast.dump(node)}")


def parse_dsl_constants(source: str) -> dict[str, int]:
    """Parse all top-level ``NAME : int = <expr>`` constants.

    Multi-pass: later constants may reference earlier ones (e.g.
    N_PIECES = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1)).  Also picks up plain
    ``NAME = <literal int>`` assignments.
    """
    tree = ast.parse(source)
    env: dict[str, int] = {}

    def _candidates():
        for n in tree.body:
            if (isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
                    and isinstance(n.annotation, ast.Name)
                    and n.annotation.id == "int" and isinstance(n.value, ast.AST)):
                yield n.target.id, n.value
            elif (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.AST)):
                yield n.targets[0].id, n.value

    pending = list(_candidates())
    while pending:
        progressed = False
        still_pending = []
        for name, value in pending:
            try:
                env[name] = _eval_expr(value, env)
                progressed = True
            except ConstantError:
                still_pending.append((name, value))
        if not progressed:
            break  # cyclic / unsupported refs
        pending = still_pending
    return env


def strip_comments(source: str) -> str:
    """Remove ``# ...`` comments outside of string literals."""
    out: list[str] = []
    i, n = 0, len(source)
    in_str: str | None = None
    while i < n:
        ch = source[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(source[i + 1])
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            out.append(ch)
            i += 1
            continue
        if ch == "#":
            while i < n and source[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# --------------------------------------------------------------------------
# DSL -> JSON mapping helpers
# --------------------------------------------------------------------------


def _assignment_value_node(tree: ast.AST, name: str) -> ast.AST | None:
    """Return the AST value node of a top-level ``NAME = <expr>`` assignment."""
    for n in tree.body:
        target = None
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            target = n.targets[0]
        elif isinstance(n, ast.AnnAssign):
            target = n.target
        if target is not None and isinstance(target, ast.Name) \
                and target.id == name and isinstance(n.value, ast.AST):
            return n.value
    return None


def _eval_value(node: ast.AST, env: dict[str, int]) -> Any:
    """Evaluate a DSL value that may contain literals AND record constructors.

    Handles the ``Board(...)`` / ``Interval(...)`` record-constructor calls used
    in ``GIVEN_INITIAL_BOARDS`` (which ``ast.literal_eval`` rejects):

    * ``Interval(a, b)`` -> ``{"start": a, "end": b}``
    * ``Board(field=.., ...)`` -> ``{field: value, ...}`` (recursively evaluated)
    * int/str/bool constants, list/tuple, dict

    Raises ``ConstantError`` for anything not statically evaluable.
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise ConstantError(f"Unresolved constant {node.id}")
    if isinstance(node, ast.List):
        return [_eval_value(e, env) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_value(e, env) for e in node.elts)
    if isinstance(node, ast.Dict):
        return {
            ast.literal_eval(k): _eval_value(v, env)
            for k, v in zip(node.keys, node.values)
        }
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name == "Interval":
            args = [_eval_value(a, env) for a in node.args]
            if len(args) < 2:
                raise ConstantError("Interval() needs start and end")
            return {"start": args[0], "end": args[1]}
        # Generic record constructor: Board(field=.., ...) / CutList(...) / ...
        result: dict[str, Any] = {}
        for kw in node.keywords:
            if kw.arg is not None:
                result[kw.arg] = _eval_value(kw.value, env)
        return result
    raise ConstantError(f"Value not statically evaluable: {ast.dump(node)}")


def _literal_assignment(tree: ast.AST, name: str) -> Any | None:
    """Return the literal value of a top-level ``NAME = <literal>`` assignment."""
    node = _assignment_value_node(tree, name)
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (TypeError, ValueError):
        # Constructor-heavy values (GIVEN_INITIAL_BOARDS = [ Board(...) ])
        # need the specialised evaluator.
        try:
            return _eval_value(node, {})
        except ConstantError:
            return None


def _merge_defects(bad_pairs: list[tuple[int, int]],
                   curved_pairs: list[tuple[int, int]]) -> list[tuple[int, int, int]]:
    """Merge bad + curved intervals into non-overlapping defect segments.

    Returns a sorted list of ``(start, end, quality)`` where quality is 2 (bad)
    or 3 (curved).  Adjacent intervals sharing a boundary stay distinct (e.g.
    bad [0,19] then bad [19,57]) and zero-length gaps do not produce defects.

    A sweep over the sorted unique boundary positions is used so that starts
    and ends at the SAME position are handled correctly (the interval ending at
    p is flushed before the interval starting at p begins).
    """
    events: list[tuple[int, int]] = []  # (pos, kind) kind +1 = start, -1 = end
    kind_bad = 1
    kind_curved = 2
    for s, e in bad_pairs:
        if e > s:
            events.append((s, kind_bad, 1))
            events.append((e, kind_bad, -1))
    for s, e in curved_pairs:
        if e > s:
            events.append((s, kind_curved, 1))
            events.append((e, kind_curved, -1))
    if not events:
        return []

    positions = sorted({p for p, _k, _d in events})
    active_bad = False
    active_curved = False
    defects: list[tuple[int, int, int]] = []
    seg_start: int | None = None
    for p in positions:
        # Flush the current segment before applying transitions at p, so an
        # interval ending at p and another starting at p stay distinct and a
        # zero-length boundary does not merge them.
        if seg_start is not None and p > seg_start:
            q = 2 if active_bad else 3
            defects.append((seg_start, p, q))
        # Apply transitions at this position.
        for pos, kind, delta in events:
            if pos != p:
                continue
            if delta == 1:
                if kind == kind_bad:
                    active_bad = True
                else:
                    active_curved = True
            else:
                if kind == kind_bad:
                    active_bad = False
                else:
                    active_curved = False
        # Start a new segment if anything is active (bad dominates curved).
        if active_bad or active_curved:
            seg_start = p
        else:
            seg_start = None
    defects.sort()
    return defects


def _build_scan_parts(length: int, defects: list[tuple[int, int, int]]) -> list[dict[str, Any]]:
    """Synthesise ScanBoardParts over [0, length].

    Good stretches become Quality==1 parts; each defect becomes a part tagged
    with its quality.  Adjacent same-quality parts are coalesced.  Defects are
    clamped to [0, length] (the DSL occasionally lists intervals past a board's
    declared length, e.g. ``Interval(18,20)`` on a length-15 board).
    """
    # Clamp and dedupe defect intervals to the board.
    clamped: list[tuple[int, int, int]] = []
    for s, e, q in defects:
        if e <= 0 or s >= length or e <= s:
            continue
        cs, ce = max(0, s), min(length, e)
        if ce > cs:
            clamped.append((cs, ce, q))
    clamped.sort(key=lambda t: (t[0], t[1]))

    parts: list[tuple[int, int, int]] = []
    pos = 0
    for s, e, q in clamped:
        if e <= pos:
            # Defect lies entirely within what we already emitted (overlap);
            # but a defect STARTING exactly where the previous one ended
            # (s == pos) MUST still be emitted (adjacent defects at a shared
            # boundary are distinct intervals, e.g. [0,19] then [19,57]).
            if s < pos:
                continue
        if s > pos:
            parts.append((pos, s, 1))
        if e > pos:
            parts.append((max(s, pos), e, q))
            pos = max(pos, e)
    if pos < length:
        parts.append((pos, length, 1))
    if not parts and length > 0:
        parts.append((0, length, 1))

    coalesced: list[tuple[int, int, int]] = []
    for s, e, q in parts:
        if coalesced and coalesced[-1][2] == q and coalesced[-1][1] == s:
            coalesced[-1] = (coalesced[-1][0], e, q)
        else:
            coalesced.append((s, e, q))

    scan_parts: list[dict[str, Any]] = []
    for idx, (s, e, q) in enumerate(coalesced, start=1):
        scan_parts.append({
            "Id": idx,
            "StartPosition": s,
            "EndPosition": e,
            "Quality": q,
            "Length": e - s,
            "Interval": [s, e],
        })
    return scan_parts


# --------------------------------------------------------------------------
# Main conversion
# --------------------------------------------------------------------------


def dsl_to_json(source: str, *, defaults: dict[str, Any] | None = None,
                number_of_beams: int | None = None,
                verbose: bool = True) -> dict[str, Any]:
    """Convert a woodcutting DSL source string into the benchmark JSON dict."""
    defaults = defaults or {}
    notes: list[str] = []
    source = strip_comments(source)
    tree = ast.parse(source)
    env = parse_dsl_constants(source)

    n_boards = env.get("N_BOARDS", 0)
    layer_length = env.get("BEAM_LENGTH")
    if layer_length is None:
        layer_length = env.get("LAYER_LENGTH")
    beam_depth = env.get("BEAM_DEPTH", 0)
    max_board_length = env.get("MAX_BOARD_LENGTH", 0)

    if number_of_beams is None:
        number_of_beams = env.get("N_BEAMS", n_boards)

    # Beam skip margins (BEAM_SKIP_START / BEAM_SKIP_END), falling back to the
    # CLI-provided default when the DSL does not declare them.
    beam_skip_start = env.get("BEAM_SKIP_START", defaults.get("beam_skip_start", 10))
    beam_skip_end = env.get("BEAM_SKIP_END", defaults.get("beam_skip_end", 10))
    min_length_of_board_in_layer = env.get(
        "MIN_LENGTH_OF_BOARD_IN_LAYER", defaults.get("min_length_of_board_in_layer", 10)
    )
    gap_to_board_abut = env.get(
        "GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS", defaults.get("gap_to_board_abut", 10)
    )
    max_shift_curved_cut = env.get(
        "MAX_SHIFT_CURVED_CUT", defaults.get("max_shift_curved_cut", 50)
    )

    # FORBIDDEN_INTERVALS literal (list of [Begin, End]).
    forbidden = _literal_assignment(tree, "FORBIDDEN_INTERVALS")
    forbidden_pairs: list[tuple[int, int]] = []
    if isinstance(forbidden, (list, tuple)):
        for it in forbidden:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                s, e = int(it[0]), int(it[1])
                if (s, e) != (0, 0):
                    forbidden_pairs.append((s, e))
    else:
        # Regex fallback: FORBIDDEN_INTERVALS = [[a,b], [c,d], ...]
        fm = re.search(r"FORBIDDEN_INTERVALS\s*=\s*\[(.*)\]", source, re.DOTALL)
        if fm:
            for im in re.finditer(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", fm.group(1)):
                s, e = int(im.group(1)), int(im.group(2))
                if (s, e) != (0, 0):
                    forbidden_pairs.append((s, e))

    # ---------------------------- Boards ----------------------------
    boards: list[dict[str, Any]] = []
    given = _literal_assignment(tree, "GIVEN_INITIAL_BOARDS")
    original_lengths = _literal_assignment(tree, "ORIGINAL_BOARDS")

    def _iter_pairs(raw: Any) -> list[tuple[int, int]]:
        """Turn a list of ``{"start": s, "end": e}`` (or ``[s, e]``) into pairs,
        dropping degenerate (0, 0) padding."""
        pairs: list[tuple[int, int]] = []
        if raw is None:
            return pairs
        for it in raw if isinstance(raw, (list, tuple)) else []:
            if isinstance(it, dict):
                s, e = it.get("start"), it.get("end")
            elif isinstance(it, (list, tuple)) and len(it) >= 2:
                s, e = it[0], it[1]
            else:
                continue
            try:
                s, e = int(s), int(e)
            except (TypeError, ValueError):
                continue
            if (s, e) != (0, 0):
                pairs.append((s, e))
        return pairs

    if given is not None:
        given = given if isinstance(given, list) else []
        for idx, board in enumerate(given):
            if not isinstance(board, dict):
                notes.append(f"InputBoard {idx}: not a record; using defaults")
                board = {}
            length = board.get("length") or max_board_length
            if not isinstance(length, int) or length <= 0:
                length = max_board_length
            bad_pairs = _iter_pairs(board.get("bad_intervals"))
            curved_pairs = _iter_pairs(board.get("curved_intervals"))
            defects = _merge_defects(bad_pairs, curved_pairs)
            boards.append({
                "Position": idx,
                "RawBoard": {
                    "Id": idx + 1,
                    "Length": length,
                    "Width": defaults.get("board_width", 0),
                    "Height": defaults.get("board_height", 0),
                    "ScanBoardParts": _build_scan_parts(length, defects),
                },
            })
    else:
        lengths: list[int] = []
        if isinstance(original_lengths, (list, tuple)):
            lengths = [int(v) for v in original_lengths]
        if not lengths:
            lengths = [max_board_length] * max(n_boards, 1) if n_boards else []
        for idx in range(len(lengths)):
            length = lengths[idx]
            boards.append({
                "Position": idx,
                "RawBoard": {
                    "Id": idx + 1,
                    "Length": length,
                    "Width": defaults.get("board_width", 0),
                    "Height": defaults.get("board_height", 0),
                    "ScanBoardParts": _build_scan_parts(length, []),
                },
            })

    if n_boards == 0:
        n_boards = len(boards)
    if max_board_length == 0 and boards:
        max_board_length = max(b["RawBoard"]["Length"] for b in boards)

    beam_cfg = {
        "BeamLength": layer_length if layer_length is not None else max_board_length,
        "BeamWidth": defaults.get("beam_width", 0),
        "BeamHeight": defaults.get("beam_height", 0),
        "NumberOfLayers": beam_depth,
        "NumberOfBeams": number_of_beams,
        "BeamSkipStart": beam_skip_start,
        "BeamSkipEnd": beam_skip_end,
        "MinLengthOfBoardInLayer": min_length_of_board_in_layer,
        "GapToBoardAbutInConsecutiveLayers": gap_to_board_abut,
        "MaxShiftCurvedCut": max_shift_curved_cut,
        "StaticForbiddenZones": [
            {"Begin": s, "End": e} for s, e in forbidden_pairs
        ],
    }

    if verbose and notes:
        for note in notes:
            print(f"  note: {note}")

    return {
        "BeamConfiguration": beam_cfg,
        "InputBoards": boards,
    }


def convert_file(dsl_path: Path, out_path: Path | None = None, **kwargs: Any) -> Path:
    source = dsl_path.read_text(encoding="utf-8")
    data = dsl_to_json(source, **kwargs)
    if out_path is None:
        out_path = dsl_path.with_suffix(".json")
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="DSL file(s) to convert")
    parser.add_argument("-o", "--outdir", default=None,
                        help="Directory to write JSON files (default: next to each DSL)")
    parser.add_argument("--number-of-beams", type=int, default=None,
                        help="Override BeamConfiguration.NumberOfBeams "
                             "(default: N_BOARDS constant)")
    parser.add_argument("--beam-width", type=int, default=0)
    parser.add_argument("--beam-height", type=int, default=0)
    parser.add_argument("--skip", type=int, default=10, help="BeamSkipStart/End")
    parser.add_argument("--min-length", type=int, default=10,
                        help="MinLengthOfBoardInLayer")
    parser.add_argument("--gap", type=int, default=10,
                        help="GapToBoardAbutInConsecutiveLayers")
    parser.add_argument("--max-shift", type=int, default=50,
                        help="MaxShiftCurvedCut")
    parser.add_argument("--board-width", type=int, default=0)
    parser.add_argument("--board-height", type=int, default=0)
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress notes")
    args = parser.parse_args()

    defaults = {
        "beam_width": args.beam_width,
        "beam_height": args.beam_height,
        "beam_skip_start": args.skip,
        "beam_skip_end": args.skip,
        "min_length_of_board_in_layer": args.min_length,
        "gap_to_board_abut": args.gap,
        "max_shift_curved_cut": args.max_shift,
        "board_width": args.board_width,
        "board_height": args.board_height,
    }

    for path in args.inputs:
        p = Path(path)
        out_dir = Path(args.outdir) if args.outdir else p.parent
        out = convert_file(
            p,
            out_path=out_dir / (p.stem + ".json"),
            defaults=defaults,
            number_of_beams=args.number_of_beams,
            verbose=not args.quiet,
        )
        print(f"{p.name} -> {out}")


if __name__ == "__main__":
    main()
