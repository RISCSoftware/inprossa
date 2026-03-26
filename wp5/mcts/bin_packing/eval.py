"""Evaluate a trained bin-packing checkpoint using MCTS rollout.

Compares:
  - MCTS model  (gumbel_muzero_policy, same as selfplay in train.py)
  - FFD greedy  (first legal bin slot)
  - Ground truth (n_bins_opt stored in state at init)

Usage:
  python mcts/bin_packing/eval.py
  python mcts/bin_packing/eval.py checkpoint=/path/to/000400.ckpt batch_size=128 seed=0
"""

import os

os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["JAX_TRACEBACK_FILTERING"] = "off"


import pickle
import sys
import time
from functools import partial

import jax
import jax.numpy as jnp
import mctx
import numpy as np
from pydantic import BaseModel

from mcts.bin_packing.env import (
    DEFAULT_MAX_ITEM_SIZE,
    DEFAULT_MAX_ITEMS,
    DEFAULT_MIN_ITEM_SIZE,
    BinPackingState,
    init,
    step_env,
)
from mcts.bin_packing.net import BinPackingNet, make_attention_mask, to_tokens


# os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3"
os.environ["JAX_TRACEBACK_FILTERING"] = "off"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"


DEFAULT_MAX_ITEMS = 128  # DEBUG


# Must mirror train.py exactly so pickle can resolve __main__.Config
class Config(BaseModel):
    max_items: int = DEFAULT_MAX_ITEMS
    min_item_size: float = DEFAULT_MIN_ITEM_SIZE
    max_item_size: float = DEFAULT_MAX_ITEM_SIZE
    seed: int = 0
    max_num_iters: int = 400
    hidden_size: int = 192
    depth: int = 12
    num_heads: int = 3
    selfplay_batch_size: int = 512
    num_simulations: int = 2 * DEFAULT_MAX_ITEMS
    max_num_steps: int = DEFAULT_MAX_ITEMS
    training_batch_size: int = 128
    learning_rate: float = 1e-3
    weight_decay: float = 1e-2
    eval_interval: int = 5

    class Config:
        extra = "forbid"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# _CKPT_DIR = "/workspace/checkpoints/bin_packing_20260312000804"  # old encoding
# _CKPT_DIR = "/workspace/checkpoints/bin_packing_20260312173659"  # also old encoding
_CKPT_DIR = "/workspace/checkpoints/bin_packing_20260313133031"
_DEFAULT_CKPT = os.path.join(_CKPT_DIR, "000400.ckpt")
_DEFAULT_BATCH = 12  # DEBUG
_DEFAULT_SEED = 42


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # --- Parse CLI args (key=value style, same as train.py) -----------------
    ckpt_path = _DEFAULT_CKPT
    batch_size = _DEFAULT_BATCH
    seed = _DEFAULT_SEED

    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            if k == "checkpoint":
                ckpt_path = v
            elif k == "batch_size":
                batch_size = int(v)
            elif k == "seed":
                seed = int(v)

    # --- Devices -------------------------------------------------------------
    devices = jax.local_devices()
    num_devices = len(devices)
    print(f"Devices   : {num_devices}  ({[d.platform for d in devices]})")

    assert batch_size % num_devices == 0, f"batch_size {batch_size} must be divisible by num_devices {num_devices}"
    batch_per_device = batch_size // num_devices

    # --- Load checkpoint -----------------------------------------------------
    print(f"Loading: {ckpt_path}")
    with open(ckpt_path, "rb") as f:
        ckpt = pickle.load(f)

    # config = ckpt["config"]
    config = Config()
    params = ckpt["params"]  # single-device params (saved as params[0] in train.py)
    print(f"Iteration : {ckpt['iteration']}")
    print(f"Config    : {config}")

    # Replicate params to all devices
    params = jax.device_put_replicated(params, devices)

    max_items = config.max_items
    num_simulations = config.num_simulations

    _init = partial(
        init,
        max_items=max_items,
        min_item_size=config.min_item_size,
        max_item_size=config.max_item_size,
    )
    _step = partial(step_env, max_items=max_items)
    _to_tokens = partial(to_tokens, max_items=max_items)

    net = BinPackingNet(
        hidden_size=config.hidden_size,
        depth=config.depth,
        num_heads=config.num_heads,
    )
    neg_inf = jnp.finfo(jnp.float32).min

    # --- Recurrent function (identical to train.py) --------------------------
    # params is the first argument as per the mctx convention; pmap passes the
    # per-device slice automatically when this is called inside a pmapped fn.

    def recurrent_fn(params, rng_key, action, state: BinPackingState):
        del rng_key
        prev_rewards = state.rewards
        next_state = jax.vmap(_step)(state, action)
        tokens = jax.vmap(_to_tokens)(next_state.observation)
        mask = jax.vmap(make_attention_mask)(next_state.observation)  # (batch, SEQ_LEN, SEQ_LEN)
        value, bin_logits = net.apply(params, tokens, mask)
        logits = bin_logits[:, 1 : max_items + 1]
        logits = jnp.where(next_state.legal_action_mask, logits, neg_inf)
        reward = next_state.rewards - prev_rewards
        value = jnp.where(next_state.terminated, jnp.float32(0.0), value)
        discount = jnp.where(next_state.terminated, jnp.float32(0.0), jnp.float32(1.0))
        return (
            mctx.RecurrentFnOutput(
                reward=reward,
                discount=discount,
                prior_logits=logits,
                value=value,
            ),
            next_state,
        )

    # --- Initialise a fixed batch of environments ----------------------------
    rng = jax.random.PRNGKey(seed)
    rng, subkey = jax.random.split(rng)
    keys = jax.random.split(subkey, batch_size)
    init_states_flat: BinPackingState = jax.vmap(_init)(keys)

    n_bins_opt_mean = float(init_states_flat.n_bins_opt.mean())
    n_bins_opt_std = float(init_states_flat.n_bins_opt.std())
    print(f"\nGround truth  n_bins_opt : {n_bins_opt_mean:.2f} ± {n_bins_opt_std:.2f}  " f"(batch={batch_size})")

    # Reshape to (num_devices, batch_per_device, ...) for pmap
    def shard(x):
        return x.reshape((num_devices, batch_per_device) + x.shape[1:])

    def unshard(x):
        return x.reshape((-1,) + x.shape[2:])

    init_states: BinPackingState = jax.tree_util.tree_map(shard, init_states_flat)

    # --- Visualization setup (items array is fixed; record actions during eval) --
    N_VIS = 10
    n_vis = min(N_VIS, batch_size)
    # Capture items for ALL episodes; vis episode selection happens after both loops.
    all_items_np = np.asarray(jax.device_get(init_states_flat.items))  # (batch_size, max_items)

    def build_bin_contents(vis_records, episode_ids):
        """Replay recorded (steps, terminated, actions) tuples for selected episodes."""
        n = len(episode_ids)
        bin_contents = [[[] for _ in range(max_items)] for _ in range(n)]
        for steps, terminated, actions in vis_records:
            for out_ep, ep in enumerate(episode_ids):
                if terminated[ep]:
                    continue
                bin_contents[out_ep][actions[ep]].append(float(all_items_np[ep, steps[ep]]))
        return bin_contents

    # --- One pmap-compiled MCTS step -----------------------------------------

    @jax.pmap
    def mcts_step(params, key: jnp.ndarray, state: BinPackingState):
        key, key1 = jax.random.split(key)
        tokens = jax.vmap(_to_tokens)(state.observation)
        mask = jax.vmap(make_attention_mask)(state.observation)  # (batch, SEQ_LEN, SEQ_LEN)
        value, all_logits = net.apply(params, tokens, mask)
        bin_logits = all_logits[:, 1 : max_items + 1]

        # For already-terminated episodes the legal mask is all-False, which
        # would cause gumbel_muzero_policy to receive all-invalid actions.
        # Provide a dummy fallback so every batch entry has at least one valid
        # action; the resulting action is harmless (stepping a terminated state
        # with action 0 keeps terminated=True because step remains >= n_items).
        has_valid = jnp.any(state.legal_action_mask, axis=-1)  # (batch,)
        fallback = jnp.zeros_like(state.legal_action_mask).at[:, 0].set(True)
        effective_mask = jnp.where(has_valid[:, None], state.legal_action_mask, fallback)

        bin_logits = jnp.where(effective_mask, bin_logits, neg_inf)

        root = mctx.RootFnOutput(prior_logits=bin_logits, value=value, embedding=state)
        policy_output = mctx.gumbel_muzero_policy(
            params=params,
            rng_key=key1,
            root=root,
            recurrent_fn=recurrent_fn,
            num_simulations=num_simulations,
            invalid_actions=~effective_mask,
            qtransform=mctx.qtransform_completed_by_mix_value,
            gumbel_scale=0.0,
        )

        # At eval time take the greedy action from the MCTS-improved policy
        # (action_weights), not policy_output.action which includes Gumbel noise.
        action = jnp.argmax(policy_output.action_weights, axis=-1)
        next_state = jax.vmap(_step)(state, action)
        return key, next_state, action

    # --- MCTS rollout (Python loop so pmap compiles once, reuses thereafter) --
    print(f"\nRunning MCTS evaluation  " f"(batch={batch_size}, num_simulations={num_simulations}) ...")
    print("Compiling first step (may take ~1 min) ...")

    rng, subkey = jax.random.split(rng)
    pmap_keys = jax.random.split(subkey, num_devices)  # one key per device
    state = init_states
    step_count = 0
    t0 = time.time()
    mcts_vis_records = []  # list of (steps, terminated, actions) for vis episodes

    while not bool(jnp.all(state.terminated)):
        # Capture pre-step info for ALL episodes.
        # state is already synced (jnp.all above blocks); unshard is a free reshape.
        state_flat = jax.tree_util.tree_map(unshard, state)
        rec_steps = np.asarray(jax.device_get(state_flat.step))
        rec_terminated = np.asarray(jax.device_get(state_flat.terminated))

        pmap_keys, state, actions_sharded = mcts_step(params, pmap_keys, state)

        rec_actions = np.asarray(jax.device_get(actions_sharded)).reshape(batch_size)
        mcts_vis_records.append((rec_steps, rec_terminated, rec_actions))

        step_count += 1
        if step_count == 1:
            state.terminated.block_until_ready()
            print(f"  First step compiled in {time.time() - t0:.1f}s, continuing ...")
        if step_count % 10 == 0:
            n_done = int(jnp.sum(state.terminated))
            print(f"  step {step_count:3d}  episodes done: {n_done}/{batch_size}")

    state.terminated.block_until_ready()
    mcts_elapsed = time.time() - t0

    # Flatten device dimension for statistics
    mcts_final = jax.tree_util.tree_map(unshard, state)
    mcts_ratio = mcts_final.n_bins_opt / mcts_final.n_bins_used

    # --- FFD greedy evaluation -----------------------------------------------
    print(f"\nRunning FFD greedy evaluation ...")

    @jax.pmap
    def greedy_body(state: BinPackingState):
        actions = jnp.argmax(state.legal_action_mask, axis=-1)
        return jax.vmap(_step)(state, actions), actions

    greedy_state = init_states
    t1 = time.time()
    greedy_vis_records = []

    while not bool(jnp.all(greedy_state.terminated)):
        state_flat = jax.tree_util.tree_map(unshard, greedy_state)
        rec_steps = np.asarray(jax.device_get(state_flat.step))
        rec_terminated = np.asarray(jax.device_get(state_flat.terminated))

        greedy_state, actions_sharded = greedy_body(greedy_state)

        rec_actions = np.asarray(jax.device_get(actions_sharded)).reshape(batch_size)
        greedy_vis_records.append((rec_steps, rec_terminated, rec_actions))

    greedy_state.terminated.block_until_ready()
    greedy_elapsed = time.time() - t1

    # Flatten device dimension for statistics
    greedy_final = jax.tree_util.tree_map(unshard, greedy_state)
    greedy_ratio = greedy_final.n_bins_opt / greedy_final.n_bins_used

    # Select vis episodes: prefer those where MCTS saves the most bins vs greedy.
    # Sorting by descending improvement means the most interesting contrasts come first.
    mcts_bins_np = np.asarray(jax.device_get(mcts_final.n_bins_used))    # (batch_size,)
    greedy_bins_np = np.asarray(jax.device_get(greedy_final.n_bins_used))  # (batch_size,)
    improvement_np = greedy_bins_np - mcts_bins_np                         # higher = MCTS better
    vis_episode_ids = np.argsort(improvement_np)[::-1][:n_vis].tolist()

    mcts_bin_contents = build_bin_contents(mcts_vis_records, vis_episode_ids)
    greedy_bin_contents = build_bin_contents(greedy_vis_records, vis_episode_ids)
    mcts_used = mcts_bins_np[vis_episode_ids]
    greedy_used = greedy_bins_np[vis_episode_ids]

    # --- Report --------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Checkpoint  : {ckpt_path}")
    print(f"Iteration   : {ckpt['iteration']}")
    print(f"Batch size  : {batch_size}  ({num_devices} devices × {batch_per_device})")
    print(f"Simulations : {num_simulations}")
    print()
    print(f"Ground truth  n_bins_opt : {n_bins_opt_mean:.3f} ± {n_bins_opt_std:.3f}")
    print()
    print(
        f"MCTS model    n_bins_used: "
        f"{float(mcts_final.n_bins_used.mean()):.3f} ± "
        f"{float(mcts_final.n_bins_used.std()):.3f}  "
        f"[{mcts_elapsed:.1f}s]"
    )
    print(
        f"              opt ratio  : "
        f"{float(mcts_ratio.mean()):.4f} ± {float(mcts_ratio.std()):.4f}  "
        f"(1.0 = perfect)"
    )
    print()
    print(
        f"FFD greedy    n_bins_used: "
        f"{float(greedy_final.n_bins_used.mean()):.3f} ± "
        f"{float(greedy_final.n_bins_used.std()):.3f}  "
        f"[{greedy_elapsed:.1f}s]"
    )
    print(f"              opt ratio  : " f"{float(greedy_ratio.mean()):.4f} ± {float(greedy_ratio.std()):.4f}")
    print()
    improvement = float((mcts_ratio - greedy_ratio).mean())
    sign = "+" if improvement >= 0 else ""
    print(f"Improvement vs greedy    : {sign}{improvement:.4f}  (positive = better)")
    print("=" * 60)

    # --- Visualization -------------------------------------------------------
    # Build optimal bin contents from opt_assignment stored in init_states.
    all_n_bins_opt = np.asarray(jax.device_get(init_states_flat.n_bins_opt))
    all_opt_items = np.asarray(jax.device_get(init_states_flat.items))
    all_opt_assign = np.asarray(jax.device_get(init_states_flat.opt_assignment))
    all_n_items = np.asarray(jax.device_get(init_states_flat.n_items))

    n_bins_opt_vis = all_n_bins_opt[vis_episode_ids]
    opt_contents = [[[] for _ in range(max_items)] for _ in range(n_vis)]
    for out_ep, ep in enumerate(vis_episode_ids):
        for i in range(int(all_n_items[ep])):
            bin_id = int(all_opt_assign[ep, i])
            if bin_id >= 0:
                opt_contents[out_ep][bin_id].append(float(all_opt_items[ep, i]))

    from visualization import plot_grid

    plot_grid(
        columns=[
            (greedy_bin_contents, greedy_used),
            (mcts_bin_contents, mcts_used),
            (opt_contents, n_bins_opt_vis),
        ],
        col_headers=["FFD greedy", f"MCTS (iter {ckpt['iteration']})", "Optimum"],
        opt_per_row=n_bins_opt_vis.tolist(),
        out_path="bin_packing_eval.png",
    )


if __name__ == "__main__":
    main()
