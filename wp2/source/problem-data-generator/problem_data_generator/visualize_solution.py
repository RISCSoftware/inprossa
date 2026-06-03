from __future__ import annotations

import argparse
import collections
import colorsys
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        raw = f.read()

    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return json.loads(raw.decode("utf-16"))

    if raw.startswith(b"\xff\xfe\x00\x00") or raw.startswith(b"\x00\x00\xfe\xff"):
        return json.loads(raw.decode("utf-32"))

    return json.loads(raw.decode("utf-8"))


def color_for_board(board_id: int) -> str:
    # Deterministic vivid color per board id.
    hue = ((board_id * 37) % 360) / 360.0
    sat = 0.68
    val = 0.90
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def collect_forbidden_zones(
    processed: dict[str, Any],
    instance: dict[str, Any] | None,
) -> list[tuple[float, float]]:
    zones: list[tuple[float, float]] = []

    cfg_summary = processed.get("ConfigurationSummary", {})
    summary_zones = cfg_summary.get("StaticForbiddenZones", [])
    for z in summary_zones:
        begin = float(z.get("Begin", 0))
        end = float(z.get("End", 0))
        if end > begin:
            zones.append((begin, end))

    if zones:
        return zones

    if instance is None:
        return []

    beam_cfg = instance.get("BeamConfiguration", {})
    for z in beam_cfg.get("StaticForbiddenZones", []):
        begin = float(z.get("Begin", 0))
        end = float(z.get("End", 0))
        if end > begin:
            zones.append((begin, end))
    return zones


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    merged: list[list[float]] = []
    for begin, end in sorted(intervals):
        if end <= begin:
            continue
        if not merged or begin > merged[-1][1]:
            merged.append([begin, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(x[0], x[1]) for x in merged]


def subtract_intervals(
    source: list[tuple[float, float]],
    cutouts: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    if not source:
        return []
    if not cutouts:
        return source

    cutouts_merged = merge_intervals(cutouts)
    result: list[tuple[float, float]] = []
    for s_begin, s_end in source:
        cur = s_begin
        for c_begin, c_end in cutouts_merged:
            if c_end <= cur:
                continue
            if c_begin >= s_end:
                break
            if cur < c_begin:
                result.append((cur, min(c_begin, s_end)))
            cur = max(cur, c_end)
            if cur >= s_end:
                break
        if cur < s_end:
            result.append((cur, s_end))
    return [(a, b) for a, b in result if b > a]


def intersect_intervals(
    left: list[tuple[float, float]],
    right: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    if not left or not right:
        return []
    result: list[tuple[float, float]] = []
    for a0, a1 in left:
        for b0, b1 in right:
            start = max(a0, b0)
            end = min(a1, b1)
            if end > start:
                result.append((start, end))
    return merge_intervals(result)


def build_good_ranges_by_board(instance: dict[str, Any] | None) -> dict[int, list[tuple[float, float]]]:
    if instance is None:
        return {}

    result: dict[int, list[tuple[float, float]]] = {}
    for ib in instance.get("InputBoards", []):
        raw = ib.get("RawBoard", {})
        board_id = int(raw.get("Id", -1))
        parts: list[tuple[float, float]] = []
        for part in raw.get("ScanBoardParts", []):
            if int(part.get("Quality", 0)) != 1:
                continue
            start = float(part.get("StartPosition", 0))
            end = float(part.get("EndPosition", 0))
            if end > start:
                parts.append((start, end))
        result[board_id] = merge_intervals(parts)
    return result


def build_edge_skipped_ranges_by_board(processed: dict[str, Any]) -> dict[int, list[tuple[float, float]]]:
    result: dict[int, list[tuple[float, float]]] = {}
    for item in processed.get("SkippedBoardMargins", []):
        board_id = int(item.get("BoardId", -1))
        intervals: list[tuple[float, float]] = []
        for interval in item.get("Intervals", []):
            start = float(interval.get("Start", 0))
            end = float(interval.get("End", 0))
            if end > start:
                intervals.append((start, end))
        result[board_id] = merge_intervals(intervals)
    return result


def build_discarded_good_ranges_by_board(
    processed: dict[str, Any],
    instance: dict[str, Any] | None,
    edge_skipped_by_board: dict[int, list[tuple[float, float]]] | None = None,
) -> dict[int, list[tuple[float, float]]]:
    if instance is None:
        return {}

    commands = processed.get("SimulatorCommands", [])
    if not isinstance(commands, list) or not commands:
        return {}

    input_boards = list(instance.get("InputBoards", []))
    if not input_boards:
        return {}

    good_ranges_by_board = build_good_ranges_by_board(instance)
    discarded: dict[int, list[tuple[float, float]]] = {}

    scan_index = 0
    scanned: collections.deque[int] = collections.deque()
    reordered: collections.deque[int] = collections.deque()
    board_buffer: int | None = None
    cut_pieces: collections.deque[tuple[int, float, float]] = collections.deque()

    for raw_cmd in commands:
        line = str(raw_cmd).strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0]

        if cmd == "scan":
            if scan_index < len(input_boards):
                scanned.append(scan_index)
                scan_index += 1
            continue

        if cmd == "bgo":
            if scanned:
                reordered.append(scanned.popleft())
            continue

        if cmd == "bout":
            if scanned:
                board_idx = scanned.popleft()
                if board_buffer is not None:
                    reordered.append(board_buffer)
                board_buffer = board_idx
            continue

        if cmd == "bin":
            if not scanned and board_buffer is not None:
                reordered.append(board_buffer)
                board_buffer = None
            continue

        if cmd == "cut":
            cut_pieces.clear()
            if not reordered:
                continue

            board_idx = reordered.popleft()
            raw_board = input_boards[board_idx].get("RawBoard", {})
            board_id = int(raw_board.get("Id", -1))
            board_len = float(raw_board.get("Length", 0))

            cuts: list[float] = []
            for token in parts[1:]:
                try:
                    cut = float(token)
                except ValueError:
                    continue
                if 0 < cut < board_len:
                    cuts.append(cut)
            cuts = sorted(cuts)

            points = [0.0, *cuts, board_len]
            for i in range(len(points) - 1):
                start = points[i]
                end = points[i + 1]
                if end > start:
                    cut_pieces.append((board_id, start, end))
            continue

        if cmd in ("keep", "discard"):
            if not cut_pieces:
                continue
            board_id, start, end = cut_pieces.popleft()
            if cmd == "discard":
                piece = [(start, end)]
                good_in_piece = intersect_intervals(piece, good_ranges_by_board.get(board_id, []))
                if good_in_piece:
                    discarded.setdefault(board_id, []).extend(good_in_piece)
            continue

    merged = {board_id: merge_intervals(ranges) for board_id, ranges in discarded.items()}
    if not edge_skipped_by_board:
        return merged

    filtered: dict[int, list[tuple[float, float]]] = {}
    for board_id, ranges in merged.items():
        filtered[board_id] = subtract_intervals(ranges, edge_skipped_by_board.get(board_id, []))
    return filtered


def build_used_ranges_by_board(
    processed: dict[str, Any],
    beam_index: int | None = None,
) -> dict[int, list[tuple[float, float]]]:
    used: dict[int, list[tuple[float, float]]] = {}
    for beam in processed.get("Beams", []):
        if beam_index is not None and int(beam.get("BeamIndex", -1)) != beam_index:
            continue
        for layer in beam.get("Layers", []):
            for p in layer.get("Placements", []):
                board_id = int(p.get("SourceBoardId", -1))
                s = float(p.get("SourceStart", 0))
                e = float(p.get("SourceEnd", 0))
                if e <= s:
                    continue
                used.setdefault(board_id, []).append((s, e))
    return {bid: merge_intervals(ranges) for bid, ranges in used.items()}


def build_used_pieces_by_board(
    processed: dict[str, Any],
    beam_index: int,
) -> dict[int, list[tuple[float, float]]]:
    pieces: dict[int, list[tuple[float, float]]] = {}
    for beam in processed.get("Beams", []):
        if int(beam.get("BeamIndex", -1)) != beam_index:
            continue
        for layer in beam.get("Layers", []):
            for placement in layer.get("Placements", []):
                board_id = int(placement.get("SourceBoardId", -1))
                source_start = float(placement.get("SourceStart", 0))
                source_end = float(placement.get("SourceEnd", 0))
                if source_end <= source_start:
                    continue
                pieces.setdefault(board_id, []).append((source_start, source_end))
    return pieces


def build_cut_points_by_board(
    processed: dict[str, Any],
    beam_index: int,
) -> dict[int, list[float]]:
    cut_points: dict[int, set[float]] = {}
    for beam in processed.get("Beams", []):
        if int(beam.get("BeamIndex", -1)) != beam_index:
            continue
        for layer in beam.get("Layers", []):
            for placement in layer.get("Placements", []):
                board_id = int(placement.get("SourceBoardId", -1))
                source_start = float(placement.get("SourceStart", 0))
                source_end = float(placement.get("SourceEnd", 0))
                if source_end <= source_start:
                    continue
                cut_points.setdefault(board_id, set()).update((source_start, source_end))
    return {board_id: sorted(points) for board_id, points in cut_points.items()}


def quality_color(quality: int) -> str:
    if quality == 1:
        return "#8fd694"
    if quality == 2:
        return "#ef476f"
    if quality == 3:
        return "#ffd166"
    return "#adb5bd"


def quality_label(quality: int) -> str:
    if quality == 1:
        return "GOOD"
    if quality == 2:
        return "BAD"
    if quality == 3:
        return "CURVE"
    return f"Q{quality}"


def format_link_id(board_id: int, start: float, end: float) -> str:
    # Use fixed precision so IDs are stable across both views.
    return f"b{board_id}-s{start:.3f}-e{end:.3f}"


def compute_instance_summaries(instance: dict[str, Any] | None) -> tuple[int, int, int]:
    if instance is None:
        return (0, 0, 0)

    raw_total = 0
    bad_total = 0
    good_total = 0
    for ib in instance.get("InputBoards", []):
        raw = ib.get("RawBoard", {})
        raw_total += int(raw.get("Length", 0))
        for part in raw.get("ScanBoardParts", []):
            start = int(part.get("StartPosition", 0))
            end = int(part.get("EndPosition", 0))
            length = max(0, end - start)
            q = int(part.get("Quality", 0))
            if q == 1:
                good_total += length
            elif q == 2:
                bad_total += length
    return (raw_total, bad_total, good_total)


def render_html(
    processed: dict[str, Any],
    forbidden_zones: list[tuple[float, float]],
    instance: dict[str, Any] | None,
    title: str,
) -> str:
    cfg = processed.get("ConfigurationSummary", {})
    stats = processed.get("Statistics", {})
    beam_length = float(cfg.get("BeamLength", 1))
    beam_skip_start = float(cfg.get("BeamSkipStart", 0))
    beam_skip_end = float(cfg.get("BeamSkipEnd", 0))
    if beam_length <= 0:
        beam_length = 1.0

    raw_total_fallback, bad_total_fallback, input_good_fallback = compute_instance_summaries(instance)
    raw_total = int(stats.get("InputGoodSeen", 0)) + int(stats.get("InputBadSeen", 0))
    if raw_total <= 0:
        raw_total = raw_total_fallback

    bad_total = int(stats.get("InputBadSeen", 0))
    if bad_total <= 0:
        bad_total = bad_total_fallback

    used_good = int(stats.get("GoodUsed", 0))
    cutout_good = int(stats.get("GoodCutOut", 0))
    skipped_margins_good = int(stats.get("GoodSkippedByBeamMargins", 0))
    remaining_good = int(stats.get("RemainingGood", 0))
    remaining_bad = int(stats.get("RemainingBad", 0))
    if used_good <= 0 and cutout_good <= 0:
        # Fallback estimate if processed statistics are missing.
        used_by_all = build_used_ranges_by_board(processed)
        used_sum = 0
        for ranges in used_by_all.values():
            used_sum += int(sum(max(0.0, b - a) for a, b in ranges))
        input_good = input_good_fallback
        used_good = used_sum
        cutout_good = max(0, input_good - used_sum)

    if remaining_good <= 0 and remaining_bad <= 0 and instance is not None:
        # Fallback when older processed files do not contain remaining fields.
        remaining_good = max(0, input_good_fallback - used_good - cutout_good)
        remaining_bad = max(0, bad_total_fallback - bad_total)

    beams = processed.get("Beams", [])

    margin_left = 80
    margin_right = 20
    margin_top = 20
    margin_bottom = 30
    layer_h = 26
    layer_gap = 10
    board_row_h = 22
    board_gap = 8
    usable_w = 1100
    x_scale = usable_w / beam_length

    source_boards: list[dict[str, Any]] = []
    max_board_length = 1.0
    edge_skipped_by_board = build_edge_skipped_ranges_by_board(processed)
    discarded_good_by_board = build_discarded_good_ranges_by_board(
        processed,
        instance,
        edge_skipped_by_board=edge_skipped_by_board,
    )
    if instance is not None:
        for ib in instance.get("InputBoards", []):
            raw = ib.get("RawBoard", {})
            board_id = int(raw.get("Id", -1))
            board_length = float(raw.get("Length", 0))
            max_board_length = max(max_board_length, board_length)
            parts = []
            for part in raw.get("ScanBoardParts", []):
                parts.append(
                    {
                        "Start": float(part.get("StartPosition", 0)),
                        "End": float(part.get("EndPosition", 0)),
                        "Quality": int(part.get("Quality", 0)),
                    }
                )
            source_boards.append({"BoardId": board_id, "Length": board_length, "Parts": parts})

    board_scale = usable_w / max_board_length
    beam_views: list[str] = []
    beam_heights: dict[int, int] = {}
    max_height = margin_top + margin_bottom + 100

    for beam in beams:
        beam_idx = int(beam.get("BeamIndex", 0))
        layers = beam.get("Layers", [])
        built_layers = len(layers)

        block_h = max(1, built_layers) * (layer_h + layer_gap) - layer_gap
        y0 = margin_top
        y1 = y0 + block_h
        items: list[str] = []
        legend_boards: set[int] = set()

        items.append(
            f'<text x="12" y="{y0 + 16}" font-size="13" font-weight="700" fill="#213547">Beam {beam_idx}</text>'
        )

        for li, layer in enumerate(layers):
            rev = built_layers - 1 - li
            y = y0 + rev * (layer_h + layer_gap)

            items.append(
                f'<rect x="{margin_left}" y="{y}" width="{usable_w}" height="{layer_h}" fill="#f7f8fa" stroke="#c2c9d6" stroke-width="1" rx="4" />'
            )

            for p in layer.get("Placements", []):
                lstart = float(p.get("LayerStart", 0))
                lend = float(p.get("LayerEnd", 0))
                bid = int(p.get("SourceBoardId", -1))
                src_start = float(p.get("SourceStart", 0))
                src_end = float(p.get("SourceEnd", 0))
                px = margin_left + lstart * x_scale
                pw = max(1.0, (lend - lstart) * x_scale)
                link_id = format_link_id(bid, src_start, src_end)
                tooltip = (
                    f"Board {bid} | layer [{int(lstart)}, {int(lend)}] | "
                    f"source [{p.get('SourceStart', '?')}, {p.get('SourceEnd', '?')}]"
                )
                items.append(
                    f'<g><title>{escape_html(tooltip)}</title><rect class="cross-part source-piece" data-board-id="{bid}" data-start="{src_start:.3f}" data-end="{src_end:.3f}" data-link-id="{link_id}" x="{px:.2f}" y="{y + 1}" width="{pw:.2f}" height="{layer_h - 2}" fill="{color_for_board(bid)}" stroke="#152536" stroke-width="0.6" rx="3" /></g>'
                )

            for seam in layer.get("Seams", []):
                sx = margin_left + float(seam) * x_scale
                items.append(
                    f'<line x1="{sx:.2f}" y1="{y - 3}" x2="{sx:.2f}" y2="{y + layer_h + 3}" stroke="#1d3557" stroke-width="1.3" />'
                )

            if beam_skip_start > 0:
                sw0 = min(beam_skip_start, beam_length) * x_scale
                items.append(
                    f'<rect x="{margin_left:.2f}" y="{y}" width="{sw0:.2f}" height="{layer_h}" fill="#495057" fill-opacity="0.24" stroke="#343a40" stroke-opacity="0.40" stroke-width="1" />'
                )
            if beam_skip_end > 0:
                right_begin = max(0.0, beam_length - beam_skip_end)
                sx1 = margin_left + right_begin * x_scale
                sw1 = min(beam_skip_end, beam_length) * x_scale
                items.append(
                    f'<rect x="{sx1:.2f}" y="{y}" width="{sw1:.2f}" height="{layer_h}" fill="#495057" fill-opacity="0.24" stroke="#343a40" stroke-opacity="0.40" stroke-width="1" />'
                )

            for begin, end in forbidden_zones:
                zx = margin_left + begin * x_scale
                zw = max(1.0, (end - begin) * x_scale)
                items.append(
                    f'<rect x="{zx:.2f}" y="{y}" width="{zw:.2f}" height="{layer_h}" fill="#6c757d" fill-opacity="0.32" stroke="#495057" stroke-opacity="0.45" stroke-width="1" />'
                )

            items.append(
                f'<text x="{margin_left - 8}" y="{y + 17}" text-anchor="end" font-size="11" fill="#223">L{layer.get("LayerIndex", li)}</text>'
            )

        axis_y = y1 + 14
        items.append(
            f'<line x1="{margin_left}" y1="{axis_y}" x2="{margin_left + usable_w}" y2="{axis_y}" stroke="#444" stroke-width="1" />'
        )
        tick_step = max(1, int(beam_length // 10))
        for x_pos in range(0, int(beam_length) + 1, tick_step):
            sx = margin_left + x_pos * x_scale
            items.append(
                f'<line x1="{sx:.2f}" y1="{axis_y}" x2="{sx:.2f}" y2="{axis_y + 4}" stroke="#444" stroke-width="1" />'
            )
            items.append(
                f'<text x="{sx:.2f}" y="{axis_y + 16}" text-anchor="middle" font-size="10" fill="#444">{x_pos}</text>'
            )

        board_items: list[str] = []
        board_top = y1 + 44
        board_items.append(
            f'<text x="12" y="{board_top + 15}" font-size="13" font-weight="700" fill="#213547">Input Boards (for Beam {beam_idx})</text>'
        )

        used_pieces_by_board = build_used_pieces_by_board(processed, beam_index=beam_idx)
        used_by_board = {board_id: merge_intervals(pieces) for board_id, pieces in used_pieces_by_board.items()}
        cut_points_by_board = build_cut_points_by_board(processed, beam_index=beam_idx)
        beam_source_boards = [
            board
            for board in source_boards
            if int(board["BoardId"]) in used_by_board
        ]
        board_y0 = board_top + 24
        for i, board in enumerate(beam_source_boards):
            y = board_y0 + i * (board_row_h + board_gap)
            board_id = int(board["BoardId"])
            board_len = float(board["Length"])
            parts = list(board["Parts"])
            used_ranges = merge_intervals(list(used_by_board.get(board_id, [])))
            if used_ranges:
                legend_boards.add(board_id)

            board_items.append(
                f'<rect x="{margin_left}" y="{y}" width="{usable_w}" height="{board_row_h}" fill="#f7f8fa" stroke="#c2c9d6" stroke-width="1" rx="4" />'
            )

            for part in parts:
                p_start = float(part["Start"])
                p_end = float(part["End"])
                q = int(part["Quality"])
                px = margin_left + p_start * board_scale
                pw = max(1.0, (p_end - p_start) * board_scale)
                tt = f"Board {board_id} | {quality_label(q)} [{int(p_start)}, {int(p_end)}]"
                board_items.append(
                    f'<g><title>{escape_html(tt)}</title><rect class="cross-part board-quality" data-board-id="{board_id}" data-start="{p_start:.3f}" data-end="{p_end:.3f}" x="{px:.2f}" y="{y + 1}" width="{pw:.2f}" height="{board_row_h - 2}" fill="{quality_color(q)}" fill-opacity="0.7" stroke="#34495e" stroke-width="0.4" rx="2" /></g>'
                )

            for u_start, u_end in used_pieces_by_board.get(board_id, []):
                ux = margin_left + u_start * board_scale
                uw = max(1.0, (u_end - u_start) * board_scale)
                link_id = format_link_id(board_id, u_start, u_end)
                board_items.append(
                    f'<g><title>{escape_html(f"USED in beam {beam_idx} [{int(u_start)}, {int(u_end)}]")}</title><rect class="cross-part source-piece" data-board-id="{board_id}" data-start="{u_start:.3f}" data-end="{u_end:.3f}" data-link-id="{link_id}" x="{ux:.2f}" y="{y + 4}" width="{uw:.2f}" height="{board_row_h - 8}" fill="{color_for_board(board_id)}" fill-opacity="0.95" stroke="#0f1d2a" stroke-width="0.8" rx="2" /></g>'
                )

            for cut_pos in cut_points_by_board.get(board_id, []):
                if cut_pos <= 0 or cut_pos >= board_len:
                    continue
                cx = margin_left + cut_pos * board_scale
                board_items.append(
                    f'<g><title>{escape_html(f"CUT at {int(cut_pos)}")}</title><line x1="{cx:.2f}" y1="{y - 1}" x2="{cx:.2f}" y2="{y + board_row_h + 1}" stroke="#7a0016" stroke-width="1.1" stroke-dasharray="2 2" /></g>'
                )

            good_parts = [(float(p["Start"]), float(p["End"])) for p in parts if int(p["Quality"]) == 1]
            good_unused = subtract_intervals(good_parts, used_ranges)
            good_unused_non_margin = subtract_intervals(good_unused, edge_skipped_by_board.get(board_id, []))
            for n_start, n_end in good_unused_non_margin:
                nx = margin_left + n_start * board_scale
                nw = max(1.0, (n_end - n_start) * board_scale)
                board_items.append(
                    f'<g><title>{escape_html(f"GOOD but not used in beam {beam_idx} [{int(n_start)}, {int(n_end)}]")}</title><rect x="{nx:.2f}" y="{y + 2}" width="{nw:.2f}" height="{board_row_h - 4}" fill="#495057" fill-opacity="0.30" stroke="#343a40" stroke-opacity="0.4" stroke-width="0.5" rx="2" /></g>'
                )

            for m_start, m_end in edge_skipped_by_board.get(board_id, []):
                mx = margin_left + m_start * board_scale
                mw = max(1.0, (m_end - m_start) * board_scale)
                board_items.append(
                    f'<g><title>{escape_html(f"SKIPPED BY BEAM MARGINS [{int(m_start)}, {int(m_end)}]")}</title><rect x="{mx:.2f}" y="{y + 3}" width="{mw:.2f}" height="{board_row_h - 6}" fill="#1f6feb" fill-opacity="0.23" stroke="#0b3d91" stroke-width="0.8" stroke-dasharray="2 2" rx="2" /></g>'
                )

            for d_start, d_end in discarded_good_by_board.get(board_id, []):
                dx = margin_left + d_start * board_scale
                dw = max(1.0, (d_end - d_start) * board_scale)
                board_items.append(
                    f'<g><title>{escape_html(f"DISCARDED GOOD [{int(d_start)}, {int(d_end)}]")}</title><rect x="{dx:.2f}" y="{y + 5}" width="{dw:.2f}" height="{board_row_h - 10}" fill="#b00020" fill-opacity="0.35" stroke="#7a0016" stroke-width="0.8" stroke-dasharray="3 2" rx="2" /></g>'
                )

            for part in parts:
                q = int(part["Quality"])
                if q not in (2, 3):
                    continue
                c_start = float(part["Start"])
                c_end = float(part["End"])
                cx = margin_left + c_start * board_scale
                cw = max(1.0, (c_end - c_start) * board_scale)
                board_items.append(
                    f'<g><title>{escape_html(f"CUT OUT ({quality_label(q)}) [{int(c_start)}, {int(c_end)}]")}</title><rect x="{cx:.2f}" y="{y + 1}" width="{cw:.2f}" height="{board_row_h - 2}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4 3" rx="2" /></g>'
                )

            board_items.append(
                f'<text x="{margin_left - 8}" y="{y + 15}" text-anchor="end" font-size="11" fill="#223">B{board_id}</text>'
            )
            board_items.append(
                f'<text x="{margin_left + usable_w + 6}" y="{y + 15}" font-size="10" fill="#4a5568">len={int(board_len)}</text>'
            )

        if beam_source_boards:
            board_rows_h = len(beam_source_boards) * (board_row_h + board_gap) - board_gap
            board_axis_y = board_y0 + board_rows_h + 12
            board_items.append(
                f'<line x1="{margin_left}" y1="{board_axis_y}" x2="{margin_left + usable_w}" y2="{board_axis_y}" stroke="#444" stroke-width="1" />'
            )
            tick_step = max(1, int(max_board_length // 10))
            for x_pos in range(0, int(max_board_length) + 1, tick_step):
                sx = margin_left + x_pos * board_scale
                board_items.append(
                    f'<line x1="{sx:.2f}" y1="{board_axis_y}" x2="{sx:.2f}" y2="{board_axis_y + 4}" stroke="#444" stroke-width="1" />'
                )
                board_items.append(
                    f'<text x="{sx:.2f}" y="{board_axis_y + 16}" text-anchor="middle" font-size="10" fill="#444">{x_pos}</text>'
                )
            view_height = int(board_axis_y + 20 + margin_bottom)
        else:
            view_height = int(y1 + margin_bottom)

        legend_items: list[str] = []
        legend_y = view_height - 38
        for i, board_id in enumerate(sorted(legend_boards)):
            lx = margin_left + i * 140
            legend_items.append(
                f'<rect x="{lx}" y="{legend_y - 11}" width="16" height="10" fill="{color_for_board(board_id)}" stroke="#1a2a3a" stroke-width="0.8" rx="2" />'
            )
            legend_items.append(
                f'<text x="{lx + 22}" y="{legend_y - 2}" font-size="11" fill="#223">InputBoard {board_id}</text>'
            )

        beam_views.append(
            f'<g id="beam-view-{beam_idx}" class="beam-view" style="display:none">'
            + "\n".join(items)
            + "\n"
            + "\n".join(board_items)
            + "\n"
            + "\n".join(legend_items)
            + "</g>"
        )
        beam_heights[beam_idx] = view_height
        max_height = max(max_height, view_height)

    width = margin_left + usable_w + margin_right
    first_beam = int(beams[0].get("BeamIndex", 0)) if beams else 0
    options_html = "\n".join(
        f'<option value="{int(beam.get("BeamIndex", 0))}">Beam {int(beam.get("BeamIndex", 0))}</option>'
        for beam in beams
    )
    heights_js = json.dumps({str(k): v for k, v in beam_heights.items()})

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape_html(title)}</title>
  <style>
    :root {{
      --bg: #f4efe8;
      --panel: #fffdf9;
      --text: #1f2937;
      --muted: #54657a;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      color: var(--text);
      background: radial-gradient(circle at 20% 0%, #f2dfc7 0%, var(--bg) 45%, #ebe7e1 100%);
    }}
    .wrap {{
      max-width: 1280px;
      margin: 16px auto 40px;
      padding: 0 12px;
    }}
    .head {{
      background: linear-gradient(135deg, #faf7f2, #fffdf9);
      border: 1px solid #ded7ce;
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 12px;
    }}
    h1 {{
      font-size: 18px;
      margin: 0 0 8px;
      letter-spacing: 0.2px;
    }}
    .meta {{
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      font-size: 13px;
      color: var(--muted);
    }}
        .summary {{
            margin-top: 10px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .summary-card {{
            padding: 8px 10px;
            border-radius: 10px;
            border: 1px solid #ddd6ce;
            background: #fffdf9;
            min-width: 180px;
        }}
        .summary-label {{
            font-size: 11px;
            color: #6b7280;
            margin-bottom: 2px;
        }}
        .summary-value {{
            font-size: 16px;
            font-weight: 700;
            color: #1f2937;
        }}
    .controls {{
      margin-top: 10px;
      font-size: 13px;
      color: var(--muted);
    }}
    .controls select {{
      border: 1px solid #c9d1da;
      border-radius: 8px;
      background: #fff;
      color: #1f2937;
      padding: 5px 10px;
      font-size: 13px;
    }}
        .controls button {{
            border: 1px solid #c9d1da;
            border-radius: 8px;
            background: #fff;
            color: #1f2937;
            padding: 5px 10px;
            font-size: 13px;
            cursor: pointer;
        }}
        .controls button:disabled {{
            cursor: not-allowed;
            opacity: 0.45;
        }}
    .canvas {{
      background: var(--panel);
      border: 1px solid #ded7ce;
      border-radius: 12px;
      overflow-x: auto;
      padding: 10px 0;
    }}
    .hint {{
      margin-top: 8px;
      font-size: 12px;
      color: #5f6f82;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 11px;
      background: #f8d7da;
      color: #8a1c23;
      border: 1px solid #efb0b5;
    }}
        .cross-part {{
            cursor: pointer;
            vector-effect: non-scaling-stroke;
            transition: stroke-width 120ms ease, filter 120ms ease;
        }}
        .cross-part.is-hovered,
        .cross-part.is-locked {{
            stroke: #0b132b;
            stroke-width: 2.6 !important;
            filter: drop-shadow(0 0 1.6px rgba(11, 19, 43, 0.42));
        }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"head\">
      <h1>{escape_html(title)}</h1>
      <div class=\"meta\">
        <div>BeamLength: {int(beam_length)}</div>
        <div>Beams: {len(beams)}</div>
        <div>Forbidden zones: {len(forbidden_zones)}</div>
        <div>BeamSkipStart: {int(beam_skip_start)}</div>
        <div>BeamSkipEnd: {int(beam_skip_end)}</div>
        <div><span class=\"badge\">Gray overlays (foreground) = static forbidden zones</span></div>
        <div><span class=\"badge\">Dark edge overlays = BeamSkipStart/BeamSkipEnd zones</span></div>
        <div><span class=\"badge\">Blue dashed overlays on input boards = good parts skipped by beam margins</span></div>
                <div><span class=\"badge\">Red hatched overlays on input boards = discarded GOOD material</span></div>
      </div>
            <div class=\"summary\">
                <div class=\"summary-card\">
                    <div class=\"summary-label\">Raw Material Total Length</div>
                    <div class=\"summary-value\">{raw_total}</div>
                </div>
                <div class=\"summary-card\">
                    <div class=\"summary-label\">Sum of BAD Parts</div>
                    <div class=\"summary-value\">{bad_total}</div>
                </div>
                <div class=\"summary-card\">
                    <div class=\"summary-label\">Sum of Cut-Out GOOD Parts</div>
                    <div class=\"summary-value\">{cutout_good}</div>
                </div>
                <div class=\"summary-card\">
                    <div class=\"summary-label\">GOOD Skipped by Beam Margins</div>
                    <div class=\"summary-value\">{skipped_margins_good}</div>
                </div>
                <div class=\"summary-card\">
                    <div class=\"summary-label\">Sum of Used GOOD Parts</div>
                    <div class=\"summary-value\">{used_good}</div>
                </div>
                <div class=\"summary-card\">
                    <div class=\"summary-label\">Remaining GOOD Material</div>
                    <div class=\"summary-value\">{remaining_good}</div>
                </div>
                <div class=\"summary-card\">
                    <div class=\"summary-label\">Remaining BAD Material</div>
                    <div class=\"summary-value\">{remaining_bad}</div>
                </div>
            </div>
      <div class=\"controls\">
                <button id=\"prev-beam\" type=\"button\">Previous</button>
        <label for=\"beam-select\">Beam:&nbsp;</label>
        <select id=\"beam-select\">{options_html}</select>
                <button id=\"next-beam\" type=\"button\">Next</button>
      </div>
    </div>
    <div class=\"canvas\">
      <svg id=\"beam-svg\" width=\"{width}\" height=\"{max_height}\" viewBox=\"0 0 {width} {max_height}\" xmlns=\"http://www.w3.org/2000/svg\">
        {'\n'.join(beam_views)}
      </svg>
    </div>
    <div class=\"hint\">Layers are rendered bottom-to-top. Select a beam to view its layers and corresponding source-board usage.</div>
  </div>
  <script>
    (function() {{
      const heights = {heights_js};
      const select = document.getElementById("beam-select");
      const svg = document.getElementById("beam-svg");
            const prevBtn = document.getElementById("prev-beam");
            const nextBtn = document.getElementById("next-beam");
            const beamIds = Array.from(select.options).map((opt) => String(opt.value));
            const EPS = 1e-6;
            const lockedElements = new Set();

            function parseSpan(el) {{
                const boardId = Number(el.dataset.boardId);
                const start = Number(el.dataset.start);
                const end = Number(el.dataset.end);
                if (!Number.isFinite(boardId) || !Number.isFinite(start) || !Number.isFinite(end)) {{
                    return null;
                }}
                return {{ boardId, start, end }};
            }}

            function overlaps(a, b) {{
                return Math.max(a.start, b.start) + EPS < Math.min(a.end, b.end);
            }}

            function clearHovered() {{
                document.querySelectorAll(".cross-part.is-hovered").forEach((el) => {{
                    el.classList.remove("is-hovered");
                }});
            }}

            function clearLocked() {{
                lockedElements.forEach((el) => el.classList.remove("is-locked"));
                lockedElements.clear();
            }}

            function matchingElements(el) {{
                const matches = new Set([el]);
                const span = parseSpan(el);
                const linkId = el.dataset.linkId;

                if (linkId) {{
                    document.querySelectorAll(`.source-piece[data-link-id="${{linkId}}"]`).forEach((m) => matches.add(m));
                }}

                if (!span) {{
                    return matches;
                }}

                document.querySelectorAll(`.cross-part[data-board-id="${{span.boardId}}"]`).forEach((candidate) => {{
                    const cSpan = parseSpan(candidate);
                    if (!cSpan) {{
                        return;
                    }}
                    if (overlaps(span, cSpan)) {{
                        matches.add(candidate);
                    }}
                }});
                return matches;
            }}

            function applyHover(el) {{
                clearHovered();
                matchingElements(el).forEach((m) => m.classList.add("is-hovered"));
            }}

            function lockSelection(el) {{
                const alreadyLocked = el.classList.contains("is-locked");
                clearLocked();
                if (alreadyLocked) {{
                    clearHovered();
                    return;
                }}
                matchingElements(el).forEach((m) => {{
                    m.classList.add("is-locked");
                    lockedElements.add(m);
                }});
            }}

            function wireCrossHighlighting() {{
                document.querySelectorAll(".cross-part").forEach((el) => {{
                    el.addEventListener("mouseenter", () => applyHover(el));
                    el.addEventListener("mouseleave", () => clearHovered());
                    el.addEventListener("click", (ev) => {{
                        ev.stopPropagation();
                        lockSelection(el);
                    }});
                }});

                document.addEventListener("click", () => {{
                    clearLocked();
                    clearHovered();
                }});
            }}

      function showBeam(beamId) {{
        document.querySelectorAll(".beam-view").forEach((el) => {{
          el.style.display = "none";
        }});
        const target = document.getElementById(`beam-view-${{beamId}}`);
        if (target) {{
          target.style.display = "inline";
        }}
        const h = heights[String(beamId)] || {max_height};
        svg.setAttribute("height", String(h));
        svg.setAttribute("viewBox", `0 0 {width} ${{h}}`);

                const idx = beamIds.indexOf(String(beamId));
                if (prevBtn) {{
                    prevBtn.disabled = idx <= 0;
                }}
                if (nextBtn) {{
                    nextBtn.disabled = idx < 0 || idx >= beamIds.length - 1;
                }}
      }}

            function stepBeam(step) {{
                const idx = beamIds.indexOf(String(select.value));
                if (idx < 0) {{
                    return;
                }}
                const nextIdx = idx + step;
                if (nextIdx < 0 || nextIdx >= beamIds.length) {{
                    return;
                }}
                select.value = beamIds[nextIdx];
                showBeam(select.value);
            }}

      if (select) {{
        select.addEventListener("change", (ev) => showBeam(ev.target.value));
                if (prevBtn) {{
                    prevBtn.addEventListener("click", () => stepBeam(-1));
                }}
                if (nextBtn) {{
                    nextBtn.addEventListener("click", () => stepBeam(1));
                }}
        select.value = "{first_beam}";
        showBeam(String(select.value));
                                wireCrossHighlighting();
      }}
    }})();
  </script>
</body>
</html>
"""
    return html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize processed woodcutting layers as a simple HTML/SVG view."
    )
    parser.add_argument("processed", help="Path to processed JSON (output of process_instance.py).")
    parser.add_argument(
        "--instance",
        default=None,
        help="Optional original problem instance JSON (used for forbidden zones if missing in processed JSON).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="woodcutting_visualization.html",
        help="Output HTML file path.",
    )
    parser.add_argument("--title", default="Woodcutting Layer Visualization", help="Page title.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_path = Path(args.processed)
    processed = load_json(processed_path)

    instance = None
    if args.instance:
        instance = load_json(Path(args.instance))

    forbidden = collect_forbidden_zones(processed, instance)
    html = render_html(processed, forbidden, instance, args.title)

    out_path = Path(args.output)
    out_path.write_text(html, encoding="utf-8")
    print(f"Visualization written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
