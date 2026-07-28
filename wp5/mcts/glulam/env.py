"""Glulam beam assembly environment.

Framework-free reference implementation of the authoritative spec in
glulam_beam_problem_description.md. Immutable state + pure functions:
``step(state, cfg, action) -> (next_state, reward)``. A rollout is a plain
list of states.

Action indexing (mask length = MAX_PIECE_LEN + 6, cut index = cut length - 1):
    0 .. N-1 : cut_1 .. cut_N                (N = MAX_PIECE_LEN)
    N        : put_buf
    N + 1    : assemble_out
    N + 2    : assemble_buf
    N + 3    : discard_out
    N + 4    : discard_buf
    N + 5    : discard_beam

Note: cut_1 .. cut_(MIN_PIECE_LEN - 1) are permanently illegal; they exist so
that the cut action number directly equals the cut length.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from itertools import accumulate


@dataclass(frozen=True)
class Piece:
    """A wood piece. ``piece_id`` / ``board_id`` are origin (lineage) ids:
    rightmost = 0 at reset, inherited by both fragments on a cut, never changed."""

    length: int
    piece_id: int
    board_id: int


@dataclass(frozen=True)
class EnvConfig:
    LAYER_LEN: int
    NUM_LAYERS: int
    MIN_PIECE_LEN: int
    MAX_PIECE_LEN: int
    MIN_BOARD_LEN: int
    MAX_BOARD_LEN: int
    INI_BOARDS: int
    INI_PIECES: int
    OBSERVABLE_BOARDS: int
    FORBIDDEN_INTERVALS: tuple[tuple[int, int], ...] = ()
    PREV_MEET_FORBIDDEN_HALF: int = 0
    # Generation knob, not a spec constant: board lengths are drawn uniformly from the top
    # BOARD_LEN_SPREAD units of each board's feasible length interval, so boards come out close
    # to MAX_BOARD_LEN. None draws from the whole interval (uniform over the full range).
    BOARD_LEN_SPREAD: int | None = None
    seed: int = 0


@dataclass(frozen=True)
class GlulamState:
    """Immutable env state. List fields are copy-on-write: ``step`` rebuilds
    exactly the containers it touches and shares untouched sub-structures."""

    queue: list[list[Piece]]  # boards left->right; saw piece = queue[-1][-1]
    out_piece: Piece | None
    buf_piece: Piece | None
    current_layer: int  # 0 .. NUM_LAYERS-1
    beam: list[list[Piece]]  # NUM_LAYERS lists; assembled pieces per layer
    finished_beams: list[list[list[Piece]]]  # completed beams, each = NUM_LAYERS piece layout
    discarded_pieces: list[Piece]  # every wasted piece, flat, in discard order (oldest first)
    discarded_total: int
    last_reward: int
    terminated: bool


# ---------------------------------------------------------------------------
# Derived quantities (computed on demand, never stored)
# ---------------------------------------------------------------------------


def saw_piece_len(state: GlulamState) -> int:
    """Length of the piece at the saw position; 0 if the queue is empty."""
    return state.queue[-1][-1].length if state.queue else 0


def current_layer_len(state: GlulamState) -> int:
    return sum(p.length for p in state.beam[state.current_layer])


def current_layer_left(state: GlulamState, cfg: EnvConfig) -> int:
    return cfg.LAYER_LEN - current_layer_len(state)


def observable_boards(state: GlulamState, cfg: EnvConfig) -> list[list[Piece]]:
    """The rightmost OBSERVABLE_BOARDS boards (all remaining if fewer)."""
    return state.queue[-cfg.OBSERVABLE_BOARDS :] if state.queue else []


def hidden_boards(state: GlulamState, cfg: EnvConfig) -> list[list[Piece]]:
    """All boards left of the observation window."""
    return state.queue[: -cfg.OBSERVABLE_BOARDS]


def observable_pieces(state: GlulamState, cfg: EnvConfig) -> list[int]:
    return [p.length for board in observable_boards(state, cfg) for p in board]


def _prefix_sums(pieces: list[Piece]) -> list[int]:
    return list(accumulate(p.length for p in pieces))


def _interior_meet_positions(pieces: list[Piece], layer_len: int) -> set[int]:
    """Strictly interior prefix sums (0 < p < LAYER_LEN), excluding beam ends."""
    return {p for p in _prefix_sums(pieces) if 0 < p < layer_len}


def prev_meet_positions(state: GlulamState, cfg: EnvConfig) -> set[int]:
    """Meeting positions in the immediately preceding layer; empty for layer 0."""
    if state.current_layer == 0:
        return set()
    return _interior_meet_positions(state.beam[state.current_layer - 1], cfg.LAYER_LEN)


def current_meet_positions(state: GlulamState, cfg: EnvConfig) -> set[int]:
    """Meeting positions in the current layer so far."""
    return _interior_meet_positions(state.beam[state.current_layer], cfg.LAYER_LEN)


# ---------------------------------------------------------------------------
# Assemble constraints helper
# ---------------------------------------------------------------------------


def _forbidden_globally(fill: int, cfg: EnvConfig) -> bool:
    """True if fill falls inside any global forbidden interval."""
    return any(s < fill < e for s, e in cfg.FORBIDDEN_INTERVALS)


def _forbidden_prev(fill: int, meets: set[int], cfg: EnvConfig) -> bool:
    """True if fill falls inside any previous-layer forbidden interval."""
    h = cfg.PREV_MEET_FORBIDDEN_HALF
    return any(p - h < fill < p + h for p in meets)


def assemble_legal(state: GlulamState, cfg: EnvConfig, piece_len: int) -> bool:
    """Check all four assemble constraints for the resulting layer fill.

    If piece_len < MIN_PIECE_LEN, returns False (forced, for mask consistency).
    """
    if piece_len < cfg.MIN_PIECE_LEN:
        return False
    cll = current_layer_len(state)
    new_fill = cll + piece_len
    left = cfg.LAYER_LEN - cll
    prev_meets = prev_meet_positions(state, cfg) if state.current_layer > 0 else set()

    # 1. Layer-gap: exact fill, or gap >= MIN_PIECE_LEN.
    if not (piece_len == left or piece_len <= left - cfg.MIN_PIECE_LEN):
        return False
    # 2. Global forbidden (exempt exact fill).
    if new_fill != cfg.LAYER_LEN and _forbidden_globally(new_fill, cfg):
        return False
    # 3. Previous-layer forbidden (only if current_layer > 0, exempt exact fill).
    if new_fill != cfg.LAYER_LEN and _forbidden_prev(new_fill, prev_meets, cfg):
        return False
    # 4. Finishability (geometric) + next-layer feasibility (one-layer lookahead).
    if new_fill != cfg.LAYER_LEN:
        if not _reachable(new_fill, prev_meets, cfg):
            return False
    if not _next_layer_finishable(new_fill, state, cfg):
        return False
    return True


def assemble_legal_with_table(state: GlulamState, cfg: EnvConfig, piece_len: int, reach_table: list[bool]) -> bool:
    """Like assemble_legal but uses a pre-computed reachable table for constraint 4."""
    if piece_len < cfg.MIN_PIECE_LEN:
        return False
    cll = current_layer_len(state)
    new_fill = cll + piece_len
    left = cfg.LAYER_LEN - cll
    prev_meets = prev_meet_positions(state, cfg) if state.current_layer > 0 else set()

    if not (piece_len == left or piece_len <= left - cfg.MIN_PIECE_LEN):
        return False
    if new_fill != cfg.LAYER_LEN and _forbidden_globally(new_fill, cfg):
        return False
    if new_fill != cfg.LAYER_LEN and _forbidden_prev(new_fill, prev_meets, cfg):
        return False
    if new_fill != cfg.LAYER_LEN:
        if not reach_table[new_fill]:
            return False
    if not _next_layer_finishable(new_fill, state, cfg):
        return False
    return True


def _reachable_table(prev_meets: set[int], cfg: EnvConfig) -> list[bool]:
    """Compute the full reachable table backward from LAYER_LEN.

    Returns a list of bool where ``reach[f]`` is True if position f can reach LAYER_LEN.
    The layer-gap condition (constraint 1) is enforced at every level:
    ``f + s == LAYER_LEN`` (exact) or ``f + s <= LAYER_LEN - MIN_PIECE_LEN``.
    """
    L = cfg.LAYER_LEN
    reach = [False] * (L + 1)
    reach[L] = True
    for f in range(L - 1, -1, -1):
        for s in range(cfg.MIN_PIECE_LEN, cfg.MAX_PIECE_LEN + 1):
            nf = f + s
            if nf == L:
                reach[f] = True
                break
            if nf > L - cfg.MIN_PIECE_LEN:
                continue
            if _forbidden_globally(nf, cfg) or _forbidden_prev(nf, prev_meets, cfg):
                continue
            if reach[nf]:
                reach[f] = True
                break
    return reach


def _reachable(fill: int, prev_meets: set[int], cfg: EnvConfig) -> bool:
    """Geometric reachability DP: can position fill reach LAYER_LEN?"""
    return _reachable_table(prev_meets, cfg)[fill]


def _next_layer_finishable(new_fill: int, state: GlulamState, cfg: EnvConfig) -> bool:
    """One-layer lookahead: is the next layer finishable given this assembly?

    For a new beam's layer 0 (current_layer == NUM_LAYERS - 1 finished), no
    previous-layer constraints apply. Otherwise, the current layer's meeting
    positions (including this assembly) apply as prev_meet_positions.
    """
    if state.current_layer == cfg.NUM_LAYERS - 1:
        next_prev_meets = set()  # new beam's layer 0: no previous layer
    else:
        current_meets = current_meet_positions(state, cfg) | {new_fill}
        next_prev_meets = current_meets
    return _reachable(0, next_prev_meets, cfg)


def assemble_legal_mask(state: GlulamState, cfg: EnvConfig) -> list[bool]:
    """Boolean list of length MAX_PIECE_LEN: mask[k-1] = assemble_legal(state, cfg, k).

    Computes the current-layer reachable table once and shares it across all candidate
    lengths, at O(LAYER_LEN * MAX_PIECE_LEN). The next-layer lookahead cannot share it --
    each candidate length yields a different meeting-position set, so it builds its own
    table -- which dominates: O(LAYER_LEN * MAX_PIECE_LEN ** 2) per observation.
    """
    prev_meets = prev_meet_positions(state, cfg) if state.current_layer > 0 else set()
    reach_table = _reachable_table(prev_meets, cfg)
    return [assemble_legal_with_table(state, cfg, k, reach_table) for k in range(1, cfg.MAX_PIECE_LEN + 1)]


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------


def max_observable_pieces(cfg: EnvConfig) -> int:
    return cfg.OBSERVABLE_BOARDS * (cfg.MAX_BOARD_LEN // cfg.MIN_PIECE_LEN)


def observe(state: GlulamState, cfg: EnvConfig) -> dict:
    """The observable variables, exactly as listed in the spec."""
    return {
        "current_layer": state.current_layer,
        "current_layer_len": current_layer_len(state),
        "current_layer_left": current_layer_left(state, cfg),
        "observable_pieces": observable_pieces(state, cfg),
        "out_piece_len": state.out_piece.length if state.out_piece else 0,
        "buf_piece_len": state.buf_piece.length if state.buf_piece else 0,
        "saw_piece_len": saw_piece_len(state),
        "prev_meet_positions": prev_meet_positions(state, cfg),
        "current_meet_positions": current_meet_positions(state, cfg),
        "assemble_legal_mask": assemble_legal_mask(state, cfg),
    }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def num_actions(cfg: EnvConfig) -> int:
    return cfg.MAX_PIECE_LEN + 6


def action_name(cfg: EnvConfig, action: int) -> str:
    n = cfg.MAX_PIECE_LEN
    if action < n:
        return f"cut_{action + 1}"
    return ["put_buf", "assemble_out", "assemble_buf", "discard_out", "discard_buf", "discard_beam"][action - n]


def legal_actions(state: GlulamState, cfg: EnvConfig) -> list[bool]:
    """Boolean mask over the fixed action order; all False once terminated."""
    n = cfg.MAX_PIECE_LEN
    mask = [False] * (n + 6)
    if state.terminated:
        return mask

    saw = saw_piece_len(state)
    out_occupied = state.out_piece is not None
    buf_occupied = state.buf_piece is not None

    if state.queue and not out_occupied:
        for k in range(cfg.MIN_PIECE_LEN, saw + 1):
            mask[k - 1] = True  # cut_k

    if out_occupied and not buf_occupied:
        mask[n] = True  # put_buf

    def can_assemble(piece_len: int) -> bool:
        return assemble_legal(state, cfg, piece_len)

    if out_occupied and can_assemble(state.out_piece.length):
        mask[n + 1] = True  # assemble_out
    if buf_occupied and can_assemble(state.buf_piece.length):
        mask[n + 2] = True  # assemble_buf
    if out_occupied:
        mask[n + 3] = True  # discard_out
    if buf_occupied:
        mask[n + 4] = True  # discard_buf
    if any(state.beam[level] for level in range(cfg.NUM_LAYERS)):
        mask[n + 5] = True  # discard_beam
    return mask


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------


def step(state: GlulamState, cfg: EnvConfig, action: int) -> tuple[GlulamState, int]:
    """Pure transition. Returns (next_state, reward) with reward = -wasted_len."""
    if not legal_actions(state, cfg)[action]:
        raise ValueError(f"Illegal action {action} ({action_name(cfg, action)})")

    n = cfg.MAX_PIECE_LEN
    wasted = 0
    wasted_pieces: list[Piece] = []

    if action < n:  # cut_k
        k = action + 1
        saw = state.queue[-1][-1]
        out_piece = Piece(k, saw.piece_id, saw.board_id)
        rem = saw.length - k
        new_last_board = list(state.queue[-1][:-1])
        if rem >= cfg.MIN_PIECE_LEN:
            new_last_board.append(Piece(rem, saw.piece_id, saw.board_id))
        elif rem > 0:  # sub-MIN remainder is removed as waste
            wasted = rem
            wasted_pieces = [Piece(rem, saw.piece_id, saw.board_id)]
        queue = state.queue[:-1]  # new list; boards shared
        if new_last_board:
            queue = queue + [new_last_board]
        state = replace(state, queue=queue, out_piece=out_piece)

    elif action == n:  # put_buf
        state = replace(state, buf_piece=state.out_piece, out_piece=None)

    elif action in (n + 1, n + 2):  # assemble_out / assemble_buf
        from_out = action == n + 1
        piece = state.out_piece if from_out else state.buf_piece
        layer = state.beam[state.current_layer] + [piece]  # new list
        beam = list(state.beam)
        beam[state.current_layer] = layer
        cur = state.current_layer
        finished = list(state.finished_beams)
        if sum(p.length for p in layer) == cfg.LAYER_LEN:
            if cur == cfg.NUM_LAYERS - 1:  # beam finished
                finished.append(beam)  # no copy needed: frozen pieces, copy-on-write
                beam = [[] for _ in range(cfg.NUM_LAYERS)]
                cur = 0
            else:
                cur += 1
        state = replace(
            state,
            beam=beam,
            current_layer=cur,
            finished_beams=finished,
            out_piece=None if from_out else state.out_piece,
            buf_piece=state.buf_piece if from_out else None,
        )

    elif action == n + 3:  # discard_out
        wasted = state.out_piece.length
        wasted_pieces = [state.out_piece]
        state = replace(state, out_piece=None)

    elif action == n + 4:  # discard_buf
        wasted = state.buf_piece.length
        wasted_pieces = [state.buf_piece]
        state = replace(state, buf_piece=None)

    else:  # discard_beam (action == n + 5)
        wasted = sum(p.length for layer in state.beam for p in layer)
        wasted_pieces = [p for layer in state.beam for p in layer]
        state = replace(
            state,
            beam=[[] for _ in range(cfg.NUM_LAYERS)],
            current_layer=0,
        )

    reward = -wasted
    terminated = not state.queue and state.out_piece is None and state.buf_piece is None
    new_discarded = state.discarded_pieces + wasted_pieces
    state = replace(
        state,
        discarded_pieces=new_discarded,
        discarded_total=state.discarded_total + wasted,
        last_reward=reward,
        terminated=terminated,
    )
    return state, reward


# ---------------------------------------------------------------------------
# Instance generation
# ---------------------------------------------------------------------------


def check_feasibility(cfg: EnvConfig) -> None:
    """Assert joint config feasibility; raise ValueError naming the violated condition."""

    def req(cond: bool, msg: str) -> None:
        if not cond:
            raise ValueError(f"Infeasible config: {msg}")

    req(cfg.MIN_PIECE_LEN >= 1, "MIN_PIECE_LEN >= 1")
    req(cfg.NUM_LAYERS >= 1, "NUM_LAYERS >= 1")
    req(cfg.OBSERVABLE_BOARDS >= 1, "OBSERVABLE_BOARDS >= 1")
    req(cfg.MIN_PIECE_LEN <= cfg.MAX_PIECE_LEN, "MIN_PIECE_LEN <= MAX_PIECE_LEN")
    req(cfg.INI_BOARDS >= 1, "INI_BOARDS >= 1")
    req(cfg.INI_PIECES >= cfg.INI_BOARDS, "INI_PIECES >= INI_BOARDS")
    req(cfg.OBSERVABLE_BOARDS <= cfg.INI_BOARDS, "OBSERVABLE_BOARDS <= INI_BOARDS")
    req(cfg.MIN_PIECE_LEN <= cfg.LAYER_LEN, "MIN_PIECE_LEN <= LAYER_LEN")
    req(cfg.MIN_PIECE_LEN <= cfg.MIN_BOARD_LEN, "MIN_PIECE_LEN <= MIN_BOARD_LEN")
    req(cfg.MIN_BOARD_LEN <= cfg.MAX_BOARD_LEN, "MIN_BOARD_LEN <= MAX_BOARD_LEN")
    req(cfg.MAX_PIECE_LEN <= cfg.MAX_BOARD_LEN, "MAX_PIECE_LEN <= MAX_BOARD_LEN")
    req(cfg.PREV_MEET_FORBIDDEN_HALF >= 0, "PREV_MEET_FORBIDDEN_HALF >= 0")
    req(cfg.BOARD_LEN_SPREAD is None or cfg.BOARD_LEN_SPREAD >= 0, "BOARD_LEN_SPREAD is None or >= 0")
    for s, e in cfg.FORBIDDEN_INTERVALS:
        req(0 <= s < e <= cfg.LAYER_LEN, "FORBIDDEN_INTERVALS entries in [0, LAYER_LEN]")
    # Base-case: layer 0 must be finishable with only global forbidden intervals.
    req(_reachable(0, set(), cfg), "layer 0 not finishable with global intervals alone")

    # Per-board piece counts n must give a non-empty board-length interval:
    #   max(MIN_BOARD_LEN, n * MIN_PIECE_LEN) <= min(MAX_BOARD_LEN, n * MAX_PIECE_LEN)
    n_min = _min_pieces_per_board(cfg)
    n_max = _max_pieces_per_board(cfg)
    req(n_min <= n_max, "some per-board piece count has a non-empty length interval")
    req(
        cfg.INI_BOARDS * n_min <= cfg.INI_PIECES <= cfg.INI_BOARDS * n_max,
        "a piece-count partition of INI_PIECES across INI_BOARDS boards exists "
        f"(need {cfg.INI_BOARDS} * {n_min} <= INI_PIECES <= {cfg.INI_BOARDS} * {n_max})",
    )


def _min_pieces_per_board(cfg: EnvConfig) -> int:
    return max(1, math.ceil(cfg.MIN_BOARD_LEN / cfg.MAX_PIECE_LEN))


def _max_pieces_per_board(cfg: EnvConfig) -> int:
    return cfg.MAX_BOARD_LEN // cfg.MIN_PIECE_LEN


def _partition_piece_counts(cfg: EnvConfig, rng: random.Random) -> list[int]:
    """Distribute INI_PIECES across INI_BOARDS boards (reserve minimum, then
    distribute the remainder randomly among boards below the maximum).

    With ``BOARD_LEN_SPREAD`` set, boards are meant to come out near ``MAX_BOARD_LEN``, which
    takes at least ``ceil(MAX_BOARD_LEN / MAX_PIECE_LEN)`` pieces — a board with fewer can never
    reach it. Those pieces are therefore handed out first, in random board order so that a short
    piece budget does not systematically starve the same end of the queue.
    """
    n_min, n_max = _min_pieces_per_board(cfg), _max_pieces_per_board(cfg)
    counts = [n_min] * cfg.INI_BOARDS
    remaining = cfg.INI_PIECES - cfg.INI_BOARDS * n_min
    if cfg.BOARD_LEN_SPREAD is not None:
        n_target = min(n_max, math.ceil(cfg.MAX_BOARD_LEN / cfg.MAX_PIECE_LEN))
        for i in rng.sample(range(cfg.INI_BOARDS), cfg.INI_BOARDS):
            grant = min(remaining, max(0, n_target - counts[i]))
            counts[i] += grant
            remaining -= grant
    for _ in range(remaining):
        candidates = [i for i, c in enumerate(counts) if c < n_max]
        counts[rng.choice(candidates)] += 1
    return counts


def _split_board(board_len: int, n_pieces: int, cfg: EnvConfig, rng: random.Random) -> list[int]:
    """Split board_len into n_pieces integer lengths, each in [MIN, MAX]."""
    lengths = []
    rem = board_len
    for i in range(n_pieces - 1):
        after = n_pieces - i - 1  # pieces still to draw after this one
        lo = max(cfg.MIN_PIECE_LEN, rem - after * cfg.MAX_PIECE_LEN)
        hi = min(cfg.MAX_PIECE_LEN, rem - after * cfg.MIN_PIECE_LEN)
        length = rng.randint(lo, hi)
        lengths.append(length)
        rem -= length
    lengths.append(rem)
    return lengths


def reset(cfg: EnvConfig) -> GlulamState:
    """Generate a fresh instance from cfg.seed and return the initial state."""
    check_feasibility(cfg)
    rng = random.Random(cfg.seed)

    counts = _partition_piece_counts(cfg, rng)
    board_lengths: list[list[int]] = []
    for n in counts:
        lo = max(cfg.MIN_BOARD_LEN, n * cfg.MIN_PIECE_LEN)
        hi = min(cfg.MAX_BOARD_LEN, n * cfg.MAX_PIECE_LEN)
        if cfg.BOARD_LEN_SPREAD is not None:  # draw from the top of the interval, near MAX_BOARD_LEN
            lo = max(lo, hi - cfg.BOARD_LEN_SPREAD)
        board_lengths.append(_split_board(rng.randint(lo, hi), n, cfg, rng))

    # Ids start at the saw end: rightmost piece / board = 0, increasing leftwards.
    queue: list[list[Piece]] = []
    flat_idx = 0
    for board_idx, lengths in enumerate(board_lengths):
        board_id = cfg.INI_BOARDS - 1 - board_idx
        board = []
        for length in lengths:
            piece_id = cfg.INI_PIECES - 1 - flat_idx
            board.append(Piece(length, piece_id, board_id))
            flat_idx += 1
        queue.append(board)

    return GlulamState(
        queue=queue,
        out_piece=None,
        buf_piece=None,
        current_layer=0,
        beam=[[] for _ in range(cfg.NUM_LAYERS)],
        finished_beams=[],
        discarded_pieces=[],
        discarded_total=0,
        last_reward=0,
        terminated=False,
    )
