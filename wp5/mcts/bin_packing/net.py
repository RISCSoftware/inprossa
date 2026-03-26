import os

import flax.linen as nn
import jax
import jax.numpy as jnp
from tqdm import tqdm

from mcts.transformer_ import TransformerBackbone

TOKEN_DIM = 6

# Input token layout (dim=6):
#   dim 0: 1 if value-estimation token, 0 otherwise
#   dim 1: 1 if bin token (used bin or new-bin slot); 0 for padding and non-bin tokens
#   dim 2: remaining capacity of this bin (0 for padding)
#   dim 3: 1 if item token (real, non-padding item); 0 otherwise
#   dim 4: size of the item (0 for padding)
#   dim 5: 1 if this is the next item to assign, 0 otherwise
#
# Padding tokens are all-zero vectors used for unused bin slots and unassigned item slots.


def to_tokens(
    obs: jnp.ndarray,
    max_items: int,
) -> jnp.ndarray:
    """Return (1 + 2*max_items, d_in) token sequence ready for BinPackingNet.

    obs is the (2*max_items,) observation from BinPackingState.observation.

    Layout:
      token 0                          : value token   [1, 0, 0,   0, 0,    0]
      tokens 1..n_used                 : used bins     [0, 1, cap, 0, 0,    0]
      token  n_used+1                  : new-bin slot  [0, 1, 1,   0, 0,    0]
      tokens n_used+2..max_items       : padding       [0, 0, 0,   0, 0,    0]
      tokens max_items+1..max_items+n  : item tokens   [0, 0, 0,   1, size, is_next]
      tokens max_items+n+1..2*max_items: padding       [0, 0, 0,   0, 0,    0]

    Bin tokens are in action-index order (token i+1 = action i).  Unused bin
    slots beyond the new-bin slot and unassigned item slots beyond the real
    items are all-zero padding tokens.  is_next=1 at item position 0 if any
    items remain.
    """
    bin_cap = obs[:max_items]  # (max_items,) — directly from observation
    item_sizes = obs[max_items:]  # (max_items,)

    # Bin tokens: used bins (cap < 1.0) plus the first unused slot (new-bin action).
    # Slots beyond the new-bin slot are padding (all zeros).
    is_used = bin_cap < 1.0
    is_new_slot = (bin_cap == 1.0) & (jnp.cumsum(bin_cap == 1.0) == 1)
    is_bin = (is_used | is_new_slot).astype(jnp.float32)

    bin_tokens = jnp.stack(
        [
            jnp.zeros(max_items),  # dim 0: not a value token
            is_bin,  # dim 1: 1 for bins (used + new-bin slot); 0 = padding
            bin_cap * is_bin,  # dim 2: capacity; zeroed for padding slots
            jnp.zeros(max_items),  # dim 3: not an item token
            jnp.zeros(max_items),  # dim 4: no item size
            jnp.zeros(max_items),  # dim 5: not the next item
        ],
        axis=-1,
    )  # (max_items, d_in)

    is_real_item = (item_sizes > 0).astype(jnp.float32)
    is_next = jnp.zeros(max_items, dtype=jnp.float32).at[0].set((item_sizes[0] > 0).astype(jnp.float32))
    item_tokens = jnp.stack(
        [
            jnp.zeros(max_items),  # dim 0: not a value token
            jnp.zeros(max_items),  # dim 1: not a bin token
            jnp.zeros(max_items),  # dim 2: no bin capacity
            is_real_item,  # dim 3: 1 for real items only; 0 = padding
            item_sizes,  # dim 4: item size (0 for padding slots)
            is_next,  # dim 5: 1 at position 0 if items remain
        ],
        axis=-1,
    )  # (max_items, d_in)

    value_token = jnp.array([[1, 0, 0, 0, 0, 0]], dtype=jnp.float32)
    return jnp.concatenate([value_token, bin_tokens, item_tokens], axis=0)
    # shape: (1 + 2*max_items, d_in)


def make_attention_mask(obs: jnp.ndarray) -> jnp.ndarray:
    """Return (S, S) bool attention mask for a single observation, S = 1 + 2*max_items.

    obs is the (2*max_items,) observation from BinPackingState.observation;
    max_items is inferred as obs.shape[0] // 2.

    The (S,) token validity vector is:
      token 0                          : value token         → always 1
      tokens 1..n_used                 : used bins           → 1
      token  n_used+1                  : new-bin slot        → 1
      tokens n_used+2..max_items       : padding bin slots   → 0
      tokens max_items+1..max_items+n  : real item tokens    → 1
      tokens max_items+n+1..2*max_items: padding item slots  → 0

    The (S, S) mask is valid[i] & valid[j]: both query and key must be non-padding.
    Mirrors the is_bin / is_real_item logic in to_tokens() exactly.
    """
    max_items = obs.shape[0] // 2
    bin_cap = obs[:max_items]
    item_sizes = obs[max_items:]

    is_used = bin_cap < 1.0
    is_new_slot = (bin_cap == 1.0) & (jnp.cumsum(bin_cap == 1.0) == 1)
    is_bin = is_used | is_new_slot  # (max_items,) bool

    is_real_item = item_sizes > 0  # (max_items,) bool

    value_mask = jnp.array([True])
    valid = jnp.concatenate([value_mask, is_bin, is_real_item])  # (S,)
    return valid[:, None] & valid[None, :]  # (S, S)


class BinPackingNet(nn.Module):
    """
    Policy + value network for bin packing, built on TransformerBackbone.

    Outputs:
      value      - scalar value estimate                (batch,)
      bin_logits - raw (pre-softmax) logits per token  (batch, seq_len)  non-bin positions = -inf
    """

    hidden_size: int = 192  # deit-tiny d_model
    depth: int = 12  # deit-tiny num_hidden_layers
    num_heads: int = 3  # deit-tiny num_attention_heads
    mlp_ratio: int = 4  # intermediate_size = 4 * hidden_size = 768

    @nn.compact
    def __call__(self, tokens: jnp.ndarray, mask: jnp.ndarray):
        # tokens: (batch, seq_len, TOKEN_DIM)
        # mask:   (batch, seq_len, seq_len) bool — from jax.vmap(make_attention_mask)(obs)

        # --- extract type masks from input features ---
        value_mask = tokens[..., 0]  # (batch, seq_len)  exactly 1 value token per seq
        bin_mask = tokens[..., 1]  # (batch, seq_len)
        # item_mask = tokens[..., 3]  # (batch, seq_len)  — now at dim 3 after dim-2 removal

        # --- embed TOKEN_DIM → hidden_size ---
        x = nn.Dense(self.hidden_size)(tokens)  # (batch, seq_len, hidden_size)

        # --- transformer backbone ---
        x = TransformerBackbone(
            hidden_size=self.hidden_size,
            depth=self.depth,
            num_heads=self.num_heads,
            mlp_ratio=self.mlp_ratio,
        )(
            x, mask=mask
        )  # (batch, seq_len, hidden_size)

        # --- shared scalar output head ---
        scalars = nn.Dense(1)(x)[..., 0]  # (batch, seq_len)

        # --- value estimate: read out the single value token ---
        value = jnp.sum(scalars * value_mask, axis=-1)  # (batch,)

        # --- bin logits: raw scores for bin positions, -inf elsewhere ---
        neg_inf = jnp.finfo(jnp.float32).min
        bin_logits = jnp.where(bin_mask.astype(bool), scalars, neg_inf)  # (batch, seq_len)

        return value, bin_logits


def demo():
    # Toy sequence: 1 value token + 3 bin tokens + 4 item tokens
    #               (batch=2, seq_len=8, d_in)
    tokens = jnp.array(
        [
            [
                [1, 0, 0, 0, 0, 0],  # value token
                [0, 1, 8, 0, 0, 0],  # bin 0, active, remaining=8
                [0, 1, 5, 0, 0, 0],  # bin 1, active, remaining=5
                [0, 1, 3, 0, 0, 0],  # bin 2, active, remaining=3
                [0, 0, 0, 1, 2, 1],  # item 0, size=2, next-to-assign
                [0, 0, 0, 1, 4, 0],  # item 1, size=4
                [0, 0, 0, 1, 3, 0],  # item 2, size=3
                [0, 0, 0, 1, 1, 0],  # item 3, size=1
            ]
        ]
        * 2,
        dtype=jnp.float32,
    )  # batch=2

    s = tokens.shape[1]
    mask = jnp.ones((tokens.shape[0], s, s), dtype=jnp.bool_)

    model = BinPackingNet()
    params = jax.jit(model.init)(jax.random.PRNGKey(0), tokens, mask)

    n_params = sum(p.size for p in jax.tree.leaves(params))
    print(f"Parameter count: {n_params:,}  ({n_params / 1e6:.2f}M)")

    value, bin_logits = jax.jit(model.apply)(params, tokens, mask)
    print(f"value:      {value}")  # (2,)
    print(f"bin_logits: {bin_logits[0]}")  # (8,) — finite only at positions 1-3


def demo_gpu():
    import pgx

    # os.environ["XLA_PYTHON_CLIENT_MEM_FRACTION"] = "0.9"
    os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
    os.environ["JAX_TRACEBACK_FILTERING"] = "off"

    gpu = jax.devices("gpu")[0]  # raises if no GPU available

    # B * S * S * H * 4 = 128 * 1024 * 1024 * 3 * 4 bytes = 1.5 GB attention matrix (all heads combined)
    # 512 bins, 512 items: batch size 128
    # 128 bins, 128 items: batch size 2048

    batch_size = 2048
    n_batches = 20

    n_value = 1
    n_bins = 128
    n_items = 128

    value_token = jnp.array([[1, 0, 0, 0, 0, 0]], dtype=jnp.float32)
    bin_tokens = jnp.array([[0, 1, 8, 0, 0, 0]] * n_bins, dtype=jnp.float32)
    item_tokens = jnp.array([[0, 0, 0, 1, 3, 0]] * n_items, dtype=jnp.float32)
    item_tokens = item_tokens.at[0].set([0, 0, 0, 1, 3, 1])
    seq = jnp.concatenate([value_token, bin_tokens, item_tokens], axis=0)
    tokens = jax.device_put(jnp.stack([seq] * batch_size, axis=0), gpu)  # (batch, 257, 6)

    s = seq.shape[0]
    mask = jax.device_put(jnp.ones((batch_size, s, s), dtype=jnp.bool_), gpu)

    model = BinPackingNet()
    params = model.init(jax.random.PRNGKey(0), tokens, mask)

    n_params = sum(p.size for p in jax.tree.leaves(params))
    print(f"Parameter count: {n_params:,}  ({n_params / 1e6:.2f}M)")

    params = jax.device_put(params, gpu)

    apply_jit = jax.jit(model.apply, device=gpu)

    # First iteration takes longer
    apply_jit(params, tokens, mask)

    for i in tqdm(range(n_batches)):
        value, bin_logits = apply_jit(params, tokens, mask)
        value.block_until_ready()  # wait for GPU to finish before next iteration
        # print(f"Batch {i}: value={value}, bin_logits[0,:3]={bin_logits[0, :3]}")


if __name__ == "__main__":
    # demo()
    demo_gpu()
