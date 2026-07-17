# inprossa-mctx

JAX + Flax implementations of **AlphaZero (Gumbel MuZero)** self-play training for combinatorial optimisation problems.

## Installation

```bash
uv sync
```

Requires Python 3.12. GPU with CUDA 12 is recommended (JAX + PyTorch CUDA builds).

## Tech Stack

- **JAX** + **Flax** — neural network and automatic differentiation
- **DeepMind `mctx`** — Monte Carlo Tree Search (Gumbel MuZero)
- **Optax** — AdamW optimizer
- **OmegaConf** — CLI configuration
- **Weights & Biases** — experiment tracking
- **Matplotlib** — visualisation

---

# Part 1 — Bin Packing

The agent learns to pack items into bins of capacity 1, minimising the number of bins used. Evaluation compares the MCTS-guided model against a greedy first-fit-decreasing (FFD) baseline and the known optimal solution.

## Architecture

```
env.py  (BinPackingState — JAX JIT-able bin-packing environment)
   │
   ▼
net.py (to_tokens → BinPackingNet: policy + value on TransformerBackbone)
   │
   ▼
train.py (self-play + MCTS via DeepMind mctx + gradient updates → checkpoints)
   │
   ▼
eval.py  (MCTS rollout vs. FFD greedy vs. optimal → bin_packing_eval.png)
```

| Module                              | Description                                                                                     |
| ----------------------------------- | ----------------------------------------------------------------------------------------------- |
| `mcts/bin_packing/env.py`           | JAX bin-packing environment: `BinPackingState`, `init()`, `step_env()`, observation, legal mask |
| `mcts/bin_packing/net.py`           | `BinPackingNet` (policy + value) on `TransformerBackbone`; 6-dim token encoding                 |
| `mcts/transformer_.py`              | `TransformerBackbone` Flax module (self-attention + MLP, optional AdaLN, causal masking)        |
| `mcts/bin_packing/train.py`         | AlphaZero / Gumbel MuZero training loop (self-play → MCTS → gradient updates → checkpoints)     |
| `mcts/bin_packing/eval.py`          | Evaluate a checkpoint: MCTS vs. greedy FFD vs. optimal; produces `bin_packing_eval.png`         |
| `mcts/bin_packing/test_net.py`      | Unit tests for `to_tokens()`                                                                    |
| `mcts/bin_packing/visualization.py` | `plot_solution()` and `plot_grid()` — stacked bar charts of bin packings                        |

## Entry Points

No `console_scripts` are defined in `pyproject.toml`. All entry points are run as
direct Python module invocations from the workspace root.

### Train

```bash
python mcts/bin_packing/train.py [key=value ...]
```

All `Config` fields can be overridden via `key=value` syntax (`OmegaConf.from_cli()`).
Training logs to **Weights & Biases** (`project="bin-packing-az"`) and saves
checkpoints to `checkpoints/bin_packing_<timestamp>/`.

Default configuration:

| Parameter             | Default | Description                                 |
| --------------------- | ------- | ------------------------------------------- |
| `max_items`           | 64      | Maximum number of items per instance        |
| `min_items`           | 8       | Minimum number of items per instance        |
| `min_item_size`       | 0.3     | Minimum item size                           |
| `max_item_size`       | 0.7     | Maximum item size                           |
| `seed`                | 0       | Random seed                                 |
| `max_num_iters`       | 400     | Total training iterations                   |
| `hidden_size`         | 192     | Transformer hidden dimension                |
| `depth`               | 12      | Number of transformer blocks                |
| `num_heads`           | 3       | Number of attention heads                   |
| `selfplay_batch_size` | 128     | Number of parallel environments (lanes)     |
| `num_simulations`     | 128     | MCTS rollouts per move (2 × max_items)      |
| `max_num_steps`       | 256     | Steps per self-play episode (4 × max_items) |
| `training_batch_size` | 128     | Gradient update batch size                  |
| `learning_rate`       | 1e-3    | AdamW learning rate                         |
| `weight_decay`        | 1e-2    | AdamW weight decay                          |
| `eval_interval`       | 5       | Evaluate + checkpoint every N iterations    |

Examples:

```bash
# Default training (400 iterations, 8–64 items)
python mcts/bin_packing/train.py

# Override key parameters
python mcts/bin_packing/train.py max_num_iters=100 selfplay_batch_size=64

# Offline wandb logging, tee output to a file
WANDB_MODE=offline python mcts/bin_packing/train.py 2>&1 | tee out6.log
```

**Checkpoint format:** Each checkpoint is a pickle file
`checkpoints/bin_packing_<timestamp>/<iteration:06d>.ckpt` containing:
`config`, `rng_key`, `params`, `opt_state`, `iteration`, `frames`, `hours`.

### Evaluate

```bash
python mcts/bin_packing/eval.py [checkpoint=<path>] [batch_size=<n>] [seed=<n>]
```

Loads a trained checkpoint and runs three solvers on the same batch of instances:

1. **MCTS model** — `mctx.gumbel_muzero_policy` with greedy action selection
2. **FFD greedy** — always picks the first legal bin (first-fit-decreasing)
3. **Optimal** — ground-truth optimal bin count stored in `BinPackingState`

Outputs an **optimality ratio** (`n_bins_opt / n_bins_used`, 1.0 = perfect) for
each method, the improvement of MCTS over greedy, and a visualisation file
`bin_packing_eval.png` showing side-by-side bin packings.

| Parameter    | Default                                                         |
| ------------ | --------------------------------------------------------------- |
| `checkpoint` | `/workspace/checkpoints/bin_packing_20260313221141/000400.ckpt` |
| `batch_size` | 12                                                              |
| `seed`       | 42                                                              |

### Unit tests

```bash
pytest mcts/bin_packing/test_net.py -v
```

### Environment demo

```bash
python mcts/bin_packing/env.py
```

Steps through a single bin-packing episode, prints statistics, and saves
`bin_packing_opt_demo.png`.

## Existing Checkpoints

| Directory                                 | Description                             |
| ----------------------------------------- | --------------------------------------- |
| `checkpoints/bin_packing_20260313133031/` | Trained on 32 items                     |
| `checkpoints/bin_packing_20260313221141/` | Trained on 8–64 items (current default) |

Each directory contains checkpoints from iteration 0 to 400 in steps of 5.

## Evaluation Metrics

| Metric                         | Description                                                           |
| ------------------------------ | --------------------------------------------------------------------- |
| `eval/model_optimality_ratio`  | `n_bins_opt / n_bins_used` for the trained MCTS model (1.0 = perfect) |
| `eval/greedy_optimality_ratio` | Same ratio for greedy FFD                                             |
| `eval/improvement_vs_greedy`   | `model_ratio - greedy_ratio` (positive = model beats greedy)          |

---

# Part 2 — Glulam Beam Assembly Problem (Leimbinder)

> **Status: Not yet implemented.**

Placeholder for a future AlphaZero / Gumbel MuZero approach to the glulam beam
assembly (Leimbinder) problem. The implementation will follow the same
architecture as bin packing — JAX environment, transformer policy/value network,
self-play training with `mctx`, and evaluation against greedy baselines.
