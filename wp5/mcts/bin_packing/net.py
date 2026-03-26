import os
import jax
import jax
import jax.numpy as jnp
import flax.linen as nn
from tqdm import tqdm

from transformer import TransformerBackbone

# Input token layout (dim=7):
#   dim 0: 1 if value-estimation token, 0 otherwise
#   dim 1: 1 if bin token, 0 otherwise
#   dim 2: 1 if bin is active (used bins + first unused/new-bin slot), 0 otherwise
#   dim 3: remaining capacity of this bin
#   dim 4: 1 if item token, 0 otherwise
#   dim 5: size of the item
#   dim 6: 1 if this is the next item to assign, 0 otherwise


def to_tokens(
    obs: jnp.ndarray,
    max_items: int,
) -> jnp.ndarray:
    """Return (1 + 2*max_items, 6) token sequence ready for BinPackingNet.

    obs is the (2*max_items,) observation from BinPackingState.observation.

    Layout:
      token 0                        : value token  [1, 0, 0, 0, 0, 0, 0]
      tokens 1..max_items            : bin tokens   [0, 1, active, cap, 0, 0, 0]
      tokens max_items+1..2*max_items: item tokens  [0, 0, 0, 0, 1, size, is_next]

    Bin tokens are in action-index order (token i+1 = action i).  active=1 for
    all used (open) bins and the first unused (new-bin) slot; active=0 for all
    further inactive slots.  cap is the remaining capacity: open bins have cap
    in (0,1), new-bin slot has cap=1.0, inactive slots have cap=0.0.  is_next=1
    at item position 0 if any items remain.
    """
    bin_cap = obs[:max_items]  # (max_items,) — directly from observation
    item_sizes = obs[max_items:]  # (max_items,)

    # Active = used bins (cap < 1.0) plus the first unused slot (new-bin action).
    # Inactive slots beyond the new-bin slot also have cap==1.0 but are not active.
    is_used = bin_cap < 1.0
    is_new_slot = (bin_cap == 1.0) & (jnp.cumsum(bin_cap == 1.0) == 1)
    is_active = (is_used | is_new_slot).astype(jnp.float32)

    bin_tokens = jnp.stack(
        [
            jnp.zeros(max_items),  # dim 0: not a value token
            jnp.ones(max_items),  # dim 1: always a bin token
            is_active,  # dim 2: 1 for used bins + new-bin slot
            bin_cap,  # dim 3: remaining capacity
            jnp.zeros(max_items),  # dim 4: not an item token
            jnp.zeros(max_items),  # dim 5: no item size
            jnp.zeros(max_items),  # dim 6: not the next item
        ],
        axis=-1,
    )  # (max_items, 7)

    is_next = jnp.zeros(max_items, dtype=jnp.float32).at[0].set((item_sizes[0] > 0).astype(jnp.float32))
    item_tokens = jnp.stack(
        [
            jnp.zeros(max_items),  # dim 0: not a value token
            jnp.zeros(max_items),  # dim 1: not a bin token
            jnp.zeros(max_items),  # dim 2: not active (bin-only field)
            jnp.zeros(max_items),  # dim 3: no bin capacity
            jnp.ones(max_items),  # dim 4: always 1 (only unassigned items shown)
            item_sizes,  # dim 5: item size (0 for padding slots)
            is_next,  # dim 6: 1 at position 0 if items remain
        ],
        axis=-1,
    )  # (max_items, 7)

    value_token = jnp.array([[1, 0, 0, 0, 0, 0, 0]], dtype=jnp.float32)
    return jnp.concatenate([value_token, bin_tokens, item_tokens], axis=0)
    # shape: (1 + 2*max_items, 7)


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
    def __call__(self, tokens: jnp.ndarray):
        # tokens: (batch, seq_len, TOKEN_DIM)

        # --- extract type masks from input features ---
        value_mask = tokens[..., 0]  # (batch, seq_len)  exactly 1 value token per seq
        bin_mask = tokens[..., 1]  # (batch, seq_len)
        # item_mask = tokens[..., 3]  # (batch, seq_len)

        # --- embed TOKEN_DIM → hidden_size ---
        x = nn.Dense(self.hidden_size)(tokens)  # (batch, seq_len, hidden_size)

        # --- transformer backbone ---
        x = TransformerBackbone(
            hidden_size=self.hidden_size,
            depth=self.depth,
            num_heads=self.num_heads,
            mlp_ratio=self.mlp_ratio,
        )(
            x
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
    #               (batch=2, seq_len=8, TOKEN_DIM=6)
    tokens = jnp.array(
        [
            [
                [1, 0, 0, 0, 0, 0, 0],  # value token
                [0, 1, 1, 8, 0, 0, 0],  # bin 0, active, remaining=8
                [0, 1, 1, 5, 0, 0, 0],  # bin 1, active, remaining=5
                [0, 1, 1, 3, 0, 0, 0],  # bin 2, active, remaining=3
                [0, 0, 0, 0, 1, 2, 1],  # item 0, size=2, next-to-assign
                [0, 0, 0, 0, 1, 4, 0],  # item 1, size=4
                [0, 0, 0, 0, 1, 3, 0],  # item 2, size=3
                [0, 0, 0, 0, 1, 1, 0],  # item 3, size=1
            ]
        ]
        * 2,
        dtype=jnp.float32,
    )  # batch=2

    model = BinPackingNet()
    params = jax.jit(model.init)(jax.random.PRNGKey(0), tokens)

    n_params = sum(p.size for p in jax.tree.leaves(params))
    print(f"Parameter count: {n_params:,}  ({n_params / 1e6:.2f}M)")

    value, bin_logits = jax.jit(model.apply)(params, tokens)
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

    value_token = jnp.array([[1, 0, 0, 0, 0, 0, 0]], dtype=jnp.float32)
    bin_tokens = jnp.array([[0, 1, 1, 8, 0, 0, 0]] * n_bins, dtype=jnp.float32)
    item_tokens = jnp.array([[0, 0, 0, 0, 1, 3, 0]] * n_items, dtype=jnp.float32)
    item_tokens = item_tokens.at[0].set([0, 0, 0, 0, 1, 3, 1])
    seq = jnp.concatenate([value_token, bin_tokens, item_tokens], axis=0)
    tokens = jax.device_put(jnp.stack([seq] * batch_size, axis=0), gpu)  # (batch, 257, 6)

    model = BinPackingNet()
    params = model.init(jax.random.PRNGKey(0), tokens)

    n_params = sum(p.size for p in jax.tree.leaves(params))
    print(f"Parameter count: {n_params:,}  ({n_params / 1e6:.2f}M)")

    params = jax.device_put(params, gpu)

    apply_jit = jax.jit(model.apply, device=gpu)

    # First iteration takes longer
    apply_jit(params, tokens)

    for i in tqdm(range(n_batches)):
        value, bin_logits = apply_jit(params, tokens)
        value.block_until_ready()  # wait for GPU to finish before next iteration
        # print(f"Batch {i}: value={value}, bin_logits[0,:3]={bin_logits[0, :3]}")


if __name__ == "__main__":
    # demo()
    demo_gpu()
