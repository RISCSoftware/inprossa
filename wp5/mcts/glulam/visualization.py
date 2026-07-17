"""Step visualization for the glulam env (matplotlib).

``render(ax, state, cfg, ...)`` draws one frame with four regions, left to
right, per the spec's Episode-visualization section:

1. hidden-pieces stack (one row per hidden board, bottom = leftmost board),
2. observable pieces (flat row, right-aligned at the saw side),
3. out_pos / buf_pos slots (fixed anchors, buf above out),
4. the currently assembled beam (Lego-brick style).

Colors are derived here (the env stores none): ``palette[piece_id % NUM_COLORS]``,
every segment with a black outline. The layout is computed once from the
initial state and config and reused for every frame, so animations do not
rescale as the queue drains.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib.axes
from matplotlib import colormaps
from matplotlib.colors import to_hex
from matplotlib.patches import Rectangle

from mcts.glulam.env import EnvConfig, GlulamState, Piece, hidden_boards, observable_boards


def _default_palette() -> tuple[str, ...]:
    cmap = colormaps["tab20"]
    return tuple(to_hex(cmap(i)) for i in range(20))


@dataclass(frozen=True)
class VizConfig:
    NUM_COLORS: int = 20
    palette: tuple[str, ...] = field(default_factory=_default_palette)

    def color(self, piece: Piece) -> str:
        return self.palette[piece.piece_id % self.NUM_COLORS]


@dataclass(frozen=True)
class Layout:
    """Fixed axes geometry, computed once per episode from the initial state."""

    seg_h: float  # segment height (wood-length units; aspect is equal)
    obs_gap: float  # horizontal gap between observable segments (= 3 * seg_h)
    x_stack: float  # left edge of the hidden-pieces stack
    x_obs_right: float  # right edge (saw side) of the observable row
    x_slot: float  # left anchor of the out/buf slots
    y_out: float
    y_buf: float
    x_beam: float  # left edge of the beam
    xlim: tuple[float, float]
    ylim: tuple[float, float]


def compute_layout(initial_state: GlulamState, cfg: EnvConfig) -> Layout:
    h = max(1.0, cfg.LAYER_LEN / 25)
    obs_gap = 3 * h
    region_gap = 6 * h

    boards = [[p.length for p in board] for board in initial_state.queue]
    stack_width = max((sum(b) for b in boards), default=0)

    # Worst-case observable-row width over the episode: the window slides
    # leftwards over the initial boards as boards are consumed at the right;
    # cutting only shrinks a board, so the initial windows bound all widths.
    n_boards = len(boards)
    obs_width = 0.0
    for consumed in range(n_boards):
        window = boards[max(0, n_boards - consumed - cfg.OBSERVABLE_BOARDS) : n_boards - consumed]
        pieces = [length for b in window for length in b]
        obs_width = max(obs_width, sum(pieces) + (len(pieces) - 1) * obs_gap)

    x_stack = 0.0
    x_obs_right = x_stack + stack_width + region_gap + obs_width
    x_slot = x_obs_right + region_gap
    x_beam = x_slot + cfg.MAX_PIECE_LEN + region_gap
    x_end = x_beam + cfg.LAYER_LEN

    n_hidden_rows = max(0, n_boards - cfg.OBSERVABLE_BOARDS)
    stack_height = n_hidden_rows * 2 * h - h if n_hidden_rows else 0.0
    y_out, y_buf = 0.0, 4 * h  # buf above out, separated by 3 * seg_h
    height = max(stack_height, cfg.NUM_LAYERS * h, y_buf + h)

    return Layout(
        seg_h=h,
        obs_gap=obs_gap,
        x_stack=x_stack,
        x_obs_right=x_obs_right,
        x_slot=x_slot,
        y_out=y_out,
        y_buf=y_buf,
        x_beam=x_beam,
        xlim=(x_stack - h, x_end + h),
        ylim=(-2.5 * h, height + h),
    )


def _segment(ax, x: float, y: float, piece: Piece, h: float, viz: VizConfig) -> None:
    ax.add_patch(
        Rectangle((x, y), piece.length, h, facecolor=viz.color(piece), edgecolor="black", linewidth=0.8)
    )


def render(
    ax: matplotlib.axes.Axes,
    state: GlulamState,
    cfg: EnvConfig,
    layout: Layout,
    viz: VizConfig | None = None,
    title: str | None = None,
) -> None:
    """Draw one episode frame into ax using the fixed layout."""
    viz = viz or VizConfig()
    h = layout.seg_h

    # 1. Hidden-pieces stack: bottom row = leftmost board, top row = rightmost.
    hidden = hidden_boards(state, cfg)
    for row, board in enumerate(hidden):
        x = layout.x_stack
        for piece in board:
            _segment(ax, x, row * 2 * h, piece, h, viz)
            x += piece.length
    # 2. Observable pieces: flat row (no board boundaries), right-aligned at the saw.
    obs = [p for board in observable_boards(state, cfg) for p in board]
    width = sum(p.length for p in obs) + max(0, len(obs) - 1) * layout.obs_gap
    x = layout.x_obs_right - width
    for piece in obs:
        _segment(ax, x, layout.y_out, piece, h, viz)
        x += piece.length + layout.obs_gap

    # 3. out_pos / buf_pos: fixed anchors; an empty position draws nothing.
    if state.out_piece is not None:
        _segment(ax, layout.x_slot, layout.y_out, state.out_piece, h, viz)
    if state.buf_piece is not None:
        _segment(ax, layout.x_slot, layout.y_buf, state.buf_piece, h, viz)

    # 4. Beam: Lego-brick style, no gaps; layer 0 at the bottom.
    for level, layer in enumerate(state.beam):
        x = layout.x_beam
        for piece in layer:
            _segment(ax, x, level * h, piece, h, viz)
            x += piece.length
    ax.add_patch(  # outline of the full beam for context
        Rectangle(
            (layout.x_beam, 0),
            cfg.LAYER_LEN,
            cfg.NUM_LAYERS * h,
            facecolor="none",
            edgecolor="0.6",
            linewidth=0.8,
            linestyle=":",
        )
    )

    # Region labels at fixed positions.
    label_y = -1.8 * h
    kw = dict(fontsize=7, color="0.35", ha="center", va="bottom")
    if len(state.queue) > cfg.OBSERVABLE_BOARDS or hidden:
        ax.text(layout.x_stack + (layout.x_obs_right - layout.x_stack) * 0.15, label_y, "hidden", **kw)
    ax.text(layout.x_obs_right - h, label_y, "queue \u2192 saw", ha="right", va="bottom", fontsize=7, color="0.35")
    ax.text(layout.x_slot + cfg.MAX_PIECE_LEN / 2, label_y, "out / buf", **kw)
    ax.text(layout.x_beam + cfg.LAYER_LEN / 2, label_y, "beam", **kw)

    ax.set_xlim(*layout.xlim)
    ax.set_ylim(*layout.ylim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    if title is not None:
        ax.set_title(title, fontsize=8)
