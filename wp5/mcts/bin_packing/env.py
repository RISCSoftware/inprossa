"""bin_packing_env.py - JAX-compatible, JIT-able, vectorisable bin-packing env.

Bin capacity is always 1.

Init procedure
--------------
  1. Roll bin *types*: for each type draw (n_items_per_bin, n_reps).
  2. Fill each type by splitting [0, 1] into n_items_per_bin pieces,
     each >= min_item_size, using the "reserve minimum + distribute remainder"
     trick so every piece is valid.
  3. Expand by repetitions → flat collection of bin instances.
  4. Forget bin structure; keep only the flat, descending-sorted item list.

Observation
-----------
  shape (2 * max_items,) float32:
    obs[:max_items] - open bins' remaining capacity, sorted *descending*, 0-padded
    obs[max_items:] - unassigned items' sizes, sorted *descending*, 0-padded
  (Directly feeds to_tokens() to build the BinPackingNet token sequence.)

Action
------
  Integer in [0, max_items).
    action < n_bins_used  : assign item to that existing open bin
    action == n_bins_used : open a new bin for this item
  Legal if bin_spaces[action] >= current item size.

Reward
------
  -1 each time a new bin is opened (dense signal; total = -(bins used)).

Array shapes are fixed at max_items - makes the env fully JIT-able /
vmappable with no Python-level dynamic shapes.
"""

import math
from typing import NamedTuple

import jax
import jax.numpy as jnp


# jax.config.update("jax_disable_jit", True)  # DEBUG


# Default hyper-parameters

DEFAULT_MAX_ITEMS: int = 32
# DEFAULT_MAX_ITEMS: int = 6  # DEBUG
DEFAULT_MIN_ITEM_SIZE: float = 0.3
DEFAULT_MAX_ITEM_SIZE: float = 0.7


_MAX_REPS: int = 16  # max repetitions per template
_MAX_ITEMS_PER_BIN: int = 4  # max items inside one bin template


class BinPackingState(NamedTuple):
    items: jnp.ndarray  # (max_items,) float32  All items (assigned and anassigned) sorted descending, padded with 0s
    n_items: jnp.ndarray  # ()         int32
    step: jnp.ndarray  # ()           int32    next-item-to-assign index
    bin_spaces: jnp.ndarray  # (max_items,) float32  Remaining capacity per bin, descending order
    n_bins_used: jnp.ndarray  # ()           int32    open bin slots count
    n_bins_opt: jnp.ndarray  # ()           int32    optimal bin count (if known)
    observation: jnp.ndarray  # (2*max_items,) float32 for the neural net
    legal_action_mask: jnp.ndarray  # (max_items,) bool
    terminated: jnp.ndarray  # ()           bool
    rewards: jnp.ndarray  # ()           float32  cumulative reward


def _make_observation(
    bin_spaces: jnp.ndarray,
    n_bins_used: jnp.ndarray,
    items: jnp.ndarray,
    step: jnp.ndarray,
    max_items: int,
) -> jnp.ndarray:
    """Build the (2 * max_items,) observation array."""
    # Bins: slots are in action-index order (bin_spaces is kept sorted descending by step_env).
    # Open bins keep their remaining capacity; all unused bins gets capacity 1.0.
    bin_idx = jnp.arange(max_items)
    is_open = bin_idx < n_bins_used
    bin_spaces_1 = jnp.where(is_open, bin_spaces, 1.0)

    # Items: unassigned = items[step:], already desc-sorted; use dynamic slice
    # Pad to 2*max_items so dynamic_slice never goes out of bounds (step ≤ max_items)
    padded = jnp.concatenate([items, jnp.zeros(max_items, dtype=jnp.float32)])
    item_obs = jax.lax.dynamic_slice(padded, (step,), (max_items,))

    return jnp.concatenate([bin_spaces_1, item_obs])


def _legal_mask(
    bin_spaces: jnp.ndarray,
    n_bins_used: jnp.ndarray,
    n_items: jnp.ndarray,
    step: jnp.ndarray,
    items: jnp.ndarray,
    max_items: int,
) -> jnp.ndarray:
    """Return (max_items,) bool legal-action mask for the *current* step."""
    terminated = step >= n_items
    safe_step = jnp.minimum(step, max_items - 1)
    item_size = items[safe_step]

    slots = jnp.arange(max_items)
    existing_ok = (slots < n_bins_used) & (bin_spaces >= item_size)
    new_bin_ok = slots == n_bins_used
    legal = existing_ok | new_bin_ok
    # All actions masked out once the episode has ended
    return jnp.where(terminated, jnp.zeros(max_items, dtype=jnp.bool_), legal)


def init(
    key: jnp.ndarray,
    max_items: int = DEFAULT_MAX_ITEMS,
    min_item_size: float = DEFAULT_MIN_ITEM_SIZE,
    max_item_size: float = DEFAULT_MAX_ITEM_SIZE,
    max_items_per_bin: int = _MAX_ITEMS_PER_BIN,
    max_reps: int = _MAX_REPS,
    bin_slack: float = 1e-4,
) -> BinPackingState:
    """Initialise one episode.  JIT-able and vmap-able over `key`.

    bin_slack: fraction of each bin's capacity left free after packing items.
    """

    # Create separate rng keys
    key, k_n, k_reps, k_cut = jax.random.split(key, 4)

    # Roll bin-template meta-parameters
    # Valid n (items/bin): n*min_size ≤ 1 ≤ n*max_size
    #   → ceil(1/max_size) ≤ n ≤ floor(1/min_size), capped by max_items_per_bin
    # Use Python math so these are compile-time constants under JIT tracing.
    min_n = max(2, math.ceil(1.0 / max_item_size))
    max_n = min(max_items_per_bin, math.floor(1.0 / min_item_size))

    max_bins = math.ceil(max_items / min_n)
    max_bin_types = max_bins

    n_items_per_type = jax.random.randint(k_n, (max_bin_types,), min_n, max_n + 1)  # (T,)
    n_reps_per_type = jax.random.randint(k_reps, (max_bin_types,), 1, max_reps + 1)
    # Enforce the max_items budget: reduce the first type that would overflow,
    # and zero out all subsequent types (their budget_left becomes 0).
    cum_before = jnp.concatenate(
        [jnp.array([0], dtype=jnp.int32), jnp.cumsum(n_items_per_type * n_reps_per_type)[:-1]]
    )  # items contributed by all preceding types at original reps
    budget_left = jnp.maximum(max_items - cum_before, 0)
    n_reps_per_type = jnp.minimum(budget_left // n_items_per_type, n_reps_per_type)  # (T,)
    type_active = n_reps_per_type > 0  # (T,) bool

    # Item sizes for each bin type
    # Sequential allocation guarantees every item ∈ [min_size, max_size] and
    # items sum exactly to 1 per bin type.  Uses lax.scan + vmap.
    raw = jax.random.uniform(k_cut, (max_bin_types, max_n))  # (T, max_n)

    def _fill_bin(raw_row, n):
        """Allocate n items in [min_size, max_size] summing to 1."""

        def step(remaining, xi):
            i, r = xi
            n_after = jnp.maximum(n - i - 1, jnp.int32(0))
            is_active = i < n
            is_last = i == n - 1
            lo = jnp.maximum(
                jnp.float32(min_item_size),
                remaining - n_after.astype(jnp.float32) * max_item_size,
            )
            hi = jnp.minimum(
                jnp.float32(max_item_size),
                remaining - n_after.astype(jnp.float32) * min_item_size,
            )
            hi = jnp.maximum(lo, hi)  # numerical guard
            size = lo + r * (hi - lo)
            size = jnp.where(is_last, remaining, size)  # last gets exact remainder
            size = jnp.where(is_active, size, jnp.float32(0.0))
            new_rem = jnp.where(is_active, remaining - size, remaining)
            return new_rem, size

        idxs = jnp.arange(max_n, dtype=jnp.int32)
        _, sizes = jax.lax.scan(step, jnp.float32(1.0 - bin_slack), (idxs, raw_row))
        return sizes

    # _fill_bin(raw[0], n_items_per_type[0])  # DEBUG

    # (T, max_n)
    sizes_per_type = jax.vmap(_fill_bin)(raw, n_items_per_type)

    # Expand to (T, R, max_n)
    sizes_per_rep_and_type = jnp.broadcast_to(sizes_per_type[:, None, :], (max_bin_types, max_reps, max_n))

    # (1, R, 1)
    rep_idx = jnp.arange(max_reps)[None, :, None]

    # (T, 1, max_n)
    item_idx = jnp.arange(max_n)[None, None, :]

    # Valid repeated bin instances
    rep_active = type_active[:, None, None] & (rep_idx < n_reps_per_type[:, None, None])

    # Valid item slots within each type
    item_active = item_idx < n_items_per_type[:, None, None]

    valid = rep_active & item_active

    # Zero out inactive entries, flatten, sort descending, trim
    item_buf = jnp.where(valid, sizes_per_rep_and_type, 0.0).reshape(-1)
    items = jnp.sort(item_buf, descending=True)[:max_items]

    n_items = jnp.sum(items > 0)

    n_bins_opt = jnp.sum(n_reps_per_type)

    # Build initial State
    step = jnp.int32(0)
    ini_bins_used = jnp.int32(0)
    bin_spaces = jnp.zeros(max_items, dtype=jnp.float32)
    legal = _legal_mask(bin_spaces, ini_bins_used, n_items, step, items, max_items)
    obs = _make_observation(bin_spaces, ini_bins_used, items, step, max_items)

    return BinPackingState(
        items=items,
        n_items=n_items,
        step=step,
        bin_spaces=bin_spaces,
        n_bins_used=ini_bins_used,
        n_bins_opt=n_bins_opt,
        observation=obs,
        legal_action_mask=legal,
        terminated=jnp.bool_(False),
        rewards=jnp.float32(0.0),
    )


def step_env(
    state: BinPackingState,
    action: jnp.ndarray,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> BinPackingState:
    """Assign items[state.step] to bin slot `action`.  Returns next state."""
    action = jnp.int32(action)
    item_size = state.items[state.step]

    # Update bin capacity
    is_new_bin = action == state.n_bins_used
    old_cap = state.bin_spaces[action]
    new_cap = jnp.where(is_new_bin, 1.0 - item_size, old_cap - item_size)
    bin_spaces = state.bin_spaces.at[action].set(new_cap)
    bin_spaces = jnp.sort(bin_spaces)[::-1]  # keep descending order

    # Advance counters
    n_bins_used = state.n_bins_used + is_new_bin.astype(jnp.int32)
    step = state.step + jnp.int32(1)
    terminated = step >= state.n_items

    # Reward: -1 each time a new bin is opened
    reward = jnp.where(is_new_bin, jnp.float32(-1.0), jnp.float32(0.0))
    rewards = state.rewards + reward

    # Legal actions for the *next* step
    legal = _legal_mask(bin_spaces, n_bins_used, state.n_items, step, state.items, max_items)

    # Observation
    obs = _make_observation(bin_spaces, n_bins_used, state.items, step, max_items)

    return BinPackingState(
        items=state.items,
        n_items=state.n_items,
        step=step,
        bin_spaces=bin_spaces,
        n_bins_used=n_bins_used,
        n_bins_opt=state.n_bins_opt,
        observation=obs,
        legal_action_mask=legal,
        terminated=terminated,
        rewards=rewards,
    )


def demo(batch_size: int = 8, n_steps: int = 4) -> None:
    """Init and step a batch of environments in parallel."""

    # Dummy state for debugging
    # state = init(jax.random.PRNGKey(0))  # DEBUG

    print(f"=== BinPackingEnv demo  batch={batch_size}  steps={n_steps} ===\n")

    rng = jax.random.PRNGKey(0)
    keys = jax.random.split(rng, batch_size)

    # Vectorised init
    states: BinPackingState = jax.jit(jax.vmap(init))(keys)

    print(f"n_items     : {states.n_items}")
    print(f"items[:4]   :\n{states.items[:, :4].round(3)}")
    print(f"legal[:4]   : {states.legal_action_mask[:, :4]}")
    print(f"obs shape   : {states.observation.shape}\n")

    # Greedy policy: pick the first legal action
    # argmax on a bool mask returns the index of the first True.
    @jax.jit
    @jax.vmap
    def greedy_step(state: BinPackingState) -> BinPackingState:
        action = jnp.argmax(state.legal_action_mask).astype(jnp.int32)
        return step_env(state, action)

    for i in range(n_steps):
        states = greedy_step(states)
        print(
            f"step {i + 1:2d} | "
            f"bins_used={states.n_bins_used} | "
            f"rewards={states.rewards.round(1)} | "
            f"done={states.terminated}"
        )

    print(f"\nn_bins_opt  : {states.n_bins_opt}")
    print(f"n_bins_used : {states.n_bins_used}")


if __name__ == "__main__":
    demo()
