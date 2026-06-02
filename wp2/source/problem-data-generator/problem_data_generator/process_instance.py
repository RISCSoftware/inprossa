from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from models.WoodCutting import WoodCutting


@dataclass
class Piece:
    board_id: int
    board_position: int
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


class PieceStream:
    def __init__(self, problem: WoodCutting):
        self.problem = problem
        self.index = 0
        self.queue: list[Piece] = []
        self.good_cut_out = 0
        self.bad_cut_out = 0
        self.good_input_seen = 0
        self.bad_input_seen = 0

    def _board_material_totals(self, input_board_index: int) -> tuple[int, int]:
        board = self.problem.InputBoards[input_board_index].RawBoard
        good = 0
        bad = 0
        for part in board.ScanBoardParts:
            length = max(0, part.EndPosition - part.StartPosition)
            q = part.Quality.value
            if q == 1:
                good += length
            elif q == 2:
                bad += length
        return (good, bad)

    def remaining_material(self) -> tuple[int, int]:
        # Remaining GOOD in queue comes from already processed boards and should not be counted as cut-out.
        remaining_good = sum(piece.length for piece in self.queue)
        remaining_bad = 0

        # Add all material from not-yet-processed boards.
        for board_idx in range(self.index, len(self.problem.InputBoards)):
            board_good, board_bad = self._board_material_totals(board_idx)
            remaining_good += board_good
            remaining_bad += board_bad

        return (remaining_good, remaining_bad)

    def _merge_intervals(self, intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if not intervals:
            return []
        merged: list[list[int]] = []
        for begin, end in sorted(intervals):
            if begin >= end:
                continue
            if not merged or begin > merged[-1][1]:
                merged.append([begin, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        return [(x[0], x[1]) for x in merged]

    def _subtract_intervals(
        self, source: list[tuple[int, int]], forbidden: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        if not source:
            return []
        if not forbidden:
            return source

        result: list[tuple[int, int]] = []
        merged_forbidden = self._merge_intervals(forbidden)
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

    def _load_next_board(self, min_len: int, max_shift_curved: int) -> bool:
        if self.index >= len(self.problem.InputBoards):
            return False

        input_board = self.problem.InputBoards[self.index]
        self.index += 1

        raw = input_board.RawBoard
        good_intervals: list[tuple[int, int]] = []
        curved_forbidden: list[tuple[int, int]] = []

        for part in raw.ScanBoardParts:
            length = part.EndPosition - part.StartPosition
            q = part.Quality.value
            if q == 1:
                good_intervals.append((part.StartPosition, part.EndPosition))
                self.good_input_seen += length
            elif q == 2:
                self.bad_cut_out += length
                self.bad_input_seen += length
            elif q == 3:
                # CURVE sections are removed with a safety margin where cuts may shift.
                left = max(0, part.StartPosition - max_shift_curved)
                right = min(raw.Length, part.EndPosition + max_shift_curved)
                curved_forbidden.append((left, right))
            else:
                # Unknown quality is treated as unusable material.
                self.good_cut_out += length

        usable = self._subtract_intervals(good_intervals, curved_forbidden)
        usable_filtered: list[tuple[int, int]] = []
        for begin, end in usable:
            seg_len = end - begin
            if seg_len >= min_len:
                usable_filtered.append((begin, end))
            else:
                self.good_cut_out += seg_len

        # Track GOOD material lost by cutting around curved sections.
        good_before = sum(end - begin for begin, end in good_intervals)
        good_after = sum(end - begin for begin, end in usable)
        if good_before > good_after:
            self.good_cut_out += good_before - good_after

        for begin, end in usable_filtered:
            self.queue.append(
                Piece(
                    board_id=raw.Id,
                    board_position=input_board.Position,
                    start=begin,
                    end=end,
                )
            )

        return True

    def pop_next_piece(self, min_len: int, max_shift_curved: int) -> Piece | None:
        while not self.queue:
            if not self._load_next_board(min_len=min_len, max_shift_curved=max_shift_curved):
                return None
        return self.queue[0]

    def consume_front(self, used_len: int) -> None:
        piece = self.queue[0]
        if used_len >= piece.length:
            self.queue.pop(0)
            return
        self.queue[0] = Piece(
            board_id=piece.board_id,
            board_position=piece.board_position,
            start=piece.start + used_len,
            end=piece.end,
        )

    def discard_front(self) -> None:
        piece = self.queue.pop(0)
        self.good_cut_out += piece.length

    def discard_all_remaining(self) -> None:
        for piece in self.queue:
            self.good_cut_out += piece.length
        self.queue.clear()


def seam_in_forbidden_zones(seam_pos: int, static_forbidden: list[tuple[int, int]]) -> bool:
    for begin, end in static_forbidden:
        if begin <= seam_pos <= end:
            return True
    return False


def seam_is_valid(
    seam_pos: int,
    beam_length: int,
    skip_start: int,
    skip_end: int,
    static_forbidden: list[tuple[int, int]],
    previous_layer_seams: list[int],
    seam_gap: int,
) -> bool:
    if seam_pos <= skip_start:
        return False
    if seam_pos >= beam_length - skip_end:
        return False
    if seam_in_forbidden_zones(seam_pos, static_forbidden):
        return False
    for prev in previous_layer_seams:
        if abs(prev - seam_pos) < seam_gap:
            return False
    return True


def choose_non_final_cut_length(
    filled: int,
    remaining: int,
    piece_length: int,
    min_len: int,
    beam_length: int,
    skip_start: int,
    skip_end: int,
    static_forbidden: list[tuple[int, int]],
    previous_layer_seams: list[int],
    seam_gap: int,
) -> int | None:
    max_take = min(piece_length, remaining - min_len)
    if max_take < min_len:
        return None

    for take in range(max_take, min_len - 1, -1):
        seam_pos = filled + take
        if seam_is_valid(
            seam_pos=seam_pos,
            beam_length=beam_length,
            skip_start=skip_start,
            skip_end=skip_end,
            static_forbidden=static_forbidden,
            previous_layer_seams=previous_layer_seams,
            seam_gap=seam_gap,
        ):
            return take
    return None


def build_solution(problem: WoodCutting) -> dict[str, Any]:
    cfg = problem.BeamConfiguration

    beam_length = cfg.BeamLength
    num_beams = cfg.NumberOfBeams
    num_layers = cfg.NumberOfLayers
    min_len = cfg.MinLengthOfBoardInLayer
    skip_start = cfg.BeamSkipStart
    skip_end = cfg.BeamSkipEnd
    seam_gap = cfg.GapToBoardAbutInConsecutiveLayers
    max_shift_curved = cfg.MaxShiftCurvedCut
    static_forbidden = [(z.Begin, z.End) for z in cfg.StaticForbiddenZones]

    stream = PieceStream(problem)

    beams_output: list[dict[str, Any]] = []
    fully_built_layers = 0
    failed_layers: list[dict[str, Any]] = []
    used_good = 0

    for beam_idx in range(num_beams):
        beam_layers: list[dict[str, Any]] = []
        prev_seams: list[int] = []
        for layer_idx in range(num_layers):
            filled = 0
            placements: list[dict[str, Any]] = []
            seams: list[int] = []

            while filled < beam_length:
                remaining = beam_length - filled
                piece = stream.pop_next_piece(min_len=min_len, max_shift_curved=max_shift_curved)
                if piece is None:
                    failed_layers.append(
                        {
                            "BeamIndex": beam_idx,
                            "LayerIndex": layer_idx,
                            "Reason": "No more usable board pieces available",
                            "FilledLength": filled,
                            "TargetLength": beam_length,
                        }
                    )
                    break

                if piece.length < min_len:
                    stream.discard_front()
                    continue

                if piece.length >= remaining:
                    # Final segment in layer, no seam created at beam end.
                    take = remaining
                    if take < min_len and filled > 0:
                        take = None
                    if take is None:
                        stream.discard_front()
                        continue

                    placements.append(
                        {
                            "LayerStart": filled,
                            "LayerEnd": filled + take,
                            "Length": take,
                            "SourceBoardId": piece.board_id,
                            "SourceBoardPosition": piece.board_position,
                            "SourceStart": piece.start,
                            "SourceEnd": piece.start + take,
                        }
                    )
                    used_good += take
                    if take < piece.length:
                        stream.good_cut_out += piece.length - take
                    stream.consume_front(take)
                    filled += take
                    break

                take = choose_non_final_cut_length(
                    filled=filled,
                    remaining=remaining,
                    piece_length=piece.length,
                    min_len=min_len,
                    beam_length=beam_length,
                    skip_start=skip_start,
                    skip_end=skip_end,
                    static_forbidden=static_forbidden,
                    previous_layer_seams=prev_seams,
                    seam_gap=seam_gap,
                )

                if take is None:
                    # This piece cannot produce a valid seam in this layer.
                    stream.discard_front()
                    continue

                seam_pos = filled + take
                placements.append(
                    {
                        "LayerStart": filled,
                        "LayerEnd": seam_pos,
                        "Length": take,
                        "SourceBoardId": piece.board_id,
                        "SourceBoardPosition": piece.board_position,
                        "SourceStart": piece.start,
                        "SourceEnd": piece.start + take,
                    }
                )
                used_good += take
                seams.append(seam_pos)
                stream.consume_front(take)
                filled = seam_pos

            if filled == beam_length:
                fully_built_layers += 1
                layer_item = {
                    "BeamIndex": beam_idx,
                    "LayerIndex": layer_idx,
                    "Length": beam_length,
                    "Seams": seams,
                    "Placements": placements,
                }
                beam_layers.append(layer_item)
                prev_seams = seams
            else:
                # Stop building remaining layers for this beam after a failure.
                break

        beams_output.append(
            {
                "BeamIndex": beam_idx,
                "BuiltLayers": len(beam_layers),
                "TargetLayers": num_layers,
                "Layers": beam_layers,
            }
        )

    remaining_good, remaining_bad = stream.remaining_material()
    good_cut_out = max(0, stream.good_input_seen - used_good - remaining_good)

    stats = {
        "RequiredLayers": num_beams * num_layers,
        "BuiltLayers": fully_built_layers,
        "BoardsProcessed": stream.index,
        "InputGoodSeen": stream.good_input_seen,
        "InputBadSeen": stream.bad_input_seen,
        "GoodCutOut": good_cut_out,
        "BadCutOut": stream.bad_cut_out,
        "GoodUsed": used_good,
        "RemainingGood": remaining_good,
        "RemainingBad": remaining_bad,
    }

    return {
        "Status": "ok" if not failed_layers else "partial",
        "ConfigurationSummary": {
            "BeamLength": beam_length,
            "NumberOfBeams": num_beams,
            "NumberOfLayers": num_layers,
            "MinLengthOfBoardInLayer": min_len,
            "BeamSkipStart": skip_start,
            "BeamSkipEnd": skip_end,
            "GapToBoardAbutInConsecutiveLayers": seam_gap,
            "MaxShiftCurvedCut": max_shift_curved,
        },
        "Statistics": stats,
        "Beams": beams_output,
        "FailedLayers": failed_layers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Process a woodcutting instance JSON and build beam layers from sequential input boards."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input JSON file path. If omitted or '-', JSON is read from stdin.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output file for the result JSON (default: stdout).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print output JSON.",
    )
    return parser.parse_args()


def read_input_text(input_arg: str | None) -> str:
    if input_arg is None or input_arg == "-":
        return sys.stdin.read()
    with open(input_arg, "rt", encoding="utf-8") as handle:
        return handle.read()


def main() -> int:
    args = parse_args()
    try:
        raw = read_input_text(args.input)
        payload = json.loads(raw)
        problem = WoodCutting.model_validate(payload)
        result = build_solution(problem)
    except (json.JSONDecodeError, ValidationError, OSError, ValueError) as exc:  # pragma: no cover - CLI error path
        print(json.dumps({"Status": "error", "Message": str(exc)}, indent=2), file=sys.stderr)
        return 1

    output_text = json.dumps(result, indent=2 if args.pretty else None)
    if args.output:
        with open(args.output, "wt", encoding="utf-8") as handle:
            handle.write(output_text)
            handle.write("\n")
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
