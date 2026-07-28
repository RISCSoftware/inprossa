# Glulam Beam Assembly Problem (Leimbinder)

## Abstract, informal problem definition

Assume the following 1D cutting and packing problem.

Wood pieces in a queue move from left to right, leave the queue, are cut by a saw and then assembled into a glulam beam or discarded.
This section defines an abstract version of it.

Lengths of all wood pieces are integers referring to one unit of length, e.g. 1 unit = 20 cm.
Real units like cm are completely abstracted away, we only account for integer units of length.

There is a queue of wood pieces before a saw; physically, picture a conveyor carrying the pieces from left to right towards the saw.
The position at the end of the queue (that will leave next) is called the _saw position_.
The saw can cut the wood piece at its position into two wood pieces.
Their lengths sum up to the original length of the cut piece.
The left of the two cut parts remains the piece at the saw.
The right part leaves the saw at the right.
The saw can cut the same part more than once, each cut making it shorter, while the respective right part leaves the saw.
The part leaving the saw must have a length at least `MIN_PIECE_LEN`.
If the remaining left part reaches a length less than `MIN_PIECE_LEN`, it is immediately removed and the next wood piece in the queue takes its position.

After the saw, there are two positions, each of which can hold one cut wood piece:
- `out_pos`: holds the piece that has just been cut
- `buf_pos`: a buffer position that holds a piece cut earlier to _save_ it.

The saw can only ever perform a cut if the subsequent `out_pos` is empty.

Pieces from `out_pos` and `buf_pos` (and no other position) can be assembled into the beam.
The partially assembled beam sits to the right of these two positions.
The beam is assembled layer by layer, and within a layer from left to right.
The layers are stacked vertically on top of each other, so every layer spans the full horizontal length of the beam (i.e. the layer length equals the beam length).
So there is no choice _where_ to put a wood piece in the beam.
An assembly action can either assemble the piece at `out_pos` or the piece at `buf_pos`, given the respective position is occupied.

In each finished beam, all wood pieces in a layer must precisely sum to `LAYER_LEN`.
This means the last wood piece must precisely fill the gap at the end of the current layer.
After the last layer of a beam has been finished, the beam is complete and a new empty beam takes its place; the finished beam is retained internally (see hidden variables).

Here is some background info about the pieces in the queue.
This is background information leading to the observable and hidden variables defined below.
The contents of the queue are fixed in advance and are not influenced by any policy.

The pieces in the queue are grouped by the original board they were cut from.
The pieces of one board form a contiguous run in the queue, and their lengths sum to that board's length, which lies in the interval from `MIN_BOARD_LEN` to `MAX_BOARD_LEN`.
Every piece in the queue is guaranteed to have a length of at least `MIN_PIECE_LEN` on entry.
This board grouping is not something the policy acts on; it only affects what is observable.

Initially, the queue holds all pieces of `INI_BOARDS` original boards.
The observation window is anchored at the right end of the queue (the saw side) and covers the pieces of the rightmost `OBSERVABLE_BOARDS` unique boards; all pieces further to the left are hidden.
If fewer than `OBSERVABLE_BOARDS` boards remain in the queue, all remaining pieces are observable.
The policy observes these pieces only as a variable-length list of their lengths; the board boundaries within the window (which pieces share an original board) are not observable.
The window respects board boundaries: for every board, either all of its pieces are observable or none are (all-or-nothing).
As the pieces of the rightmost board are consumed at the saw — each piece is cut or discarded when its length is < `MIN_PIECE_LEN` — and that board is fully used up, it leaves the window and the next board (i.e. group of pieces) to the left becomes observable; the window is re-evaluated after every board drop.

The environment tracks which pieces belong to which original board:
- Either by **assigning an original board id to each piece in the queue**: These ids are monotonically decreasing from left to right, e.g. mid-episode, when there are 9 pieces in the queue, the original board ids could be (18, 18, 18, 17, 17, 17, 17, 16, 16).
- Or by **tracking a list of lists of wood pieces**: e.g. mid-episode, piece ids could be ((91, 90, 89), (88, 87, 86, 85), (84, 83))

This assignment of pieces to original boards is not observable to the policy.

The episode terminates when no pieces remain (see Termination below).

### Objective

We want the policy to make good use of the wood. Two natural objectives are:
- **Minimize the total discarded length** (wood lost as waste).
- **Maximize the number of finished beams.**

For a fixed set of input boards the two are linked by a conservation identity: the total input length equals the length locked into finished beams, plus the discarded length, plus the length stranded in the unfinished beam at termination.
They are not equivalent, however, and differ in reward granularity and in how they treat that stranded remainder:
- The discarded length gives a step-level (intermediate) reward, since some length is typically lost at many cutting steps.
- The number of finished beams only increments when a beam is completed.

Besides the sub-`MIN_PIECE_LEN` remainder lost at the saw, pieces that cannot be assembled (e.g. because they violate forbidden-interval constraints) can also be discarded; discarding is always legal when a position is occupied. An entire beam can also be discarded (`discard_beam`), which wastes all assembled pieces in all layers of that beam at once.

## Informal definition of the RL environment

### Constants

The table below defines all environment constants. Meeting positions are the strictly interior prefix sums of piece lengths in a layer (`0 < p < LAYER_LEN`); the beam ends (0 and `LAYER_LEN`) are not meeting positions.

| Constant                   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LAYER_LEN`                | The exact total length that all wood pieces in a layer must sum to.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `NUM_LAYERS`               | The number of layers of each finished glulam beam.                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `MIN_PIECE_LEN`            | The minimum length a wood piece leaving the saw is allowed to have.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `MAX_PIECE_LEN`            | The maximum length a single wood piece may have (a queue piece, and the longest piece a cut may produce; the upper bound `N` of the `cut_k` action range).                                                                                                                                                                                                                                                                                                                                           |
| `MIN_BOARD_LEN`            | The minimum length of an original board, i.e. the minimum sum of lengths of the pieces cut from one board. Constraint: `MIN_PIECE_LEN` <= `MIN_BOARD_LEN` <= `MAX_BOARD_LEN`.                                                                                                                                                                                                                                                                                                                        |
| `MAX_BOARD_LEN`            | The maximum length of an original board, i.e. the maximum sum of lengths of the pieces cut from one board. Constraint: `MAX_PIECE_LEN` <= `MAX_BOARD_LEN`.                                                                                                                                                                                                                                                                                                                                           |
| `INI_BOARDS`               | The total number of original boards processed in one episode. Constraint: `OBSERVABLE_BOARDS <= INI_BOARDS`.                                                                                                                                                                                                                                                                                                                                                                                         |
| `INI_PIECES`               | The total number of wood pieces initially in the queue (across all `INI_BOARDS` boards).                                                                                                                                                                                                                                                                                                                                                                                                             |
| `OBSERVABLE_BOARDS`        | The number of rightmost unique boards whose pieces are observable in the queue.                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `FORBIDDEN_INTERVALS`      | List of (start, end) absolute integer intervals in the beam where no two pieces in any layer may meet. Constraint: every entry satisfies `0 <= start < end <= LAYER_LEN`. Entries may overlap (the constraint is effectively a union). For example, three intervals of a fixed small width (a few length units, not a percentage of `LAYER_LEN`, so that a longer layer is not also a more constrained one), centered at 0.2·`LAYER_LEN`, 0.5·`LAYER_LEN`, and 0.8·`LAYER_LEN`, rounded to integers. |
| `PREV_MEET_FORBIDDEN_HALF` | Half-width of the forbidden interval around each meeting position of the previous layer. Constraint: `PREV_MEET_FORBIDDEN_HALF >= 0`. For each meeting position `p` in the previous layer, the interval `(p - PREV_MEET_FORBIDDEN_HALF, p + PREV_MEET_FORBIDDEN_HALF)` is forbidden in the current layer. Setting `PREV_MEET_FORBIDDEN_HALF = 0` makes the interval empty and effectively disables constraint 3.                                                                                     |

Additional constraints: `MIN_PIECE_LEN >= 1`; `MIN_PIECE_LEN <= MAX_PIECE_LEN`; `MIN_PIECE_LEN <= LAYER_LEN`; `NUM_LAYERS >= 1`; `OBSERVABLE_BOARDS >= 1`. If `MAX_PIECE_LEN > LAYER_LEN`, cuts producing pieces longer than `LAYER_LEN` can never be assembled and are effectively wasted. Additionally, the config must pass a base-case feasibility check (`reachable(0)`, defined in assemble constraint 4 below, using only the global forbidden intervals since layer 0 has no previous layer) to ensure the first layer of a beam can always be finished.

### Observable variables

| Variable                 | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `current_layer`          | Layer id from 0 ... `NUM_LAYERS` - 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `current_layer_len`      | The sum of lengths of the wood pieces in the current unfinished layer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `current_layer_left`     | The gap at the end of the current layer, i.e. `LAYER_LEN` - `current_layer_len`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `observable_pieces`      | The list of lengths of the pieces in the observation window (the rightmost `OBSERVABLE_BOARDS` boards), ordered from left to right. Upper bound on length: `MAX_OBSERVABLE_PIECES = OBSERVABLE_BOARDS * (MAX_BOARD_LEN // MIN_PIECE_LEN)`. Padding/encoding is out of scope for this specification.                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `out_piece_len`          | The length of the piece currently at `out_pos` (0 if `out_pos` is empty).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `buf_piece_len`          | The length of the piece currently at `buf_pos` (0 if `buf_pos` is empty).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `saw_piece_len`          | The length of the piece currently at the saw position, i.e. the rightmost (last) element of `observable_pieces`; equivalently `queue[-1][-1].length`; 0 if the queue is empty.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `prev_meet_positions`    | The set of meeting positions (strictly interior prefix sums) in the immediately preceding layer. Empty if `current_layer == 0`. Upper bound on size: `ceil(LAYER_LEN / MIN_PIECE_LEN) - 1`; for a neural policy, a fixed-length indicator vector of length `LAYER_LEN` is a natural encoding. This gives the policy enough information to reason about constraint 3 without seeing the full beam.                                                                                                                                                                                                                                                                                                                                                           |
| `current_meet_positions` | The set of meeting positions (strictly interior prefix sums) in the current layer so far. Same bound and encoding as `prev_meet_positions`. This gives the policy enough information to anticipate constraint 4's next-layer check without seeing the full beam.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `assemble_legal_mask`    | A boolean list of length `N` (`N` = `MAX_PIECE_LEN`) where entry `k-1` is `True` if a piece of length `k`, placed at the current position in the current layer, would satisfy all assemble constraints (layer-gap, global forbidden intervals, previous-layer forbidden intervals, and finishability). This tells the policy which cut lengths produce an assembleable piece; it does not constrain cuts and effectively proxies "assemblable from `out_pos` immediately after the cut". The mask is fully derivable from the other observables plus the constants (no hidden information), and is provided as a convenience. Entries for `k < MIN_PIECE_LEN` are forced `False` (no such piece can exist); entries for `k > LAYER_LEN` are always `False`. |

Note: the meeting-position observables (`prev_meet_positions` and `current_meet_positions`) are set-level projections of the hidden `beam` state, not a leak of piece-level hidden information.

Note that when a layer is finished it was full (its pieces summed to exactly `LAYER_LEN`); the environment then immediately advances to a fresh, empty layer, so `current_layer_len` = 0 and `current_layer_left` = `LAYER_LEN`. A full layer is thus observable only as a transition, never as a state. The two cases differ only in `current_layer`:
- Either the finished layer was not the last one, so `current_layer` has been incremented and is now in `1 ... NUM_LAYERS - 1`,
- or the finished layer was the last one, so the beam has been finished and replaced by an empty beam, and `current_layer` = 0.

### Hidden variables

| Variable           | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `board_id`         | For each wood piece (in the queue, at `out_pos`/`buf_pos`, in the beam, or in the discarded pile), the id of the original board it was cut from.<br>These ids are monotonically decreasing from left to right.                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `piece_id`         | For each wood piece (in the queue, at `out_pos`/`buf_pos`, in the beam, or in the discarded pile), the origin piece id it descends from. Inherited by both fragments on a cut.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `hidden_pieces`    | The board-grouped structure of all queue pieces to the left of the observation window: a list of boards, each a list of pieces (with their length).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `beam`             | The full assembled beam state: `NUM_LAYERS` lists of pieces, one list per layer. Partially filled layers contain the pieces placed so far.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `finished_beams`   | All fully assembled beams completed so far: a list where each entry is a finished beam's full `NUM_LAYERS` piece layout (same structure as `beam`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `discarded_pieces` | Every piece that has left the process as waste, as a flat list in discard order (oldest first), with its length. Appended to by exactly the actions that produce waste (see the Reward section): the sub-`MIN_PIECE_LEN` left remainder at the saw on a `cut_k`, the piece removed by `discard_out` / `discard_buf`, and — on `discard_beam` — every piece of every layer of the discarded beam, flattened in layer order (layer 0 first) and left to right within each layer. A discarded beam keeps no trace of its beam structure here: its pieces become ordinary discarded pieces. Invariant: the lengths in `discarded_pieces` sum to `discarded_total`. |

### Action space

| Action                                     | Description                                                                                                                                     |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `cut_1` ... `cut_N`, `N` = `MAX_PIECE_LEN` | Cut so that a piece of the chosen length `1 ... N` leaves the saw into `out_pos`.                                                               |
| `put_buf`                                  | Move the piece from `out_pos` to `buf_pos`.                                                                                                     |
| `assemble_out`                             | Assemble the current piece at `out_pos` into the current glulam beam.                                                                           |
| `assemble_buf`                             | Assemble the current piece at `buf_pos` into the current glulam beam.                                                                           |
| `discard_out`                              | Discard the piece at `out_pos`.                                                                                                                 |
| `discard_buf`                              | Discard the piece at `buf_pos`.                                                                                                                 |
| `discard_beam`                             | Discard the entire current beam (all assembled pieces in all layers so far). Reset `current_layer` to 0 and replace the beam with an empty one. |

### Legal actions

An action is legal if and only if the listed conditions all hold, **and** for assemble actions, the assemble constraints in the subsection that follow.

| Action                               | Legal if and only if                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------ |
| `cut_k` (any of `cut_1` ... `cut_N`) | The queue is non-empty, `out_pos` is empty, and `MIN_PIECE_LEN` <= `k` <= `saw_piece_len`. |
| `put_buf`                            | `out_pos` is occupied and `buf_pos` is empty.                                              |
| `assemble_out`                       | `out_pos` is occupied and the assemble constraints (below) are satisfied.                  |
| `assemble_buf`                       | `buf_pos` is occupied and the assemble constraints (below) are satisfied.                  |
| `discard_out`                        | `out_pos` is occupied.                                                                     |
| `discard_buf`                        | `buf_pos` is occupied.                                                                     |
| `discard_beam`                       | The current beam holds at least one assembled piece.                                       |

#### Assemble constraints

The assemble actions `assemble_out` and `assemble_buf` are legal only if **all** of the following hold for the resulting layer fill (the sum of piece lengths in the layer after assembly):

1. **Layer-gap constraint**: the piece either fills the remaining gap exactly (`piece_len == current_layer_left`) or leaves a gap of at least `MIN_PIECE_LEN` (`piece_len <= current_layer_left - MIN_PIECE_LEN`). This forbids leaving a gap smaller than `MIN_PIECE_LEN`, which no future piece could ever fill (every piece leaving the saw is at least `MIN_PIECE_LEN`).
2. **Global forbidden intervals (per layer)**: if the resulting layer fill is not `LAYER_LEN` (i.e. the piece does not exactly fill the layer), then no interval `(start, end)` in `FORBIDDEN_INTERVALS` satisfies `start < resulting_layer_fill < end` (see the constants table for the interval format and example). The exact-fill case is exempt because `LAYER_LEN` is a beam end, not a meeting position.
3. **Forbidden intervals relative to the previous layer**: if `current_layer > 0` and the resulting layer fill is not `LAYER_LEN` (i.e. the piece does not exactly fill the layer), then the resulting layer fill does not fall inside any interval centered at a meeting position of the immediately preceding layer (`current_layer - 1`). For each meeting position `p` in the previous layer, the forbidden interval is `(p - PREV_MEET_FORBIDDEN_HALF, p + PREV_MEET_FORBIDDEN_HALF)` where `PREV_MEET_FORBIDDEN_HALF` is a configurable constant (the half-width). Meetings in earlier layers impose no restrictions. The exact-fill case is exempt because `LAYER_LEN` is a beam end, not a meeting position.
4. **Finishability and next-layer feasibility constraint**: the assemble action is legal only if both of the following hold:
   - **Current layer finishable**: after assembly, it must still be possible to fill the remaining gap using pieces of any length in `[MIN_PIECE_LEN, MAX_PIECE_LEN]` (the geometric reading — the check ignores the actual queue contents and the pieces at `out_pos`/`buf_pos`). Formally, define `reachable(f)` backward from the target:
     - `reachable(LAYER_LEN) = True`
     - `reachable(f) = exists s in [MIN_PIECE_LEN, MAX_PIECE_LEN]` such that:
       - `f + s == LAYER_LEN` (exact fill, always allowed), **or**
       - `f + s <= LAYER_LEN - MIN_PIECE_LEN` and `f + s` passes constraints 2 and 3 and `reachable(f + s)`
     The constraint is `reachable(resulting_layer_fill)`. If the resulting fill is `LAYER_LEN` (exact fill), the layer is done and this is vacuously satisfied.
   - **Next layer finishable (one-layer lookahead)**: the meeting positions created by the current layer (including this assembly) must leave the next layer with a geometric possibility of being finished. Specifically, `reachable(0)` must hold using the current layer's meeting positions as `prev_meet_positions` for constraints 2 and 3 (or no previous-layer constraints for a new beam's layer 0). This is a local check — it ensures only that the next layer can be finished, not that layers beyond that are guaranteed. `discard_beam` serves as a safety valve if a beam nonetheless becomes stuck due to the interaction of constraints across multiple layers.

   Note: constraint 4 is the primary mechanism preventing stranding. `discard_beam` exists as a safety valve for cases where the local one-layer lookahead is insufficient (e.g. configs whose feasibility is imperfect). A finer-grained `discard_layer` action is deliberately not provided; discarding at beam granularity is simpler and sufficient given constraint 4.

   Note: the layer-gap constraint (1) is subsumed by the finishability check — the recursion inside `reachable()` enforces the layer-gap condition at every level (`f + s <= LAYER_LEN - MIN_PIECE_LEN`), so a fill with `0 < LAYER_LEN - f < MIN_PIECE_LEN` can never be reachable. It is kept for readability and as a cheap early rejection.

   Note: within a single layer, a layer could be stranded if a global forbidden interval — or a contiguous run of previous-layer intervals — wider than `MAX_PIECE_LEN - MIN_PIECE_LEN` covers the whole `[fill + MIN_PIECE_LEN, fill + MAX_PIECE_LEN]` window. The current-layer finishability check prevents such placements from being made (described here for rationale only). Cross-layer stranding is not fully prevented — see the safety-valve note above.

These four constraints must hold simultaneously; if any fails, the assemble action is illegal.

Note that the actions `cut_1` ... `cut_(MIN_PIECE_LEN - 1)` are permanently illegal, since a piece leaving the saw must be at least `MIN_PIECE_LEN` long. They exist anyway so that the cut action number directly equals the cut length.

### Reward

We use the wasted (discarded) length as the reward signal, since it is an intermediate, step-level signal: some length is typically lost throughout the episode rather than only at the end.

The reward at each step is the negative of the length wasted by the chosen action:

`reward` = - `wasted_len`

where `wasted_len` is the length that leaves the process as waste in that step:

| Action            | `wasted_len`                                                                                                                                                                           |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cut_k`           | The left remainder at the saw if it drops below `MIN_PIECE_LEN`, i.e. `saw_piece_len` - `k` if 0 < `saw_piece_len` - `k` < `MIN_PIECE_LEN`, else 0.                                    |
| `discard_out`     | `out_piece_len`                                                                                                                                                                        |
| `discard_buf`     | `buf_piece_len`                                                                                                                                                                        |
| `discard_beam`    | The total length of all assembled pieces in the current beam (`sum of all piece lengths in all layers of beam`); always ≥ 1 since the action is legal only when the beam is non-empty. |
| all other actions | 0                                                                                                                                                                                      |

Every row of this table with a non-zero `wasted_len` also appends the piece(s) it wastes to the hidden `discarded_pieces` list (see the Hidden variables table), so `wasted_len > 0` and "a piece was appended to `discarded_pieces`" are the same event. The saw remainder is appended as a piece of length `saw_piece_len - k` inheriting the cut piece's `piece_id` and `board_id`.

The length stranded in the still-unfinished beam at termination counts as neither finished-beam output nor waste, so it yields no reward. This is a deliberately tolerated bias: the reward is purely `-wasted_len` and does not include a terminal penalty for stranded length, so completing a beam is not explicitly rewarded. Near the end of an episode, assembling an otherwise useless piece into a beam that will never be finished scores 0 (better than discarding it at `-len`), but the bias is strictly bounded by one beam's capacity (`< NUM_LAYERS * LAYER_LEN`).

### Bookkeeping variables

The environment also tracks these internal variables, not observable to the policy:

| Variable          | Description                                                                                                                                                                                  |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `discarded_total` | Total discarded length so far. Equals the summed lengths in the hidden `discarded_pieces` list, which is where per-lineage attribution of waste (including `discard_beam` waste) comes from. |
| `last_reward`     | The reward returned by the most recent step.                                                                                                                                                 |
| `terminated`      | Whether the episode has ended (queue, `out_pos`, `buf_pos` all empty).                                                                                                                       |

### Termination

The episode terminates when no wood remains to process, i.e. the queue, `out_pos` and `buf_pos` are all empty.
At that point the current beam is usually still unfinished; its already-assembled pieces count as neither finished-beam output nor waste, and thus yield no terminal reward (see the Reward section for the stranded-remainder bias).

A `max_steps` guard should be configured to prevent unbounded episodes in practice; the theoretical bound is finite (cuts are legal only when `out_pos` is empty, so each cut removes at least `MIN_PIECE_LEN` from the queue and moves it to `out_pos`; each discard removes positive length; each assemble moves wood into the beam where it stays until the beam is finished or discarded), but a practical limit is needed for rollouts.

## Episode visualization

The visualization uses its own constants, separate from the environment constants:

| Constant                 | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NUM_COLORS`             | Number of entries in the color palette. A segment's color is `palette[piece_id % NUM_COLORS]`. Default: `20`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `VIZ_NUM_FINISHED_BEAMS` | How many finished beams to display: `None` = all, `0` = only the current unfinished beam, `n` = current beam plus the `n` most recently finished beams. Default: `None`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `VIZ_SHOW_DISCARDED`     | Whether to draw the discarded-pieces region at all. When false, the region is omitted and no horizontal space is reserved for it, so the frame is exactly the four-region layout. Default: `True`.                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `VIZ_DISCARD_ROW_WIDTH`  | Row width at which the discarded-pieces pile wraps to the next row, in wood-length units. Default: `MAX_BOARD_LEN`, which makes the pile exactly as wide as the widest possible hidden-stack row. It must stay well above `MAX_PIECE_LEN`: as the row width approaches `MAX_PIECE_LEN` the pile degenerates towards one piece per row, and the reserved row count (see the layout note below) grows accordingly.                                                                                                                                                                                                                                           |
| `VIZ_PAD_FACTOR_X`       | Fraction of a region's smaller content dimension used as padding to the left and right of that region's content. This is what separates neighboring regions horizontally, so it is the larger of the two padding factors. Fixed at `0.3`; see the region-spacing note below.                                                                                                                                                                                                                                                                                                                                                                               |
| `VIZ_PAD_FACTOR_Y`       | The same, for the padding below and above a region's content. It only adds headroom inside the frame rather than separating anything, so it is smaller. Fixed at `0.15`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `VIZ_SHOW_FORBIDDEN`     | Whether to overlay forbidden-interval rectangles on the current beam. When `True`, global forbidden intervals (`FORBIDDEN_INTERVALS`) are drawn as translucent rectangles across all nonempty layers of the current beam, and local forbidden intervals (from the previous layer's meeting positions) are drawn as translucent rectangles covering only the previous and current layer. Both use solid left and right border lines (same color, not translucent) and no top or bottom borders. Global and local overlays use distinct colors. The overlay is drawn only on the current (unfinished) beam, not on finished beams below it. Default: `True`. |

An episode frame is drawn as five regions arranged left to right (the terminal state is included as the last frame; at termination the queue, observable stack, `out_pos`, and `buf_pos` all draw nothing, while the beams and the discard pile draw their final contents):

1. the hidden-pieces stack,
2. the observable pieces, except the one at the saw position,
3. the saw, `out_pos` and `buf_pos` pieces,
4. the assembled beams (finished beams and the current unfinished beam),
5. the discarded pieces (optional, see `VIZ_SHOW_DISCARDED`).

Each region consumes the following hidden variables and observable variables:

| Region                      | Variables consumed                                                                                                                                                 |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Hidden-pieces stack         | `hidden_pieces` (board-grouped piece objects with `piece_id`, `board_id`, and length)                                                                              |
| Observable pieces           | Observable piece objects in the window except the piece at the saw (hidden state, not the `observable_pieces` length list); `piece_id` per piece for coloring      |
| Saw / `out_pos` / `buf_pos` | The saw piece (`queue[-1][-1]`) and the `out_piece` / `buf_piece` objects (hidden state, not the scalar lengths); `piece_id` for coloring                          |
| Assembled beams             | `finished_beams`, `beam` (full piece layouts incl. `piece_id` per piece for coloring); `current_layer` to highlight the active layer in the topmost (current) beam |
| Discarded pieces            | `discarded_pieces` (flat list of piece objects in discard order; `piece_id` per piece for coloring)                                                                |

Variable availability:

- **Observable** (available to the policy): `current_layer`, `current_layer_len`, `current_layer_left`, `observable_pieces`, `out_piece_len`, `buf_piece_len`, `saw_piece_len`, `prev_meet_positions`, `current_meet_positions`, `assemble_legal_mask`.
- **Hidden** (not observable): `hidden_pieces`, `piece_id`, `board_id`, `beam`, `finished_beams`, `discarded_pieces`.
- **Bookkeeping** (not observable): `discarded_total`, `last_reward`, `terminated`.

The visualization reads the hidden state and bookkeeping variables to draw each frame. Scalar state (`current_layer`, `current_layer_left`, `last_reward`, `len(finished_beams)`, `discarded_total`) appears in the frame title.

The hidden wood pieces (all queue pieces to the left of the observation window) are drawn as a vertical stack of horizontal rows on the left:
- Each row represents one original board: a run of colored segments arranged from left to right, one segment per piece, each segment's length proportional to its piece length. Each segment is drawn with a black outline, so a board reads as a row of distinct bricks rather than a single rectangle.
- The queue's left-to-right order maps to the stack's bottom-to-top order: the rightmost board (group of pieces) of the hidden queue is the top row, the next board is the row below it, and so on down to the leftmost board at the bottom.
- Within each row, the pieces keep their left-to-right queue order.

Within a row, the segments are drawn flush against each other (no horizontal gap), while consecutive rows are separated vertically by 0.8 times the segment height (so the row pitch is 1.8 times the segment height).

The observable pieces are shown to the right of the stack as a vertical stack of one-segment rows, using the same segment coloring, segment height, row pitch, and length-proportional-to-piece-length convention as the hidden-pieces stack. Unlike that stack, board boundaries are not drawn here: the observable pieces appear as a plain flat list of segments, so it is no longer visible which pieces belonged to the same original board. The queue order runs bottom-up in the same direction as the hidden stack: the piece nearest the saw is the top row and the leftmost (furthest from the saw) piece is the bottom row. The piece at the saw position itself is *not* drawn here — region 3 draws it — so this region shows the observation window minus its rightmost piece. That split is a drawing choice only: the `observable_pieces` observation still includes the piece at the saw. Every segment starts at the region's left edge.

The saw, `out_pos` and `buf_pos` pieces are shown to the right of the observable pieces as three fixed slots, using the same segment coloring, segment height, and length-proportional-to-piece-length convention. Bottom to top the slots are: the piece at the saw position (on the region baseline), the `out_pos` piece, and the `buf_pos` piece — the order in which a piece travels through them.
- Consecutive slots are separated vertically by 3.5 times the segment height, considerably more than the row pitch of the other stacks, because each slot's label is drawn in the gap below it and the gap has to clear a line of text.
- A slot that is empty draws nothing, but its anchor position is fixed and does not move.
- This region carries one label per slot — `saw`, `out`, `buf` — each hanging below the slot it names rather than all three sitting on the common baseline, and each left-aligned with the slot anchor (where its piece starts) so it reads as belonging to that slot. The bottom slot's `saw` label thereby ends up on the same line as the other regions' baseline labels.

The assembled beams are drawn on the right as a vertical stack of finished beams plus the current unfinished beam, with the same segment colors and sizes and no horizontal or vertical gaps between segments within a beam (like _Lego bricks_). The current unfinished beam is drawn at the top; finished beams are stacked below it, newest first (most recently completed just under the current beam, older ones further down). The visualization-only constant `VIZ_NUM_FINISHED_BEAMS` controls how many finished beams are shown:
- `None`: show all finished beams.
- `0`: show only the current unfinished beam.
- `n` (a positive integer): show the current beam plus the `n` most recently finished beams below it.

Each beam is separated vertically by 1.6 times the segment height. The current beam's active layer is highlighted (e.g. via `current_layer`), and the highlight remains visible while that layer is still empty. The beams form a pile resting on the same baseline as the other regions: the oldest *displayed* beam sits on the baseline, newer ones above it, and the current unfinished beam on top, so the pile grows upward as beams are completed. When `VIZ_NUM_FINISHED_BEAMS` is `n`, beams older than the `n` most recent never enter the pile — they simply stop being drawn — so the pile height is bounded by `1 + n` beams and, once that many beams exist, stops growing and instead scrolls: the oldest displayed beam drops off the bottom as a new one is added on top. When `VIZ_NUM_FINISHED_BEAMS` is `None`, the pile is bounded only by how many beams the episode finishes (see the frame-extent note below for what the layout then reserves).

When `VIZ_SHOW_FORBIDDEN` is set, forbidden-interval overlays are drawn on the current (unfinished) beam only — finished beams below it do not carry overlays. The global forbidden intervals (`FORBIDDEN_INTERVALS`) are drawn as translucent rectangles spanning all nonempty layers of the current beam, with solid left and right border lines in the same color (no top or bottom borders). The local forbidden intervals — `(p - PREV_MEET_FORBIDDEN_HALF, p + PREV_MEET_FORBIDDEN_HALF)` for each `p` in `prev_meet_positions` — are drawn in a different color, also translucent with solid left/right borders, covering only the previous layer and the current layer. The rectangles are a visual approximation: the env's constraint 3 uses the *open* interval, so a meeting position exactly on a border line is legal; the border is drawn at the exact interval boundary for visual clarity, and the translucent fill extends across the full closed interval. The overlays are drawn after the beam pieces and outlines so they are visible on top of the wood segments.

The discarded pieces are shown to the right of the beams, using the same segment coloring, segment height, and length-proportional-to-piece-length convention as the hidden-pieces stack. This region is optional: it is drawn only when `VIZ_SHOW_DISCARDED` is set, and when it is not, no horizontal space is reserved for it.
- The pieces of `discarded_pieces` are laid out in discard order (oldest first), left to right within a row.
- A row wraps when the next piece would make the row exceed `VIZ_DISCARD_ROW_WIDTH`; that piece starts a new row instead. Pieces are never split across rows.
- The first row is at the bottom and later rows are stacked above it, so the pile grows upward as waste accumulates — the mirror image of the hidden-pieces stack, which drains downward.
- Within a row the segments are flush against each other; consecutive rows are separated vertically by 0.8 times the segment height, exactly as in the hidden-pieces stack.
- A discarded beam contributes its pieces individually, in the order given by `discarded_pieces` (layer 0 first, left to right within each layer). Discarded beams are never drawn as beams — once discarded, wood is just a pile of pieces.

Region spacing and labels:
- All five regions rest on a common baseline (`y = 0`), and each carries a small text label hanging below that baseline: `hidden`, `queue`, `saw`, `beams`, `discarded pieces` — plus the `out` and `buf` labels described above, which hang below their own slots instead. Baseline labels are centered on their region's content width, not on the drawn contents, so a label does not move as its region fills and drains; region 3's slot labels are left-aligned with the slot anchor instead. Region 2's label is just `queue` rather than `queue → saw`, since the saw end is now named by region 3's bottom slot.
- Each region is a bounding box holding a tight content rectangle plus padding on all four sides. Both paddings scale with the same base — the smaller of the region's two content dimensions, each dimension floored at one segment height so that a one-segment-tall or empty region still gets a gap — but with separate factors: `VIZ_PAD_FACTOR_X` left and right, the smaller `VIZ_PAD_FACTOR_Y` below and above. The horizontal padding is what does the work of separating regions, while the vertical padding only adds headroom, hence the asymmetry. The boxes are laid out left to right so that they tile the x-axis without overlapping — there is no separate region-gap constant. The gap between two regions is thus the sum of their horizontal paddings, and it scales with the size of the regions it separates, so a small region (the slots) sits closer to its neighbors than two large ones do to each other.

Frame extent:
- The segment height is derived from `MAX_PIECE_LEN`, not from `LAYER_LEN`, so a piece keeps its drawn aspect ratio across configs and a longer layer draws a genuinely longer beam. Tying it to `LAYER_LEN` instead would scale the vertical stacks along with the layer, turning a longer layer into a uniformly scaled — and therefore not visibly longer — frame.
- The frame reserves the same `xlim` / `ylim` for every frame of an episode, so the animation does not rescale as the queue drains: region contents grow and shrink inside boxes that never move. Region widths come from the constants (the widest board for the hidden stack, `MAX_PIECE_LEN` for the observable and slot regions, `LAYER_LEN` for the beams, `VIZ_DISCARD_ROW_WIDTH` for the discard pile), and each region's height covers the most it ever holds during the episode: the initial number of hidden boards, the largest observable window (excluding the saw piece), three slots, `1 + min(VIZ_NUM_FINISHED_BEAMS, beams finished)` beams, and the row count of the final discard pile.
- When the episode is not known in advance, the heights can instead be bounded from the constants alone: every beam finished (`INI_BOARDS * MAX_BOARD_LEN / (NUM_LAYERS * LAYER_LEN)`) and the entire input wasted (`1 + total_input_len / (VIZ_DISCARD_ROW_WIDTH - MAX_PIECE_LEN + 1)` discard rows, since greedy packing closes a row only once its fill exceeds `VIZ_DISCARD_ROW_WIDTH - MAX_PIECE_LEN`). These bounds are safe but loose — typically several times the height actually used — so frames drawn with them carry a wide empty band above the piles.

Each wood piece carries two provenance ids that the environment tracks but does not reveal to the policy: an origin `piece_id` and an origin `board_id`. At reset the queue pieces are enumerated `0, ..., INI_PIECES - 1` as their `piece_id`, starting at the saw end: the rightmost piece gets id 0 and ids increase to the left, so they are monotonically decreasing from left to right (as in the example above). Each piece takes the id of its original board as its `board_id`, enumerated the same way: the rightmost board has id 0 at reset. When the saw cuts a piece, both resulting parts — the piece leaving into `out_pos` and the left remainder that stays at the saw — inherit the `piece_id` and `board_id` of the piece they came from; no action ever changes the id of a piece or board. So `piece_id` is an origin/lineage id, not unique across the pieces present at a given time: all fragments descending from the same original piece share it.

A segment's color is its `piece_id` modulo `NUM_COLORS`, mapped into a fixed color list of `NUM_COLORS` entries (see the visualization constants table above). Because `piece_id` is inherited across cuts, all fragments of an original piece share one color; the black outline around every segment (see above) keeps neighboring pieces visually separable even when they share a color.

## Weighted random policy

Rollout metrics (waste, stuck-beam count) are distribution-dependent and not spec clauses; the exact board/piece generation distribution is a config knob (see the plan). "Stuck-beam count" is an umbrella term for two observational counters, both reported at the end of a rollout but neither asserted as an invariant: **`stuck_progress_steps`** counts steps where neither `assemble_out` nor `assemble_buf` was legal (the beam could not make progress), and **`stuck_geometry_steps`** counts steps where `assemble_legal_mask` is all `False` (no cut length is geometrically assembleable at the current layer position). The two diverge whenever a legally assembleable piece sits at `out_pos`/`buf_pos` while no cut length is assembleable, or when the queue is empty short of termination. See the plan (§E, §F) for details. The weighted random policy assigns probability to action groups, then subdivides within each group. Each node in the tree below shows the constant name and an example value; sub-nodes show how the parent's mass is split. All values are configurable. Mass is spread uniformly over the legal actions in each subgroup. If a subgroup has no legal actions, its mass is redistributed by renormalizing the weights of its non-empty sibling subgroups (with only two subgroups this is just "the mass flows to the sibling"). If an entire group has no legal actions, its mass is redistributed the same way, by renormalizing the weights of the remaining non-empty groups. Group weights are normalized to sum to 1.0 before allocation.

```
Total
├── Cut (P_CUT = 0.64)
│   ├── Longest cut where (i) the resulting length would be assemblable next   (P_LONGEST_PREF_CUT = 0.80 of cut mass)
│   ├── Cuts for which (i) holds   (P_REMAINING_PREF_CUTS = 0.15 of cut mass)
│   └── Remaining cuts
├── Put buffer (P_PUT_BUF = 0.05)
├── Assemble (P_ASSEMBLE = 0.30)
│   ├── assemble_out   (P_ASSEMBLE_OUT = 0.80 of assemble mass)
│   └── assemble_buf
├── Discard piece (P_DISCARD_PIECE = 0.009)
│   ├── discard_out    (P_DISCARD_OUT = 0.25 of discard-piece mass)
│   └── discard_buf
└── Discard beam (P_DISCARD_BEAM = 0.001)
```

The three cut subgroups partition the legal cuts: the single longest cut satisfying (i), the *other*
cuts satisfying (i), and the cuts that do not satisfy it. Biasing so heavily towards the longest
assemblable cut keeps the saw from nibbling a long queue piece into many short ones: a longer cut
fills more of the layer per step and leaves a shorter — and thus less useful — remainder at the saw.

### Policy constants

These constants configure the weighted random policy, not the environment. `P_DISCARD_BEAM = 0.001` is a raw weight, not a per-step probability: it would imply ~1000 steps to clear a stuck beam only if every other group stayed legal throughout. In a genuinely stuck state that is not the case — the fallback rule renormalizes over the legal groups, and with no cut and no assemble available `discard_beam` competes only with the discard-piece and put-buffer groups, so beams clear substantially sooner than the raw weight suggests. Treat ~1000 steps as a loose upper bound on the recovery lag rather than an expectation.

| Constant                | Description                                                                                                                                                                                                                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `P_CUT`                 | Total probability mass for cut actions. Example: 0.64.                                                                                                                                                                                                                                                                            |
| `P_LONGEST_PREF_CUT`    | Fraction of the cut mass allocated to the single longest preferred cut, i.e. the largest `k` that is both a legal `cut_k` and flagged `True` in `assemble_legal_mask`. Example: 0.80.                                                                                                                                             |
| `P_REMAINING_PREF_CUTS` | Fraction of the cut mass allocated to the *other* preferred cuts (flagged in `assemble_legal_mask` and legal, excluding the longest one), spread uniformly. Example: 0.15. The remainder, `1 - P_LONGEST_PREF_CUT - P_REMAINING_PREF_CUTS`, goes to the non-preferred legal cuts. Constraint: the two fractions sum to at most 1. |
| `P_ASSEMBLE`            | Total probability mass for assemble actions. Example: 0.30.                                                                                                                                                                                                                                                                       |
| `P_ASSEMBLE_OUT`        | Fraction of the assemble mass allocated to `assemble_out`. Example: 0.80; the remaining `1 - P_ASSEMBLE_OUT` goes to `assemble_buf`.                                                                                                                                                                                              |
| `P_DISCARD_PIECE`       | Total probability mass for discard-piece actions (`discard_out` and `discard_buf`). Example: 0.009.                                                                                                                                                                                                                               |
| `P_DISCARD_OUT`         | Fraction of the discard-piece mass allocated to `discard_out`. Example: 0.25; the remaining `1 - P_DISCARD_OUT` goes to `discard_buf`.                                                                                                                                                                                            |
| `P_DISCARD_BEAM`        | Probability mass for `discard_beam`. Example: 0.001.                                                                                                                                                                                                                                                                              |
| `P_PUT_BUF`             | Probability mass for `put_buf`. Example: 0.05.                                                                                                                                                                                                                                                                                    |
