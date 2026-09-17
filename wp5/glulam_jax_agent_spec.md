# Glulam Beam Assembly Problem — JAX Agent Specification

Companion to [glulam_problem_and_simple_env_spec.md](glulam_problem_and_simple_env_spec.md),
which is authoritative for the problem dynamics, constants, observable and hidden variables,
actions, legality, and reward. It binds this implementation as it binds the simple one; where this
document departs from it, the deviation is marked explicitly.

This document specifies **only what is new** in casting that problem as a reinforcement learning
problem and solving it with a JAX/Flax transformer guided by tree search: the POMDP framing, the
policy input and its encoding, the network, the search, instance generation, and the training
setup.

## Design philosophies

The encoding below follows the same set of design philosophies as the rest of the workspace:

- **Spec-first, executable-second.** Specs are authoritative and framework-free; implementations
  exist to prove spec completeness — a branch that cannot be written without inventing a rule
  marks a spec gap, not a code gap.
- **Reference, don't duplicate.** Anything reusable is referenced, not copied; new documents are
  companions to one authoritative spec, with an explicit reuse map.
- **Minimal, set-based policy input.** Items as sets — no arbitrary ids, no positions that carry
  meaning. The observation may hold labels and bookkeeping; the policy input must not. Every
  attribute the model sees has a written justification. The same information is never fed twice;
  an attribute is left out when it is applied at the output instead (legality), superseded by a
  better representation (intervals over meet positions), or redundant with what is already there.
- **Legality masks are outputs, not inputs.** The network receives geometry (intervals, lengths),
  never precomputed yes/no answers; masks enforce legality at the logits — one instance of the
  observation → policy-input boundary (see [Layers and boundaries](#layers-and-boundaries)).
- **Permutation invariance as a semantic principle.** Token identity flows through features, never
  through *sequence* positions: a token is identified by which feature block it occupies and by the
  values in it. Invariance holds exactly where the problem is a set (conveyor contents aside from
  order, intervals), with explicit ordering features only where order is load-bearing (distance to
  the saw).
- **Configs as jointly feasible objects.** Constants come with constraint tables and base-case
  feasibility checks; violation raises a named error instead of degenerate instances.
- **JIT-friendliness by design, not adaptation.** Fixed capacities, padding, and masks from the
  start; pure functions; immutable state; no Python-level dynamic shapes; randomness through
  explicit keys only.
- **Architecture independent of capacities.** Network weights depend only on architecture
  hyperparameters (`TOKEN_DIM`, hidden size, depth), never on instance-set bounds. Bounds fix
  tensor shapes and sequence length; growing them recompiles but does not change the model. Every
  list that is unbounded in theory and `BOUND_`-bounded in practice is therefore one token per
  item, never a fixed-width feature block — observables and actions alike.
- **Documentation invariant to refactoring.** Internal links, framework-free problem descriptions,
  and every structural decision recorded together with its rationale — the *why* next to the
  *what*.

Anything not covered here — queue mechanics, cutting, assembly, legality of actions, reward — is
unchanged, and the reader is referred to the authoritative spec's corresponding section. In
particular, the full reuse map is:

| Topic                                            | Authoritative section (glulam_problem_and_simple_env_spec.md) |
| ------------------------------------------------ | ---------------------------------------------------------- |
| Problem dynamics (queue, saw, out/buf, assembly) | "Abstract, informal problem definition"                    |
| Environment constants                            | "Instance constants" table                                 |
| Instances, episodes, instance sets               | "Instances and instance sets"                              |
| Observable variables                             | "Observable variables" table                               |
| Hidden variables                                 | "Hidden variables" table                                   |
| Action space                                     | "Action space" table                                       |
| Legal actions + assemble constraints             | "Legal actions" + "Assemble constraints"                   |
| Reward                                           | "Reward" table                                             |

The sections below define, in order: the [layers and boundaries](#layers-and-boundaries) between
env state, observation, and policy input; the [policy input](#policy-input) itself, as scalars and
lists; how the beam is reduced to
[allowed intervals](#the-assembled-beam-as-allowed-intervals); and how
[instance sets and bounds](#instance-sets-and-bounds) fix static shapes; and the
[token encoding](#token-encoding) that turns the policy input into a fixed-shape tensor.
[Not yet specified](#not-yet-specified) lists the parts of the scope above that this document does
not cover yet.

## Not yet specified

Scope this document is intended to cover, still to be written:

- **POMDP formalisation** — state, observation, action, transition, reward, termination, cast
  formally from the authoritative spec's tables; which variables are hidden and why.
- **Transformer architecture** — depth, attention heads, hidden size, normalisation, parameter
  sharing; the hyperparameters that constitute "architecture" under the capacity-independence
  philosophy.
- **MCTS** — action priors from the policy head, value estimate, search parameters, how legality
  masks enter the search.
- **Planning without a transition model** — MuZero-style learned dynamics; what replaces the
  environment during search, and what that implies for the policy input.
- **Instance generation** — how an instance set is sampled; which constants vary and over what
  ranges; per-instance feasibility checks.
- **Training setup** — self-play loop, targets, losses, optimiser, batching across instances,
  evaluation protocol.

## Layers and boundaries

Three layers are kept apart throughout this document:

- **Env state** — everything the simulator holds, including the hidden variables of the
  authoritative spec: `board_id` and `piece_id` per piece, the full `beam`, `hidden_pieces` left of
  the observation window.
- **Observation** — the spec's observable variables. In the POMDP sense: what a compliant policy may
  condition on, as a single-step quantity.
- **Policy input** — what the model actually sees. Minimal and label-free; defined in
  [Policy input](#policy-input).

The two boundaries between them differ in severity. **State → observation** is *information
hiding*: crossing it relaxes the problem and invalidates any comparison against a compliant agent.
**Observation → policy input** is *minimality*: crossing it wastes capacity and changes nothing
about the problem.

The invariant this document maintains, stated once: **the policy input is a function of the
observation and of the policy-visible instance constants (enumerated in Policy input), never of
hidden state.**

Visualization and reporting consume env state directly and are deliberately unconstrained —
nothing they produce feeds a decision. They are not observations and are never called that.

Terminology note: the *observation window* (the rightmost `OBSERVABLE_BOARDS` boards of the queue)
is the authoritative spec's term for the visible part of the conveyor and is unrelated to the
"observation" layer above; it is kept unchanged.

## Policy input

What the model sees, for one instance. This section is about *content*: which quantities, and why.
It says nothing about token dimensions, positions, dtypes, capacities, or bounds — those follow in
[Instance sets and bounds](#instance-sets-and-bounds) and in the token sections. Lengths are
expressed relative to the instance's `LAYER_LEN`, so an exact fill is always `1`. Ratios below are
the defined quantities themselves, not an encoding of something else.

Derived quantities are fed only when producing them needs arithmetic the linear embedding cannot
do. A quantity the model can reach by attending to a token that already holds it is a lookup, and
duplicating it would breach "the same information is never fed twice". This rule decides the two
non-linear scalars below, the cut tokens' saw remainder, and the absence of info positions on the
six named actions.

The content falls into two categories.

### Scalars

Fixed cardinality, dedicated positions.

| scalar                                              | justification                                                                                                                       |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `saw_piece_len / LAYER_LEN` (0 = empty)             | the piece being cut; `cut_k` acts on it                                                                                             |
| `out_piece_len / LAYER_LEN` (0 = empty)             | the piece at `out_pos`; `put_buf`, `assemble_out`, `discard_out` act on it; an empty slot is a real state                          |
| `buf_piece_len / LAYER_LEN` (0 = empty)             | the piece at `buf_pos`; `assemble_buf`, `discard_buf` act on it; an empty slot is a real state                                      |
| `current_layer_len / LAYER_LEN`                     | the current layer's fill. The interval lists are expressed over test-piece length, relative to this fill, while forbidden intervals are absolute beam positions — without it the model cannot locate itself in absolute coordinates |
| beam progress `(current_layer + current_layer_len / LAYER_LEN) / NUM_LAYERS` | 0 for an empty beam, 1 for a full one. Exact from two observables, since finished layers are full by definition. Fed because it is a *product* of quantities already present, hence non-linear, and because it is the cost of `discard_beam` |
| `current_layer / NUM_LAYERS`                        | progress within the beam                                                                                                            |
| `1 / NUM_LAYERS`                                    | one layer as a fraction of the beam; distinguishes 1/2 from 5/10                                                                    |
| `boards_left / INI_BOARDS`                          | progress through the pile (`boards_left`: boards not yet on the conveyor; see the spec's observable-variables table)                |
| `1 / INI_BOARDS`                                    | one board as a fraction of the episode's material                                                                                   |
| `MIN_PIECE_LEN / LAYER_LEN`                         | dead-zone and legal-cut geometry                                                                                                    |
| `MAX_PIECE_LEN / LAYER_LEN`                         | which cuts exist for this instance (the policy input does not see the output mask)                                                  |
| `PREV_MEET_FORBIDDEN_HALF / LAYER_LEN`              | how the policy's own meeting positions will constrain the next layer; partly visible through the next-layer intervals, explicit is cheap |

### Lists

Variable length; each item is presented to the model as one token.

| list                                                           | item attributes                 | justification                                                                                                    |
| -------------------------------------------------------------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| conveyor pieces behind the saw (excludes saw, out, buf)        | length; position toward the saw | position is the one load-bearing order — it decides what is cut next                                             |
| allowed intervals, current layer                               | start, end                      | geometry is input, legality is output; the intervals are the *reason* behind the legal mask                       |
| allowed intervals, next layer                                  | start, end                      | one-layer lookahead, needed to plan cuts ahead                                                                   |
| action candidates: one per cut length, plus the six named actions | cut length, or action type   | the policy scores each candidate; candidates are not observations of the environment; legality is applied at the output |

The two interval lists are derived in
[The assembled beam as allowed intervals](#the-assembled-beam-as-allowed-intervals). How long each
list may become is a bounds matter and is deferred to
[Instance sets and bounds](#instance-sets-and-bounds).

### Actions

The action-candidate list, item by item (spec: "Action space" table):

- `cut_k`, one per cut length `k` — cut a piece of length `k` off the saw piece into `out_pos`.
- `put_buf` — move the piece from `out_pos` to `buf_pos`.
- `assemble_out` — assemble the piece at `out_pos` into the current layer.
- `assemble_buf` — assemble the piece at `buf_pos` into the current layer.
- `discard_out` — discard the piece at `out_pos`.
- `discard_buf` — discard the piece at `buf_pos`.
- `discard_beam` — discard the whole current beam and start an empty one at layer 0.

### Deliberately excluded

Each with its reason — this is where the "minimal, set-based" philosophy becomes concrete:

- `prev_meet_positions` / `current_meet_positions` — replaced by the interval lists derived from
  them.
- `assemble_legal_mask` — consumed only by the interval derivation; its geometric content reaches
  the model as the interval lists. (This is a different array from the legal-action mask of
  `legal_actions`, which is applied at the output logits and is not policy input either.)
- `current_layer_left` — equals `1 −` the fill above, a *linear* function of a fed quantity, so the
  embedding reconstructs it for free. (`current_layer_len` itself is no longer excluded; see
  Scalars.)
- `LAYER_LEN` — the unit; all lengths are relative to it.
- `INI_PIECES` — not policy-visible; it would expose the count of hidden pieces.
- `OBSERVABLE_BOARDS` — parameterises the observation mechanism, not the problem; its effect is
  already visible as the number of conveyor items.
- `MIN_BOARD_LEN`, `MAX_BOARD_LEN` — a weak prior on unobserved supply; left out initially.
- `FORBIDDEN_INTERVALS` — a list, and already folded into the allowed intervals.
- `board_id` — a hidden variable; not compliant.

The policy input is thus a function of the observation and of the instance constants named above,
never of hidden state.

## The assembled beam as allowed intervals

The policy input does not contain the beam's pieces. The policy never chooses *where* to assemble
(spec: no choice of position), only *what length* to cut, buffer, assemble, or discard — so the
useful beam-derived signal is not "which pieces sit in the layer" but "**which test-piece lengths
are still assembleable**". That set is, for the current layer, a union of disjoint allowed intervals
$[L_1, U_1], [L_2, U_2], \dots$ over the integer test-piece length $k$, computed by climbing $k$
from the bottom up:

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
The current-layer interval list is therefore the set of $k$ with
`assemble_legal_mask[k-1] == True`, presented as merged consecutive ranges.

#### The next layer

The same construction is applied one layer up while the current layer is still
being assembled: imagine a test piece placed at the start of that next layer (hypothetically). Its
allowed intervals follow from the global forbidden
intervals plus the previous-layer intervals imposed by the **current** layer's meeting positions
*as they stand now* — the meetings are a per-state observable, so the interval lists are
computed once per state, before the action is known (the env's finer per-candidate lookahead in
constraint 4, which unions in each candidate's own new meeting, stays env-side and is *not* part
of the policy input). These intervals are
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

Interval list vs. mask: a `MAX_PIECE_LEN`-boolean mask carries the same information, but the
interval union is the *reason* behind it — the model learns geometry (where forbiddens sit,
how the previous layer constrains this one, when a cut can reopen an interval), not a bit-vector.

## Instance sets and bounds

One model is trained on a **set of instances** whose instance constants differ (spec: "Instances
and instance sets"). Static JAX shapes therefore cannot follow any single instance; they follow
bounds over the set.

**Naming.** A bound over the instance set carries the bounded quantity's own name with the prefix
`BOUND_`: `BOUND_MAX_PIECE_LEN`. The prefix is applied mechanically, derived quantities included
(`BOUND_MAX_OBSERVABLE_PIECES`). Only `S` (sequence length) and `TOKEN_DIM` stay unprefixed: `S`
has no per-instance meaning, and `TOKEN_DIM` is architecture.

**A bound exists only where it fixes a tensor shape.** Exactly three quantities in
[Policy input](#policy-input) have variable length, so there are exactly three bounds — this table
is the complete `BOUND_` namespace:

| bound                         | fixes the length of                                              |
| ----------------------------- | ---------------------------------------------------------------- |
| `BOUND_MAX_OBSERVABLE_PIECES` | the conveyor-piece list                                          |
| `BOUND_MAX_INTERVALS`         | each allowed-interval list (current layer, next layer)           |
| `BOUND_MAX_PIECE_LEN`         | the action-candidate list, which holds `BOUND_MAX_PIECE_LEN + 6` |

Only `BOUND_MAX_PIECE_LEN` bounds an instance *constant*; the other two bound derived counts. **No
other instance constant needs a bound**, because nothing else sizes a tensor — the scalars of the
policy input have fixed cardinality, and rule parameters such as `PREV_MEET_FORBIDDEN_HALF` size
nothing at all.

Each bound must hold for **every** instance in the set. The environment asserts this rather than
silently truncating a list. How the values are chosen for a given set belongs to instance
generation (see [Not yet specified](#not-yet-specified)).

**Why the interval count is boundable at all.** A finite `BOUND_MAX_INTERVALS` exists because each
global forbidden interval, and each meeting position of the previous layer, can split the allowed
region of a layer at most once more — and a layer holds fewer than `LAYER_LEN / MIN_PIECE_LEN`
meeting positions. The bound is **per layer**, so each of the two interval lists takes it.

**The rule.** Shapes come from `BOUND_*`; everything else — values, normalisations, legality checks
— comes from the instance. The conveyor list is `BOUND_MAX_OBSERVABLE_PIECES` long with validity
masking, while each piece's length is `len / LAYER_LEN` using the *instance's* `LAYER_LEN`. Never
normalise by a `BOUND_` value: the policy input must be instance-intrinsic, so that the same
instance yields identical input under any instance set.

**Action list sizing.** The candidate list has one token per cut length `1 .. BOUND_MAX_PIECE_LEN`
plus the six named actions, for every instance. Candidates permanently illegal for an instance
(`k < MIN_PIECE_LEN`, `k > MAX_PIECE_LEN`) are still present and are masked at the output.

## Token encoding

The policy input becomes a sequence of `S` tokens, each a `TOKEN_DIM`-dimensional feature vector
with `TOKEN_DIM = 27`. The feature space is partitioned into **disjoint blocks**: the scalars own
one block, each list owns one block, and no two blocks share a position. A token writes its own
block and leaves every other position at zero.

Disjointness does the work that type flags used to do. A token's kind is readable from which block
it occupies, so nothing carries an `is_…` marker — no location one-hot, no interval flag, no value
or action marker. The accepted cost is that a length in one block shares no weights with a length
in another: a conveyor piece's length, an interval endpoint and a cut length are the same physical
quantity in the same units, and the model learns each separately. In exchange, the single
embedding `Dense(TOKEN_DIM → hidden)` acts as a separate linear encoder per list, so per-list
parameters come free of per-list machinery.

Every block width is fixed by the problem's rules and by this encoding, never by an instance or a
bound, which is what keeps one model valid across an instance set.

### Blocks

| block                   | positions | contents                                                                                  |
| ----------------------- | --------- | ----------------------------------------------------------------------------------------- |
| global                  | 0–11      | the twelve [scalars](#scalars), in table order                                             |
| conveyor piece          | 12–13     | length over `LAYER_LEN`; position toward the saw                                           |
| interval, current layer | 14–15     | start, end                                                                                 |
| interval, next layer    | 16–17     | start, end                                                                                 |
| action                  | 18–26     | seven one-hot positions, then two info positions                                           |

The action block in full:

| position | meaning                                                                 |
| -------- | ------------------------------------------------------------------------ |
| 18       | `cut` — set on **every** cut token, shared                                |
| 19–24    | `put_buf`, `assemble_out`, `assemble_buf`, `discard_out`, `discard_buf`, `discard_beam` — one position each |
| 25       | cut length `k / LAYER_LEN`                                                |
| 26       | saw remainder `(saw_piece_len − k) / LAYER_LEN`                           |

Cut tokens share position 18 and are told apart by positions 25–26. The six named actions each own
a position and leave 25–26 at zero: everything they would carry is a lookup in the global token,
so feeding it would duplicate. The remainder at position 26 is the opposite case — it exists
nowhere and needs a subtraction across two tokens — and it is what signals that a cut strands
waste when the remainder falls below `MIN_PIECE_LEN`.

Those two info positions belong to the whole action block, so a named action can be given a value
later without changing `TOKEN_DIM` or the architecture.

### Sequence layout

One token per item, in this order:

```
position 0                       value/global token
next BOUND_MAX_OBSERVABLE_PIECES conveyor pieces
next BOUND_MAX_INTERVALS         current-layer intervals
next BOUND_MAX_INTERVALS         next-layer intervals
next BOUND_MAX_PIECE_LEN + 6     actions
```

`S = 1 + BOUND_MAX_OBSERVABLE_PIECES + 2 · BOUND_MAX_INTERVALS + BOUND_MAX_PIECE_LEN + 6`, a
compile-time constant for an instance set. Which of those positions carry information varies every
step — conveyor tokens drain and refill, interval tokens appear and vanish as the geometry
changes, and the legal subset of actions changes — but the forward pass always runs on all `S`
positions. Variation is handled through the attention mask and the legality mask, never through a
change of shape.

### Padding and the attention mask

Padding is the **all-zero token**, and no real token can be all-zero:

- the global token always carries `1 / NUM_LAYERS`;
- a conveyor piece has length at least `MIN_PIECE_LEN`;
- an interval's start is at least `MIN_PIECE_LEN / LAYER_LEN`;
- every action token sets exactly one one-hot position.

So validity needs no flag and no special case: a token is valid iff it is not all-zero. The global
token and all action tokens are always valid; conveyor and interval tokens are valid iff the item
exists at this step. With `valid ∈ {0,1}^S`, the attention mask is

$$\text{mask}_{ij} = \text{valid}_i \land \text{valid}_j,$$

so padding neither attends nor is attended, and its residual stream passes through untouched.

### No positional encoding

No position ids, sinusoids or learned positional embeddings are added. A bare transformer is
permutation-invariant over its input positions, so every token must be identifiable from its
features alone — and under disjoint blocks it is: the block says what kind of token this is, and
the values within the block say which one.

Within a block, items separate by value. Conveyor pieces carry their position toward the saw, the
one ordering the problem makes load-bearing. Intervals carry endpoints, which are distinct and
ordered by construction. Cut tokens carry their length. The six named actions each own a position.
Nothing is left ambiguous, and nothing depends on where a token sits in the sequence.

### Output heads

The network embeds each token with `Dense(hidden_size)`, runs the transformer backbone, and applies
**one shared scalar head** `Dense(1)` to every final hidden state, giving `scalars ∈ ℝ^S`. Two
readouts:

| token           | head output                                                                    |
| --------------- | -------------------------------------------------------------------------------- |
| global (0)      | the value estimate, read directly from `scalars[0]`                            |
| action tokens   | the raw pre-softmax logit for that action                                      |
| all others      | discarded — they share the head but are unused                                 |

The separate value token of the previous layout is gone: the global token carries the value
readout. Non-action positions are forced to $-\infty$ before the softmax, which then runs across the
action tokens only.

### Action-logit mapping

Let `A = 1 + BOUND_MAX_OBSERVABLE_PIECES + 2 · BOUND_MAX_INTERVALS` be the first action position.
The action tokens are in one-to-one correspondence with the environment's fixed action indexing:

| env action index          | env action         | token position      |
| ------------------------- | ------------------ | ------------------- |
| 0 .. `BOUND_MAX_PIECE_LEN`−1 | `cut_1` .. `cut_N` | `A` .. `A + N − 1`  |
| `N`                       | `put_buf`          | `A + N`             |
| `N + 1`                   | `assemble_out`     | `A + N + 1`         |
| `N + 2`                   | `assemble_buf`     | `A + N + 2`         |
| `N + 3`                   | `discard_out`      | `A + N + 3`         |
| `N + 4`                   | `discard_buf`      | `A + N + 4`         |
| `N + 5`                   | `discard_beam`     | `A + N + 5`         |

with `N = BOUND_MAX_PIECE_LEN`. The legal-action mask has length `N + 6` and maps
position-for-position onto this range: illegal actions go to $-\infty$ before the softmax or the
MCTS prior. Cut tokens that no instance can ever use — `k < MIN_PIECE_LEN` or `k > MAX_PIECE_LEN`
for this instance — exist in the layout so that token order matches cut length, and never receive
finite probability.

**Diagram (to be generated).** A rendered (token × feature) grid would make the block structure
legible at a glance. None exists yet, and note that `docs/` is gitignored, so a diagram kept there
is absent from a fresh clone; it should be committed somewhere tracked or the reference dropped.
