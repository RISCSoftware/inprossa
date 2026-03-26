"""AlphaZero (Gumbel MuZero) training for single-player bin packing.

Structure mirrors pgx/examples/alphazero/train.py with these key differences:
  - Flax params only (no Haiku mutable state tuple)
  - Single-player discount = 1.0  (not -1.0 — no perspective flip)
  - Inline auto-reset via jnp.where over BinPackingState fields
  - Network input: token sequences from to_tokens(), not raw observations
  - Evaluation: optimality ratio vs. greedy first-fit baseline

Evaluation metrics:
  eval/model_optimality_ratio   = n_bins_opt / n_bins_used for the trained model
  eval/greedy_optimality_ratio  = n_bins_opt / n_bins_used for greedy first-fit
  eval/improvement_vs_greedy    = model_ratio - greedy_ratio  (positive = better than greedy)
  Ratio of 1.0 means perfect packing (matched the known optimal bin count).
  Higher is better; ratio > greedy means the model outperforms first-fit.

Eval policy note:
  evaluate() uses the raw network policy (prior logits, greedy argmax), not MCTS.
  This matches the pgx reference which documents: "A simplified evaluation by sampling.
  Only for debugging. Please use MCTS and run tournaments for serious evaluation."
"""

import pandas as pd
import datetime
import os
import pickle
import sys
import time
from functools import partial
from typing import NamedTuple

import jax
import jax.numpy as jnp
import mctx
import optax
import wandb
from omegaconf import OmegaConf
from pydantic import BaseModel

os.environ["CUDA_VISIBLE_DEVICES"] = "1,2"
# os.environ["CUDA_VISIBLE_DEVICES"] = "2"
os.environ["JAX_TRACEBACK_FILTERING"] = "off"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"

# Ensure mcts/ and mcts/bin_packing/ are importable regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


from env import (
    DEFAULT_MAX_ITEM_SIZE,
    DEFAULT_MAX_ITEMS,
    DEFAULT_MIN_ITEM_SIZE,
    BinPackingState,
    init,
    step_env,
)
from net import BinPackingNet, to_tokens

devices = jax.local_devices()
num_devices = len(devices)


class Config(BaseModel):
    max_items: int = DEFAULT_MAX_ITEMS
    min_item_size: float = DEFAULT_MIN_ITEM_SIZE
    max_item_size: float = DEFAULT_MAX_ITEM_SIZE
    seed: int = 0
    max_num_iters: int = 400
    # network
    hidden_size: int = 192
    depth: int = 12
    num_heads: int = 3
    # selfplay
    selfplay_batch_size: int = 512  # no of envs in parallel (lanes) (all gpus combined)
    num_simulations: int = 2 * DEFAULT_MAX_ITEMS # no of rollouts
    # max_num_steps: int = 10 * DEFAULT_MAX_ITEMS  # at least 10 episodes per lane
    max_num_steps: int = DEFAULT_MAX_ITEMS  # at least 1 finished episodes per lane
    # training
    training_batch_size: int = 128  # batch size for gradient updates (all gpus combined)
    learning_rate: float = 1e-3
    weight_decay: float = 1e-2
    # eval
    eval_interval: int = 5

    class Config:
        extra = "forbid"


conf_dict = OmegaConf.from_cli()
config: Config = Config(**conf_dict)
print(config)

# Partials with fixed env hyperparameters
_init = partial(
    init,
    max_items=config.max_items,
    min_item_size=config.min_item_size,
    max_item_size=config.max_item_size,
)
_step = partial(step_env, max_items=config.max_items)
_to_tokens = partial(to_tokens, max_items=config.max_items)

# Network (Flax — only params are mutable, no running stats)
net = BinPackingNet(
    hidden_size=config.hidden_size,
    depth=config.depth,
    num_heads=config.num_heads,
)
# optimizer = optax.adam(learning_rate=config.learning_rate)
optimizer = optax.adamw(
    learning_rate=config.learning_rate,
    weight_decay=config.weight_decay,
)

# Token sequence length: 1 value token + max_items bin tokens + max_items item tokens
SEQ_LEN: int = 1 + 2 * config.max_items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tree_where(cond: jnp.ndarray, true_tree, false_tree):
    """Element-wise where over a JAX pytree.  cond shape: (batch,)."""
    return jax.tree.map(
        lambda t, f: jnp.where(cond.reshape((-1,) + (1,) * (t.ndim - 1)), t, f),
        true_tree,
        false_tree,
    )


# ---------------------------------------------------------------------------
# MuZero recurrent function
# ---------------------------------------------------------------------------


def recurrent_fn(params, rng_key: jnp.ndarray, action: jnp.ndarray, state: BinPackingState):
    """Step the env and evaluate the resulting state for Gumbel MuZero search."""
    del rng_key
    prev_rewards = state.rewards  # (batch,) cumulative

    next_state = jax.vmap(_step)(state, action)
    tokens = jax.vmap(_to_tokens)(next_state.observation)  # (batch, SEQ_LEN, 7)
    value, bin_logits = net.apply(params, tokens)

    # Slice bin logits to action space [1 .. max_items] and mask illegal actions
    logits = bin_logits[:, 1 : config.max_items + 1]  # (batch, max_items)
    neg_inf = jnp.finfo(jnp.float32).min
    logits = jnp.where(next_state.legal_action_mask, logits, neg_inf)

    reward = next_state.rewards - prev_rewards  # per-step reward (0 or -1)
    value = jnp.where(next_state.terminated, jnp.float32(0.0), value)
    discount = jnp.where(
        next_state.terminated, jnp.float32(0.0), jnp.float32(1.0)
    )  # single-player: no perspective flip

    return (
        mctx.RecurrentFnOutput(
            reward=reward,
            discount=discount,
            prior_logits=logits,
            value=value,
        ),
        next_state,
    )


# ---------------------------------------------------------------------------
# Selfplay
# ---------------------------------------------------------------------------


class SelfplayOutput(NamedTuple):
    observation: jnp.ndarray  # (max_num_steps, batch, 2*max_items)
    reward: jnp.ndarray  # (max_num_steps, batch)
    terminated: jnp.ndarray  # (max_num_steps, batch)
    action_weights: jnp.ndarray  # (max_num_steps, batch, max_items)
    discount: jnp.ndarray  # (max_num_steps, batch)


@jax.pmap
def selfplay(params, rng_key: jnp.ndarray) -> SelfplayOutput:
    batch_size = config.selfplay_batch_size // num_devices

    def step_fn(state: BinPackingState, xs):
        key, step_idx = xs
        # jax.debug.print("step: {step}", step=step_idx)
        key1, key2 = jax.random.split(key)

        # Evaluate the current state
        tokens = jax.vmap(_to_tokens)(state.observation)  # (batch, SEQ_LEN, 7)
        value, all_logits = net.apply(params, tokens)
        bin_logits = all_logits[:, 1 : config.max_items + 1]  # (batch, max_items)
        neg_inf = jnp.finfo(jnp.float32).min
        bin_logits = jnp.where(state.legal_action_mask, bin_logits, neg_inf)

        root = mctx.RootFnOutput(prior_logits=bin_logits, value=value, embedding=state)
        policy_output = mctx.gumbel_muzero_policy(
            params=params,
            rng_key=key1,
            root=root,
            recurrent_fn=recurrent_fn,
            num_simulations=config.num_simulations,
            invalid_actions=~state.legal_action_mask,
            qtransform=mctx.qtransform_completed_by_mix_value,
            gumbel_scale=1.0,
        )

        prev_rewards = state.rewards
        next_state = jax.vmap(_step)(state, policy_output.action)
        reward = next_state.rewards - prev_rewards
        discount = jnp.where(next_state.terminated, jnp.float32(0.0), jnp.float32(1.0))

        # Auto-reset terminated episodes (keeps fixed array shapes under JIT)
        reset_keys = jax.random.split(key2, batch_size)
        reset_state = jax.vmap(_init)(reset_keys)
        carry = _tree_where(next_state.terminated, reset_state, next_state)

        return carry, SelfplayOutput(
            observation=state.observation,
            reward=reward,
            terminated=next_state.terminated,
            action_weights=policy_output.action_weights,
            discount=discount,
        )

    rng_key, sub_key = jax.random.split(rng_key)
    keys = jax.random.split(sub_key, batch_size)
    state = jax.vmap(_init)(keys)

    key_seq = jax.random.split(rng_key, config.max_num_steps)
    step_indices = jnp.arange(config.max_num_steps)
    _, data = jax.lax.scan(step_fn, state, (key_seq, step_indices))
    return data


# ---------------------------------------------------------------------------
# Loss input computation
# ---------------------------------------------------------------------------


class Sample(NamedTuple):
    observation: jnp.ndarray  # (batch, 2*max_items)
    # policy and value target
    policy_tgt: jnp.ndarray  # (batch, max_items)
    value_tgt: jnp.ndarray  # (batch,)
    mask: jnp.ndarray  # (batch,)  — 0 for truncated episodes


@jax.pmap
def compute_loss_input(data: SelfplayOutput) -> Sample:
    batch_size = config.selfplay_batch_size // num_devices

    # True for steps that belong to a completed episode
    value_mask = jnp.cumsum(data.terminated[::-1, :], axis=0)[::-1, :] >= 1

    # Backward scan: v_t = r_t + discount_t * v_{t+1}
    def body_fn(carry, i):
        ix = config.max_num_steps - i - 1
        v = data.reward[ix] + data.discount[ix] * carry
        return v, v

    _, value_tgt = jax.lax.scan(
        body_fn,
        jnp.zeros(batch_size),
        jnp.arange(config.max_num_steps),
    )
    value_tgt = value_tgt[::-1, :]

    return Sample(
        observation=data.observation,
        policy_tgt=data.action_weights,
        value_tgt=value_tgt,
        mask=value_mask,
    )


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def loss_fn(params, samples: Sample):
    tokens = jax.vmap(_to_tokens)(samples.observation)
    value, bin_logits = net.apply(params, tokens)
    logits = bin_logits[:, 1 : config.max_items + 1]  # (batch, max_items)

    policy_loss = optax.softmax_cross_entropy(logits, samples.policy_tgt)
    policy_loss = jnp.mean(policy_loss)

    value_loss = optax.l2_loss(value, samples.value_tgt)
    value_loss = (value_loss * samples.mask).sum() / jnp.maximum(samples.mask.sum(), 1)

    return policy_loss + value_loss, (policy_loss, value_loss)


@partial(jax.pmap, axis_name="i")
def train(params, opt_state, data: Sample):
    grads, (policy_loss, value_loss) = jax.grad(loss_fn, has_aux=True)(params, data)
    grads = jax.lax.pmean(grads, axis_name="i")
    updates, opt_state = optimizer.update(grads, opt_state, params)
    params = optax.apply_updates(params, updates)
    return params, opt_state, policy_loss, value_loss


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


@jax.pmap
def evaluate(rng_key: jnp.ndarray, params):
    """Optimality ratio (n_bins_opt / n_bins_used) for model and greedy first-fit."""
    batch_size = config.selfplay_batch_size // num_devices
    neg_inf = jnp.finfo(jnp.float32).min

    key, subkey = jax.random.split(rng_key)
    keys = jax.random.split(subkey, batch_size)
    init_states = jax.vmap(_init)(keys)

    # Trained model: greedy argmax of policy logits
    def model_body(val):
        key, state = val
        tokens = jax.vmap(_to_tokens)(state.observation)
        _, bin_logits = net.apply(params, tokens)
        logits = bin_logits[:, 1 : config.max_items + 1]
        logits = jnp.where(state.legal_action_mask, logits, neg_inf)
        actions = jnp.argmax(logits, axis=-1)
        return key, jax.vmap(_step)(state, actions)

    _, model_final = jax.lax.while_loop(
        lambda val: ~jnp.all(val[1].terminated),
        model_body,
        (key, init_states),
    )

    # Greedy first-fit: first (lowest-index) legal bin slot
    def greedy_body(state):
        actions = jnp.argmax(state.legal_action_mask, axis=-1)
        return jax.vmap(_step)(state, actions)

    greedy_final = jax.lax.while_loop(
        lambda s: ~jnp.all(s.terminated),
        greedy_body,
        init_states,
    )

    # Optimality ratio: 1.0 = perfect packing, lower = more bins wasted
    model_ratio = model_final.n_bins_opt / model_final.n_bins_used
    greedy_ratio = greedy_final.n_bins_opt / greedy_final.n_bins_used
    return model_ratio, greedy_ratio


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    wandb.init(project="bin-packing-az", config=config.model_dump())

    # Initialize model params (Flax — no mutable state)
    dummy_tokens = jnp.zeros((2, SEQ_LEN, 7), dtype=jnp.float32)
    params = net.init(jax.random.PRNGKey(config.seed), dummy_tokens)
    opt_state = optimizer.init(params)
    # Replicate to all devices
    params, opt_state = jax.device_put_replicated((params, opt_state), devices)

    # Checkpoint directory
    now = datetime.datetime.now(datetime.timezone.utc)
    now = now.strftime("%Y%m%d%H%M%S")
    ckpt_dir = os.path.join("checkpoints", f"bin_packing_{now}")
    os.makedirs(ckpt_dir, exist_ok=True)

    iteration: int = 0
    hours: float = 0.0
    frames: int = 0
    log = {"iteration": iteration, "hours": hours, "frames": frames}

    rng_key = jax.random.PRNGKey(config.seed)
    while True:
        # Evaluate and checkpoint at specified intervals
        if iteration % config.eval_interval == 0 and iteration > 0:  # TODO: DEBUG: remove iteration > 0
            rng_key, subkey = jax.random.split(rng_key)
            keys = jax.random.split(subkey, num_devices)
            model_ratio, greedy_ratio = evaluate(keys, params)
            log.update(
                {
                    "eval/model_optimality_ratio": model_ratio.mean().item(),
                    "eval/greedy_optimality_ratio": greedy_ratio.mean().item(),
                    "eval/improvement_vs_greedy": (model_ratio - greedy_ratio).mean().item(),
                }
            )

            # Checkpoint
            params_0, opt_state_0 = jax.tree_util.tree_map(lambda x: x[0], (params, opt_state))
            with open(os.path.join(ckpt_dir, f"{iteration:06d}.ckpt"), "wb") as f:
                pickle.dump(
                    {
                        "config": config,
                        "rng_key": rng_key,
                        "params": jax.device_get(params_0),
                        "opt_state": jax.device_get(opt_state_0),
                        "iteration": iteration,
                        "frames": frames,
                        "hours": hours,
                    },
                    f,
                )

        print(log)
        wandb.log(log)

        if iteration >= config.max_num_iters:
            break

        iteration += 1
        log = {"iteration": iteration}
        st = time.time()

        # Selfplay
        rng_key, subkey = jax.random.split(rng_key)
        keys = jax.random.split(subkey, num_devices)
        data: SelfplayOutput = selfplay(params, keys)
        # data.observation.shape: (devices, max_num_steps, n_envs_parallel, 2 * max_items)
        # data.reward.shape: (devices, max_num_steps, n_envs_parallel)

        samples: Sample = compute_loss_input(data)

        # df = pd.DataFrame(data.observation[0, :DEFAULT_MAX_ITEMS, 0, :])
        # print(df.to_string(index=False))

        # Gather from devices, flatten (num_devices × max_num_steps × batch_per_device), shuffle
        # After pmap: (num_devices, max_num_steps, batch_per_device, ...)
        samples = jax.device_get(samples)
        samples = jax.tree_util.tree_map(lambda x: x.reshape((-1, *x.shape[3:])), samples)
        frames += samples.observation.shape[0]
        rng_key, subkey = jax.random.split(rng_key)
        ixs = jax.random.permutation(subkey, jnp.arange(samples.observation.shape[0]))
        samples = jax.tree_util.tree_map(lambda x: x[ixs], samples)

        num_updates = samples.observation.shape[0] // config.training_batch_size
        minibatches = jax.tree_util.tree_map(lambda x: x.reshape((num_updates, num_devices, -1) + x.shape[1:]), samples)

        # Training
        policy_losses, value_losses = [], []
        for i in range(num_updates):
            minibatch: Sample = jax.tree_util.tree_map(lambda x: x[i], minibatches)
            params, opt_state, policy_loss, value_loss = train(params, opt_state, minibatch)
            policy_losses.append(policy_loss.mean().item())
            value_losses.append(value_loss.mean().item())

        et = time.time()
        hours += (et - st) / 3600
        log.update(
            {
                "train/policy_loss": sum(policy_losses) / len(policy_losses),
                "train/value_loss": sum(value_losses) / len(value_losses),
                "hours": hours,
                "frames": frames,
            }
        )
