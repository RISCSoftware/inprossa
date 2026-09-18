"""Draw the glulam policy-input sequence against the token feature positions.

The point of the figure is the block-diagonal sparsity: the feature space is
partitioned into disjoint blocks, one per list plus one for the scalars, and a
token writes only its own block. That is what replaces every type flag.

The figure shows the policy input, not the padded JAX tensor, so it names no
bound and shows no padding. Each list appears as a run elided between its first
and last item. The global block is drawn as a single abstract cell rather than
twelve; per-position detail is deferred to a later figure.

Run it directly; importing it draws nothing.
"""

from pathlib import Path

OUT = Path(__file__).parent.parent / "docs" / "private" / "glulam_token_diagram.png"

# (label, width) per block -- widths sum to TOKEN_DIM.
BLOCKS = [
    ("global\n0-11", 12),
    ("conveyor\n12-13", 2),
    ("iv curr\n14-15", 2),
    ("iv next\n16-17", 2),
    ("action\n18-26", 9),
]
TOKEN_DIM = sum(w for _, w in BLOCKS)

GLOBAL, CONV, IVC, IVN, ACT = range(5)


def shade(v):
    """Map a cell value in (0, 1] onto a visible alpha range.

    A plain floor such as ``max(v, 0.3)`` renders every small value alike, which
    makes an interval's start and end indistinguishable. This keeps the whole
    range separable while leaving nothing invisible.
    """
    return 0.25 + 0.75 * v


# (label, block index, values) -- values None marks an elision row, which draws
# no cells and shows a vertical ellipsis in its run's block instead.
ROWS = [
    ("global", GLOBAL, [0.75]),
    ("conveyor piece 1", CONV, [0.62, 0.20]),
    ("⋮", CONV, None),
    ("conveyor piece C", CONV, [0.28, 1.00]),
    ("interval, current 1", IVC, [0.15, 0.45]),
    ("⋮", IVC, None),
    ("interval, current V", IVC, [0.55, 0.95]),
    ("interval, next 1", IVN, [0.10, 0.50]),
    ("⋮", IVN, None),
    ("interval, next W", IVN, [0.62, 0.98]),
    ("cut_1", ACT, [1, 0, 0, 0, 0, 0, 0, 0.08, 0.86]),
    ("⋮", ACT, None),
    ("cut_K", ACT, [1, 0, 0, 0, 0, 0, 0, 0.90, 0.06]),
    ("put_buf", ACT, [0, 1, 0, 0, 0, 0, 0, 0, 0]),
    ("assemble_out", ACT, [0, 0, 1, 0, 0, 0, 0, 0, 0]),
    ("assemble_buf", ACT, [0, 0, 0, 1, 0, 0, 0, 0, 0]),
    ("discard_out", ACT, [0, 0, 0, 0, 1, 0, 0, 0, 0]),
    ("discard_buf", ACT, [0, 0, 0, 0, 0, 1, 0, 0, 0]),
    ("discard_beam", ACT, [0, 0, 0, 0, 0, 0, 1, 0, 0]),
]

LEGEND = (
    "C  pieces on the conveyor      V  current-layer intervals      "
    "W  next-layer intervals      — all three vary from step to step\n"
    "K  = MAX_PIECE_LEN, one cut action per cut length"
)


def draw(out_path=OUT):
    """Render the figure and write it to out_path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    fill, edge, empty = "#3d6e8f", "#4a4a4a", "#f2f2f2"
    n_rows = len(ROWS)
    fig, ax = plt.subplots(figsize=(0.46 * TOKEN_DIM + 3.6, 0.36 * n_rows + 2.2))

    starts, x = [], 0
    for _, w in BLOCKS:
        starts.append(x)
        x += w

    for r, (label, block, values) in enumerate(ROWS):
        y = n_rows - 1 - r
        x0, w = starts[block], BLOCKS[block][1]

        if values is None:  # elision: no cells, just a vertical ellipsis
            run = next(v for lbl, b, v in ROWS if b == block and v is not None)
            occupied = [i for i, v in enumerate(run) if v] or [0]
            # Centre on the first contiguous group, not the whole span: the cut
            # run occupies 18 and 25-26, whose midpoint is empty space.
            group = [occupied[0]]
            for i in occupied[1:]:
                if i != group[-1] + 1:
                    break
                group.append(i)
            mid = x0 + (group[0] + group[-1] + 1) / 2
            ax.text(-0.5, y + 0.5, label, ha="right", va="center", fontsize=11)
            ax.text(mid, y + 0.5, label, ha="center", va="center", fontsize=11)
            continue

        for b, (bx, (_, bw)) in enumerate(zip(starts, BLOCKS)):
            if b != block:
                for i in range(bw):
                    ax.add_patch(patches.Rectangle((bx + i, y), 1, 1, fc=empty, ec="white", lw=0.6))
            elif b == GLOBAL:  # one abstract cell spanning the whole block
                ax.add_patch(patches.Rectangle((bx, y), bw, 1, fc=fill, ec=edge, lw=0.8, alpha=shade(values[0])))
                ax.text(
                    bx + bw / 2,
                    y + 0.5,
                    "12 scalars",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=9,
                )
            else:
                for i, v in enumerate(values):
                    ax.add_patch(
                        patches.Rectangle(
                            (bx + i, y),
                            1,
                            1,
                            ec="white",
                            lw=0.6,
                            fc=fill if v else empty,
                            alpha=shade(v) if v else 1.0,
                        )
                    )
        ax.text(-0.5, y + 0.5, label, ha="right", va="center", fontsize=9)

    for x0, (blabel, w) in zip(starts, BLOCKS):
        if x0:
            ax.plot([x0, x0], [0, n_rows + 0.15], color=edge, lw=1.4)
        ax.text(x0 + w / 2, n_rows + 0.35, blabel, ha="center", va="bottom", fontsize=9)

    ax.text(-0.5, -1.35, LEGEND, ha="left", va="top", fontsize=8.5, color="#333333")

    ax.set_xlim(-7.0, TOKEN_DIM + 0.2)
    ax.set_ylim(-2.6, n_rows + 1.4)
    ax.axis("off")
    ax.set_aspect("equal")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    print(f"wrote {draw()}")
