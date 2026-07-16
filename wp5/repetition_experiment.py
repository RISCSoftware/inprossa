#!/usr/bin/env python3
"""
repetition_experiment.py
═══════════════════════════════════════════════════════════════════════════════
Can a transformer (no positional encodings, one [CLS] token) learn to detect
duplicate values in an integer sequence?

  Task   : Given x₁ … x_L,  xᵢ ∈ {0,…,99},  L ∈ [1,100]  (≤ 100)
           Class 0  →  all values are distinct
           Class 1  →  at least one value is repeated

Theoretical answer:  YES — one attention layer is sufficient in principle.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY THE ATTENTION MATRIX SUFFICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Let D = hidden_size and e_v ∈ ℝ^D be the learned embedding of integer value v.
With D ≥ 100 the embeddings can be orthogonal, giving  e_v · e_u = δ_{v=u}.

Step 1 – "Same-value" attention head.
  With W_Q = W_K = I (or any shared linear map), the score matrix becomes

      score(xᵢ, xⱼ) = (W_Q eₓᵢ) · (W_K eₓⱼ)  ≈  δ(xᵢ = xⱼ).

  After softmax, token i attends strongly to every other token that carries
  the same integer value.  Through W_V this attention sum becomes a "match
  signal" residual in the token's representation:

      if repeated   →  large residual  (attended to at least one other token)
      if unique     →  small residual  (self-attention, softmax spreads mass)

  NOTE: without positional encodings the computation is permutation-equivariant,
  which is exactly what we need – repetition is a property of the multiset, not
  the order of the sequence.

Step 2 – [CLS] aggregation.
  The [CLS] token has no value content; it is prepended and attends to all real
  tokens.  After layer 1 the real tokens' representations encode their individual
  match signals.  [CLS] reads the max / OR of these signals:

      Bonus insight: since the attention is scaled dot-product with softmax,
      the [CLS] token can effectively compute "does any token have a large
      match signal?" in a single additional attention head.  A two-layer MLP
      on the [CLS] output then classifies.

  Two transformer layers suffice in practice (and empirically train well):
    Layer 1  →  token-to-token "find matches" attention.
    Layer 2  →  [CLS]-aggregating attention over the enriched representations.

Key insight vs. MLPs / RNNs
  An MLP without attention cannot solve this task with fixed parameters over
  variable-length sequences, because it has no mechanism to compare arbitrary
  pairs of tokens.  A transformer's all-to-all attention explicitly models
  every (i, j) pair, making this the *natural* inductive bias for collision
  detection.

Reference: the above construction is an instance of the "associative recall"
  circuits studied in mechanistic interpretability (e.g. Olsson et al., 2022,
  "In-context Learning and Induction Heads").
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys

import jax
import jax.numpy as jnp
import flax.linen as nn
import numpy as np
import optax
from tqdm import trange, tqdm

# ── locate the mcts package ────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcts.transformer_ import TransformerBackbone

# ── vocabulary constants ───────────────────────────────────────────────────
NUM_VALUES = 100  # integers 0 … 99
CLS_IDX = 100  # special [CLS] token index
VOCAB_SIZE = 101  # embeddings for indices 0 … 100
# Padding positions are filled with 0 during data generation; the attention
# mask zeroes out their contribution so the chosen fill value is irrelevant.


# ══════════════════════════════════════════════════════════════════════════
# Model
# ══════════════════════════════════════════════════════════════════════════


class RepetitionClassifier(nn.Module):
    """Transformer classifier for the duplicate-detection task.

    The [CLS] token is prepended at position 0 by the caller.
    No positional encoding is used – the task is permutation-invariant.
    """

    hidden_size: int
    depth: int
    num_heads: int
    mlp_ratio: int = 4

    @nn.compact
    def __call__(self, token_ids: jnp.ndarray, mask: jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray]:
        """
        Parameters
        ----------
        token_ids : (B, S) int32
            Token indices.  Position 0 is always CLS_IDX; positions 1…L are
            integer values 0–99; positions L+1… are padding (filled with 0,
            masked out).
        mask : (B, S) bool
            True for real tokens (including [CLS]), False for padding.

        Returns
        -------
        cls_logits : (B, 2) float32
            Sequence-level logits from the [CLS] token.
        tok_logits : (B, S, 2) float32
            Per-token logits (duplicate / not-duplicate) for all positions.
            Only positions 1…L are meaningful; position 0 ([CLS]) and padding
            positions should be ignored via the mask.
        """
        # Learnable token embeddings.  No positional encoding added.
        x = nn.Embed(num_embeddings=VOCAB_SIZE, features=self.hidden_size)(token_ids)
        # (B, S, hidden_size)

        # Attention mask: query i may attend to key j only when both are real.
        attn_mask = mask[:, :, None] & mask[:, None, :]  # (B, S, S) bool

        x = TransformerBackbone(
            hidden_size=self.hidden_size,
            depth=self.depth,
            num_heads=self.num_heads,
            mlp_ratio=self.mlp_ratio,
            use_conditioning=False,
            use_causal_masking=False,
        )(x, c=None, mask=attn_mask)
        # (B, S, hidden_size)

        x_f32 = x.astype(jnp.float32)

        # [CLS] head: sequence-level binary classification.
        cls_logits = nn.Dense(2)(x_f32[:, 0, :])  # (B, 2)

        # Token head: per-position duplicate detection.
        # Separate Dense so the two tasks don't share output weights.
        tok_logits = nn.Dense(2)(x_f32)  # (B, S, 2)

        return cls_logits, tok_logits


# ══════════════════════════════════════════════════════════════════════════
# Data generation  (NumPy – no need to JIT-compile)
# ══════════════════════════════════════════════════════════════════════════


def _make_example(np_rng: np.random.Generator, label: int, max_seq_len: int):
    """Build a single (tokens, mask, label) example."""
    if label == 0:
        # Unique sequence: sample without replacement.
        L = int(np_rng.integers(2, max_seq_len + 1))
        seq = np_rng.choice(NUM_VALUES, size=L, replace=False)
    else:
        # Repeated sequence: start unique, then overwrite one position.
        L = int(np_rng.integers(2, max_seq_len + 1))
        seq = np_rng.choice(NUM_VALUES, size=L, replace=False)
        dup_src = int(np_rng.integers(0, L - 1))
        seq[-1] = seq[dup_src]  # force one duplicate
        np_rng.shuffle(seq)  # randomise position

    S = 1 + max_seq_len
    tokens = np.zeros(S, dtype=np.int32)
    tokens[0] = CLS_IDX
    tokens[1 : 1 + L] = seq  # padding positions stay 0

    mask_arr = np.zeros(S, dtype=bool)
    mask_arr[0] = True  # [CLS]
    mask_arr[1 : 1 + L] = True  # real sequence tokens

    return tokens, mask_arr, label


def generate_batch(
    np_rng: np.random.Generator,
    batch_size: int,
    max_seq_len: int = 100,
) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    """Return a balanced batch (50 % unique, 50 % with repetition).

    Returns
    -------
    token_ids : (B, 1 + max_seq_len) int32
    mask      : (B, 1 + max_seq_len) bool
    labels    : (B,) int32
    """
    half = batch_size // 2
    examples = [_make_example(np_rng, 0, max_seq_len) for _ in range(half)] + [
        _make_example(np_rng, 1, max_seq_len) for _ in range(batch_size - half)
    ]
    idx = np_rng.permutation(batch_size)
    token_arr = np.array([e[0] for e in examples], dtype=np.int32)[idx]
    mask_arr = np.array([e[1] for e in examples], dtype=bool)[idx]
    label_arr = np.array([e[2] for e in examples], dtype=np.int32)[idx]
    return jnp.array(token_arr), jnp.array(mask_arr), jnp.array(label_arr)


def generate_batch_fixed_length(
    np_rng: np.random.Generator,
    batch_size: int,
    L: int,
    max_seq_len: int = 100,
) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    """Balanced batch where every sequence has *exactly* length L."""
    assert 2 <= L <= max_seq_len

    def make(label):
        if label == 0 and L > NUM_VALUES:
            # Can't have L > 100 unique values from 0–99 → force repetition
            label = 1
        if label == 0:
            seq = np_rng.choice(NUM_VALUES, size=L, replace=False)
        else:
            if L < 2:
                label = 0
                seq = np_rng.choice(NUM_VALUES, size=L, replace=False)
            else:
                seq = np_rng.choice(NUM_VALUES, size=L, replace=False)
                seq[-1] = seq[int(np_rng.integers(0, L - 1))]
                np_rng.shuffle(seq)

        S = 1 + max_seq_len
        tokens = np.zeros(S, dtype=np.int32)
        tokens[0] = CLS_IDX
        tokens[1 : 1 + L] = seq
        mask_arr = np.zeros(S, dtype=bool)
        mask_arr[0] = True
        mask_arr[1 : 1 + L] = True
        return tokens, mask_arr, label

    half = batch_size // 2
    examples = [make(0) for _ in range(half)] + [make(1) for _ in range(batch_size - half)]
    idx = np_rng.permutation(batch_size)
    token_arr = np.array([e[0] for e in examples], dtype=np.int32)[idx]
    mask_arr = np.array([e[1] for e in examples], dtype=bool)[idx]
    label_arr = np.array([e[2] for e in examples], dtype=np.int32)[idx]
    return jnp.array(token_arr), jnp.array(mask_arr), jnp.array(label_arr)


# ══════════════════════════════════════════════════════════════════════════
# Token-label helpers
# ══════════════════════════════════════════════════════════════════════════


def token_labels_from_ids(
    token_ids: np.ndarray,  # (B, S) int32
    mask: np.ndarray,  # (B, S) bool — True for real tokens incl. [CLS]
) -> np.ndarray:
    """Return (B, S) int32 per-token duplicate labels.

    Label = 1 if the token's integer value appears more than once in the
    sequence (positions 1…L only); 0 otherwise.  Position 0 ([CLS]) is
    always 0 — it is excluded from the token loss via the seq mask.
    """
    B, S = token_ids.shape
    labels = np.zeros((B, S), dtype=np.int32)
    for b in range(B):
        # Real value positions: non-CLS real tokens
        real = np.where(mask[b])[0]
        real = real[real > 0]  # exclude CLS at pos 0
        if real.size == 0:
            continue
        values = token_ids[b, real]
        _, counts = np.unique(values, return_counts=True)
        # Build a count lookup for each value
        val_to_count: dict[int, int] = {}
        for v, c in zip(np.unique(values), counts):
            val_to_count[int(v)] = int(c)
        for pos in real:
            labels[b, pos] = 1 if val_to_count[int(token_ids[b, pos])] > 1 else 0
    return labels


def balanced_accuracy_tokens(
    tok_preds: np.ndarray,  # (B, S) int — predicted per-token class
    tok_labels: np.ndarray,  # (B, S) int — ground-truth per-token class
    seq_mask: np.ndarray,  # (B, S) bool — True for real non-CLS positions
) -> float:
    """Mean per-sequence balanced accuracy for the token duplicate task.

    Per-sequence balanced accuracy = mean recall over the classes that are
    actually present in that sequence.  Averaged over all sequences.
    """
    accs = []
    for b in range(len(tok_preds)):
        pred = tok_preds[b][seq_mask[b]]
        true = tok_labels[b][seq_mask[b]]
        if len(pred) == 0:
            continue
        classes = np.unique(true)
        recalls = [float(np.mean(pred[true == c] == c)) for c in classes]
        accs.append(float(np.mean(recalls)))
    return float(np.mean(accs)) if accs else 0.0


# ══════════════════════════════════════════════════════════════════════════
# Training
# ══════════════════════════════════════════════════════════════════════════


def build_train_step(
    model: RepetitionClassifier,
    optimizer: optax.GradientTransformation,
    alpha: float = 1.0,
):
    """Return a JIT-compiled training step closure.

    Total loss = loss_cls + alpha * loss_tok.
    """

    @jax.jit
    def train_step(params, opt_state, token_ids, mask, seq_labels, tok_labels):
        """seq_labels: (B,) int — sequence-level class.
        tok_labels : (B, S) int — per-token duplicate labels.
        """
        # seq_mask_no_cls: real non-CLS positions used for token loss
        seq_mask_no_cls = mask & ~(jnp.arange(mask.shape[1]) == 0)  # (B, S)

        def loss_fn(p):
            cls_logits, tok_logits = model.apply(p, token_ids, mask)

            # Sequence-level loss (CLS token)
            loss_cls = jnp.mean(optax.softmax_cross_entropy_with_integer_labels(cls_logits, seq_labels))

            # Token-level loss: average CE over real non-CLS tokens
            all_ce = optax.softmax_cross_entropy_with_integer_labels(tok_logits, tok_labels)  # (B, S)
            n_real = jnp.sum(seq_mask_no_cls, dtype=jnp.float32)
            loss_tok = jnp.sum(all_ce * seq_mask_no_cls) / jnp.maximum(n_real, 1.0)

            return loss_cls + alpha * loss_tok, (cls_logits, loss_cls, loss_tok)

        (loss, (cls_logits, loss_cls, loss_tok)), grads = jax.value_and_grad(loss_fn, has_aux=True)(params)
        updates, new_opt_state = optimizer.update(grads, opt_state, params)
        new_params = optax.apply_updates(params, updates)
        cls_acc = jnp.mean((jnp.argmax(cls_logits, axis=-1) == seq_labels).astype(jnp.float32))
        return new_params, new_opt_state, loss, loss_cls, loss_tok, cls_acc

    return train_step


def build_eval_step(model: RepetitionClassifier):
    @jax.jit
    def eval_step(params, token_ids, mask):
        """Return (cls_logits, tok_logits) for external metric computation."""
        cls_logits, tok_logits = model.apply(params, token_ids, mask)
        return cls_logits, tok_logits

    return eval_step


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════


def main() -> None:
    # ── hyper-parameters ──────────────────────────────────────────────────
    # hidden_size ≥ 100 so the 100 token embeddings have room to be
    # nearly orthogonal; 256 gives comfortable separation.
    hidden_size = 3 * 64
    depth = 2  # layer 1 = find matches; layer 2 = CLS aggregation
    num_heads = 3  # 64 dims/head – enough for the QK match detector
    mlp_ratio = 4
    batch_size = 2_048
    n_steps = 5_000
    lr = 3e-4
    weight_decay = 1e-2
    warmup_steps = 100
    alpha = 1.0  # coupling: total_loss = loss_cls + alpha * loss_tok
    max_seq_len = 10
    log_every = 500
    eval_size = 2_048

    print(__doc__)
    print("=" * 70)
    print(f"Model:  hidden={hidden_size}, depth={depth}, heads={num_heads}")
    print(f"Train:  steps={n_steps}, batch={batch_size}, lr={lr}, wd={weight_decay}, alpha={alpha}")
    print("=" * 70)

    # ── model init ────────────────────────────────────────────────────────
    model = RepetitionClassifier(
        hidden_size=hidden_size,
        depth=depth,
        num_heads=num_heads,
        mlp_ratio=mlp_ratio,
    )
    rng = jax.random.PRNGKey(0)
    S = 1 + max_seq_len
    dummy_ids = jnp.zeros((1, S), dtype=jnp.int32)
    dummy_mask = jnp.ones((1, S), dtype=bool)
    params = model.init(rng, dummy_ids, dummy_mask)

    n_params = sum(p.size for p in jax.tree.leaves(params))
    print(f"Parameters: {n_params:,}\n")

    # ── optimizer (linear warmup + cosine decay) ──────────────────────────
    lr_schedule = optax.warmup_cosine_decay_schedule(
        init_value=0.0,
        peak_value=lr,
        warmup_steps=warmup_steps,
        decay_steps=n_steps,
        end_value=lr * 0.01,
    )
    optimizer = optax.adamw(lr_schedule, weight_decay=weight_decay)
    opt_state = optimizer.init(params)
    train_step = build_train_step(model, optimizer, alpha=alpha)
    eval_step = build_eval_step(model)

    # ── training loop ─────────────────────────────────────────────────────
    np_rng = np.random.default_rng(42)
    for step in trange(n_steps, desc="training"):
        token_ids_np, mask_np, seq_labels = generate_batch(np_rng, batch_size, max_seq_len)
        tok_labels = jnp.array(token_labels_from_ids(np.array(token_ids_np), np.array(mask_np)))
        params, opt_state, loss, loss_cls, loss_tok, cls_acc = train_step(
            params, opt_state, token_ids_np, mask_np, seq_labels, tok_labels
        )

        if (step + 1) % log_every == 0:
            tqdm.write(
                f"  step {step+1:5d}  loss={float(loss):.4f}"
                f"  loss_cls={float(loss_cls):.4f}  loss_tok={float(loss_tok):.4f}"
                f"  cls_acc={float(cls_acc):.3f}"
            )

    # ── evaluation ────────────────────────────────────────────────────────
    eval_rng = np.random.default_rng(999)

    def _eval_batch(token_ids_np, mask_np, seq_labels_np):
        """Return (cls_acc, tok_balanced_acc) for one batch."""
        tok_labels_np = token_labels_from_ids(token_ids_np, mask_np)
        cls_logits, tok_logits = eval_step(params, jnp.array(token_ids_np), jnp.array(mask_np))
        # CLS accuracy
        cls_pred = np.array(jnp.argmax(cls_logits, axis=-1))
        cls_acc = float(np.mean(cls_pred == seq_labels_np))
        # Token balanced accuracy: exclude CLS (pos 0) from mask
        tok_pred = np.array(jnp.argmax(tok_logits, axis=-1))  # (B, S)
        seq_mask_no_cls = mask_np.copy()
        seq_mask_no_cls[:, 0] = False
        tok_bal_acc = balanced_accuracy_tokens(tok_pred, tok_labels_np, seq_mask_no_cls)
        return cls_acc, tok_bal_acc

    print("\n--- Evaluation (balanced batch, 2048 samples each) ---")
    print(f"  {'':12s}  {'CLS acc':>10s}  {'tok bal-acc':>12s}")

    t_np, m_np, l_np = [np.array(x) for x in generate_batch(eval_rng, eval_size, max_seq_len)]
    ca, tba = _eval_batch(t_np, m_np, l_np)
    print(f"  {'Overall':12s}  {ca:>10.4f}  {tba:>12.4f}")

    eval_lengths = [(f"L={L}", L) for L in [2, 5, 10, 20, 50, 99] if L <= max_seq_len]
    for desc, L in eval_lengths:
        t_np, m_np, l_np = [np.array(x) for x in generate_batch_fixed_length(eval_rng, eval_size, L, max_seq_len)]
        ca, tba = _eval_batch(t_np, m_np, l_np)
        print(f"  {desc:12s}  {ca:>10.4f}  {tba:>12.4f}")

    return params, model, max_seq_len


def inspect_sequence(params, model: RepetitionClassifier, seq: list[int], max_seq_len: int = 100) -> None:
    """Feed a single integer sequence through the trained model and print
    CLS and per-token probabilities in a human-readable table.
    """
    from jax.nn import softmax

    L = len(seq)
    S = 1 + max_seq_len
    token_ids = np.zeros((1, S), dtype=np.int32)
    token_ids[0, 0] = CLS_IDX
    token_ids[0, 1 : 1 + L] = seq

    mask = np.zeros((1, S), dtype=bool)
    mask[0, 0] = True
    mask[0, 1 : 1 + L] = True

    cls_logits, tok_logits = model.apply(params, jnp.array(token_ids), jnp.array(mask))
    cls_probs = np.array(softmax(cls_logits[0].astype(jnp.float32)))  # (2,)
    tok_probs = np.array(softmax(tok_logits[0].astype(jnp.float32)))  # (S, 2)

    print("\n" + "─" * 52)
    print(f"  Sequence: {seq}")
    print("─" * 52)
    print(
        f"  [CLS]  →  P(no-dup)={cls_probs[0]:.3f}  P(dup)={cls_probs[1]:.3f}"
        f"  →  {'DUP' if cls_probs[1] > 0.5 else 'unique'}"
    )
    print("─" * 52)
    print(f"  {'pos':>4}  {'value':>6}  {'P(unique)':>10}  {'P(dup)':>8}  pred")
    print("─" * 52)
    for i, v in enumerate(seq):
        pos = i + 1  # position in token array (0 = CLS)
        p_uniq = tok_probs[pos, 0]
        p_dup = tok_probs[pos, 1]
        pred = "DUP" if p_dup > 0.5 else "unique"
        print(f"  {pos:>4}  {v:>6}  {p_uniq:>10.3f}  {p_dup:>8.3f}  {pred}")
    print("─" * 52)


if __name__ == "__main__":
    params, model, max_seq_len = main()
    inspect_sequence(params, model, [1, 1, 2, 3, 4, 5, 6, 7, 8, 9], max_seq_len)
    inspect_sequence(params, model, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], max_seq_len)
