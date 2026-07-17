# Glulam Beam Env — Implementation Plan

Companion to [glulam_beam_problem_description.md](glulam_beam_problem_description.md), which is the
authoritative specification. This plan covers a single, framework-free Python implementation whose
purpose is: a **random policy**, **step visualization**, and serving as an executable **completeness
test of the spec**. No gym, no JAX.

## A. Module layout

A small package under `mcts/glulam/`:

- `env.py` — config/constants, state, `reset`, `observe`, `legal_actions`, `step`.
- `policy.py` — random policy over the legal-action mask.
- `visualization.py` — `render(ax, state)` plus frame / animation helpers.
- `test_env.py` — invariant assertions and a spec-completeness rollout.

Design: an immutable `@dataclass` state plus pure functions (`step(state, action) -> (state, reward)`).
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

EnvConfig:               # env dynamics
    LAYER_LEN, NUM_LAYERS, MIN_PIECE_LEN, MAX_PIECE_LEN,
    MIN_BOARD_LEN_SUM, MAX_BOARD_LEN,
    INI_BOARDS, INI_PIECES, OBSERVABLE_BOARDS, seed

VizConfig:               # rendering only
    NUM_COLORS, palette (NUM_COLORS colors)

GlulamState:
    queue:           list[list[Piece]]  # boards, left->right; each board = pieces left->right
                                        # saw piece = queue[-1][-1]
    out_piece:       Piece | None
    buf_piece:       Piece | None
    current_layer:   int                # 0 .. NUM_LAYERS-1
    beam:            list[list[Piece]]  # NUM_LAYERS lists; assembled pieces per layer
    finished_beams:  int
    discarded_total: int
    last_reward:     float
    terminated:      bool
```

Derived (computed on demand, not stored):

- `saw_piece_len      = queue[-1][-1].length if queue else 0`
- `current_layer_len  = sum(p.length for p in beam[current_layer])`
- `current_layer_left = LAYER_LEN - current_layer_len`
- `observable_pieces  = [p.length for p in flatten(queue[-OBSERVABLE_BOARDS:])]`  (left->right; all remaining if fewer boards)

Board grouping (the list-of-lists) and every piece's `piece_id` / `board_id` are stored but excluded
from the observation, matching the spec's "not observable" clause. `piece_id` is an origin/lineage id,
not unique across live fragments (both parts of a cut share it). Consuming the saw piece pops from
`queue[-1]`; an emptied board is dropped; the observation window is a plain suffix slice.

`step` never mutates: it rebuilds exactly the containers it touches (e.g. `queue[-1]` becomes a new
list, `beam[current_layer]` becomes a new list on assemble) and shares untouched sub-structures
(copy-on-write); the state itself is replaced via `dataclasses.replace` or reconstruction, never
edited in place.

## C. Instance generation (`reset`)

Generate `INI_BOARDS` boards, each of length in `[MIN_BOARD_LEN_SUM, MAX_BOARD_LEN]`, split into
integer pieces each in `[MIN_PIECE_LEN, MAX_PIECE_LEN]` and summing to the board length; `INI_PIECES`
pieces in total. Enumerate the initial pieces `0 .. INI_PIECES-1` as their `piece_id`, starting at the
saw end: the rightmost piece gets id 0, ids increase to the left. Assign each board its `board_id` the
same way (rightmost board = 0 at reset, decreasing left->right as in the spec), carried by all of its
pieces. Ids are fixed at reset; cutting never changes the id of any piece or board.

At the top of `reset`, assert joint config feasibility and raise `ValueError` naming the violated
condition (instead of risking an infinite generation loop or an invalid instance). At minimum:

- `INI_PIECES >= INI_BOARDS`;
- `MIN_PIECE_LEN <= MIN_BOARD_LEN_SUM <= MAX_BOARD_LEN` and `MAX_PIECE_LEN <= MAX_BOARD_LEN`
  (re-assert the spec constraints);
- a piece-count partition of `INI_PIECES` across the boards exists such that every board `b` with
  `n_b` pieces has `n_b * MIN_PIECE_LEN <= MAX_BOARD_LEN` and a non-empty per-board length interval:
  `max(MIN_BOARD_LEN_SUM, n_b * MIN_PIECE_LEN) <= min(MAX_BOARD_LEN, n_b * MAX_PIECE_LEN)`.

Note: the spec constrains but does not fully fix the generation distribution (board-length sampling,
how `INI_PIECES` is partitioned across boards). Implement it as a config-driven helper
(reserve-minimum-then-distribute-remainder) and treat the exact distribution as a knob, not a spec
requirement.

## D. Core functions

### `observe(state)`
Returns `(observable_pieces, current_layer, current_layer_len, current_layer_left,
out_piece_len, buf_piece_len, saw_piece_len)`. Variable-length list, no padding.

### `legal_actions(state)`
Boolean mask of length `MAX_PIECE_LEN + 6`, fixed order:
`cut_1 .. cut_N`, `cut_layer_finish`, `put_buf`, `assemble_out`, `assemble_buf`, `discard_out`,
`discard_buf`. Conditions transcribed verbatim from the spec's Legal-actions table. In particular,
`assemble_out` is legal iff `out` is occupied and (`out_piece_len == current_layer_left` or
`out_piece_len <= current_layer_left - MIN_PIECE_LEN`); likewise for `assemble_buf`. This never leaves
a layer gap in the open interval `(0, MIN_PIECE_LEN)`.

### `step(state, action) -> (next_state, reward)`  (pure)

- **`cut_k` / `cut_layer_finish`** (`k = current_layer_left` for the latter): the saw piece `s`
  (`= queue[-1][-1]`) is split. A new piece of length `k` goes to `out_pos`, inheriting `s.piece_id`
  and `s.board_id`; the left remainder `rem = s.length - k` stays at the saw and also keeps
  `s.piece_id` / `s.board_id`.
  - `rem == 0`      -> pop the saw piece (exact, no waste).
  - `0 < rem < MIN` -> pop it, `wasted = rem`.
  - `rem >= MIN`    -> replace the saw piece with a **new** `Piece(length=rem, ...same ids...)`;
    `queue[-1]` becomes a new list containing it (no in-place mutation).
  Drop an emptied board. `reward = -wasted`.
- **`put_buf`**: `buf = out; out = None`. reward 0.
- **`assemble_out` / `assemble_buf`**: `beam[current_layer]` becomes a new list with the `Piece`
  appended; clear the position. If the layer sum reaches `LAYER_LEN`: if it was the last layer ->
  `finished_beams += 1`, reset `beam` to `NUM_LAYERS` empty layers, `current_layer = 0`; else
  `current_layer += 1`. reward 0.
- **`discard_out` / `discard_buf`**: `wasted = piece.length`; clear the position; `reward = -wasted`.

Then update `discarded_total`, `last_reward`, and recompute
`terminated = (not queue) and out_piece is None and buf_piece is None`.

### Reward
`reward = -wasted_len`, exactly the spec's table. Stranded beam pieces at termination yield nothing.

## E. Random policy (`policy.py`)

`choice(indices where legal_actions(state) is True)` — respects the mask. Note `cut_layer_finish`
overlaps a specific `cut_k`, so both can be legal simultaneously and it is slightly double-weighted in
the action distribution; harmless for a random baseline (document with a comment).

## F. Invariants / spec-completeness test (`test_env.py`)

Assert every step (these are executable spec clauses):

- `0 <= current_layer_len <= LAYER_LEN`; a completed layer sums to exactly `LAYER_LEN`.
- `current_layer_left` is never in the open interval `(0, MIN_PIECE_LEN)` (guaranteed by the tightened
  assemble condition) — so no layer can become unfillable.
- Every saw piece is always `>= MIN_PIECE_LEN` (entry guarantee + remainder-removal rule).
- No deadlock: `terminated or legal_actions(state).any()`. (When `out` is empty and the queue is
  non-empty, `cut_(MIN_PIECE_LEN)` is legal; a discard is always legal when a position is occupied.)
- Length conservation:
  `input_total == locked_in_finished + discarded_total + stranded_beam + in_flight(out, buf, queue)`
  at every step, where `locked_in_finished = finished_beams * NUM_LAYERS * LAYER_LEN`.
- Per-lineage conservation: for each origin `piece_id`, the summed lengths of all live fragments plus
  its fragments discarded so far never exceed the origin piece's initial length.
- No mutation: after a full rollout, `states[0]` is unchanged (e.g. its total queue length still
  equals `input_total`) — directly detects accidental in-place mutation of shared sub-structures.

If any branch cannot be written without inventing a rule the spec does not state, that pinpoints a
spec gap.

## G. Step visualization (`visualization.py`)

`render(ax, state)` draws into a passed Axes, following the existing
[mcts/bin_packing/visualization.py](mcts/bin_packing/visualization.py) style. Every segment's color is
`palette[piece.piece_id % NUM_COLORS]` (the env stores no color; it is derived here), and every
segment gets a black outline so neighboring pieces stay separable even when they share a color. Four
regions, left to right, per the spec's Episode-visualization section:

1. **Hidden-pieces stack (left):** one horizontal **row** per hidden board; each row is a run of
   flush, colored segments (one per piece, width proportional to length). Bottom-to-top =
   rightmost-to-leftmost hidden board; pieces keep left->right order within a row; rows separated
   vertically by >= one **segment height**.
2. **Observable pieces:** a **single horizontal row** of segments, same segment height / length
   convention. Board boundaries are **not** drawn here — it is a plain flat list, so which pieces
   shared an original board is not visible; consecutive segments get a horizontal gap of
   >= 3x segment height.
3. **`out` / `buf` pieces:** `out` at the same height as the observable row; `buf` above it, separated
   vertically by >= 3x segment height; an empty position draws nothing.
4. **Beam (right):** layered Lego-brick style, no horizontal or vertical gaps, `current_layer`
   partially filled, same colors and sizes.

Because `piece_id` is inherited across cuts, all fragments of an original piece share a color; the
black outlines keep them separable. Scalar state (`current_layer`, `current_layer_left`, `last_reward`,
`finished_beams`, `discarded_total`) goes in the title.

**Fixed layout:** compute the axes limits once from the initial state and config — max hidden-board
length, worst-case observable-row width (incl. the 3x-segment-height gaps), fixed x-anchors for the
saw-side / `out_pos` / `buf_pos` slots, and `LAYER_LEN` x `NUM_LAYERS` for the beam — and apply the
same `xlim`/`ylim` to every frame, so the animation does not rescale as the queue drains. Right-align
the observable row at the saw side; `out_pos` and `buf_pos` keep fixed anchor positions even when
empty (an empty slot still draws nothing, per spec, but its location is stable).

**Frames / animation:** because `step` is pure, a rollout yields `states = [s0, s1, ...]`; frame `t` is
`render(ax, states[t])`. Emit one PNG per step (filmstrip / grid) or stitch a GIF
(`imageio` or `matplotlib.animation.FuncAnimation`).

## H. Build order

1. `env.py`: config, state, `reset`, `observe`, `legal_actions`, `step`.
2. `policy.py`: random policy.
3. `test_env.py`: invariants + a random rollout to termination (spec-completeness check).
4. `visualization.py`: `render` + frame/animation helpers.
