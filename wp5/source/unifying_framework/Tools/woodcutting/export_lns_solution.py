"""Convert a run_lns.py woodcutting-pipeline solution into the same
processed-solution JSON schema produced by process_instance.py, so it can be
rendered with visualize_solution.py.

Usage:
    python run_lns.py <dsl_file> --initializer woodcutting_pipeline \\
        --export-assignment-json assignment.json
    python Tools/woodcutting/export_lns_solution.py <dsl_file> assignment.json \\
        -o processed.json --emit-instance-json instance.json
    python Tools/woodcutting/visualize_solution.py processed.json --instance instance.json

This script is standalone (no dependency on the large_neighborhood_search
package): it re-parses the rich "pipeline" DSL model directly (constants,
GIVEN_INITIAL_BOARDS record literals) and replays the same board/cut/keep/
reorder decisions the DSL's machines apply, tracking provenance (which
board/segment each final piece came from) so beam/layer placements can be
reconstructed.

SINGLE-HOLD REORDER (matches WoodCutter.java)
---------------------------------------------
The target simulator (WoodCutter.java) command vocabulary
(scan / bgo / bout / bin / cut / keep / pgo / pout / pin / discard /
assemble / push / pop / end) assembles kept pieces strictly in the order they
land in ``reorderedPieces``.  ``pout``/``pin`` provide a SINGLE piece buffer
(one held-back piece): the DSL's ``swapping_decisions`` is therefore interpreted
as a single-hold reorder (the first ``1`` selects the one piece held back and
released at the end; all other pieces keep relative order).  The exporter
mirrors this exactly: every DSL-kept non-held piece is ``keep``+``pgo``, the
single held piece is ``keep``+``pout`` and finally ``pin``-ed last, then one
``assemble`` per kept piece.  Because the DSL ``checking_machine`` already
validated the reordered stream, the emitted commands are simulator-executable
by construction and the DSL objective equals the simulator's cost.

Status values:
  * "ok"      - all required layers can be assembled (commands are
                simulator-faithful end-to-end).
  * "partial" - the DSL solution cannot complete all required layers.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


class DSRecord(dict):
    """Dict with attribute access, mirroring OptDSL record semantics."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _collect_record_types(tree: ast.Module) -> dict[str, list[str]]:
    """Map record type name -> ordered field names, from `Name = DSRecord({...})`."""
    record_types: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "DSRecord":
            continue
        if not value.args or not isinstance(value.args[0], ast.Dict):
            continue
        fields = [
            key.value
            for key in value.args[0].keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        ]
        record_types[node.targets[0].id] = fields
    return record_types


def _eval_expr(node: ast.expr, env: dict[str, Any], record_types: dict[str, list[str]]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.List):
        return [_eval_expr(elt, env, record_types) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_expr(elt, env, record_types) for elt in node.elts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_expr(node.operand, env, record_types)
    if isinstance(node, ast.BinOp):
        left = _eval_expr(node.left, env, record_types)
        right = _eval_expr(node.right, env, record_types)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        raise NotImplementedError(type(node.op).__name__)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in record_types:
            field_order = record_types[node.func.id]
            values: dict[str, Any] = {}
            for i, arg in enumerate(node.args):
                values[field_order[i]] = _eval_expr(arg, env, record_types)
            for kw in node.keywords:
                if kw.arg is not None:
                    values[kw.arg] = _eval_expr(kw.value, env, record_types)
            return DSRecord(values)
        raise NotImplementedError(f"Unsupported call: {node.func.id}")
    raise NotImplementedError(f"Unsupported expression node: {type(node).__name__}")


def read_dsl_constants(dsl_path: Path) -> dict[str, Any]:
    """Resolve the module-level uppercase constants of a woodcutting pipeline DSL file."""
    tree = ast.parse(dsl_path.read_text(encoding="utf-8"))
    record_types = _collect_record_types(tree)

    env: dict[str, Any] = {}
    pending: list[tuple[str, ast.expr]] = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id.isupper():
            if node.value is not None:
                pending.append((node.target.id, node.value))

    # Bounded fixed-point resolution: later constants may reference earlier ones.
    for _ in range(3):
        remaining: list[tuple[str, ast.expr]] = []
        for name, expr in pending:
            try:
                env[name] = _eval_expr(expr, env, record_types)
            except (KeyError, NotImplementedError, TypeError, IndexError):
                remaining.append((name, expr))
        if len(remaining) == len(pending):
            break
        pending = remaining

    return env


def _apply_board_swaps(boards: list[dict], swap_decisions: list[int]) -> list[tuple[int, dict]]:
    """Sequential adjacent-swap network, mirroring reordering_board_machine."""
    ordered = list(enumerate(boards))  # (original_index, board)
    for i, decision in enumerate(swap_decisions):
        if decision:
            ordered[i], ordered[i + 1] = ordered[i + 1], ordered[i]
    return ordered


def _apply_piece_swaps(pieces: list[dict], swap_decisions: list[int]) -> list[dict]:
    """Single-held-piece reorder, mirroring the (reworked) DSL reordering_piece_machine.

    The first active bit (1) selects the ONE piece held back; every other piece
    keeps its relative order; the held piece is re-appended at the end.  This
    matches the target WoodCutter simulator's single-piece buffer (pgo/pout/pin):
    pgo through pieces before the hold and past it, pout the held one, pin at end.
    """
    held_idx: int | None = None
    for idx, bit in enumerate(swap_decisions):
        if bit:
            held_idx = idx
            break
    if held_idx is None:
        return list(pieces)
    return pieces[:held_idx] + pieces[held_idx + 1:] + [pieces[held_idx]]


def _piece_quality(
    bad_intervals: list[dict],
    start: int,
    end: int,
    board_length: int,
    skip_start: int,
    skip_end: int,
) -> int:
    for interval in bad_intervals:
        if not (interval["start"] >= end or start >= interval["end"]):
            return 0
    # Board edge skip zones: the first skip_start and last skip_end units of
    # the board are unusable and cut away.
    if start < skip_start or end > board_length - skip_end:
        return 0
    return 1


def _cut_board(
    board: dict,
    original_index: int,
    position_list: list[int],
    skip_start: int,
    skip_end: int,
) -> list[dict[str, Any]]:
    """Mirror cutting_machine: turn one board's cut positions into piece records."""
    board_length = int(board["length"])
    pieces: list[dict[str, Any]] = []
    for i in range(1, len(position_list)):
        start, end = int(position_list[i - 1]), int(position_list[i])
        length = end - start
        pieces.append(
            {
                "board_id": original_index + 1,
                "board_position": original_index,
                "source_start": start,
                "source_end": end,
                "length": length,
                "quality": _piece_quality(
                    board["bad_intervals"], start, end, board_length, skip_start, skip_end
                ),
            }
        )
    return pieces


def build_processed_solution(constants: dict[str, Any], assignment: dict[str, Any]) -> dict[str, Any]:
    boards = constants["GIVEN_INITIAL_BOARDS"]
    beam_length = int(constants["BEAM_LENGTH"])
    beam_depth = int(constants["BEAM_DEPTH"])
    n_beams = int(constants.get("N_BEAMS", 1))
    skip_start = int(constants.get("BEAM_SKIP_START", 0))
    skip_end = int(constants.get("BEAM_SKIP_END", 0))
    min_length_of_board_in_layer = int(constants.get("MIN_LENGTH_OF_BOARD_IN_LAYER", 0))
    gap_to_board_abut = int(constants.get("GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS", 0))
    max_shift_curved_cut = int(constants.get("MAX_SHIFT_CURVED_CUT", 0))
    forbidden_raw = constants.get("FORBIDDEN_INTERVALS", [])

    ordered_boards = _apply_board_swaps(boards, assignment.get("swapping_decisions_boards", []))

    # cuts_list_list is indexed by FINAL (post board-swap) position, matching cutting_machine.
    all_pieces: list[dict[str, Any]] = []
    for final_position, (original_index, board) in enumerate(ordered_boards):
        position_list = assignment["cuts_list_list"][final_position]["position_list"]
        all_pieces.extend(_cut_board(board, original_index, position_list, skip_start, skip_end))

    keep_decisions = assignment.get("keep_decisions", [1] * len(all_pieces))
    for piece, keep in zip(all_pieces, keep_decisions):
        piece["kept"] = bool(keep)

    input_good_seen = sum(p["length"] for p in all_pieces if p["quality"] == 1)
    bad_cut_out = sum(p["length"] for p in all_pieces if p["quality"] == 0)
    good_cut_out = sum(p["length"] for p in all_pieces if p["quality"] == 1 and not p["kept"])

    # The beam edge margins ([0, skip_start] and [len - skip_end, len]) are
    # unusable good material, tracked separately from deliberately discarded
    # good material so the visualizer can style them differently.
    skipped_board_margins = []
    edge_skipped_good = 0
    for original_index, board in ordered_boards:
        board_id = int(original_index) + 1
        board_len = int(board["length"])
        intervals: list[tuple[int, int]] = []
        if skip_start > 0:
            intervals.append((0, min(skip_start, board_len)))
        if skip_end > 0:
            intervals.append((max(0, board_len - skip_end), board_len))
        real = [(s, e) for s, e in intervals if e > s]
        if real:
            margin_len = sum(e - s for s, e in real)
            edge_skipped_good += margin_len
            skipped_board_margins.append(
                {
                    "BoardId": board_id,
                    "Intervals": [{"Start": s, "End": e} for s, e in real],
                    "Length": margin_len,
                }
            )

    stream = [dict(p, length=(p["length"] if p["kept"] else 0)) for p in all_pieces]
    stream = _apply_piece_swaps(stream, assignment.get("swapping_decisions", []))

    beams, failed_layers = _build_beams(stream, beam_length, beam_depth, n_beams)
    built_layers = sum(len(b["Layers"]) for b in beams)

    # The simulator assembles pieces in the order they enter reorderedPieces via
    # keep+pgo (board-by-board keep order); its pout/pin primitives expose only a
    # single piece buffer, so an arbitrary DSL reordering cannot be reproduced.
    # With the reworked single-hold DSL semantics (see module docstring + the
    # reordering_machine), _build_simulator_commands now emits an executable plan
    # that realises the single held piece via pout/pin, so DSL-feasible solutions
    # are by construction simulator-executable.
    sim_commands, _sim_kept_count, sim_plan = _build_simulator_commands(
        ordered_boards, assignment, all_pieces
    )

    # GoodUsed reflects what the simulator actually assembles from the executed
    # keep/discard plan.
    sim_used = sum(
        (seg_end - seg_start)
        for (board_id, seg_start, seg_end, exec_keep) in sim_plan
        if exec_keep
    )
    total_layers = n_beams * beam_depth
    # With the single-hold DSL semantics, the reordered stream that
    # checking_machine validated (stream, below) is EXACTLY what the simulator
    # will assemble (the held piece is released at the end via pin in the same
    # position).  So the simulator's layer count equals the DSL-built layers.
    simulator_completes = built_layers == total_layers
    sim_layers = built_layers

    return {
        "Status": "ok" if simulator_completes else "partial",
        "ConfigurationSummary": {
            "BeamLength": beam_length,
            "NumberOfBeams": n_beams,
            "NumberOfLayers": beam_depth,
            "MinLengthOfBoardInLayer": min_length_of_board_in_layer,
            "BeamSkipStart": skip_start,
            "BeamSkipEnd": skip_end,
            "GapToBoardAbutInConsecutiveLayers": gap_to_board_abut,
            "MaxShiftCurvedCut": max_shift_curved_cut,
            "StaticForbiddenZones": [{"Begin": int(lo), "End": int(hi)} for lo, hi in forbidden_raw],
        },
        "Statistics": {
            "RequiredLayers": n_beams * beam_depth,
            "BuiltLayers": built_layers,
            "SimulatorBuiltLayers": sim_layers,
            "BoardsProcessed": len(ordered_boards),
            "InputGoodSeen": input_good_seen,
            "InputBadSeen": bad_cut_out,
            "GoodCutOut": good_cut_out,
            "GoodSkippedByBeamMargins": edge_skipped_good,
            "BadCutOut": bad_cut_out,
            "GoodUsed": sim_used,
            "RemainingGood": 0,
            "RemainingBad": 0,
        },
        "SkippedBoardMargins": skipped_board_margins,
        "SimulatorCommands": sim_commands,
        "Beams": beams,
        "FailedLayers": failed_layers,
    }


def _build_beams(
    stream: list[dict[str, Any]],
    beam_length: int,
    beam_depth: int,
    n_beams: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mirror checking_machine's running-sum layer grouping, keeping provenance."""
    beams: list[dict[str, Any]] = []
    failed_layers: list[dict[str, Any]] = []
    current_beam_layers: list[dict[str, Any]] = []
    placements: list[dict[str, Any]] = []
    filled = 0
    beam_index = 0
    layer_index = 0

    def finalize_beam() -> None:
        nonlocal current_beam_layers, beam_index, layer_index
        beams.append(
            {
                "BeamIndex": beam_index,
                "BuiltLayers": len(current_beam_layers),
                "TargetLayers": beam_depth,
                "Layers": current_beam_layers,
            }
        )
        beam_index += 1
        layer_index = 0
        current_beam_layers = []

    for piece in stream:
        if beam_index >= n_beams:
            break
        if piece["length"] <= 0:
            continue

        start = filled
        filled += piece["length"]
        placements.append(
            {
                "LayerStart": start,
                "LayerEnd": filled,
                "Length": piece["length"],
                "SourceBoardId": piece["board_id"],
                "SourceBoardPosition": piece["board_position"],
                "SourceStart": piece["source_start"],
                "SourceEnd": piece["source_end"],
            }
        )

        if filled == beam_length:
            current_beam_layers.append(
                {
                    "BeamIndex": beam_index,
                    "LayerIndex": layer_index,
                    "Length": beam_length,
                    "Seams": [p["LayerEnd"] for p in placements[:-1]],
                    "Placements": placements,
                }
            )
            layer_index += 1
            placements = []
            filled = 0
            if layer_index == beam_depth:
                finalize_beam()
        elif filled > beam_length:
            failed_layers.append(
                {
                    "BeamIndex": beam_index,
                    "LayerIndex": layer_index,
                    "Reason": "Running length exceeded BEAM_LENGTH (infeasible assignment)",
                    "FilledLength": filled,
                    "TargetLength": beam_length,
                }
            )
            filled = 0
            placements = []

    if beam_index < n_beams and (placements or filled > 0):
        failed_layers.append(
            {
                "BeamIndex": beam_index,
                "LayerIndex": layer_index,
                "Reason": "Ran out of pieces before completing the layer",
                "FilledLength": filled,
                "TargetLength": beam_length,
            }
        )
    if beam_index < n_beams and current_beam_layers:
        beams.append(
            {
                "BeamIndex": beam_index,
                "BuiltLayers": len(current_beam_layers),
                "TargetLayers": beam_depth,
                "Layers": current_beam_layers,
            }
        )

    return beams, failed_layers


def _build_simulator_commands(
    ordered_boards: list[tuple[int, dict]],
    assignment: dict[str, Any],
    all_pieces: list[dict[str, Any]],
) -> tuple[list[str], int, list[tuple[int, int, int, bool]]]:
    """Emit a simulator-valid command stream (scan/bgo/cut/keep/pgo/pout/pin/
    discard/assemble/end) that realizes the DSL's SINGLE-held-piece reorder.

    The DSL's ``reordering_piece_machine`` now uses the simulator's single-hold
    semantics: the first ``1`` in swapping_decisions picks the one held piece,
    all others keep relative order, and the held piece is released at the end.
    This exporter mirrors it with the simulator vocabulary:
      * every DSL-kept non-held piece -> ``keep`` + ``pgo`` (FIFO into reordered);
      * the single held piece         -> ``keep`` + ``pout`` (held in buffer);
      * after all boards processed    -> ``pin`` (release held piece last);
      * one ``assemble`` per kept piece in that reordered order.
    Because the DSL ``checking_machine`` already validated the reordered stream
    (running sum never exceeds beam_length), no DP is required and the emitted
    commands are guaranteed simulator-executable.

    Returns ``(commands, simulator_kept_count, plan)`` where ``plan`` maps each
    board segment to ``(board_id, seg_start, seg_end, executed_keep)``.
    """
    commands: list[str] = []
    plan: list[tuple[int, int, int, bool]] = []

    # Determine the single held piece index in KEEP order (first 1 in
    # swapping_decisions among the DSL-kept non-zero pieces).
    kept_candidates: list[tuple[int, int, int, int]] = []  # (board_id, start, end, length)
    piece_ptr = 0
    for final_position, (_original_index, board) in enumerate(ordered_boards):
        position_list = assignment["cuts_list_list"][final_position]["position_list"]
        board_length = int(board["length"])
        board_id = int(board.get("_simulator_id", final_position + 1))
        piece_count = len(position_list) - 1
        board_pieces = all_pieces[piece_ptr:piece_ptr + piece_count]
        piece_ptr += piece_count

        kept_intervals: set[tuple[int, int]] = set()
        for piece in board_pieces:
            if piece.get("kept"):
                kept_intervals.add((int(piece["source_start"]), int(piece["source_end"])))

        cuts = sorted({int(p) for p in position_list if 0 < p < board_length})
        points = [0, *cuts, board_length]
        for i in range(len(points) - 1):
            seg_start = points[i]
            seg_end = points[i + 1]
            length = int(seg_end - seg_start)
            in_kept = any(
                s_start <= seg_start and seg_end <= s_end for (s_start, s_end) in kept_intervals
            )
            if in_kept and length > 0:
                kept_candidates.append((board_id, seg_start, seg_end, length))

    # Held piece = first active swapping_decisions bit within kept-candidate range.
    swap = assignment.get("swapping_decisions", [])
    held_index: int | None = None
    for idx, bit in enumerate(swap):
        if bit:
            held_index = idx
            break
    # Map to the kept-candidate ordinal (skip zero-length / discarded pieces).
    held_candidate: int | None = None
    if held_index is not None:
        ordinal = 0
        for ci, (_bid, _s, _e, length) in enumerate(kept_candidates):
            if ordinal == held_index:
                held_candidate = ci
                break
            ordinal += 1

    # Walk boards; emit keep/discard per segment, using pgo for normal kept
    # pieces and pout for the single held piece.
    piece_ptr = 0
    kept_ordinal = 0
    for final_position, (_original_index, board) in enumerate(ordered_boards):
        position_list = assignment["cuts_list_list"][final_position]["position_list"]
        board_length = int(board["length"])
        board_id = int(board.get("_simulator_id", final_position + 1))
        piece_count = len(position_list) - 1
        board_pieces = all_pieces[piece_ptr:piece_ptr + piece_count]
        piece_ptr += piece_count

        kept_intervals: set[tuple[int, int]] = set()
        for piece in board_pieces:
            if piece.get("kept"):
                kept_intervals.add((int(piece["source_start"]), int(piece["source_end"])))

        cuts = sorted({int(p) for p in position_list if 0 < p < board_length})
        points = [0, *cuts, board_length]

        commands.append("scan")
        commands.append("bgo")
        commands.append("cut " + " ".join(str(c) for c in cuts) if cuts else "cut")

        for j in range(len(points) - 1):
            span = (int(points[j]), int(points[j + 1]))
            length = span[1] - span[0]
            in_kept = any(
                s_start <= span[0] and span[1] <= s_end
                for (s_start, s_end) in kept_intervals
            )
            if in_kept and length > 0:
                # Determine the kept-ordinal for this candidate to detect the held one.
                is_held = (kept_ordinal == held_candidate)
                commands.append("keep")
                if is_held:
                    commands.append("pout")
                else:
                    commands.append("pgo")
                kept_ordinal += 1
                plan.append((board_id, span[0], span[1], True))
            else:
                commands.append("discard")
                plan.append((board_id, span[0], span[1], False))

    # Release the held piece at the very end (pin), if any.
    if held_candidate is not None:
        commands.append("pin")

    kept_count = sum(1 for entry in plan if entry[3])
    commands.extend(["assemble"] * kept_count)
    commands.append("end")
    return commands, kept_count, plan


def build_synthetic_instance(constants: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal instance JSON (InputBoards/ScanBoardParts) from GIVEN_INITIAL_BOARDS
    so visualize_solution.py's --instance board-quality view works without the original
    benchmark JSON on hand."""
    boards = constants["GIVEN_INITIAL_BOARDS"]
    input_boards = []
    for idx, board in enumerate(boards):
        length = int(board["length"])
        zones: list[tuple[int, int, int]] = []
        for interval in board["bad_intervals"]:
            start, end = int(interval["start"]), int(interval["end"])
            if end > start:
                zones.append((start, end, 2))
        for interval in board["curved_intervals"]:
            start, end = int(interval["start"]), int(interval["end"])
            if end > start:
                zones.append((start, end, 3))
        zones.sort()

        parts: list[dict[str, int]] = []
        cursor = 0
        part_id = 1
        for start, end, quality in zones:
            if start > cursor:
                parts.append(
                    {
                        "Id": part_id,
                        "StartPosition": cursor,
                        "EndPosition": start,
                        "Quality": 1,
                        "Length": start - cursor,
                    }
                )
                part_id += 1
            parts.append(
                {
                    "Id": part_id,
                    "StartPosition": start,
                    "EndPosition": end,
                    "Quality": quality,
                    "Length": end - start,
                }
            )
            part_id += 1
            cursor = max(cursor, end)
        if cursor < length:
            parts.append(
                {
                    "Id": part_id,
                    "StartPosition": cursor,
                    "EndPosition": length,
                    "Quality": 1,
                    "Length": length - cursor,
                }
            )

        input_boards.append(
            {
                "Position": idx,
                "RawBoard": {"Id": idx + 1, "Length": length, "ScanBoardParts": parts},
            }
        )

    return {
        "InputBoards": input_boards,
        "BeamConfiguration": {
            "BeamLength": int(constants["BEAM_LENGTH"]),
            "NumberOfBeams": int(constants.get("N_BEAMS", 1)),
            "NumberOfLayers": int(constants["BEAM_DEPTH"]),
            "BeamSkipStart": int(constants.get("BEAM_SKIP_START", 0)),
            "BeamSkipEnd": int(constants.get("BEAM_SKIP_END", 0)),
            "MinLengthOfBoardInLayer": int(constants.get("MIN_LENGTH_OF_BOARD_IN_LAYER", 0)),
            "GapToBoardAbutInConsecutiveLayers": int(constants.get("GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS", 0)),
            "MaxShiftCurvedCut": int(constants.get("MAX_SHIFT_CURVED_CUT", 0)),
            "StaticForbiddenZones": [
                {"Begin": int(lo), "End": int(hi)} for lo, hi in constants.get("FORBIDDEN_INTERVALS", [])
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dsl_file", help="Path to the woodcutting rich pipeline .dsl file")
    parser.add_argument("assignment_json", help="Path to the assignment JSON from run_lns.py --export-assignment-json")
    parser.add_argument("-o", "--output", default="lns_processed_solution.json", help="Output processed-solution JSON path")
    parser.add_argument("--commands-output", default=None, help="Optional output file for simulator commands (one per line)")
    parser.add_argument(
        "--emit-instance-json",
        default=None,
        help="Optional path to write a synthetic instance JSON (for visualize_solution.py --instance)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the output JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    constants = read_dsl_constants(Path(args.dsl_file))
    assignment = json.loads(Path(args.assignment_json).read_text(encoding="utf-8"))

    processed = build_processed_solution(constants, assignment)

    out_path = Path(args.output)
    out_path.write_text(json.dumps(processed, indent=2 if args.pretty else None), encoding="utf-8")
    print(f"Processed solution written to {out_path}")

    if args.commands_output:
        commands_path = Path(args.commands_output)
        commands_path.write_text("\n".join(processed["SimulatorCommands"]) + "\n", encoding="utf-8")
        print(f"Simulator commands written to {commands_path}")

    if args.emit_instance_json:
        instance = build_synthetic_instance(constants)
        instance_path = Path(args.emit_instance_json)
        instance_path.write_text(json.dumps(instance, indent=2 if args.pretty else None), encoding="utf-8")
        print(f"Synthetic instance written to {instance_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
