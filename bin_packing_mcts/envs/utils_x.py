import numpy as np


def get_full_bins(
    n_bins: int = 1,
    min_size: float = 0.1,
    max_size: float = 0.4,
    bin_size: float = 1.0,
    min_empty: float = 0.0,
    max_empty: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    assert 0 <= min_size <= max_size <= bin_size - min_empty
    assert 0 <= min_empty <= max_empty < bin_size

    avg_item_size = (min_size + max_size) / 2
    n_items = int(2 * bin_size / avg_item_size)

    bins = []
    while len(bins) < n_bins:
        n_candidates = 2 * (n_bins - len(bins))

        # Sample empty space per candidate; shape: (n_candidates,)
        empty = np.random.uniform(min_empty, max_empty, size=n_candidates)
        usable = bin_size - empty  # shape: (n_candidates,)

        # Shape: (n_candidates, n_items)
        sizes = np.random.uniform(min_size, max_size, size=(n_candidates, n_items))

        # Prepend a column of zeros, then cumsum along items axis
        # Shape: (n_candidates, n_items + 1)
        intervals = np.concatenate(
            [np.zeros((n_candidates, 1)), np.cumsum(sizes, axis=1)],
            axis=1,
        )

        # Last index in each row where the cumsum is still <= usable (per-row)
        i_last = np.sum(intervals <= usable[:, np.newaxis], axis=1) - 1  # shape: (n_candidates,)
        last_size = usable - intervals[np.arange(n_candidates), i_last]

        valid = (i_last < n_items) & (min_size <= last_size) & (last_size <= max_size)

        for idx in np.where(valid)[0]:
            if len(bins) >= n_bins:
                break
            il = i_last[idx]
            ivs = intervals[idx, : il + 2].copy()
            ivs[-1] = usable[idx]
            bins.append(ivs)

    item_sizes = np.concatenate([np.diff(ivs) for ivs in bins])
    bin_assignment = np.concatenate([np.full(len(ivs) - 1, i, dtype=int) for i, ivs in enumerate(bins)])
    return item_sizes, bin_assignment


def first_fit(item_sizes: np.ndarray, bin_size: float = 1.0) -> np.ndarray:
    """Solve a bin-packing instance with the First Fit heuristic.

    Items are packed in the order given.  Each item is placed into the first
    open bin that has sufficient remaining capacity; if none exists a new bin
    is opened.

    Parameters
    ----------
    item_sizes:
        1-D array of item sizes.  All values must satisfy 0 < size <= bin_size.
    bin_size:
        Capacity of every bin (default 1.0).

    Returns
    -------
    assignment : np.ndarray of int, shape (n_items,)
        assignment[i] is the bin index that item i was placed into.
    """
    n_items = len(item_sizes)
    assignment = np.empty(n_items, dtype=int)
    remaining = []  # remaining capacity of each open bin

    for i, size in enumerate(item_sizes):
        placed = False
        for b, cap in enumerate(remaining):
            if cap >= size:
                assignment[i] = b
                remaining[b] -= size
                placed = True
                break
        if not placed:
            assignment[i] = len(remaining)
            remaining.append(bin_size - size)

    return assignment


def demo() -> None:
    n_unique_bins = 3
    item_sizes, bin_assignment = get_full_bins(
        n_bins=n_unique_bins,
        min_size=0.1,
        max_size=0.7,
        bin_size=1.0,
        min_empty=0.00,
        max_empty=0.00,
    )
    print(f"Generated {n_unique_bins} bins with {len(item_sizes)} items total.")

    n_bins = 10000
    # TODO:
    # - sample from a dirichlet distribution with n_unique_bins categories and large edge concentration
    # -
    alpha = np.full(n_unique_bins, 0.1)
    weights = np.random.dirichlet(alpha)

    repetitions = np.round(weights * n_bins).astype(int)
    repetitions = np.sort(repetitions)[::-1]
    repetitions[0] += n_bins - repetitions.sum()

    ###

    eps = 0.001
    n_unique_bins = 2
    item_sizes = np.array([0.5 + eps, 0.25 + eps, 0.25 - 2 * eps, 0.25 + 2 * eps, 0.25 + 2 * eps, 0.25 - 2 * eps])
    bin_assignment = np.array([0, 0, 0, 1, 1, 1])
    repetitions = np.array([4, 2])

    print(f"Repetitions: {repetitions.tolist()}")

    # Repeat bins: for each unique bin, tile its items according to its repetition count
    item_sizes = np.concatenate(
        [np.tile(item_sizes[bin_assignment == b], repetitions[b]) for b in range(n_unique_bins)]
    )

    item_sizes = np.sort(item_sizes)[::-1]

    ff_assignment = first_fit(item_sizes, bin_size=1.0)
    n_ff_bins = ff_assignment.max() + 1
    print(f"First Fit uses {n_ff_bins} bins  (optimal lower bound: {n_bins}).")
    # for b in range(n_ff_bins):
    #     mask = ff_assignment == b
    #     fill = item_sizes[mask].sum()
    #     print(f"  FF bin {b:>2d}: {mask.sum():>2d} items, fill={fill:.3f}")


if __name__ == "__main__":
    demo()
