import numpy as np


def get_full_bins(
    min_size: float = 0.1,
    max_size: float = 0.4,
    box_size: float = 1.0,
) -> np.ndarray:
    assert 0 <= min_size < max_size <= 1.0

    avg_item_size = (min_size + max_size) / 2
    n_items = 2 * box_size / avg_item_size

    while True:
        sizes = np.random.uniform(min_size, max_size, size=int(n_items))
        intervals = np.concatenate(([0.0], np.cumsum(sizes)))

        i_last = np.searchsorted(intervals, box_size, side="right") - 1
        last_size = box_size - intervals[i_last]

        if (i_last < len(sizes)) and (min_size <= last_size <= max_size):
            # Success!
            break

    intervals = intervals[: i_last + 2]
    intervals[-1] = box_size

    return intervals


print(get_full_bins())
