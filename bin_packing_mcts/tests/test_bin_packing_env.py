"""Basic smoke tests for BinPackingEnv."""

import numpy as np
import pytest
from easydict import EasyDict

from bin_packing_mcts.envs.bin_packing_env import BinPackingEnv


def make_env(max_items: int = 6, min_items: int = 3, seed: int = 42) -> BinPackingEnv:
    cfg = EasyDict(
        dict(
            env_id="bin_packing",
            max_items=max_items,
            min_items=min_items,
            max_item_size=0.9,
            min_item_size=0.1,
        )
    )
    env = BinPackingEnv(cfg)
    env.seed(seed)
    return env


# ---------------------------------------------------------------------------
# Observation structure
# ---------------------------------------------------------------------------


def test_reset_obs_shape():
    env = make_env(max_items=6)
    obs = env.reset()
    assert set(obs.keys()) == {"bins", "items", "action_mask", "to_play"}
    assert obs["bins"].shape == (6,)
    assert obs["items"].shape == (6,)
    assert obs["action_mask"].shape == (6,)
    assert obs["to_play"] == -1


def test_initial_obs_bins_all_one():
    """Before any step all bin slots are unused and must have capacity 1.0."""
    env = make_env(max_items=6)
    obs = env.reset()
    np.testing.assert_array_equal(obs["bins"], np.ones(6, dtype=np.float32))


def test_initial_items_sorted_desc():
    """Items part of initial observation must be sorted descending."""
    env = make_env(max_items=10, min_items=10, seed=0)
    obs = env.reset()
    items = obs["items"]
    # All non-zero items should be sorted descending
    non_zero = items[items > 0]
    assert list(non_zero) == sorted(non_zero, reverse=True)


# ---------------------------------------------------------------------------
# Action mask
# ---------------------------------------------------------------------------


def test_initial_action_mask_only_new_bin():
    """At the very start only action 0 (open first bin) should be legal."""
    env = make_env(max_items=6)
    obs = env.reset()
    mask = obs["action_mask"]
    assert mask[0] == 1, "Opening a new bin must be legal on the first step."
    assert mask[1:].sum() == 0, "No other actions should be legal before any bin is open."


def test_action_mask_existing_bin_fits():
    """After placing one item, placing in the same bin should be legal if it fits."""
    env = make_env(max_items=6)
    obs = env.reset()
    # Open the first bin (action 0)
    ts = env.step(0)
    obs2 = ts.obs
    # The bin we just opened has remaining capacity; a second item may fit.
    # We just check that action 0 is legal iff remaining_cap >= next_item_size.
    bins = obs2["bins"]
    items = obs2["items"]
    mask = obs2["action_mask"]
    next_item = items[items > 0][0]
    cap = bins[0]
    if cap >= next_item - 1e-9:
        assert mask[0] == 1
    else:
        assert mask[0] == 0


# ---------------------------------------------------------------------------
# Episode dynamics
# ---------------------------------------------------------------------------


def test_full_episode_terminates():
    """An episode must end after exactly n_items steps."""
    env = make_env(max_items=10, min_items=5, seed=7)
    obs = env.reset()
    n_items_in_ep = int((obs["items"] > 0).sum())

    done = False
    steps = 0
    while not done:
        mask = obs["action_mask"]
        legal = np.where(mask == 1)[0]
        action = int(legal[0])  # greedy: always pick first legal action
        ts = env.step(action)
        obs = ts.obs
        done = ts.done
        steps += 1

    assert steps == n_items_in_ep


def test_terminal_reward_negative_bins():
    """Terminal reward must equal -(number of bins used)."""
    env = make_env(max_items=10, min_items=5, seed=3)
    obs = env.reset()

    done = False
    last_ts = None
    while not done:
        mask = obs["action_mask"]
        legal = np.where(mask == 1)[0]
        action = int(legal[-1])  # always open new bin (pessimal policy)
        ts = env.step(action)
        obs = ts.obs
        done = ts.done
        last_ts = ts

    n_bins = last_ts.info["n_bins"]
    assert last_ts.reward[0] == pytest.approx(-n_bins)


def test_non_terminal_reward_zero():
    """All intermediate step rewards must be 0."""
    env = make_env(max_items=6, seed=1)
    obs = env.reset()
    done = False
    while not done:
        mask = obs["action_mask"]
        legal = np.where(mask == 1)[0]
        ts = env.step(int(legal[0]))
        if not ts.done:
            assert ts.reward[0] == pytest.approx(0.0)
        obs = ts.obs
        done = ts.done


def test_bins_sorted_descending_after_each_step():
    """The bins part of the observation must remain sorted descending at every step.
    Open bin slots ([:n_bins]) are sorted descending; unused slots ([n_bins:]) are 1.0."""
    env = make_env(max_items=10, min_items=8, seed=99)
    obs = env.reset()
    done = False
    while not done:
        mask = obs["action_mask"]
        legal = np.where(mask == 1)[0]
        ts = env.step(int(legal[0]))
        bins = ts.obs["bins"]
        n_bins = ts.info["n_bins"]
        open_caps = bins[:n_bins]
        unused_caps = bins[n_bins:]
        assert list(open_caps) == sorted(open_caps, reverse=True), f"Open bins not sorted: {bins}"
        np.testing.assert_array_equal(unused_caps, np.ones(len(unused_caps), dtype=np.float32))
        obs = ts.obs
        done = ts.done


# ---------------------------------------------------------------------------
# ENV_REGISTRY
# ---------------------------------------------------------------------------


def test_env_registry():
    from ding.utils import ENV_REGISTRY

    assert "bin_packing" in ENV_REGISTRY
