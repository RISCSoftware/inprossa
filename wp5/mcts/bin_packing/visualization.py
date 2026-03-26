"""Visualization helpers for bin packing solutions."""

import matplotlib.pyplot as plt
import matplotlib.axes
import numpy as np

_ALT = ["#4C72B0", "#DD8452"]  # alternating item colors within a bin


def plot_solution(
    ax: matplotlib.axes.Axes,
    bin_contents: list[list[float]],
    n_bins: int,
    opt: int | None = None,
) -> None:
    """Draw a single bin packing solution as a stacked bar chart.

    Parameters
    ----------
    ax          : target Axes
    bin_contents: bin_contents[b] = list of item sizes in bin b (in placement order)
    n_bins      : number of bins used (only bins 0..n_bins-1 are drawn)
    opt         : known optimal bin count; if given, marks the bin count with ★ when matched
    """
    for b in range(n_bins):
        bottom = 0.0
        for k, sz in enumerate(bin_contents[b]):
            ax.bar(b, sz, bottom=bottom, color=_ALT[k % 2], edgecolor="white", linewidth=0.4, width=0.8)
            bottom += sz

    ax.set_xlim(-0.5, max(n_bins - 0.5, 0.5))
    ax.set_ylim(0, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)

    label = str(n_bins)
    if opt is not None and n_bins == opt:
        label += " ★"
    ax.text(0.98, 0.97, label, transform=ax.transAxes, fontsize=7, ha="right", va="top")


def plot_grid(
    columns: list[tuple[list[list[list[float]]], "list[int] | np.ndarray"]],
    col_headers: list[str],
    opt_per_row: "list[int] | np.ndarray",
    out_path: str,
) -> None:
    """Save an n_rows × n_cols grid of bin packing solutions.

    Parameters
    ----------
    columns     : one entry per column, each a (bin_contents_list, n_used_list) pair
                  bin_contents_list[ep][b] = list of item sizes in bin b of episode ep
    col_headers : column header strings, one per column
    opt_per_row : known optimal bin count for each row; shown once left of the first column
    out_path    : file path for the saved PNG
    """
    n_rows = len(opt_per_row)
    n_cols = len(columns)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(2.5 * n_cols, 2 * n_rows), sharey=True, sharex="row")

    # Normalise to 2-D array even for n_cols == 1 or n_rows == 1
    if n_rows == 1 and n_cols == 1:
        axes = [[axes]]
    elif n_rows == 1:
        axes = [list(axes)]
    elif n_cols == 1:
        axes = [[row] for row in axes]

    for col_idx, header in enumerate(col_headers):
        axes[0][col_idx].set_title(header, fontsize=8, pad=3)

    for row_idx, opt in enumerate(opt_per_row):
        max_bins_in_row = max(int(n_used_list[row_idx]) for _, n_used_list in columns)
        for col_idx, (contents_list, n_used_list) in enumerate(columns):
            ax = axes[row_idx][col_idx]
            n_bins = int(n_used_list[row_idx])
            plot_solution(ax, contents_list[row_idx], n_bins, opt=opt)
            if col_idx == 0:
                ax.set_yticks([0, 0.5, 1.0])
                ax.tick_params(axis="y", labelsize=6)

            # Show opt label once, left of the first column only
            if col_idx == 0:
                ax.text(
                    -0.12, 0.5, f"opt={opt}", transform=ax.transAxes, fontsize=6, ha="right", va="center", clip_on=False
                )

        # With sharex="row", set the shared x range to fit the widest subplot
        axes[row_idx][0].set_xlim(-0.5, max_bins_in_row - 0.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {out_path}")
