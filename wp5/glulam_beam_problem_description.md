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
After the last layer of a beam has been finished, the beam disappears and is replaced by an empty beam to assemble.

Ok, here is some background info about the pieces in the queue.
This is background information leading to observable and hidden variables in the RL environment we will define later.
The contents of the queue are fixed in advance and are not influenced by the policy.

The pieces in the queue are grouped by the original board they were cut from.
The pieces of one board form a contiguous run in the queue, and their lengths sum to that board's length, which lies in the interval from `MIN_BOARD_LEN_SUM` to `MAX_BOARD_LEN`.
Every piece in the queue is guaranteed to have a length of at least `MIN_PIECE_LEN` on entry.
This board grouping is not something the policy acts on; it only affects what is observable.

Initially, the queue holds all pieces of `INI_BOARDS` original boards.
The observation window is anchored at the right end of the queue (the saw side) and always covers exactly the pieces of the rightmost `OBSERVABLE_BOARDS` unique boards; all pieces further to the left are hidden.
If fewer than `OBSERVABLE_BOARDS` boards remain in the queue, all remaining pieces are observable.
The policy observes these pieces only as a variable-length list of their lengths; the board boundaries within the window (which pieces share an original board) are not observable.
The window respects board boundaries: for every board, either all of its pieces are observable or none are (all-or-nothing).
As the pieces of the rightmost board are consumed at the saw — each piece is cut or discarded when its length is < `MIN_PIECE_LEN` — and that board is fully used up, the next board (i.e. group of pieces) to the left becomes observable.

The environment tracks which pieces belong to which original board:
- Either by **assigning an original board id to each piece in the queue**: These ids are monotonically decreasing from left to right, e.g. when there are 9 pieces in the queue the original board ids at a given time could be (18, 18, 18, 17, 17, 17, 17, 16, 16).
- Or by **tracking a list of lists of wood pieces**: e.g. piece ids are ((91, 90, 89), (88, 87, 86, 85), (84, 83))

This assignment of pieces to original boards is not observable to the policy.

The episode terminates when no pieces remain, i.e. the queue, `out_pos` and `buf_pos` are all empty.
At that point the current beam is usually still unfinished; its already-assembled pieces count as neither finished-beam output nor discarded waste.

### Objective

We want the policy to make good use of the wood. Two natural objectives are:
- **Minimize the total discarded length** (wood lost as waste).
- **Maximize the number of finished beams.**

For a fixed set of input boards the two are linked by a conservation identity: the total input length equals the length locked into finished beams, plus the discarded length, plus the length stranded in the unfinished beam at termination.
They are not equivalent, however, and differ in reward granularity and in how they treat that stranded remainder:
- The discarded length gives a step-level (intermediate) reward, since some length is typically lost at many cutting steps.
- The number of finished beams only increments when a beam is completed.

Besides the sub-`MIN_PIECE_LEN` remainder lost at the saw, pieces that fit no layer can also be discarded (details later).
We will experiment with different reward formulations in our environment definition later.

## Informal definition of the RL environment

### Constants

We already introduced all constants of the environment.

| Constant            | Description                                                                                                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LAYER_LEN`         | The exact total length that all wood pieces in a layer must sum to.                                                                                                               |
| `NUM_LAYERS`        | The number of layers of each finished glulam beam.                                                                                                                                |
| `MIN_PIECE_LEN`     | The minimum length a wood piece leaving the saw is allowed to have.                                                                                                               |
| `MAX_PIECE_LEN`     | The maximum length a single wood piece may have (a queue piece, and the longest piece a cut may produce; the upper bound `N` of the `cut_k` action range).                        |
| `MIN_BOARD_LEN_SUM` | The minimum length of an original board, i.e. the minimum sum of lengths of the pieces cut from one board. Constraint: `MIN_PIECE_LEN` <= `MIN_BOARD_LEN_SUM` <= `MAX_BOARD_LEN`. |
| `MAX_BOARD_LEN`     | The maximum length of an original board, i.e. the maximum sum of lengths of the pieces cut from one board. Constraint: `MAX_PIECE_LEN` <= `MAX_BOARD_LEN`.                        |
| `INI_BOARDS`        | The total number of original boards processed in one episode.                                                                                                                     |
| `INI_PIECES`        | The total number of wood pieces initially in the queue (across all `INI_BOARDS` boards).                                                                                          |
| `OBSERVABLE_BOARDS` | The number of rightmost unique boards whose pieces are observable in the queue.                                                                                                   |

### Observable variables

| Variable             | Description                                                                                                                               |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `current_layer`      | Layer id from 0 ... `NUM_LAYERS` - 1                                                                                                      |
| `current_layer_len`  | The sum of lengths of the wood pieces in the current unfinished layer.                                                                    |
| `current_layer_left` | The gap at the end of the current layer, i.e. `LAYER_LEN` - `current_layer_len`.                                                          |
| `observable_pieces`  | The list of lengths of the pieces in the observation window (the rightmost `OBSERVABLE_BOARDS` boards), ordered from left to right.       |
| `out_piece_len`      | The length of the piece currently at `out_pos` (0 if `out_pos` is empty).                                                                 |
| `buf_piece_len`      | The length of the piece currently at `buf_pos` (0 if `buf_pos` is empty).                                                                 |
| `saw_piece_len`      | The length of the piece currently at the saw position, i.e. the rightmost (last) element of `observable_pieces`; 0 if the queue is empty. |

Note that when a layer is finished it was full (its pieces summed to exactly `LAYER_LEN`); the environment then immediately advances to a fresh, empty layer, so `current_layer_len` = 0 and `current_layer_left` = `LAYER_LEN`. The two cases differ only in `current_layer`:
- Either the finished layer was not the last one, so `current_layer` has been incremented and is now in `1 ... NUM_LAYERS - 1`,
- or the finished layer was the last one, so the beam has been finished and replaced by an empty beam, and `current_layer` = 0.

### Hidden variables

| Variable        | Description                                                                                                                                   |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `board_id`      | For each wood piece in the queue, the id of the original board it was cut from.<br>These ids are monotonically decreasing from left to right. |
| `hidden_pieces` | The list of lengths of all queue pieces to the left of the observation window.                                                                |

### Action space

| Action                                     | Description                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cut_1` ... `cut_N`, `N` = `MAX_PIECE_LEN` | Cut so that a piece of the chosen length `1 ... N` leaves the saw into `out_pos`.                                                                                                                                                                                                              |
| `cut_layer_finish`                         | It equals `cut_k` for `k` = `current_layer_left`, i.e. it cuts a piece that fits precisely into the gap at the end of the layer. This special action collapses with precisely one of the other cuts and is just a helper for the neural network to accurately cut the piece of the last layer. |
| `put_buf`                                  | Move the piece from `out_pos` to `buf_pos`.                                                                                                                                                                                                                                                    |
| `assemble_out`                             | Assemble the current piece at `out_pos` into the current glulam beam.                                                                                                                                                                                                                          |
| `assemble_buf`                             | Assemble the current piece at `buf_pos` into the current glulam beam.                                                                                                                                                                                                                          |
| `discard_out`                              | Discard the piece at `out_pos`.                                                                                                                                                                                                                                                                |
| `discard_buf`                              | Discard the piece at `buf_pos`.                                                                                                                                                                                                                                                                |

### Legal actions

An action is legal if and only if the listed conditions all hold.

| Action                               | Legal if and only if                                                                                                                  |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `cut_k` (any of `cut_1` ... `cut_N`) | The queue is non-empty, `out_pos` is empty, and `MIN_PIECE_LEN` <= `k` <= `saw_piece_len`.                                            |
| `cut_layer_finish`                   | The queue is non-empty, `out_pos` is empty, and `MIN_PIECE_LEN` <= `current_layer_left` <= `saw_piece_len`.                           |
| `put_buf`                            | `out_pos` is occupied and `buf_pos` is empty.                                                                                         |
| `assemble_out`                       | `out_pos` is occupied and either `out_piece_len` = `current_layer_left` or `out_piece_len` <= `current_layer_left` - `MIN_PIECE_LEN`. |
| `assemble_buf`                       | `buf_pos` is occupied and either `buf_piece_len` = `current_layer_left` or `buf_piece_len` <= `current_layer_left` - `MIN_PIECE_LEN`. |
| `discard_out`                        | `out_pos` is occupied.                                                                                                                |
| `discard_buf`                        | `buf_pos` is occupied.                                                                                                                |

The `assemble_out` / `assemble_buf` conditions ensure a piece is assembled only if it either fills the layer exactly (`current_layer_left` reaches 0) or leaves a remaining gap of at least `MIN_PIECE_LEN`. This forbids leaving a gap smaller than `MIN_PIECE_LEN`, which no future piece could ever fill (every piece leaving the saw is at least `MIN_PIECE_LEN`).

Note that the actions `cut_1` ... `cut_(MIN_PIECE_LEN - 1)` are permanently illegal, since a piece leaving the saw must be at least `MIN_PIECE_LEN` long. They exist anyway so that the cut action index directly equals the cut length.

### Reward

We use the wasted (discarded) length as the reward signal, since it is an intermediate, step-level signal: some length is typically lost throughout the episode rather than only at the end.

The reward at each step is the negative of the length wasted by the chosen action:

`reward` = - `wasted_len`

where `wasted_len` is the length that leaves the process as waste in that step:

| Action                       | `wasted_len`                                                                                                                                        |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cut_k` / `cut_layer_finish` | The left remainder at the saw if it drops below `MIN_PIECE_LEN`, i.e. `saw_piece_len` - `k` if 0 < `saw_piece_len` - `k` < `MIN_PIECE_LEN`, else 0. |
| `discard_out`                | `out_piece_len`                                                                                                                                     |
| `discard_buf`                | `buf_piece_len`                                                                                                                                     |
| all other actions            | 0                                                                                                                                                   |

The length stranded in the still-unfinished beam at termination counts as neither finished-beam output nor waste, so it yields no reward.

### Termination

The episode terminates when no wood remains to process, i.e. the queue, `out_pos` and `buf_pos` are all empty.
At that point the current beam is usually still unfinished; its already-assembled pieces count as neither finished-beam output nor waste, and thus yield no terminal reward.

## Episode visualization

An episode frame is drawn as four regions arranged left to right:

1. the hidden-pieces stack,
2. the observable pieces,
3. the `out_pos` and `buf_pos` pieces,
4. the currently assembled beam.

The hidden wood pieces (all queue pieces to the left of the observation window) are drawn as a vertical stack of horizontal rows on the left:
- Each row represents one original board: a run of colored segments arranged from left to right, one segment per piece, each segment's length proportional to its piece length. Each segment is drawn with a black outline, so a board reads as a row of distinct bricks rather than a single rectangle.
- The queue's left-to-right order maps to the stack's bottom-to-top order: the rightmost board (group of pieces) of the hidden queue is the top row, the next board is the row below it, and so on down to the leftmost board at the bottom.
- Within each row, the pieces keep their left-to-right queue order.

Within a row, the segments are drawn flush against each other (no horizontal gap), while consecutive rows are separated vertically by at least one segment height.

The observable pieces are shown to the right of the stack as a single horizontal row of segments, using the same segment coloring, segment height, and length-proportional-to-piece-length convention as the stack. Unlike the stack, board boundaries are not drawn here: the observable pieces appear as a plain flat list of segments in one row, so it is no longer visible which pieces belonged to the same original board. Consecutive segments in this row are separated by a horizontal gap of at least three times the segment height, so the individual pieces read as a list.

The `out_pos` and `buf_pos` pieces are shown to the right of the observable pieces, using the same segment coloring, segment height, and length-proportional-to-piece-length convention:
- The `out_pos` piece is drawn at the same height as the observable pieces.
- The `buf_pos` piece is drawn above the `out_pos` piece, separated vertically by at least three times the segment height.
- A position that is empty draws nothing.

The assembled, layered glulam beam is drawn on the right with the same segment colors and sizes, but with no horizontal or vertical gaps between segments (like _Lego bricks_).

Each wood piece carries two provenance ids that the environment tracks but does not reveal to the policy: an origin `piece_id` and an origin `board_id`. At reset the queue pieces are enumerated `0, ..., INI_PIECES - 1` as their `piece_id`, starting at the saw end: the rightmost piece gets id 0 and ids increase to the left, so they are monotonically decreasing from left to right (as in the example above). Each piece takes the id of its original board as its `board_id`, enumerated the same way: the rightmost board has id 0 at reset. When the saw cuts a piece, both resulting parts — the piece leaving into `out_pos` and the left remainder that stays at the saw — inherit the `piece_id` and `board_id` of the piece they came from; no action ever changes the id of a piece or board. So `piece_id` is an origin/lineage id, not unique across the pieces present at a given time: all fragments descending from the same original piece share it.

A segment's color is its `piece_id` modulo `NUM_COLORS`, mapped into a fixed color list of `NUM_COLORS` entries (`NUM_COLORS` is a visualization-only constant, which is why it does not appear in the environment constants table). Because `piece_id` is inherited across cuts, all fragments of an original piece share one color; the black outline around every segment (see above) keeps neighboring pieces visually separable even when they share a color.
