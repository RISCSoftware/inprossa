# Glulam Beam Env — Implementation Plan

Companion to [glulam_beam_problem_description.md](glulam_beam_problem_description.md), which is the
authoritative specification. This plan covers a single, framework-free Python implementation whose
purpose is: a **random policy**, **step visualization**, and serving as an executable **completeness
test of the spec**. No gym, no JAX.

## A. Module layout

A small package under `mcts/glulam/`:

- `env.py` — config/constants, state, `reset`, `observe`, `legal_actions`, `step`.
- `policy.py` — uniform and weighted random policies over the legal-action mask.
- `configs.py` — example environment configurations.
- `visualization.py` — `render(ax, state, cfg, layout, viz_config, title=None)` plus `compute_layout` and frame / animation helpers.
- `test_env.py` — invariant assertions, spec-completeness rollout, and stuck-geometry counter reporting.
- `run_episodes.py` — episode runner that generates PNG frames and animated GIFs.

Design: an immutable `@dataclass` state plus pure functions (`step(state, cfg, action) -> (state, reward)`).
Immutability is a hard requirement (see B), not a convention: earlier states in a rollout must never be
corrupted by later steps. A rollout is therefore just a list of states — convenient for frame-by-frame
visualization and for use as an oracle.

## B. State representation

Mirrors the spec's variable tables. Each wood piece carries its length plus two provenance ids the
env tracks but never reveals to the policy: an origin `piece_id` and an origin `board_id`. The env
knows nothing about colors — coloring is derived from `piece_id` purely in the visualization.

```
Piece:                   # @dataclass(frozen=True) — pieces are immutable
    length:   int
    piece_id: int        # origin piece id (0 .. INI_PIECES-1, rightmost = 0); inherited by both fragments on a cut
    board_id: int        # origin board id (0 .. INI_BOARDS-1, rightmost = 0); inherited on a cut

PieceGroup:              # @dataclass(frozen=True) — an ordered run of pieces laid end to end
    pieces: tuple[Piece, ...]
    # derived on demand, nothing duplicated in state:
    #   total_length()            sum of the piece lengths
    #   prefix_sums()             running totals, left to right
    #   meet_positions(layer_len) {p for p in prefix_sums() if 0 < p < layer_len}
    #   append(piece), pop_last()  return a NEW PieceGroup; never mutate
    #   __len__ / __iter__ / __bool__ / __getitem__  so it reads as a sequence

EnvConfig:               # env dynamics
    LAYER_LEN, NUM_LAYERS, MIN_PIECE_LEN, MAX_PIECE_LEN,
    MIN_BOARD_LEN, MAX_BOARD_LEN,
    INI_BOARDS, INI_PIECES, OBSERVABLE_BOARDS, seed,
    FORBIDDEN_INTERVALS: list[tuple[int, int]],     # global forbidden (start, end) intervals
    PREV_MEET_FORBIDDEN_HALF: int,                   # half-width of per-meeting forbidden intervals
    BOARD_LEN_SPREAD: int | None                     # generation knob (§C), not a spec constant

VizConfig:               # rendering only
    NUM_COLORS, palette (NUM_COLORS colors),
    VIZ_NUM_FINISHED_BEAMS: int | None,              # see the visualization constants table in the spec
    VIZ_SHOW_FORBIDDEN, VIZ_SHOW_DISCARDED: bool,
    VIZ_DISCARD_ROW_WIDTH: int | None,               # None = MAX_BOARD_LEN
    label_fontsize, title_fontsize: float,           # region labels / frame title
    global_forbidden_color, local_forbidden_color: str

PolicyConfig:            # weighted random policy only
    P_CUT, P_LONGEST_PREF_CUT, P_REMAINING_PREF_CUTS, P_ASSEMBLE, P_ASSEMBLE_OUT,
    P_DISCARD_PIECE, P_DISCARD_OUT, P_DISCARD_BEAM, P_PUT_BUF

GlulamState:
    queue:           tuple[PieceGroup, ...]   # boards, left->right; each board = pieces left->right
                                              # saw piece = queue[-1][-1]
    out_piece:       Piece | None
    buf_piece:       Piece | None
    current_layer:   int                      # 0 .. NUM_LAYERS-1
    beam:            tuple[PieceGroup, ...]   # NUM_LAYERS layers, layer 0 first
    finished_beams:  tuple[tuple[PieceGroup, ...], ...]   # completed beams, each = NUM_LAYERS layers
    discarded_pieces: PieceGroup              # every wasted piece, flat, in discard order (oldest first)
    discarded_total: int
    last_reward:     int
    terminated:      bool
```

Derived (computed on demand, not stored):

- `saw_piece_len      = queue[-1][-1].length if queue else 0`
- `current_layer_len  = beam[current_layer].total_length()`
- `current_layer_left = LAYER_LEN - current_layer_len`
- `observable_pieces  = [p.length for p in flatten(queue[-OBSERVABLE_BOARDS:])]`  (left->right; all remaining if fewer boards)
- `hidden_pieces       = queue[:-OBSERVABLE_BOARDS]`  (board-grouped; empty if fewer than OBSERVABLE_BOARDS boards remain)
- `prev_meet_positions = beam[current_layer - 1].meet_positions(LAYER_LEN)`  (only if current_layer > 0; excludes beam ends)
- `current_meet_positions = beam[current_layer].meet_positions(LAYER_LEN)`

### Why `PieceGroup`

A board in the queue, a layer of a beam, and the discard pile are the same shape: an ordered run of
pieces laid end to end, whose length is the sum of its pieces and whose internal boundaries are its
prefix sums. Today only `Piece` is a dataclass and all three groups are bare `list[Piece]`, so that
arithmetic is re-derived at every call site — `sum(p.length for p in ...)` / `accumulate(...)` appears
5 times in `env.py` (`_prefix_sums`, `_interior_meet_positions`, `current_layer_len`, ...), 9 times in
`test_env.py`'s invariant checks, and again in `visualization.py` when measuring row widths. Giving
the group a type collapses those to three methods.

The second reason is immutability. Section A calls it a hard requirement, but `list[list[Piece]]`
enforces nothing: only `step`'s internal discipline stops a caller — or a future branch of `step` —
from mutating a list that an earlier state still references. That is exactly the failure the
"no mutation" invariant in F has to test for after the fact. Tuple-backed `PieceGroup` (and tuples
for `queue` / `beam` / `finished_beams`) makes it structural, and the invariant becomes a
belt-and-braces check rather than the only line of defence.

Two caveats:

- `total_length()` is O(n). Fine for boards (~3 pieces) and layers (at most `LAYER_LEN // MIN_PIECE_LEN`),
  but `discarded_pieces` grows to thousands of entries over a long episode, so `discarded_total` stays
  the O(1) accessor: production code reads that field, never `discarded_pieces.total_length()`. The
  one place the O(n) call is warranted is the waste-conservation assertion in §F, and only under the
  sampling rule stated there — a naive every-step call would make a long rollout quadratic in the
  number of discarded pieces.
- The migration touches `env.py`, `test_env.py` and `visualization.py`, but it is mechanical: every
  site either loses a hand-rolled sum or swaps `list` for `tuple`.

Considered and not adopted: a `Beam` wrapper around `tuple[PieceGroup, ...]`. A beam carries no data
beyond its layers, and the interesting operations on it (finishability, forbidden intervals between
adjacent layers) are already functions of `(state, cfg)` in `env.py` — a third wrapper would add
indirection without removing duplication. Worth revisiting only if finished beams ever need per-beam
metadata, e.g. the step at which they were completed.

Board grouping (the tuple of `PieceGroup`s), every piece's `piece_id` / `board_id`, and
`discarded_pieces` are stored but excluded from the observation, matching the spec's
"not observable" clause.
`discarded_pieces` starts empty at `reset` and only ever grows. `piece_id` is an origin/lineage id,
not unique across live fragments (both parts of a cut share it). Consuming the saw piece pops from
`queue[-1]`; an emptied board is dropped; the observation window is a plain suffix slice.

`step` never mutates: it rebuilds exactly the containers it touches (e.g. `queue[-1]` becomes a new
`PieceGroup`, `beam[current_layer]` becomes a new `PieceGroup` on assemble) and shares untouched
sub-structures (copy-on-write); the state itself is replaced via `dataclasses.replace` or
reconstruction, never edited in place. With `PieceGroup` and tuple containers this is enforced by the
types rather than by convention.

## C. Instance generation (`reset`)

Generate `INI_BOARDS` boards, each of length in the piece-count-intersected interval
`[max(MIN_BOARD_LEN, n_b * MIN_PIECE_LEN), min(MAX_BOARD_LEN, n_b * MAX_PIECE_LEN)]` (where `n_b` is
the number of pieces in that board; see the piece-count-partition bullet below), split into
integer pieces each in `[MIN_PIECE_LEN, MAX_PIECE_LEN]` and summing to the board length; `INI_PIECES`
pieces in total. Enumerate the initial pieces `0 .. INI_PIECES-1` as their `piece_id`, starting at the
saw end: the rightmost piece gets id 0, ids increase to the left. Assign each board its `board_id` the
same way (rightmost board = 0 at reset, decreasing left->right as in the spec), carried by all of its
pieces. Ids are fixed at reset; cutting never changes the id of any piece or board.

At the top of `reset`, assert joint config feasibility and raise `ValueError` naming the violated
condition (instead of risking an infinite generation loop or an invalid instance). At minimum:

- `INI_PIECES >= INI_BOARDS`;
- `MIN_PIECE_LEN >= 1` and `MIN_PIECE_LEN <= MAX_PIECE_LEN`;
- `NUM_LAYERS >= 1`;
- `OBSERVABLE_BOARDS >= 1`;
- `MIN_PIECE_LEN <= MIN_BOARD_LEN <= MAX_BOARD_LEN` and `MAX_PIECE_LEN <= MAX_BOARD_LEN`
  (re-assert the spec constraints);
- `OBSERVABLE_BOARDS <= INI_BOARDS`;
- `MIN_PIECE_LEN <= LAYER_LEN`; note: if `MAX_PIECE_LEN > LAYER_LEN`, pieces longer than a layer can
  never be assembled and must always be discarded (legal but wasteful);
- `PREV_MEET_FORBIDDEN_HALF >= 0`;
- every `(start, end)` in `FORBIDDEN_INTERVALS` satisfies `0 <= start < end <= LAYER_LEN`;
- the config passes a base-case feasibility check (`reachable(0)` using only the global forbidden
  intervals, since layer 0 has no previous layer);
- a piece-count partition of `INI_PIECES` across the boards exists such that every board `b` (with
  `n_b` pieces) has a non-empty per-board length interval:
  `max(MIN_BOARD_LEN, n_b * MIN_PIECE_LEN) <= min(MAX_BOARD_LEN, n_b * MAX_PIECE_LEN)`.

Note: the spec constrains but does not fully fix the generation distribution (board-length sampling,
how `INI_PIECES` is partitioned across boards). Implement it as a config-driven helper
(reserve-minimum-then-distribute-remainder) and treat the exact distribution as a knob, not a spec
requirement.

**`BOARD_LEN_SPREAD` (generation knob).** Uniform sampling over the whole per-board interval puts the
average board at the middle of `[MIN_BOARD_LEN, MAX_BOARD_LEN]`, which draws a hidden stack of visibly
ragged rows. With `BOARD_LEN_SPREAD = s` set, each board's length is instead drawn uniformly from the
top `s` units of its feasible interval (`lo = max(lo, hi - s)`), so boards come out close to
`MAX_BOARD_LEN`; `None` keeps the full-interval draw. Two details make the knob actually bite:

- The piece count bounds the board length: a board of `n` pieces cannot exceed `n * MAX_PIECE_LEN`, so
  boards with too few pieces stay short of `MAX_BOARD_LEN` no matter what `BOARD_LEN_SPREAD` says.
  `_partition_piece_counts` therefore hands out `ceil(MAX_BOARD_LEN / MAX_PIECE_LEN)` pieces per board
  first (in random board order, so a short piece budget does not always starve the same end of the
  queue) before distributing what is left.
- Consequently `INI_PIECES` should be at least `INI_BOARDS * ceil(MAX_BOARD_LEN / MAX_PIECE_LEN)` for
  the knob to reach every board; the example configs are sized that way.

Feasibility gains one check: `BOARD_LEN_SPREAD is None or BOARD_LEN_SPREAD >= 0`.

## D. Core functions

### `observe(state, cfg)`
Returns a dict with the spec's observable variables:
`current_layer`, `current_layer_len`, `current_layer_left`, `observable_pieces` (variable-length
list, no padding; upper bound `MAX_OBSERVABLE_PIECES = OBSERVABLE_BOARDS * (MAX_BOARD_LEN // MIN_PIECE_LEN)`),
`out_piece_len`, `buf_piece_len`, `saw_piece_len`, `prev_meet_positions`, `current_meet_positions`, and `assemble_legal_mask` (a
boolean list of length `MAX_PIECE_LEN`).

`assemble_legal_mask[k-1]` is `True` if a piece of length `k`, placed at the current layer position,
would satisfy all four assemble constraints (layer-gap, global forbidden intervals, previous-layer
forbidden intervals, and finishability). It tells the policy which cut lengths produce an assembleable
piece; it does not constrain cuts.

### `legal_actions(state, cfg)`
Boolean mask of length `MAX_PIECE_LEN + 6`, fixed order:
`cut_1 .. cut_N` (indices 0..N-1), `put_buf` (N), `assemble_out` (N+1), `assemble_buf` (N+2),
`discard_out` (N+3), `discard_buf` (N+4), `discard_beam` (N+5).
Conditions transcribed verbatim from the spec's Legal-actions
table. For `assemble_out` / `assemble_buf`, the four assemble constraints (below) must all hold for
the resulting layer fill (`new_layer_len = current_layer_len + piece_len`).

#### Assemble constraints helper
`assemble_legal(state, cfg, piece_len) -> bool` checks all four constraints for the resulting
`new_layer_len = current_layer_len + piece_len`. If `piece_len < MIN_PIECE_LEN`, returns `False`
(forced, so the mask consistency invariant holds).

1. **Layer-gap**: `piece_len == current_layer_left` or `piece_len <= current_layer_left - MIN_PIECE_LEN`.
2. **Global forbidden**: if `new_layer_len != LAYER_LEN`, no `(start, end)` in `FORBIDDEN_INTERVALS`
   satisfies `start < new_layer_len < end`. The exact-fill case is exempt (beam end, not a meeting).
3. **Previous-layer forbidden** (only if `current_layer > 0` and `new_layer_len != LAYER_LEN`):
   `new_layer_len` is not inside any interval `(p - PREV_MEET_FORBIDDEN_HALF, p + PREV_MEET_FORBIDDEN_HALF)`
   for any `p` in `prev_meet_positions` (strictly interior prefix sums). The exact-fill case
   (`new_layer_len == LAYER_LEN`) is exempt because `LAYER_LEN` is a beam end, not a meeting position.
4. **Finishability and next-layer feasibility** (geometric reading — ignores queue/out/buf contents):
   - **Current layer finishable**: `reachable(new_layer_len)` where `reachable(f)` is defined as:
     `reachable(LAYER_LEN) = True`; `reachable(f) = exists s in [MIN_PIECE_LEN, MAX_PIECE_LEN]` with
     `f + s == LAYER_LEN` (exact fill) or (`f + s <= LAYER_LEN - MIN_PIECE_LEN` and `f + s` passes
     constraints 2–3 and `reachable(f + s)`).
   - **Next layer finishable (one-layer lookahead)**: `reachable(0)` using the current layer's meeting
     positions (including this assembly) as `prev_meet_positions` for constraints 2–3 (or no
     previous-layer constraints for a new beam's layer 0). This is a local check: it ensures only that
     the next layer can be finished, not that layers beyond that are guaranteed. `discard_beam` is the
     safety valve if a beam nonetheless becomes stuck. Compute the current-layer `reachable` DP table
     once per observation state and share it across all candidate lengths in `assemble_legal_mask`;
     that table costs `O(LAYER_LEN * MAX_PIECE_LEN)`. The next-layer lookahead cannot share it: each
     candidate length produces a different meeting-position set and so needs its own
     `O(LAYER_LEN * MAX_PIECE_LEN)` DP, which makes the lookahead the dominant term and the mask
     `O(LAYER_LEN * MAX_PIECE_LEN²)` per observation. (Measured: 13 DP tables per mask on `large_50`,
     `MAX_PIECE_LEN = 20`, on average; candidates that fail the cheap constraints 1–3 exit before the
     lookahead builds its table.) If that ever matters, memoize the lookahead on the meeting-position set —
     but note the mask is already computed once per step inside the policy, so the win is in not
     recomputing masks elsewhere rather than in the DP itself.

Used by both `legal_actions` (for assemble legality) and `observe` (for `assemble_legal_mask`).

### `step(state, cfg, action) -> (next_state, reward)`  (pure)

- **`cut_k`**: the saw piece `s` (`= queue[-1][-1]`) is split. A new piece of length `k` goes to
  `out_pos`, inheriting `s.piece_id` and `s.board_id`; the left remainder `rem = s.length - k` stays
  at the saw and also keeps `s.piece_id` / `s.board_id`.
  - `rem == 0`      -> pop the saw piece (exact, no waste).
  - `0 < rem < MIN` -> pop it, `wasted = rem`.
  - `rem >= MIN`    -> replace the saw piece with a **new** `Piece(length=rem, ...same ids...)`;
    `queue[-1]` becomes a new `PieceGroup` containing it (no in-place mutation).
  Drop an emptied board. `reward = -wasted`.
- **`put_buf`**: `buf = out; out = None`. reward 0.
- **`assemble_out` / `assemble_buf`**: `beam[current_layer]` becomes a new `PieceGroup` with the
  `Piece` appended; clear the position. If the layer sum reaches `LAYER_LEN`: if it was the last
  layer -> append the completed `beam` tuple to `finished_beams` (no copy needed: pieces, groups and
  the containers are all immutable), reset `beam` to `NUM_LAYERS` empty
  layers, `current_layer = 0`; else `current_layer += 1`. reward 0.
- **`discard_out` / `discard_buf`**: `wasted = piece.length`; clear the position; `reward = -wasted`.
- **`discard_beam`**: `wasted = sum of all piece lengths in all layers of beam`; reset `beam` to
  `NUM_LAYERS` empty layers, `current_layer = 0`; `reward = -wasted`.

Every branch that sets `wasted > 0` also appends the wasted `Piece` objects to the
`discarded_pieces` group. Rather than threading that through each branch, the cleanest shape is for
each branch to produce a local `wasted_pieces: tuple[Piece, ...]` and for the common tail to derive
both `discarded_total` and the extended `discarded_pieces` group from that one value — which makes
the `discarded_pieces.total_length() == discarded_total` invariant true by construction rather than
by discipline. Per branch:
- `cut_k`: `[Piece(rem, saw.piece_id, saw.board_id)]` when `0 < rem < MIN_PIECE_LEN`, else `[]`.
  Note the remainder piece must be constructed even though the current code only needs its length.
- `discard_out` / `discard_buf`: `[piece]`.
- `discard_beam`: `[p for layer in beam for p in layer]` — layer 0 first, left to right within a
  layer. Read from `beam` *before* it is reset.
- all other actions: `[]`.

Then update `discarded_total`, `discarded_pieces`, `last_reward`, and recompute
`terminated = (not queue) and out_piece is None and buf_piece is None`.

### Reward
`reward = -wasted_len`, exactly the spec's table. Stranded beam pieces at termination yield nothing.

## E. Random policy (`policy.py`)

Two policies:

- **`uniform_policy`**: uniform choice over legal actions. Respects the mask.
- **`weighted_policy`**: distributes probability mass over action groups per the spec's Weighted
  random policy section. Takes a `PolicyConfig` with `P_CUT`, `P_LONGEST_PREF_CUT`,
  `P_REMAINING_PREF_CUTS`, `P_ASSEMBLE`, `P_ASSEMBLE_OUT`, `P_DISCARD_PIECE`, `P_DISCARD_OUT`,
  `P_DISCARD_BEAM`, `P_PUT_BUF`. Cut mass is split three ways over a partition of the legal cuts:
  the single longest *preferred* cut (largest `k` that is a legal `cut_k` and flagged `True` in
  `assemble_legal_mask`), the other preferred cuts, and the non-preferred ones. Since action index
  `i` is `cut_(i+1)` and `assemble_legal_mask[i]` flags length `i+1`, "longest" is just the largest
  flagged legal index. Assemble mass is split between `assemble_out`
  and `assemble_buf`. Discard-piece mass splits between `discard_out` and `discard_buf` per `P_DISCARD_OUT`.
  `discard_beam` is its own single-member group taking `P_DISCARD_BEAM` of the total. Both levels use
  the same fallback, implemented once in a `_spread(mass, subgroups)` helper: empty subgroups drop out
  and the remaining weights are renormalized, so their mass flows to the non-empty siblings. Group
  weights normalized to sum to 1.0.

`run_episode(cfg, policy_seed, policy=weighted_policy, policy_config=None, max_steps=100_000)`
rolls out to termination, returning `(states, actions, rewards, stuck_progress_steps)`. If `policy_config`
is `None` and `policy` is `weighted_policy`, a default `PolicyConfig` with the spec's example values
is used. `stuck_progress_steps` counts steps where neither assemble_out nor assemble_buf was legal (the beam
could not make progress), accumulated from the masks already computed for the policy — no extra DP
passes. This is distinct from `stuck_geometry_steps` (§F), which counts steps where `assemble_legal_mask`
is all `False` (no cut length is geometrically assembleable). The two diverge whenever a legally
assembleable piece sits at `out`/`buf` while no cut length is assembleable, or when the queue is
empty short of termination. The progress counter is reported by `run_episode` (episode runs);
the geometry counter is reported by `run_checked_episode` (checked rollouts in `test_env.py`).
Neither is an assertion. `max_steps` guards against unbounded episodes. Note: `P_DISCARD_BEAM = 0.001` is a raw
weight, not a per-step probability: it would imply ~1000 steps to clear a stuck beam only if every
other group stayed legal throughout. In practice, other groups' mass is redistributed by the
fallback rule, so beams clear substantially sooner than the raw weight suggests. Treat ~1000 steps
as a loose upper bound on the recovery lag rather than an expectation — easy to misread as poor
cutting rather than a stuck-beam recovery lag.

## F. Invariants / spec-completeness test (`test_env.py`)

Assert every step (these are executable spec clauses):

- `0 <= current_layer_len <= LAYER_LEN`; a completed layer sums to exactly `LAYER_LEN`.
- `current_layer_left` is never in the open interval `(0, MIN_PIECE_LEN)` (guaranteed by the
  layer-gap assemble constraint).
- The current layer is always finishable: `reachable(current_layer_len)` holds using constraints 2–3.
- The next layer is always finishable: `reachable(0)` holds using the current layer's meeting
  positions, or with no previous-layer constraints if `current_layer == NUM_LAYERS - 1` (the next
  layer is a new beam's layer 0).
- Every saw piece is always `>= MIN_PIECE_LEN` (entry guarantee + remainder-removal rule).
- No meeting position in any layer of the current beam or any finished beam falls inside any
  `FORBIDDEN_INTERVALS` interval.
- If `current_layer > 0`, no meeting position in the current layer falls inside any
  `(p - PREV_MEET_FORBIDDEN_HALF, p + PREV_MEET_FORBIDDEN_HALF)` for `p` in the previous
  layer's meeting positions (strictly interior). This holds for every consecutive layer pair in the
  current beam (layer `i` vs layer `i-1` for `i > 0`) and for every consecutive pair in each finished beam.
- `assemble_legal_mask` is consistent: for each `k`, `mask[k-1]` matches
  `assemble_legal(state, cfg, k)`.
- `current_layer_len == max(current_meet_positions)` when the current layer is non-empty (and 0 when
  empty) — catches a `current_meet_positions` implementation that filters the wrong endpoint. A full
  layer is never observed as a state (the env advances immediately), so this invariant can only ever
  see a non-full layer.
- No deadlock: `terminated or any(legal_actions(state, cfg))`. (Discards are always legal when a position
  is occupied; cuts are legal when the queue is non-empty and `out_pos` is empty.)
- Length conservation:
  `input_total == locked_in_finished + discarded_total + stranded_beam + in_flight(out, buf, queue)`
  at every step, where `locked_in_finished = len(finished_beams) * NUM_LAYERS * LAYER_LEN`.
- Waste conservation: `discarded_pieces.total_length() == discarded_total`. This is the check that
  the new `discarded_pieces` bookkeeping cannot drift from the reward signal, but the sum is O(n) in
  the number of discarded pieces, so running it on every step makes a long rollout quadratic
  (`xlarge_200` reaches thousands of waste entries over ~2000 steps). Instead track the expected
  total incrementally in the test — it already maintains a per-action tally for the per-lineage check
  below — assert the incremental value against `discarded_total` every step, and do the full O(n)
  recomputation from `discarded_pieces` only on the last step of the rollout and every N steps
  (N ≈ 100) in between.
- Per-lineage conservation (equality): for each origin `piece_id`, the summed lengths of all live
  fragments (queue + out + buf + current beam) plus fragments locked in finished beams plus
  fragments discarded so far equal the origin piece's initial length exactly. The discarded part is
  now read straight off `state.discarded_pieces` grouped by `piece_id`, which replaces the test's own
  per-action waste attribution (including the `discard_beam` case, which previously had to read the
  beam layout before the discard was applied). Keeping the test's independent tally alongside the
  state's list — and asserting the two agree — is worth it: derive-from-state alone would no longer
  catch a `step` that attributes waste to the wrong lineage.
- No mutation: after a full rollout, `states[0]` is unchanged (e.g. its total queue length still
  equals `input_total`) — directly detects accidental in-place mutation of shared sub-structures.
- **Stuck-geometry counter** (observational, not an assertion): count steps in which `assemble_legal_mask`
  is all `False` (no cut length is geometrically assembleable at the current layer position). Report this
  count as `stuck_geometry_steps` alongside waste at the end of a rollout. It is the empirical answer
  to whether the one-layer lookahead is sufficient in practice. This is distinct from `stuck_progress_steps`
  (§E), which counts steps where neither `assemble_out` nor `assemble_buf` was legal (the beam could not
  make progress regardless of whether a geometrically assembleable cut exists). The progress counter
  is reported by `run_episode` (episode runs); the geometry counter by `run_checked_episode`
  (checked rollouts). Neither is an assertion.

If any branch cannot be written without inventing a rule the spec does not state, that pinpoints a
spec gap; such gaps should be reported to the spec's author and the spec updated accordingly.

## G. Step visualization (`visualization.py`)

`render(ax, state, cfg, layout, viz_config, title=None)` draws into a passed Axes, following the existing
[mcts/bin_packing/visualization.py](mcts/bin_packing/visualization.py) style. Every segment's color is
`viz_config.palette[piece.piece_id % viz_config.NUM_COLORS]` (the env stores no color; it is derived
here), and every segment gets a black outline so neighboring pieces stay separable even when they
share a color. Five regions, left to right, per the spec's Episode-visualization section:

1. **Hidden-pieces stack (left):** one horizontal **row** per hidden board; each row is a run of
   flush, colored segments (one per piece, width proportional to length). The queue's
   left-to-right order maps to the stack's bottom-to-top order: the rightmost board of the hidden
   queue is the top row, the next board is the row below it, and so on down to the leftmost board
   at the bottom. Row pitch = `h + 0.8h` (segment height plus 0.8h vspace).
2. **Observable pieces:** a **vertical stack** of segments running in the same direction as the
   hidden stack — top = nearest the saw, bottom = furthest from it. The piece *at* the saw is not
   drawn here (region 3 has it), so this is the window minus its rightmost piece; a drawing split
   only, `observable_pieces` still includes it. Piece display width is capped at `MAX_PIECE_LEN`.
   Board boundaries are not drawn. Row pitch = `h + 0.8h`. The visualization reads the underlying
   piece objects (hidden state) for coloring, not the observable length scalars.
3. **saw / `out` / `buf` pieces:** three fixed slots, bottom to top in the order a piece travels
   through them: saw piece (`queue[-1][-1]`) on the baseline, then `out`, then `buf`. An empty slot
   draws nothing. Slot pitch = `h + 3.5h` — much wider than the other stacks because each slot's
   label hangs in the gap below it and must clear a line of text. Three labels, one per slot
   (`saw`, `out`, `buf`), left-aligned with the slot anchor.
4. **Assembled beams:** a pile resting on the baseline — oldest displayed beam at the bottom, the
   current unfinished beam on top. Each beam is drawn Lego-brick style (no gaps within a beam), with
   `current_layer` highlighted in the topmost beam even while that layer is empty.
   `VIZ_NUM_FINISHED_BEAMS` controls how many finished beams are shown (see the visualization constants
   table in the spec). Beam pitch = `NUM_LAYERS * h + 1.6h` (segment height per layer plus 1.6h vspace).
5. **Discarded pieces (right, optional):** drawn only when `VIZ_SHOW_DISCARDED`; when off, the region
   reserves no width and no height. Greedy row packing over `discarded_pieces` in discard order: fill a
   row left to right, and when the next piece would push the row past `VIZ_DISCARD_ROW_WIDTH`
   (default `MAX_BOARD_LEN`) start a new row above it. First row on the baseline, pile grows upward.
   Row pitch = `h + 0.8h` — the same convention as region 1. Beams discarded via `discard_beam` arrive
   already flattened in `discarded_pieces`, so this region needs no beam-specific handling.

Scalar state (`current_layer`, `current_layer_left`, `last_reward`, `len(finished_beams)`,
`discarded_total`) goes in the title.

**Fixed layout with per-region padding boxes.** Each region has a `RegionBox` with a tight content
rectangle and padding on all four sides: `pad_x = pad_factor_x * base` left and right,
`pad_y = pad_factor_y * base` below and above, with `base = min(content_w, content_h)` and both
content dimensions floored at `h` so that a one-segment-tall (or empty) region still gets a gap to
its neighbours. `pad_factor_x = 0.3` and `pad_factor_y = 0.15`: the horizontal padding is the
inter-region spacing, the vertical padding is only headroom, so they are tuned separately. Regions
are placed left to right so that the padded boxes tile the x-axis without overlap — no separate
`region_gap` constant is needed. All content rests on `y = 0` (bottom-aligned).

The segment height is `h = max(1, MAX_PIECE_LEN / 12.5)`. It is deliberately tied to `MAX_PIECE_LEN`
rather than to `LAYER_LEN`: pieces then keep their drawn aspect ratio across configs, and doubling
`LAYER_LEN` draws a beam twice as long instead of scaling the whole frame (which, since the vertical
stacks scale with `h`, only turned the frame portrait and shrank everything again).

Region widths come from the constants: `max(sum(board))` for region 1, `MAX_PIECE_LEN` for regions 2
and 3, `LAYER_LEN` for region 4, `VIZ_DISCARD_ROW_WIDTH` for region 5.

Region heights are `n_rows * (h + 0.8h) - 0.8h` (regions 1, 2, 5), `3 * (h + 3.5h) - 3.5h` for
region 3's three slots, and `(1 + n_finished_shown) * (NUM_LAYERS * h + 1.6h) - 1.6h` for region 4.
`compute_layout` takes the rollout's `states` optionally and derives the row counts two ways:

| Region         | From `states` (used by `run_episodes`)                                                          | From the initial state + config alone                                                                               |
| -------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 1 hidden stack | `INI_BOARDS - OBSERVABLE_BOARDS` (exact: it only drains)                                        | same                                                                                                                |
| 2 observable   | largest window the episode shows, minus the saw piece                                           | largest piece count over all sliding windows of `OBSERVABLE_BOARDS` consecutive initial boards, minus the saw piece |
| 4 beams        | `1 + min(VIZ_NUM_FINISHED_BEAMS, beams finished)`                                               | `1 + min(VIZ_NUM_FINISHED_BEAMS, INI_BOARDS * MAX_BOARD_LEN // (NUM_LAYERS * LAYER_LEN))`                           |
| 5 discard pile | rows of the final pile (packing a prefix can only add rows, so the fullest pile is the maximum) | `1 + total_input_len // max(1, VIZ_DISCARD_ROW_WIDTH - MAX_PIECE_LEN + 1)`                                          |

The config-only column is a safe bound but a loose one — it assumes the whole input is wasted and
every possible beam finished — so frames sized that way carry a wide empty band above the piles;
`run_episodes` therefore passes `states`. Both columns keep one `xlim`/`ylim` for the whole episode,
so the animation does not rescale as the queue drains.

Two traps in the region-5 bound, both of which produced unusable frames once:
- It **degenerates when `VIZ_DISCARD_ROW_WIDTH == MAX_PIECE_LEN`**: the divisor collapses to 1 and the
  bound becomes `total_input_len` rows (1851 on `large_50`, ~40x region 1), which crushes every other
  region into the bottom sliver of the frame. Hence the `MAX_BOARD_LEN` default (divisor 31, 60 rows
  against region 1's 47).
- The greedy packing must be **the same code** in the layout and in the drawing (`_discard_placements`),
  or the reserved height silently stops matching the drawn pile.

The observable-window bound matters for the same reason on a smaller scale: the config-only
`OBSERVABLE_BOARDS * (MAX_BOARD_LEN // MIN_PIECE_LEN)` reserves 36 rows where the actual queue never
exceeds 16 on `medium`.

**Frames / animation:** because `step` is pure, a rollout yields `states = [s0, s1, ...]`; frame `t` is
`render(ax, states[t], cfg, layout, viz_config)`. Emit one PNG per step (filmstrip / grid) or stitch a GIF
(`imageio` or `matplotlib.animation.FuncAnimation`).

## H. Build order

Initial build (done):

1. `env.py`: config, state, `reset`, `observe`, `legal_actions`, `step`.
2. `policy.py`: random policy.
3. `test_env.py`: invariants + a random rollout to termination (spec-completeness check).
4. `visualization.py`: `render` + frame/animation helpers.

Since done: `discarded_pieces` (the state field, the append rules on every wasting action, and the
`sum(discarded_pieces) == discarded_total` invariant in `test_env.py`), and the whole fifth
visualization region — `VIZ_SHOW_DISCARDED`, `VIZ_DISCARD_ROW_WIDTH`, the greedy row-packed pile with
conditional layout reservation, the `discarded pieces` label, and the per-slot `saw` / `out` / `buf`
labels. The
spec's `VIZ_STACK_OBS_GAP` / `VIZ_REGION_GAP` are gone: the padding boxes above superseded them, and
the spec's Episode-visualization section was updated to match.

Outstanding, in dependency order:

5. `PieceGroup` migration (§B): introduce the type, retype `queue` / `beam` / `finished_beams` to
   tuples, and collapse the hand-rolled sums and `accumulate` calls in `env.py`, `test_env.py` and
   `visualization.py` onto its methods. Behaviour-preserving — do it first and on its own, so the
   next two steps land on immutable containers and the diff stays reviewable. This step also removes
   the double mask computation in `test_env.py`'s `run_checked_episode` (review issue 4): the test
   currently calls `assemble_legal_mask(state, cfg)` for the `stuck_geometry_steps` counter and then
   `weighted_policy` recomputes the identical mask internally — `2 × O(LAYER_LEN · MAX_PIECE_LEN²)`
   per step. The fix is to pass the already-computed mask through to the policy (or hoist the counter
   into a shared helper), which is natural to do here since both files are already being edited.
6. Regenerate the episode artifacts under `logs/glulam/` after any visualization change, and after
   step 5 confirm it changed nothing: a rollout's step count, beam count, `discarded_total` and stuck
   counters (`stuck_progress_steps` from `run_episode`, `stuck_geometry_steps` from
   `run_checked_episode`) are the regression check — step 5 must preserve all of them.

`visualization.py` still has no test coverage, and the layout has now regressed twice (once in the
piece anchoring, once in the region-5 row bound, which crushed every region into the bottom sliver of
the frame). A test asserting rectangle positions for 0/1/N finished beams and for a known discard
pile, plus one asserting that no region's drawn content escapes its `RegionBox` and that `ylim` is
within a small factor of the tallest drawn content, would have caught both.
