"""Layout assertions for the glulam visualization.

These cover the frame geometry rather than the pixels: that every drawn segment stays
inside the region box reserved for it, that the region boxes tile the x-axis without
overlapping, and that the reserved frame is not wildly larger than the content it holds.
The last one is the regression guard for a layout bug that made the discard region reserve
~1850 rows, which crushed every other region into the bottom sliver of the frame.

Runnable directly (``uv run python -m mcts.glulam.test_visualization``) or via pytest.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from mcts.glulam.configs import EXAMPLE_CONFIGS
from mcts.glulam.env import EnvConfig, GlulamState, reset
from mcts.glulam.policy import run_episode, weighted_policy
from mcts.glulam.visualization import Layout, VizConfig, compute_layout, render

# Small configs only: these are geometry checks, not rollout checks.
LAYOUT_CONFIGS = ["small", "medium", "narrow_window"]


def _rollout(name: str) -> tuple[list[GlulamState], EnvConfig]:
    cfg = EXAMPLE_CONFIGS[name]
    states, _, _, _ = run_episode(cfg, 0, policy=weighted_policy)
    return states, cfg


def _drawn_rects(ax) -> list[tuple[float, float, float, float]]:
    """(left, bottom, right, top) of every rectangle drawn into ax."""
    return [
        (p.get_x(), p.get_y(), p.get_x() + p.get_width(), p.get_y() + p.get_height())
        for p in ax.patches
        if isinstance(p, Rectangle)
    ]


def _assert_inside_a_box(rects, layout: Layout, tol: float, where: str) -> None:
    boxes = list(layout.boxes.values())
    for left, bottom, right, top in rects:
        assert any(
            b.left - tol <= left and right <= b.right + tol and b.bottom - tol <= bottom and top <= b.top + tol
            for b in boxes
        ), f"{where}: rectangle ({left:.2f}, {bottom:.2f})-({right:.2f}, {top:.2f}) escapes every region box"


def test_boxes_tile_the_x_axis_without_overlap() -> None:
    for name in LAYOUT_CONFIGS:
        cfg = EXAMPLE_CONFIGS[name]
        for viz in (VizConfig(), VizConfig(VIZ_SHOW_DISCARDED=False), VizConfig(VIZ_NUM_FINISHED_BEAMS=0)):
            layout = compute_layout(reset(cfg), cfg, viz)
            boxes = list(layout.boxes.values())
            assert len(boxes) == (4 if not viz.VIZ_SHOW_DISCARDED else 5), f"{name}: unexpected region count"
            for earlier, later in zip(boxes, boxes[1:]):
                assert earlier.right <= later.left + 1e-9, f"{name}: region boxes overlap on the x-axis"


def test_drawn_content_stays_inside_its_region_box() -> None:
    """Every segment, beam outline and forbidden overlay lands inside a reserved box."""
    fig, ax = plt.subplots()
    try:
        for name in LAYOUT_CONFIGS:
            states, cfg = _rollout(name)
            viz = VizConfig()
            layout = compute_layout(states[0], cfg, viz, states=states)
            for t, state in enumerate(states):
                ax.clear()
                render(ax, state, cfg, layout, viz)
                _assert_inside_a_box(_drawn_rects(ax), layout, tol=1e-6, where=f"{name} step {t}")
    finally:
        plt.close(fig)


def test_frame_is_not_much_taller_than_its_content() -> None:
    """ylim must track the content, not a loose worst-case bound.

    The rollout-sized layout may exceed the tallest thing ever drawn only by the region
    padding; a bound-based layout is allowed to be looser but not unboundedly so.
    """
    fig, ax = plt.subplots()
    try:
        for name in LAYOUT_CONFIGS:
            states, cfg = _rollout(name)
            viz = VizConfig()
            for tag, kwargs, slack in [("rollout", {"states": states}, 1.5), ("bound", {}, 6.0)]:
                layout = compute_layout(states[0], cfg, viz, **kwargs)
                tallest = 0.0
                for state in states:
                    ax.clear()
                    render(ax, state, cfg, layout, viz)
                    tallest = max([tallest] + [top for _, _, _, top in _drawn_rects(ax)])
                limit = slack * tallest + 4 * layout.seg_h
                assert layout.ylim[1] <= limit, (
                    f"{name} ({tag}): ylim top {layout.ylim[1]:.1f} reserves far more than the "
                    f"{tallest:.1f} the episode ever draws"
                )
    finally:
        plt.close(fig)


def test_degenerate_discard_row_width_does_not_blow_up_a_rollout_sized_frame() -> None:
    """A row width equal to MAX_PIECE_LEN packs one piece per row — the pile gets tall, not absurd.

    The config-only bound genuinely degenerates here (its divisor collapses to 1), which is why
    VIZ_DISCARD_ROW_WIDTH defaults to MAX_BOARD_LEN; sizing from the rollout stays exact.
    """
    states, cfg = _rollout("medium")
    viz = VizConfig(VIZ_DISCARD_ROW_WIDTH=cfg.MAX_PIECE_LEN)
    layout = compute_layout(states[0], cfg, viz, states=states)
    n_discarded = len(states[-1].discarded_pieces)
    row_pitch = layout.seg_h + layout.stack_vspace
    rows_reserved = round((layout.box("discarded").content_h + layout.stack_vspace) / row_pitch)
    assert rows_reserved <= n_discarded, f"reserved {rows_reserved} rows for {n_discarded} pieces, one per row at most"


if __name__ == "__main__":
    test_boxes_tile_the_x_axis_without_overlap()
    test_drawn_content_stays_inside_its_region_box()
    test_frame_is_not_much_taller_than_its_content()
    test_degenerate_discard_row_width_does_not_blow_up_a_rollout_sized_frame()
    print("visualization layout checks passed")
