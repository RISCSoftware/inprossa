"""
To avoid having many Piece(length=0, good=1), I just fill the list with
randomly generated filler pieces.
"""

import random
from IncrementalPipeline.Objects.piece import Piece

def random_partition(m, n):
    """
    Generate a random list of `n` non-negative integers that sum to `m`.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if m < 0:
        raise ValueError("m must be non-negative")
    if n == 1:
        return [m]
    
    # Sample n-1 cuts in [0, m + n - 1), then count stars between bars
    cuts = sorted(random.sample(range(m + n - 1), n - 1))
    return [b - a - 1 for a, b in zip([-1] + cuts, cuts + [m + n - 1])]


def empty_piece_filler(fixed_pieces, desired_length):
    """
    Inserts filler pieces randomly between and around fixed_pieces
    while preserving the original order of the fixed pieces.

    Args:
        fixed_pieces (List[Piece]): Ordered fixed pieces.
        desired_length (int): Target total number of pieces.

    Returns:
        List[Piece]: Combined and ordered list of fixed + filler pieces.
    """
    n_fixed = len(fixed_pieces)
    n_fillers = desired_length - n_fixed

    if n_fillers < 0:
        raise ValueError("desired_length must be >= number of fixed pieces")
    if n_fillers == 0:
        return fixed_pieces.copy()

    # Generate random filler distribution across n_fixed + 1 gaps
    filler_distribution = random_partition(n_fillers, n_fixed + 1)

    result = []
    for i in range(n_fixed + 1):
        # Add fillers in the i-th gap
        result.extend([Piece(length=0, good=1, id=None) for _ in range(filler_distribution[i])])
        # Add fixed piece (unless we're at the last slot)
        if i < n_fixed:
            result.append(fixed_pieces[i])

    return result