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
import pickle
import sys
import time
from functools import partial

import numpy as np

import jax
import jax.numpy as jnp
import mctx

os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["JAX_TRACEBACK_FILTERING"] = "off"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pydantic import BaseModel

from env import (
    DEFAULT_MAX_ITEM_SIZE,
    DEFAULT_MAX_ITEMS,
    DEFAULT_MIN_ITEM_SIZE,
    BinPackingState,
    init,
    step_env,
)
from net import BinPackingNet, to_tokens


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
_CKPT_DIR = "/workspace/checkpoints/bin_packing_20260312173659"
_DEFAULT_CKPT = os.path.join(_CKPT_DIR, "000399.ckpt")
_DEFAULT_BATCH = 256
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

    # --- Load checkpoint -----------------------------------------------------
    print(f"Loading: {ckpt_path}")
    with open(ckpt_path, "rb") as f:
        ckpt = pickle.load(f)

    config = ckpt["config"]
    params = ckpt["params"]  # single-device params (saved as params[0] in train.py)
    print(f"Iteration : {ckpt['iteration']}")
    print(f"Config    : {config}")

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

    def recurrent_fn(params, rng_key, action, state: BinPackingState):
        del rng_key
        prev_rewards = state.rewards
        next_state = jax.vmap(_step)(state, action)
        tokens = jax.vmap(_to_tokens)(next_state.observation)
        value, bin_logits = net.apply(params, tokens)
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
    init_states: BinPackingState = jax.vmap(_init)(keys)

    n_bins_opt_mean = float(init_states.n_bins_opt.mean())
    n_bins_opt_std = float(init_states.n_bins_opt.std())
    print(f"\nGround truth  n_bins_opt : {n_bins_opt_mean:.2f} ± {n_bins_opt_std:.2f}  " f"(batch={batch_size})")

    # --- One JIT-compiled MCTS step ------------------------------------------

    @jax.jit
    def mcts_step(key: jnp.ndarray, state: BinPackingState):
        key, key1 = jax.random.split(key)
        tokens = jax.vmap(_to_tokens)(state.observation)
        value, all_logits = net.apply(params, tokens)
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
        return key, next_state

    # --- MCTS rollout (Python loop so JIT compiles once, reuses thereafter) --
    print(f"\nRunning MCTS evaluation  " f"(batch={batch_size}, num_simulations={num_simulations}) ...")
    print("JIT-compiling first step (may take ~1 min) ...")

    rng, subkey = jax.random.split(rng)
    state = init_states
    step_count = 0
    t0 = time.time()

    while not bool(jnp.all(state.terminated)):
        subkey, state = mcts_step(subkey, state)
        step_count += 1
        if step_count == 1:
            state.terminated.block_until_ready()
            print(f"  First step compiled in {time.time() - t0:.1f}s, continuing ...")
        if step_count % 10 == 0:
            n_done = int(jnp.sum(state.terminated))
            print(f"  step {step_count:3d}  episodes done: {n_done}/{batch_size}")

    state.terminated.block_until_ready()
    mcts_elapsed = time.time() - t0
    mcts_final = state

    mcts_ratio = mcts_final.n_bins_opt / mcts_final.n_bins_used

    # --- FFD greedy evaluation -----------------------------------------------
    print(f"\nRunning FFD greedy evaluation ...")

    @jax.jit
    def greedy_body(state: BinPackingState) -> BinPackingState:
        actions = jnp.argmax(state.legal_action_mask, axis=-1)
        return jax.vmap(_step)(state, actions)

    greedy_state = init_states
    t1 = time.time()
    while not bool(jnp.all(greedy_state.terminated)):
        greedy_state = greedy_body(greedy_state)
    greedy_state.terminated.block_until_ready()
    greedy_elapsed = time.time() - t1

    greedy_final = greedy_state
    greedy_ratio = greedy_final.n_bins_opt / greedy_final.n_bins_used

    # --- Report --------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Checkpoint  : {ckpt_path}")
    print(f"Iteration   : {ckpt['iteration']}")
    print(f"Batch size  : {batch_size}")
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
    # Show 10 episodes in a 10×2 grid: left = FFD greedy, right = MCTS.
    # Both columns use the same initial states.

    N_VIS = 10
    n_vis = min(N_VIS, batch_size)
    vis_init = jax.tree_util.tree_map(lambda x: x[:n_vis], init_states)
    n_bins_opt_vis = np.asarray(jax.device_get(vis_init.n_bins_opt))

    def track_episodes(get_actions_fn):
        """Run n_vis episodes with get_actions_fn, returning bin_contents and n_bins_used."""
        bin_contents = [[[] for _ in range(max_items)] for _ in range(n_vis)]
        state = vis_init

        while not bool(jnp.all(state.terminated)):
            actions = get_actions_fn(state)

            actions_np = np.asarray(jax.device_get(actions))
            steps_np = np.asarray(jax.device_get(state.step))
            items_np = np.asarray(jax.device_get(state.items))
            terminated_np = np.asarray(jax.device_get(state.terminated))

            for ep in range(n_vis):
                if terminated_np[ep]:
                    continue
                action = int(actions_np[ep])
                step_idx = int(steps_np[ep])
                item_size = float(items_np[ep, step_idx])
                bin_contents[ep][action].append(item_size)

            state = jax.vmap(_step)(state, actions)

        n_used = np.asarray(jax.device_get(state.n_bins_used))
        return bin_contents, n_used

    # Greedy action function
    @jax.jit
    def _greedy_actions(state: BinPackingState):
        return jnp.argmax(state.legal_action_mask, axis=-1)

    # MCTS action function
    @jax.jit
    def _mcts_actions(state: BinPackingState):
        key = jax.random.PRNGKey(0)  # deterministic at eval; key unused (gumbel_scale=0)
        tokens = jax.vmap(_to_tokens)(state.observation)
        value, all_logits = net.apply(params, tokens)
        bl = all_logits[:, 1 : max_items + 1]
        has_valid = jnp.any(state.legal_action_mask, axis=-1)
        fallback = jnp.zeros_like(state.legal_action_mask).at[:, 0].set(True)
        eff_mask = jnp.where(has_valid[:, None], state.legal_action_mask, fallback)
        bl = jnp.where(eff_mask, bl, neg_inf)
        root = mctx.RootFnOutput(prior_logits=bl, value=value, embedding=state)
        po = mctx.gumbel_muzero_policy(
            params=params,
            rng_key=key,
            root=root,
            recurrent_fn=recurrent_fn,
            num_simulations=num_simulations,
            invalid_actions=~eff_mask,
            qtransform=mctx.qtransform_completed_by_mix_value,
            gumbel_scale=0.0,
        )
        return jnp.argmax(po.action_weights, axis=-1)

    print(f"\nCollecting {n_vis} episodes (greedy) for visualization ...")
    greedy_contents, greedy_used = track_episodes(_greedy_actions)

    print(f"Collecting {n_vis} episodes (MCTS) for visualization ...")
    mcts_contents, mcts_used = track_episodes(_mcts_actions)

    # --- Build optimal bin contents from opt_assignment stored in init_states -
    opt_items_np = np.asarray(jax.device_get(vis_init.items))
    opt_assign_np = np.asarray(jax.device_get(vis_init.opt_assignment))
    opt_n_items_np = np.asarray(jax.device_get(vis_init.n_items))

    opt_contents = [[[] for _ in range(max_items)] for _ in range(n_vis)]
    for ep in range(n_vis):
        n_items_ep = int(opt_n_items_np[ep])
        for i in range(n_items_ep):
            bin_id = int(opt_assign_np[ep, i])
            if bin_id >= 0:
                opt_contents[ep][bin_id].append(float(opt_items_np[ep, i]))

    # --- Plot 10×3 grid ------------------------------------------------------
    from visualization import plot_grid

    plot_grid(
        columns=[
            (greedy_contents, greedy_used),
            (mcts_contents, mcts_used),
            (opt_contents, n_bins_opt_vis),
        ],
        col_headers=["FFD greedy", f"MCTS (iter {ckpt['iteration']})", "Optimum"],
        opt_per_row=n_bins_opt_vis.tolist(),
        out_path="bin_packing_eval.png",
    )


if __name__ == "__main__":
    main()
