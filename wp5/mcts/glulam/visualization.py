"""Step visualization for the glulam env (matplotlib).

``render(ax, state, cfg, layout, viz, title)`` draws one frame with five
regions, left to right, per the spec's Episode-visualization section:

1. hidden-pieces stack (one row per hidden board, bottom = leftmost board),
2. observable pieces except the one at the saw (vertical stack, top = nearest the saw),
3. saw / out_pos / buf_pos slots (fixed anchors, bottom to top, label under each),
4. assembled beams (a pile resting on the region baseline: oldest shown beam at
   the bottom, newer ones above it, the current unfinished beam on top;
   controlled by VIZ_NUM_FINISHED_BEAMS),
5. discarded pieces (greedy-packed rows, bottom-up; optional, VIZ_SHOW_DISCARDED).

Colors are derived here (the env stores none): ``palette[piece_id % NUM_COLORS]``,
every segment with a black outline. ``compute_layout`` is called once per episode and
its result reused for every frame, so animations do not rescale as the queue drains;
pass it the rollout's states to size the frame to what that episode actually reaches
instead of to the (much looser) worst case derivable from the config alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import matplotlib.axes
from matplotlib import colormaps
from matplotlib.colors import to_hex
from matplotlib.patches import Rectangle

from mcts.glulam.env import (
    EnvConfig,
    GlulamState,
    Piece,
    hidden_boards,
    observable_boards,
    prev_meet_positions,
)


def _default_palette() -> tuple[str, ...]:
    cmap = colormaps["tab20"]
    return tuple(to_hex(cmap(i)) for i in range(20))


@dataclass(frozen=True)
class VizConfig:
    NUM_COLORS: int = 20
    palette: tuple[str, ...] = field(default_factory=_default_palette)
    VIZ_NUM_FINISHED_BEAMS: int | None = None  # None = all, 0 = current only, n = current + n finished
    VIZ_SHOW_FORBIDDEN: bool = True  # overlay global and local forbidden intervals on the beam
    VIZ_SHOW_DISCARDED: bool = True  # draw region 5 at all; when False it reserves no space
    VIZ_DISCARD_ROW_WIDTH: int | None = None  # row width of the discard pile; None = MAX_BOARD_LEN
    label_fontsize: float = 10.5  # region labels
    title_fontsize: float = 12.0  # frame title
    global_forbidden_color: str = "#e6194B"  # translucent fill + solid left/right borders
    local_forbidden_color: str = "#329EA8"

    def color(self, piece: Piece) -> str:
        return self.palette[piece.piece_id % self.NUM_COLORS]

    def discard_row_width(self, cfg: EnvConfig) -> int:
        """Row width at which the discard pile wraps, in wood-length units.

        Defaults to ``MAX_BOARD_LEN`` (the widest possible hidden-stack row), which also
        keeps the reserved row count bounded: greedy packing closes a row only once its
        fill exceeds ``row_width - MAX_PIECE_LEN``, so a row width equal to
        ``MAX_PIECE_LEN`` would degenerate to one piece per row.
        """
        return cfg.MAX_BOARD_LEN if self.VIZ_DISCARD_ROW_WIDTH is None else self.VIZ_DISCARD_ROW_WIDTH


@dataclass(frozen=True)
class RegionBox:
    """Padded bounding box for one visualization region.

    ``content_x`` / ``content_y`` is the bottom-left corner of the *content* area
    (inside the padding). ``content_w`` / ``content_h`` is the tight content size.
    ``pad_x`` / ``pad_y`` is the padding left/right and below/above the content, so the
    full box spans ``(content_x - pad_x, content_y - pad_y)`` to
    ``(content_x + content_w + pad_x, content_y + content_h + pad_y)``.
    """

    content_x: float
    content_y: float
    content_w: float
    content_h: float
    pad_x: float
    pad_y: float

    @property
    def left(self) -> float:
        return self.content_x - self.pad_x

    @property
    def right(self) -> float:
        return self.content_x + self.content_w + self.pad_x

    @property
    def bottom(self) -> float:
        return self.content_y - self.pad_y

    @property
    def top(self) -> float:
        return self.content_y + self.content_h + self.pad_y

    @property
    def width(self) -> float:
        return self.content_w + 2 * self.pad_x

    @property
    def height(self) -> float:
        return self.content_h + 2 * self.pad_y


def _saw_piece(state: GlulamState) -> Piece | None:
    """The piece at the saw position (``queue[-1][-1]``), or None if the queue is empty."""
    return state.queue[-1][-1] if state.queue and state.queue[-1] else None


def _observable_without_saw(state: GlulamState, cfg: EnvConfig) -> list[Piece]:
    """Observable-window pieces, left to right, minus the one at the saw.

    The saw piece is the rightmost of the window; region 3 draws it as its bottom slot, so
    region 2 leaves it out to avoid drawing the same piece twice. This is a drawing split
    only — the ``observable_pieces`` observation still includes the saw piece.
    """
    obs = [p for board in observable_boards(state, cfg) for p in board]
    return obs[:-1]


def _discard_placements(pieces: Sequence[Piece], row_width: int, cfg: EnvConfig) -> list[tuple[int, float, float]]:
    """Greedy row packing of the discard pile: one ``(row, x_offset, width)`` per piece.

    Pieces are packed in discard order (oldest first), left to right; a piece that would
    push the row past ``row_width`` starts a new row above instead. Row 0 is the bottom row.
    Shared by the layout (row count) and the drawing code so the two cannot drift apart.
    """
    out: list[tuple[int, float, float]] = []
    row, x = 0, 0.0
    for piece in pieces:
        w = float(min(piece.length, cfg.MAX_PIECE_LEN))
        if x + w > row_width + 0.01 and x > 0:  # wrap (a lone oversized piece keeps its row)
            row += 1
            x = 0.0
        out.append((row, x, w))
        x += w
    return out


@dataclass(frozen=True)
class Layout:
    """Fixed axes geometry, computed once per episode and reused for every frame."""

    seg_h: float  # segment height (wood-length units; aspect is equal)
    stack_vspace: float  # vertical gap between rows in regions 1, 2, 5
    beam_vspace: float  # vertical gap between beams in region 4
    slot_vspace: float  # vertical gap between the three slots in region 3 (holds their labels)
    pad_factor_x: float  # left/right padding = pad_factor_x * min(content_w, content_h) per region
    pad_factor_y: float  # below/above padding, same base but a smaller factor
    boxes: dict[str, RegionBox]  # per-region padded bounding boxes
    y_saw: float  # region 3 slot baselines, bottom to top
    y_out: float
    y_buf: float
    beam_height: float  # total height of the beam region (content)
    xlim: tuple[float, float]
    ylim: tuple[float, float]

    def box(self, name: str) -> RegionBox:
        return self.boxes[name]


def compute_layout(
    initial_state: GlulamState,
    cfg: EnvConfig,
    viz: VizConfig,
    states: Sequence[GlulamState] | None = None,
) -> Layout:
    """Compute the fixed axes geometry for one episode.

    Without ``states`` every region is sized from ``initial_state`` and ``cfg`` alone, using
    worst-case bounds (all of the input wasted, every beam finished). Those bounds are safe but
    loose, so most frames end up with a large empty band above the piles. Passing the rollout's
    ``states`` sizes the regions to what the episode actually reaches instead — still one fixed
    ``xlim`` / ``ylim`` for every frame, so the animation does not rescale.
    """
    # Segment height. Tied to MAX_PIECE_LEN, not LAYER_LEN, so that a piece keeps its drawn
    # aspect ratio across configs and a longer layer draws a *longer* beam rather than a
    # uniformly scaled-up frame (with LAYER_LEN the vertical stacks grew with it and the frame
    # turned portrait, which shrank everything again).
    h = max(1.0, cfg.MAX_PIECE_LEN / 12.5)
    stack_vspace = 0.8 * h  # regions 1, 2, 5
    beam_vspace = 1.6 * h  # region 4
    # Region 3's slots are spaced much wider than the other stacks because each slot's label is
    # drawn in the gap below it; the gap has to clear a line of text, not just separate segments.
    slot_vspace = 3.5 * h
    # Padding = factor * min(content_w, content_h), floored at one segment height. The horizontal
    # factor is what spaces the regions apart, so it is the larger of the two; the vertical one only
    # adds headroom above and below the content, which needs less.
    pad_factor_x = 0.3
    pad_factor_y = 0.15

    boards = [[p.length for p in board] for board in initial_state.queue]
    n_boards = len(boards)

    # --- Tight content sizes per region ---
    # Region 1: hidden stack — width = max board length, height = n_hidden rows.
    stack_content_w = max((sum(b) for b in boards), default=0)
    n_hidden_rows = max(0, n_boards - cfg.OBSERVABLE_BOARDS)
    stack_content_h = n_hidden_rows * (h + stack_vspace) - stack_vspace if n_hidden_rows else 0.0

    # Region 2: observable vertical stack — width = MAX_PIECE_LEN, worst-case piece count. The
    # piece at the saw belongs to region 3, so it is not counted here.
    # Without a rollout: the queue is fixed in advance, so the exact bound is the largest piece
    # count over all sliding windows of OBSERVABLE_BOARDS consecutive boards (cuts only ever
    # shorten the piece at the saw, so no window can hold more pieces than it starts with). That
    # is already far tighter than the config-only OBSERVABLE_BOARDS * (MAX_BOARD_LEN //
    # MIN_PIECE_LEN). With a rollout: the largest window the episode actually shows.
    obs_content_w = float(cfg.MAX_PIECE_LEN)
    if states is not None:
        max_obs_pieces = max((len(_observable_without_saw(s, cfg)) for s in states), default=0)
    else:
        k = cfg.OBSERVABLE_BOARDS
        max_obs_pieces = max(
            (sum(len(b) for b in boards[i : i + k]) - 1 for i in range(max(1, n_boards - k + 1))),
            default=0,
        )
    max_obs_pieces = max(0, max_obs_pieces)
    obs_content_h = max_obs_pieces * (h + stack_vspace) - stack_vspace if max_obs_pieces else 0.0

    # Region 3: saw / out / buf slots — width = MAX_PIECE_LEN, height = 3 slots.
    slot_content_w = float(cfg.MAX_PIECE_LEN)
    slot_content_h = 3 * (h + slot_vspace) - slot_vspace  # three slots with two gaps

    # Region 4: beams — width = LAYER_LEN, height = (1 + n_finished shown) beam pitches. Without a
    # rollout the beam count is bounded by the total input length; with one it is what the episode
    # reaches. Either way VIZ_NUM_FINISHED_BEAMS caps how many are ever drawn.
    if states is not None:
        n_finished_total = max((len(s.finished_beams) for s in states), default=0)
    else:
        n_finished_total = cfg.INI_BOARDS * cfg.MAX_BOARD_LEN // (cfg.NUM_LAYERS * cfg.LAYER_LEN)
    n_finished_shown = (
        n_finished_total if viz.VIZ_NUM_FINISHED_BEAMS is None else min(viz.VIZ_NUM_FINISHED_BEAMS, n_finished_total)
    )
    beam_content_w = float(cfg.LAYER_LEN)
    beam_content_h = (1 + n_finished_shown) * (cfg.NUM_LAYERS * h + beam_vspace) - beam_vspace

    # Region 5: discarded pile — width = VIZ_DISCARD_ROW_WIDTH, row count of the fullest pile.
    # Without a rollout: greedy packing closes a row only once its fill exceeds
    # row_width - MAX_PIECE_LEN, so every closed row holds at least
    # (row_width - MAX_PIECE_LEN + 1) units, giving the bound below from the total input length.
    # It degenerates to one piece per row if row_width == MAX_PIECE_LEN — hence the MAX_BOARD_LEN
    # default. With a rollout: the pile only ever grows and the packing is a prefix of itself, so
    # packing the largest pile gives the exact row count.
    discard_row_width = viz.discard_row_width(cfg)
    discard_content_w = float(discard_row_width)
    if states is not None:
        fullest = max((s.discarded_pieces for s in states), key=len, default=())
        placements = _discard_placements(fullest, discard_row_width, cfg)
        max_discard_rows = max(1, 1 + max((row for row, _, _ in placements), default=0))
    else:
        total_input_len = sum(sum(b) for b in boards)
        max_discard_rows = max(1, 1 + total_input_len // max(1, discard_row_width - cfg.MAX_PIECE_LEN + 1))
    discard_content_h = max_discard_rows * (h + stack_vspace) - stack_vspace

    # --- Place regions left to right, using padded boxes for spacing ---
    # All content rests on y = 0 (bottom-aligned). Regions are placed so that
    # the padded boxes tile the x-axis without overlap.
    def _pad(cw: float, ch: float) -> tuple[float, float]:
        # A region that is one segment tall (or empty, like the hidden stack of a config
        # with no hidden boards) still needs a gap to its neighbours, hence the h floor.
        base = min(max(cw, h), max(ch, h))
        return pad_factor_x * base, pad_factor_y * base

    # Place content areas: content_x = x_cursor + pad, then advance by full box width.
    specs = [
        ("hidden", stack_content_w, stack_content_h),
        ("observable", obs_content_w, obs_content_h),
        ("slots", slot_content_w, slot_content_h),
        ("beams", beam_content_w, beam_content_h),
    ]
    if viz.VIZ_SHOW_DISCARDED:  # when off, region 5 reserves no width and no height
        specs.append(("discarded", discard_content_w, discard_content_h))
    boxes: dict[str, RegionBox] = {}
    x = 0.0
    for name, cw, ch in specs:
        pad_x, pad_y = _pad(cw, ch)
        boxes[name] = RegionBox(x + pad_x, 0.0, cw, ch, pad_x, pad_y)
        x += cw + 2 * pad_x

    # Region 3 slot baselines, bottom to top: saw on the baseline, then out, then buf.
    slot_pitch = h + slot_vspace
    y_saw = 0.0
    y_out = slot_pitch
    y_buf = 2 * slot_pitch

    # Overall height: tallest padded box, plus headroom for labels.
    max_h = max(b.height for b in boxes.values())
    min_x = min(b.left for b in boxes.values())
    max_x = max(b.right for b in boxes.values())

    return Layout(
        seg_h=h,
        stack_vspace=stack_vspace,
        beam_vspace=beam_vspace,
        slot_vspace=slot_vspace,
        pad_factor_x=pad_factor_x,
        pad_factor_y=pad_factor_y,
        boxes=boxes,
        y_saw=y_saw,
        y_out=y_out,
        y_buf=y_buf,
        beam_height=beam_content_h,
        xlim=(min_x - h, max_x + h),
        ylim=(-4.5 * h, max_h + h),
    )


def _segment(ax, x: float, y: float, piece: Piece, h: float, viz: VizConfig) -> None:
    ax.add_patch(Rectangle((x, y), piece.length, h, facecolor=viz.color(piece), edgecolor="black", linewidth=0.8))


def _forbidden_rect(
    ax: matplotlib.axes.Axes,
    x_left: float,
    y_bottom: float,
    width: float,
    height: float,
    color: str,
    h: float,
) -> None:
    """Draw a translucent forbidden-interval rectangle with solid left/right borders only.

    No top/bottom border. The fill is translucent (alpha = 0.2); the left and right
    border lines are the same color at full opacity.
    """
    ax.add_patch(
        Rectangle(
            (x_left, y_bottom),
            width,
            height,
            facecolor=color,
            alpha=0.2,
            edgecolor="none",
            linewidth=0,
        )
    )
    # Solid left and right border lines (no top/bottom).
    ax.plot(
        [x_left, x_left],
        [y_bottom, y_bottom + height],
        color=color,
        linewidth=1.0,
        alpha=1.0,
    )
    ax.plot(
        [x_left + width, x_left + width],
        [y_bottom, y_bottom + height],
        color=color,
        linewidth=1.0,
        alpha=1.0,
    )


def _draw_forbidden_overlays(
    ax: matplotlib.axes.Axes,
    state: GlulamState,
    cfg: EnvConfig,
    layout: Layout,
    viz: VizConfig,
    beam_y: float,
) -> None:
    """Overlay global and local forbidden intervals on the current beam.

    - **Global** (`FORBIDDEN_INTERVALS`): translucent rectangles spanning all nonempty
      layers of the current beam, with solid left/right border lines in the same color.
    - **Local** (from `prev_meet_positions`): translucent rectangles in a different color,
      covering only the previous layer and the current layer, with solid left/right borders.
      Drawn only when ``current_layer > 0``.
    """
    h = layout.seg_h
    x0 = layout.box("beams").content_x

    # Determine which layers are nonempty (have at least one piece).
    nonempty = [i for i, layer in enumerate(state.beam) if len(layer) > 0]
    if not nonempty:
        return
    y_top = beam_y + (max(nonempty) + 1) * h
    y_bottom = beam_y

    # Global forbidden intervals: span all nonempty layers.
    for s, e in cfg.FORBIDDEN_INTERVALS:
        _forbidden_rect(ax, x0 + s, y_bottom, e - s, y_top - y_bottom, viz.global_forbidden_color, h)

    # Local forbidden intervals: from prev layer meeting positions.
    # Cover only the previous layer and the current layer.
    if state.current_layer > 0:
        prev_meets = prev_meet_positions(state, cfg)
        half = cfg.PREV_MEET_FORBIDDEN_HALF
        if half > 0 and prev_meets:
            y_local_bottom = beam_y + (state.current_layer - 1) * h
            y_local_top = beam_y + (state.current_layer + 1) * h
            for p in prev_meets:
                left = max(0, p - half)
                right = min(cfg.LAYER_LEN, p + half)
                if right > left:
                    _forbidden_rect(
                        ax,
                        x0 + left,
                        y_local_bottom,
                        right - left,
                        y_local_top - y_local_bottom,
                        viz.local_forbidden_color,
                        h,
                    )


def _draw_discarded_pile(
    ax: matplotlib.axes.Axes,
    state: GlulamState,
    cfg: EnvConfig,
    layout: Layout,
    viz: VizConfig,
    x0: float,
    row_width: int,
) -> None:
    """Draw the discarded-pieces pile as greedy-packed rows, bottom-up.

    Pieces are laid out in discard order (oldest first), left to right within a row.
    A row wraps when the next piece would exceed ``row_width``. First row at the
    bottom, pile grows upward. Row pitch = h + stack_vspace.
    """
    h = layout.seg_h
    row_pitch = h + layout.stack_vspace
    placements = _discard_placements(state.discarded_pieces, row_width, cfg)
    for piece, (row, dx, w) in zip(state.discarded_pieces, placements):
        ax.add_patch(
            Rectangle(
                (x0 + dx, row * row_pitch),
                w,
                h,
                facecolor=viz.color(piece),
                edgecolor="black",
                linewidth=0.8,
            )
        )


def render(
    ax: matplotlib.axes.Axes,
    state: GlulamState,
    cfg: EnvConfig,
    layout: Layout,
    viz: VizConfig,
    title: str | None = None,
) -> None:
    """Draw one episode frame into ax using the fixed layout."""
    h = layout.seg_h
    sv = layout.stack_vspace  # vertical gap for regions 1, 2, 5

    b1 = layout.box("hidden")
    b2 = layout.box("observable")
    b3 = layout.box("slots")
    b4 = layout.box("beams")
    b5 = layout.box("discarded") if viz.VIZ_SHOW_DISCARDED else None

    # 1. Hidden-pieces stack: bottom row = leftmost board, top row = rightmost.
    #    Row pitch = h + sv.
    hidden = hidden_boards(state, cfg)
    for row, board in enumerate(hidden):
        x = b1.content_x
        y = row * (h + sv)
        for piece in board:
            _segment(ax, x, y, piece, h, viz)
            x += piece.length

    # 2. Observable pieces: vertical stack running with the queue, so the piece nearest the
    #    saw is on top and the leftmost (furthest from the saw) at the bottom — the same
    #    direction as the hidden stack above. The piece at the saw itself belongs to region 3.
    #    Piece display width is at most MAX_PIECE_LEN. Row pitch = h + sv.
    for row, piece in enumerate(_observable_without_saw(state, cfg)):
        display_w = min(piece.length, cfg.MAX_PIECE_LEN)
        ax.add_patch(
            Rectangle(
                (b2.content_x, row * (h + sv)),
                display_w,
                h,
                facecolor=viz.color(piece),
                edgecolor="black",
                linewidth=0.8,
            )
        )

    # 3. saw / out_pos / buf_pos: fixed anchors, bottom to top; an empty slot draws nothing.
    for piece, y in (
        (_saw_piece(state), layout.y_saw),
        (state.out_piece, layout.y_out),
        (state.buf_piece, layout.y_buf),
    ):
        if piece is not None:
            _segment(ax, b3.content_x, y, piece, h, viz)

    # 4. Assembled beams: a pile resting on the region baseline (y = 0), oldest
    #    finished beam at the bottom, current unfinished beam on top.
    #    Beam pitch = NUM_LAYERS * h + beam_vspace.
    n_show = viz.VIZ_NUM_FINISHED_BEAMS
    finished_shown = state.finished_beams if n_show is None else state.finished_beams[-n_show:] if n_show > 0 else []

    beam_pitch = cfg.NUM_LAYERS * h + layout.beam_vspace
    x_beam = b4.content_x

    # Draw finished beams bottom-up: oldest at y=0, newer above it.
    for fb_idx, finished_beam in enumerate(finished_shown):
        y = fb_idx * beam_pitch
        for level, layer in enumerate(finished_beam):
            x = x_beam
            for piece in layer:
                _segment(ax, x, y + level * h, piece, h, viz)
                x += piece.length

    # Draw the current (topmost, unfinished) beam on top of the pile.
    beam_y = len(finished_shown) * beam_pitch
    for level, layer in enumerate(state.beam):
        x = x_beam
        lw = 1.6 if level == state.current_layer else 0.8
        for piece in layer:
            ax.add_patch(
                Rectangle(
                    (x, beam_y + level * h),
                    piece.length,
                    h,
                    facecolor=viz.color(piece),
                    edgecolor="black",
                    linewidth=lw,
                )
            )
            x += piece.length
    ax.add_patch(  # outline of the current beam for context
        Rectangle(
            (x_beam, beam_y),
            cfg.LAYER_LEN,
            cfg.NUM_LAYERS * h,
            facecolor="none",
            edgecolor="0.6",
            linewidth=0.8,
            linestyle=":",
        )
    )
    ax.add_patch(  # active-layer marker
        Rectangle(
            (x_beam, beam_y + state.current_layer * h),
            cfg.LAYER_LEN,
            h,
            facecolor="none",
            edgecolor="0.25",
            linewidth=1.2,
            linestyle="--",
        )
    )

    # Forbidden-interval overlays on the current (topmost) beam.
    if viz.VIZ_SHOW_FORBIDDEN:
        _draw_forbidden_overlays(ax, state, cfg, layout, viz, beam_y)

    # 5. Discarded pieces: greedy-packed rows, bottom-up (optional region).
    if b5 is not None:
        _draw_discarded_pile(ax, state, cfg, layout, viz, b5.content_x, viz.discard_row_width(cfg))

    # Region labels, hanging 0.5h below the baseline of what they name.
    label_dy = -0.5 * h
    kw = dict(fontsize=viz.label_fontsize, color="0.35", va="top")
    if len(state.queue) > cfg.OBSERVABLE_BOARDS or hidden:
        ax.text(b1.content_x + b1.content_w / 2, label_dy, "hidden", ha="center", **kw)
    # "queue" rather than "queue \u2192 saw": the saw end is now named by region 3's bottom slot,
    # and the longer caption collided with it.
    ax.text(b2.content_x + b2.content_w / 2, label_dy, "queue", ha="center", **kw)
    # Region 3 carries one label per slot, each hanging below its own slot rather than all at
    # the baseline, and left-aligned with the slot anchor so it reads as belonging to that slot.
    for y, name in ((layout.y_saw, "saw"), (layout.y_out, "out"), (layout.y_buf, "buf")):
        ax.text(b3.content_x, y + label_dy, name, ha="left", **kw)
    ax.text(b4.content_x + b4.content_w / 2, label_dy, "beams", ha="center", **kw)
    if b5 is not None:
        ax.text(b5.content_x + b5.content_w / 2, label_dy, "discarded pieces", ha="center", **kw)

    ax.set_xlim(*layout.xlim)
    ax.set_ylim(*layout.ylim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    if title is not None:
        ax.set_title(title, fontsize=viz.title_fontsize)
