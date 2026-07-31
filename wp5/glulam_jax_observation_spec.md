# Glulam Beam Assembly Problem — JAX Observation and Token Encoding Specification

Companion to [glulam_beam_problem_description.md](glulam_beam_problem_description.md), which remains
the authoritative specification of the problem dynamics, constants, observable and hidden variables,
actions, legality, and reward. This document specifies **only what is new** for a JAX/Flax
implementation of a neural-guided policy: everything needed to turn the spec's observable variables
into a fixed-shape, JIT-safe input for a transformer network.

## 0. Design philosophies

The encoding below follows the same set of design philosophies as the rest of the workspace:

- **Spec-first, executable-second.** Specs are authoritative and framework-free; implementations
  exist to prove spec completeness — a branch that cannot be written without inventing a rule
  marks a spec gap, not a code gap.
- **Reference, don't duplicate.** Anything reusable is referenced, not copied; new documents are
  companions to one authoritative spec, with an explicit reuse map.
- **Minimal, set-based encodings.** Observations are canonical and label-free; every input scalar
  is either derivable on demand or explicitly justified. Redundant inputs are a smell.
- **Legality masks are outputs, not inputs.** The network receives geometry (intervals, lengths),
  never precomputed yes/no answers; masks enforce legality at the logits.
- **Permutation invariance as a semantic principle.** Token identity flows through features, never
  through positions — invariance exactly where the problem is a set (queue contents aside from
  order, intervals), explicit ordering features only where order is load-bearing (distance to the
  saw).
- **Configs as jointly feasible objects.** Constants come with constraint tables and base-case
  feasibility checks; violation raises a named error instead of degenerate instances.
- **JIT-friendliness by design, not adaptation.** Fixed capacities, padding, and masks from the
  start; pure functions; immutable state; no Python-level dynamic shapes; randomness through
  explicit keys only.
- **Documentation invariant to refactoring.** Internal links, framework-free problem descriptions,
  and every structural decision recorded together with its rationale — the *why* next to the
  *what*.

Anything not covered here — queue mechanics, cutting, assembly, legality of actions, reward — is
unchanged, and the reader is referred to the authoritative spec's corresponding section. In
particular, the full reuse map is:

| Topic                                            | Authoritative section (glulam_beam_problem_description.md) |
| ------------------------------------------------ | ---------------------------------------------------------- |
| Problem dynamics (queue, saw, out/buf, assembly) | "Abstract, informal problem definition"                    |
| Environment constants                            | "Constants" table                                          |
| Observable variables                             | "Observable variables" table                               |
| Hidden variables                                 | "Hidden variables" table                                   |
| Action space                                     | "Action space" table                                       |
| Legal actions + assemble constraints             | "Legal actions" + "Assemble constraints"                   |
| Reward                                           | "Reward" table                                             |

The sections below define, in order: the fixed-shape array encoding of the observation (§1), the
transformer token layout and the token encoding table (§2), padding and the attention mask (§3),
the network output heads (§4), and the action-logit mapping (§5).

## 1. Fixed-shape observation encoding

The authoritative spec's "Observable variables" table defines *what* is observable; this section
defines *how* those observables are materialised as fixed-shape arrays so that the environment is
JIT-compilable and vectorisable. Padding/encoding was deliberately left out of scope there; it is
specified here.

| Variable (from spec)     | Array shape                     | dtype         | Padding value |
| ------------------------ | ------------------------------- | ------------- | ------------- |
| `observable_pieces`      | `(MAX_OBSERVABLE_PIECES,)`      | int32         | 0             |
| `prev_meet_positions`    | `(LAYER_LEN,)` indicator vector | float32 (0/1) | 0             |
| `current_meet_positions` | `(LAYER_LEN,)` indicator vector | float32 (0/1) | 0             |
| `assemble_legal_mask`    | `(MAX_PIECE_LEN,)`              | bool          | `False`       |
| `current_layer`          | `()`                            | int32         | —             |
| `current_layer_len`      | `()`                            | int32         | —             |
| `current_layer_left`     | `()`                            | int32         | —             |
| `out_piece_len`          | `()`                            | int32         | —             |
| `buf_piece_len`          | `()`                            | int32         | —             |
| `saw_piece_len`          | `()`                            | int32         | —             |

Notes:

- `MAX_OBSERVABLE_PIECES = OBSERVABLE_BOARDS * (MAX_BOARD_LEN // MIN_PIECE_LEN)` — the upper bound
  given in the spec's observable-variables table, now used as the fixed array length. Entries beyond
  the actual number of observable pieces are 0-padded on the right. Order is preserved
  left-to-right (toward the saw), exactly as in the spec.
- The two meeting-position observables are encoded as fixed-length indicator vectors of length
  `LAYER_LEN`, as already suggested in the spec ("a fixed-length indicator vector of length
  `LAYER_LEN` is a natural encoding"). Entry `p` is 1 iff `p` is a meeting position of the
  respective layer. This replaces the spec's mathematical `set[int]` with a static shape.
- All scalars are int32. No Python-level dynamic shapes appear anywhere in the observation.

## 2. Transformer token encoding

The network input is a sequence of fixed-length tokens, each a `TOKEN_DIM`-dimensional feature
vector (`TOKEN_DIM = 21`), following the pattern established by the bin-packing net in this
workspace. One *value token* sits at sequence position 0 (its network head carries the value
readout); all subsequent tokens represent either a **piece** in a specific location, an **allowed
assembly interval**, a **cut action**, or an **action** such as `put_buf`, `assemble_out`,
`assemble_buf`, `discard_out`, `discard_buf`, `discard_beam`.

### 2.1 Token layout

Named constants:

- `P = 3` — piece-slot tokens (saw, out, buf), one each, always present (an empty slot is a token
  with `nlen = 0` and its location flag set).
- `Q = MAX_OBSERVABLE_PIECES` — queue piece tokens (§1).
- `I = 2 * MAX_INTERVALS` — allowed-interval tokens (§2.4). Each forbidden interval (from
  `FORBIDDEN_INTERVALS`, or centred on a previous-layer meeting position) can split the allowed
  length region at most once more, and the previous layer has fewer than `LAYER_LEN / MIN_PIECE_LEN`
  meeting positions, so `MAX_INTERVALS = #FORBIDDEN_INTERVALS + LAYER_LEN // MIN_PIECE_LEN + 2` is
  a safe per-layer compile-time bound; the factor 2 covers the current and the next layer.
- `N = MAX_PIECE_LEN` — cut tokens, one per possible cut length `k = 1..N` (index `k-1`), so the
  cut token number directly equals the cut length — mirroring the action indexing in the spec's
  legal-actions section.
- `A = 6` — action tokens, in the spec's fixed action order: `put_buf`, `assemble_out`,
  `assemble_buf`, `discard_out`, `discard_buf`, `discard_beam`.

```
token 0                     : value token
tokens 1 .. 3               : saw token, out token, buf token
tokens 4 .. 3+Q             : queue piece tokens
tokens 4+Q .. 3+Q+I         : allowed-interval tokens (current layer, then next layer)
tokens 4+Q+I .. 3+Q+I+N     : cut tokens cut_1 .. cut_N
tokens 4+Q+I+N .. 3+Q+I+N+5 : action tokens
```

Sequence length `S = 4 + Q + I + N + 6` is a compile-time constant per config.

The assembled beam does **not** appear as piece tokens. What the policy needs from the beam is the
geometry of which test-piece lengths may still be assembled into the current layer — and, for
planning cuts ahead, into the layer after it. That geometry is a union of disjoint allowed-length
intervals for each layer, encoded directly as interval tokens (§2.4). The full `beam` remains a
hidden variable, as in the spec.

### 2.2 Token encoding tables

The token sequence is `S = 4 + Q + I + N + 6` tokens of `TOKEN_DIM = 21` features each. A rendered
image of the full (token × feature) grid, in the style of
[docs/scripts/transformer_diagram.py](docs/scripts/transformer_diagram.py) (the bin-packing token
diagram), supplements the tables below:

**Image (to be generated):** `docs/scripts/glulam_token_diagram.py` →
![Glulam token encoding diagram](docs/glulam_token_diagram.png)

**Table 2.2a — Token types.** One row per token type, in layout order (§2.1).

| token type (index range) | description                                                        | features set                                                    |
| ------------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------- |
| value (0)                | the single value-readout token; carries `current_layer`            | `is_value`, `is_value_act`, `nlen = current_layer / NUM_LAYERS` |
| saw (1)                  | the piece at the saw position (`nlen = 0` if the queue is empty)   | `is_saw_piece`, `nlen`, `board_frac`                            |
| out (2)                  | the piece at `out_pos` (`nlen = 0` if empty)                       | `is_out_piece`, `nlen`, `board_frac`                            |
| buf (3)                  | the piece at `buf_pos` (`nlen = 0` if empty)                       | `is_buf_piece`, `nlen`, `board_frac`                            |
| queue piece (4 .. 3+Q)   | one observable queue piece, in `ord_frac` order                    | `is_queue_piece`, `nlen`, `ord_frac`, `board_frac`              |
| interval (4+Q .. 3+Q+I)  | one allowed assembly-length interval (§2.4), current or next layer | `is_curr_iv` or `is_next_iv`, `iv_start`, `iv_end`              |
| cut `k` (3+Q+I+k)        | action token for `cut_k`; `nlen = k / LAYER_LEN` identifies `k`    | `is_action`, `is_cut_act`, `nlen`                               |
| `put_buf`                | action token for `put_buf`                                         | `is_action`, `is_put_buf_act`                                   |
| `assemble_out`           | action token for `assemble_out`                                    | `is_action`, `is_assemble_out_act`                              |
| `assemble_buf`           | action token for `assemble_buf`                                    | `is_action`, `is_assemble_buf_act`                              |
| `discard_out`            | action token for `discard_out`                                     | `is_action`, `is_discard_out_act`                               |
| `discard_buf`            | action token for `discard_buf`                                     | `is_action`, `is_discard_buf_act`                               |
| `discard_beam`           | action token for `discard_beam`                                    | `is_action`, `is_discard_beam_act`                              |

**Table 2.2b — Feature positions.** One row per dim (or dim block) of the `TOKEN_DIM = 21` vector.

| dim  | name                                                                                                                                                            | set on                            | description                                                                                                      |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 0    | `is_value`                                                                                                                                                      | value token                       | marks the single value token; its output head carries the value readout (§4)                                     |
| 1–4  | `is_queue_piece`, `is_saw_piece`, `is_out_piece`, `is_buf_piece`                                                                                                | exactly one per slot/queue piece  | location one-hot for the four in-flight piece positions                                                          |
| 5–12 | `is_cut_act`, `is_put_buf_act`, `is_assemble_out_act`, `is_assemble_buf_act`, `is_discard_out_act`, `is_discard_buf_act`, `is_discard_beam_act`, `is_value_act` | exactly one per action-side token | action-type one-hot (7 action groups + value) — makes tokens self-identifying without positional encoding (§2.5) |
| 13   | `nlen`                                                                                                                                                          | all piece + cut + value tokens    | normalised length `len / LAYER_LEN`; value token carries `current_layer / NUM_LAYERS`                            |
| 14   | `ord_frac`                                                                                                                                                      | queue pieces only                 | position of the piece in the observation window, `j / n_obs` (saw end = 1)                                       |
| 15   | `board_frac`                                                                                                                                                    | all piece tokens                  | origin `board_id / (INI_BOARDS - 1)`; ⚠ hidden-variable leak, must be 0 in compliant runs                        |
| 16   | `iv_start`                                                                                                                                                      | interval tokens                   | allowed-start bound of the interval, `L_i / LAYER_LEN`                                                           |
| 17   | `iv_end`                                                                                                                                                        | interval tokens                   | allowed-end bound of the interval, `U_i / LAYER_LEN` (inclusive)                                                 |
| 18   | `is_curr_iv`                                                                                                                                                    | current-layer interval tokens     | one of the two interval flags: this interval describes the current layer's test piece                            |
| 19   | `is_next_iv`                                                                                                                                                    | next-layer interval tokens        | the other interval flag: this interval describes the next layer's test piece                                     |
| 20   | `is_action`                                                                                                                                                     | all action tokens                 | marks tokens whose output head is an action logit (§4)                                                           |

Feature definitions (long form):

- **`is_value`** (dim 0): marks the single value token at position 0. Its output head carries the
  value readout (§4); its `nlen` field carries the scalar observable `current_layer` (exception:
  this one entry is a normalised id, not a length — see `nlen` below).
- **Location one-hot** (dims 1–4): `is_queue_piece`, `is_saw_piece`, `is_out_piece`,
  `is_buf_piece`. Exactly one is set on every queue/saw/out/buf piece token (including empty
  saw/out/buf slots, which keep their flag with `nlen = 0`).
- **Action-type one-hot** (dims 5–12): mutually exclusive; exactly one is set on every action-side
  token (value, cut, and the six action tokens). This is what makes those tokens **self-identifying
  independent of sequence position** (see the permutation-invariance note in §2.5): the transformer
  does not need to know a token's index
  to know which env action it feeds. The eight types are the seven env action groups — `is_cut_act`
  (shared by all `N` cut tokens), `is_put_buf_act`, `is_assemble_out_act`, `is_assemble_buf_act`,
  `is_discard_out_act`, `is_discard_buf_act`, `is_discard_beam_act` — plus `is_value_act` as the
  eighth type, carried by the value token so every action-side token has exactly one action-type
  bit set. Interval tokens are self-identifying through their own `is_curr_iv` / `is_next_iv`
  one-hot (below), and the all-zero token is padding (§2.4). Cut tokens are told apart
  **within** the cut type by `nlen = k / LAYER_LEN`.
- **`nlen`** (dim 13): the normalised length, `len / LAYER_LEN`, of any length-valued quantity —
  a piece's length, a cut token's nominal cut length `k`, the saw/out/buf slot contents (0 when
  the slot is empty). The env itself keeps integer length units (spec: "Lengths of all wood
  pieces are integers"); the division happens at the tokenisation boundary, so the network sees
  fractional lengths while env-side legality stays exact on integers. Values lie in `[0, 1]`
  under the constraint `MAX_PIECE_LEN <= LAYER_LEN` (recommended); configs with
  `MAX_PIECE_LEN > LAYER_LEN` (permitted by the spec) produce `nlen > 1` on queue/saw/out/buf
  and cut tokens (`k > LAYER_LEN` stays a legal, effectively wasted env action), and the
  encoding tolerates those values without clipping. The single
  exception is the value token, whose `nlen` field carries `current_layer` / `NUM_LAYERS` (a
  normalised *id*, not a length); for the six action tokens it is 0.
- **`ord_frac`** (dim 14): the piece's position in the observation window, normalised to `(0, 1]`
  as `j / n_obs` where `n_obs` is the current number of observable pieces and `j = 1 … n_obs` is
  the left-to-right index of the piece within the observable window (`j = n_obs` at the saw end).
  **Carried by queue pieces only** — and meaningless on slot/action/interval tokens. This is the
  encoding's only ordinal feature and replaces any positional embedding for the one block where
  order genuinely matters (distance to the saw determines which piece is cut next).
- **`board_frac`** (dim 15): the piece's origin `board_id` normalised to `[0, 1]` as
  `board_id / max(1, INI_BOARDS - 1)` (the `max` guards the boundary config `INI_BOARDS = 1`,
  where every `board_id` is 0), or 0 for non-piece tokens — including **empty** saw/out/buf
  slot tokens, which are piece-location tokens carrying no piece. ⚠ **Spec deviation — hidden-variable
  leak.** `board_id` is a hidden variable per the spec's hidden-variables table, and board
  boundaries within the observation window are explicitly "not observable". Encoding it here leaks
  hidden information into the observation and **relaxes the problem**. It is included as an
  experimental ablation axis (the board-drop event drives window movement, which the value
  function benefits from), and must be set to all-zeros for spec-compliant runs. Compliant runs
  replace this feature by 0; the token layout and `TOKEN_DIM` are unchanged.
- **`iv_start`, `iv_end`** (dims 16–17): the inclusive allowed-length bounds `[L_i, U_i]` of one
  interval, both normalised by `LAYER_LEN`; §2.4 defines how the intervals are computed. An
  assemble action with piece length `k` is exactly-legal iff `k` lies in one of the current
  layer's intervals; a cut producing length `k` is geometrically sensible iff `k` lies in one of
  the current layer's intervals at the moment the piece reaches assembly.
- **`is_curr_iv`, `is_next_iv`** (dims 18–19): the interval-layer one-hot — which layer the
  interval describes (§2.4). Two flags rather than one, in the same style as the location and
  action one-hots: a token without a type flag is unidentifiable under permutation invariance.
- **`is_action`** (dim 20): 1 on every token whose output head is an action logit — all cut and
  action tokens; 0 on the value token, all piece tokens, and all interval tokens. Used to mask
  non-action positions to $-\infty$ before the softmax (§4).

The scalar observables `current_layer_len` and `current_layer_left` are **not** given their own
feature, by redundancy rather than recoverability: both are highly correlated with the interval
geometry (roughly, the last current-layer interval's `iv_end` approximates the remaining gap —
up to the layer-gap guard, and strictly below `current_layer_left` whenever constraint 4 has
pruned the exact fill), and the "stuck" state (no current-layer intervals at all) is directly
visible. Neither observable is *exactly* recoverable from the tokens, which is accepted:
`current_layer_left` remains directly observable env-side (§1) and only the network's input is
kept minimal. `current_layer` rides on the value token's `nlen` field (see above), so it is
available to every token after one attention step. Note that the two meet-position indicator
vectors from §1 (`prev_meet_positions`, `current_meet_positions`) do **not** become token
features: the interval tokens are their replacement as network input — they remain in the
observation as the quantities from which the intervals are derived.

`assemble_legal_mask` (§1) is likewise not encoded into tokens: it is derivable state, provided to
the policy only as a legality mask on the output logits (§5), never as network input. The §1 mask
array is consumed by the interval construction of §2.3 — and by nothing else in this document; it
is kept in the observation because it is an authoritative observable of the spec. (The
current-layer interval tokens already carry the mask's geometric content; the mask exists
env-side for exact integer legality.)

### 2.3 The assembled beam as allowed intervals

The network does not see the beam's pieces. The policy never chooses *where* to assemble (spec: no
choice of position), only *what length* to cut, buffer, assemble, or discard — so the useful
beam-derived signal is not "which pieces sit in the layer" but "**which test-piece lengths are
still assembleable**". That set is, for the current layer, a union of disjoint allowed intervals
$[L_1, U_1], [L_2, U_2], \dots$ over the integer test-piece length $k$, computed by climbing
$k$ from the bottom up:

- below `MIN_PIECE_LEN` no piece can exist, so lengths are forbidden; let $L_1 \ge$
  `MIN_PIECE_LEN` be the shortest assembleable length. $[1, L_1)$ is forbidden.
- increase $k$ until the **end position** `current_layer_len` $+\ k$ first becomes forbidden:
  (i) $k$ exceeds the remaining layer gap `current_layer_left` — no piece fits any more — or the
  candidate $k$ lands inside a *dead zone* $(\text{left} - \text{MIN\_PIECE\_LEN}, \text{left})$:
  equivalently the new gap `left` $-\ k \in (0, \text{MIN\_PIECE\_LEN})$, which no future piece
  could ever fill (spec, assemble constraint 1); or (ii) the end position falls
  inside a forbidden interval of either type: a global `FORBIDDEN_INTERVALS` entry, or
  $(p - \text{PREV\_MEET\_FORBIDDEN\_HALF},\ p + \text{PREV\_MEET\_FORBIDDEN\_HALF})$ around a
  meeting position $p$ of the previous layer (spec, constraints 2–3). That closes an allowed
  interval at $U_i$.
- skip $k$ while it stays forbidden, reopen at the next allowed $L_{i+1}$, and continue until
  $k$ reaches the remaining gap. End positions at `LAYER_LEN` need no special case: they are
  beam ends, never meeting positions (the spec's exact-fill exemption), so the climber extends
  the last interval's $U$ to the exact fill whenever it reaches it.

Determining "assembleable" uses the same four constraints the env's `assemble_legal` check uses
(spec, "Assemble constraints"): layer-gap and the two forbidden-interval families apply directly to
the end-position arithmetic above; the finishability/lookahead constraint 4 eliminates the
*remaining* candidate intervals — those that survive 1–3 but strand the layer or the next layer.
The interval set for the network is therefore the set of $k$ with
`assemble_legal_mask[k-1] == True`, presented as merged consecutive ranges rather than a
`MAX_PIECE_LEN`-long boolean vector.

**The next layer.** The same construction is applied one layer up while the current layer is still
being assembled: imagine a test piece placed at the start of that next layer (hypothetically). Its
allowed intervals follow from the global forbidden
intervals plus the previous-layer intervals imposed by the **current** layer's meeting positions
*as they stand now* — the meetings are a per-state observable, so the network's interval set is
computed once per state, before the action is known (the env's finer per-candidate lookahead in
constraint 4, which unions in each candidate's own new meeting, stays env-side and is *not* part
of the encoding). These intervals are
exactly the meetings-checked feasibility behind constraint 4's one-layer lookahead, expressed
geometrically instead of as a DP recursion. Note that next-layer test pieces live in the **next
layer's own coordinates** `[0, LAYER_LEN]` (a fresh layer fills upward from 0): forbidden end
positions there are the open intervals
$(p - \text{PREV\_MEET\_FORBIDDEN\_HALF},\ p + \text{PREV\_MEET\_FORBIDDEN\_HALF})$ around the
current layer's meetings $p$, plus the global forbiddens — so every allowed end position keeps at
least that half-width clearance from each current-layer meeting. In particular, with
`PREV_MEET_FORBIDDEN_HALF = 0` (spec: "effectively disables constraint 3") there are **no**
previous-layer constraints at all, and the largest allowed interval extends all the way to the
exact fill at `LAYER_LEN`; likewise with `H > 0`, end positions *above* the topmost meeting's
clearance are allowed, so the largest interval end is, in general, `LAYER_LEN`, never capped by
anything in the *current* layer's coordinates. When the current layer is the beam's last layer
(`current_layer ==
NUM_LAYERS - 1`), the next layer is a fresh beam's layer 0: no previous-layer constraints exist,
and the intervals derive from global forbiddens alone (see `assemble_legal`'s
`_next_layer_finishable` branch in the reference implementation).

Interval set vs. mask: a `MAX_PIECE_LEN`-boolean mask carries the same information, but the
interval union is the *reason* behind it — the transformer learns geometry (where forbiddens sit,
how the previous layer constrains this one, when a cut can reopen an interval), not a bit-vector.

### 2.4 Padding tokens

Every variable-length block is filled up to its fixed token count with padding tokens — the
all-zero token (`TOKEN_DIM` zeros, no flags set). See §3 for how padding is masked out of
attention.

### 2.5 Variable token count per step; no positional encoding

Two properties of this encoding are worth stating explicitly, because both diverge from
"canonical" transformer usage:

**The number of processed tokens varies across the episode.** `S = 4 + Q + I + N + 6` fixes the
*capacity* of the sequence, not the number of tokens that actually carry information at a given
step. At different steps of the same episode the valid-token count differs: queue piece tokens
drain as boards are consumed, the observation window refills as boards drop, interval tokens shift
and (dis)appear as assemblies change the allowed-length geometry of both the current and the next
layer, and the saw/out/buf slots are filled and emptied by cutting, buffering, assembly, and
discarding. The same statement holds on the **output side**: the value head is always one scalar,
but the effective policy head is only ever the subset of action tokens whose env action is legal at
that step (§5) — that subset changes size and composition at every step. The transformer forward
pass, however, always runs on all `S` positions; variation is handled exclusively through the
attention mask (§3) and the legality mask (§5), never through a change of array shapes. This is
what keeps the network JIT-compilable over an entire episode.

**There is no positional encoding, so every token must be self-identifying — and the action
one-hot is not optional.** No position ids, sinusoids, or learned positional embeddings are added.
A bare transformer is permutation-invariant over its input positions; without positional encodings
it can tell two tokens apart **only** through their feature vectors. That has a sharp consequence
for action tokens: if `put_buf`, `assemble_out`, `assemble_buf`, `discard_out`, `discard_buf`,
and `discard_beam` all carried the same features, the network would map them to the **same**
output logit regardless of their layout position — the §5 slicing could not recover six distinct
actions from six permuted copies of identical logits. The eight-way action-type one-hot (§2.2)
exists precisely to break that symmetry: it makes each of the seven action groups — and the value
token — distinguishable by feature alone, with cut tokens told apart within their group by
`nlen = k / LAYER_LEN`. The same argument applies on the piece side to the four location one-hots,
and on the interval side to the `is_curr_iv` / `is_next_iv` pair.

Within the remaining feature-identical groups, permutation invariance is *desired*:

- **Queue tokens** carry `ord_frac` (dim 14), so each queue token is unique and their mutual order
  is a feature, not a position. The spec grants the policy no ordering preference *among* pieces
  beyond their lengths and positions toward the saw; `ord_frac` encodes exactly that and nothing
  more. Queue pieces of equal length at the same position cannot exist (positions are unique per
  step), so no true ambiguity remains.
- **Interval tokens** carry their endpoints `iv_start` / `iv_end`: earlier intervals have strictly
  smaller bounds, and the interval set of each layer is a set — so interval tokens are
  permutation-invariant by design, with all ordering information readable from their values.
- Padding tokens are all-zero, carry no flags, and are excluded by the attention mask (§3).

An empty saw/out/buf slot is still a real token (its location one-hot set, `nlen = 0`), and a
"stuck" layer simply contributes no interval tokens at all — both states are legible from the
token set.

## 3. Padding and attention mask

Padding follows the bin-packing recipe exactly: unused slots in the queue block, the interval
block, and any token position beyond the real entries are **all-zero vectors** (all flags 0).
Because an empty saw/out/buf slot has `nlen = 0` but keeps its location one-hot, the validity
distinguishing "real token" from "padding" is:

- token 0, the three slot tokens (saw, out, buf), all cut tokens, and all action tokens:
  always valid (cut/action tokens remain valid even when illegal — legality is enforced at the
  logits, §5);
- queue tokens: valid iff `is_queue_piece = 1`;
- interval tokens: valid iff `is_curr_iv = 1` or `is_next_iv = 1`.

Let `valid ∈ {0,1}^S` be that vector. The attention mask is

$$\text{mask}_{ij} = \text{valid}_i \land \text{valid}_j \in \{0,1\}^{S \times S},$$

i.e. both query and key must be non-padding. Padding tokens attend and are attended by nothing;
their residual stream passes through unchanged (see the bin-packing implementation for the softmax
numerics that guarantee this).

## 4. Network output heads

The network embeds each `TOKEN_DIM`-dimensional token with a linear layer
(`Dense(hidden_size)`), runs the transformer backbone, and applies **one shared scalar head**
(`Dense(1)`) to every token's final hidden state, giving `scalars ∈ ℝ^S`. Two readouts:

| token type                       | head output                                                                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| value token (0)                  | the scalar value estimate $v = \text{scalars}_0 \cdot \text{is\_value}_0$ (masked sum over the sequence, which has exactly one value token) |
| action tokens (`is_action = 1`)  | raw (pre-softmax) action logit at that token's position; all non-action positions are forced to $-\infty$ before the softmax                |
| piece tokens and interval tokens | discarded (their head output shares the same `Dense(1)` layer but is unused)                                                                |

Softmax across the action-token logits gives the action-selection probabilities, exactly the
bin-packing pattern ("apply softmax across bin token outputs" → here: across action tokens).

## 5. Action-logit mapping

The action tokens are in one-to-one correspondence with the spec's fixed action indexing
(mask length `MAX_PIECE_LEN + 6`):

| env action index | env action         | token index (from §2.1) |
| ---------------- | ------------------ | ----------------------- |
| 0 .. N-1         | `cut_1` .. `cut_N` | 3+Q+I+1 .. 3+Q+I+N      |
| N                | `put_buf`          | 3+Q+I+N+1               |
| N+1              | `assemble_out`     | 3+Q+I+N+2               |
| N+2              | `assemble_buf`     | 3+Q+I+N+3               |
| N+3              | `discard_out`      | 3+Q+I+N+4               |
| N+4              | `discard_buf`      | 3+Q+I+N+5               |
| N+5              | `discard_beam`     | 3+Q+I+N+6               |

The action logits sliced from the token outputs are combined with the environment's legal-action
mask (spec's "Legal actions" section, materialised in JAX as a fixed-shape boolean array of length
`MAX_PIECE_LEN + 6`): illegal actions are set to $-\infty$ prior to the softmax / MCTS prior, so
legality is enforced identically at the output even though all action tokens are always "valid"
for attention (§3). The permanently illegal `cut_1` .. `cut_(MIN_PIECE_LEN-1)` tokens therefore
exist in the layout (so the cut token number equals the cut length) but never receive finite
probability.
