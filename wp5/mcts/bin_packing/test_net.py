"""Tests for to_tokens in net.py."""

import os
import sys


import jax.numpy as jnp
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


from net import to_tokens

MAX_ITEMS = 4  # small, easy to reason about
SEQ_LEN = 1 + 2 * MAX_ITEMS  # 9


def _obs(bin_caps, item_sizes):
    """Build a (2*MAX_ITEMS,) obs from plain lists (padded with 0s)."""
    b = list(bin_caps) + [0.0] * (MAX_ITEMS - len(bin_caps))
    s = list(item_sizes) + [0.0] * (MAX_ITEMS - len(item_sizes))
    return jnp.array(b + s, dtype=jnp.float32)


def test_output_shape():
    obs = _obs([1.0], [0.5])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    assert tokens.shape == (SEQ_LEN, 7)


def test_value_token():
    obs = _obs([1.0], [0.5])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    np.testing.assert_array_equal(tokens[0], [1, 0, 0, 0, 0, 0, 0])


def test_bin_tokens_dims():
    """dim 1 is always 1; dims 0,4,5,6 are always 0 for bin tokens."""
    obs = _obs([0.7, 1.0], [0.3])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    bin_tokens = tokens[1 : MAX_ITEMS + 1]  # (MAX_ITEMS, 7)
    np.testing.assert_array_equal(bin_tokens[:, 0], 0)  # not value
    np.testing.assert_array_equal(bin_tokens[:, 1], 1)  # always bin
    np.testing.assert_array_equal(bin_tokens[:, 4], 0)  # not item
    np.testing.assert_array_equal(bin_tokens[:, 5], 0)  # no item size
    np.testing.assert_array_equal(bin_tokens[:, 6], 0)  # not next


def test_bin_is_active():
    """Used bins + first unused slot are active; further inactive slots are not."""
    # bins: 0.6 (used), 1.0 (new-bin slot), 1.0 (inactive), 1.0 (inactive)
    obs = _obs([0.6, 1.0, 1.0, 1.0], [0.4])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    is_active = np.array(tokens[1 : MAX_ITEMS + 1, 2])
    np.testing.assert_array_equal(is_active, [1, 1, 0, 0])


def test_bin_capacities_forwarded():
    caps = [0.6, 1.0, 0.0, 0.0]
    obs = _obs(caps, [0.4])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    bin_caps = np.array(tokens[1 : MAX_ITEMS + 1, 3])  # cap is now dim 3
    np.testing.assert_allclose(bin_caps, caps, atol=1e-6)


def test_item_tokens_dims():
    """dim 4 is always 1; dims 0,1,2,3 are always 0 for item tokens."""
    obs = _obs([1.0], [0.5, 0.3])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    item_tokens = tokens[MAX_ITEMS + 1 :]  # (MAX_ITEMS, 7)
    np.testing.assert_array_equal(item_tokens[:, 0], 0)
    np.testing.assert_array_equal(item_tokens[:, 1], 0)
    np.testing.assert_array_equal(item_tokens[:, 2], 0)
    np.testing.assert_array_equal(item_tokens[:, 3], 0)
    np.testing.assert_array_equal(item_tokens[:, 4], 1)


def test_item_sizes_forwarded():
    sizes = [0.5, 0.3, 0.0, 0.0]
    obs = _obs([1.0], sizes)
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    item_sizes = np.array(tokens[MAX_ITEMS + 1 :, 5])  # size is now dim 5
    np.testing.assert_allclose(item_sizes, sizes, atol=1e-6)


def test_is_next_set_when_items_remain():
    obs = _obs([1.0], [0.5, 0.3])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    assert tokens[MAX_ITEMS + 1, 6] == 1.0  # first item token: is_next (dim 6)
    assert tokens[MAX_ITEMS + 2, 6] == 0.0  # second item token: not is_next


def test_is_next_zero_when_no_items():
    obs = _obs([0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0])
    tokens = to_tokens(obs, max_items=MAX_ITEMS)
    np.testing.assert_array_equal(tokens[MAX_ITEMS + 1 :, 6], 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
