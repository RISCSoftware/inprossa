"""Glulam beam assembly environment.

Framework-free reference implementation of the authoritative spec in
glulam_beam_problem_description.md. Immutable state + pure functions:
``step(state, cfg, action) -> (next_state, reward)``. A rollout is a plain
list of states.

Action indexing (mask length = MAX_PIECE_LEN + 6, cut index = cut length - 1):
    0 .. N-1 : cut_1 .. cut_N                (N = MAX_PIECE_LEN)
    N        : cut_layer_finish              (= cut_k for k = current_layer_left)
    N + 1    : put_buf
    N + 2    : assemble_out
    N + 3    : assemble_buf
    N + 4    : discard_out
    N + 5    : discard_buf

Note: cut_1 .. cut_(MIN_PIECE_LEN - 1) are permanently illegal; they exist so
that the cut action index directly equals the cut length.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace


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
    MIN_BOARD_LEN_SUM: int
    MAX_BOARD_LEN: int
    INI_BOARDS: int
    INI_PIECES: int
    OBSERVABLE_BOARDS: int
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
    finished_beams: int
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
    return ["cut_layer_finish", "put_buf", "assemble_out", "assemble_buf", "discard_out", "discard_buf"][action - n]


def legal_actions(state: GlulamState, cfg: EnvConfig) -> list[bool]:
    """Boolean mask over the fixed action order; all False once terminated."""
    n = cfg.MAX_PIECE_LEN
    mask = [False] * (n + 6)
    if state.terminated:
        return mask

    saw = saw_piece_len(state)
    left = current_layer_left(state, cfg)
    out_occupied = state.out_piece is not None
    buf_occupied = state.buf_piece is not None

    if state.queue and not out_occupied:
        for k in range(cfg.MIN_PIECE_LEN, saw + 1):
            mask[k - 1] = True  # cut_k
        if cfg.MIN_PIECE_LEN <= left <= saw:
            mask[n] = True  # cut_layer_finish

    if out_occupied and not buf_occupied:
        mask[n + 1] = True  # put_buf

    def can_assemble(piece_len: int) -> bool:
        # Fill the layer exactly, or leave a gap of at least MIN_PIECE_LEN.
        return piece_len == left or piece_len <= left - cfg.MIN_PIECE_LEN

    if out_occupied and can_assemble(state.out_piece.length):
        mask[n + 2] = True  # assemble_out
    if buf_occupied and can_assemble(state.buf_piece.length):
        mask[n + 3] = True  # assemble_buf
    if out_occupied:
        mask[n + 4] = True  # discard_out
    if buf_occupied:
        mask[n + 5] = True  # discard_buf
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

    if action <= n:  # cut_k or cut_layer_finish
        k = current_layer_left(state, cfg) if action == n else action + 1
        saw = state.queue[-1][-1]
        out_piece = Piece(k, saw.piece_id, saw.board_id)
        rem = saw.length - k
        new_last_board = list(state.queue[-1][:-1])
        if rem >= cfg.MIN_PIECE_LEN:
            new_last_board.append(Piece(rem, saw.piece_id, saw.board_id))
        elif rem > 0:  # sub-MIN remainder is removed as waste
            wasted = rem
        queue = state.queue[:-1]  # new list; boards shared
        if new_last_board:
            queue = queue + [new_last_board]
        state = replace(state, queue=queue, out_piece=out_piece)

    elif action == n + 1:  # put_buf
        state = replace(state, buf_piece=state.out_piece, out_piece=None)

    elif action in (n + 2, n + 3):  # assemble_out / assemble_buf
        from_out = action == n + 2
        piece = state.out_piece if from_out else state.buf_piece
        layer = state.beam[state.current_layer] + [piece]  # new list
        beam = list(state.beam)
        beam[state.current_layer] = layer
        cur = state.current_layer
        finished = state.finished_beams
        if sum(p.length for p in layer) == cfg.LAYER_LEN:
            if cur == cfg.NUM_LAYERS - 1:  # beam finished, replaced by empty one
                beam = [[] for _ in range(cfg.NUM_LAYERS)]
                cur = 0
                finished += 1
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

    elif action == n + 4:  # discard_out
        wasted = state.out_piece.length
        state = replace(state, out_piece=None)

    else:  # discard_buf
        wasted = state.buf_piece.length
        state = replace(state, buf_piece=None)

    reward = -wasted
    terminated = not state.queue and state.out_piece is None and state.buf_piece is None
    state = replace(
        state,
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
    req(cfg.MIN_PIECE_LEN <= cfg.MAX_PIECE_LEN, "MIN_PIECE_LEN <= MAX_PIECE_LEN")
    req(cfg.INI_BOARDS >= 1, "INI_BOARDS >= 1")
    req(cfg.OBSERVABLE_BOARDS >= 1, "OBSERVABLE_BOARDS >= 1")
    req(cfg.INI_PIECES >= cfg.INI_BOARDS, "INI_PIECES >= INI_BOARDS")
    req(cfg.MIN_PIECE_LEN <= cfg.MIN_BOARD_LEN_SUM, "MIN_PIECE_LEN <= MIN_BOARD_LEN_SUM")
    req(cfg.MIN_BOARD_LEN_SUM <= cfg.MAX_BOARD_LEN, "MIN_BOARD_LEN_SUM <= MAX_BOARD_LEN")
    req(cfg.MAX_PIECE_LEN <= cfg.MAX_BOARD_LEN, "MAX_PIECE_LEN <= MAX_BOARD_LEN")

    # Per-board piece counts n must give a non-empty board-length interval:
    #   max(MIN_BOARD_LEN_SUM, n * MIN_PIECE_LEN) <= min(MAX_BOARD_LEN, n * MAX_PIECE_LEN)
    n_min = _min_pieces_per_board(cfg)
    n_max = _max_pieces_per_board(cfg)
    req(n_min <= n_max, "some per-board piece count has a non-empty length interval")
    req(
        cfg.INI_BOARDS * n_min <= cfg.INI_PIECES <= cfg.INI_BOARDS * n_max,
        "a piece-count partition of INI_PIECES across INI_BOARDS boards exists "
        f"(need {cfg.INI_BOARDS} * {n_min} <= INI_PIECES <= {cfg.INI_BOARDS} * {n_max})",
    )


def _min_pieces_per_board(cfg: EnvConfig) -> int:
    return max(1, math.ceil(cfg.MIN_BOARD_LEN_SUM / cfg.MAX_PIECE_LEN))


def _max_pieces_per_board(cfg: EnvConfig) -> int:
    return cfg.MAX_BOARD_LEN // cfg.MIN_PIECE_LEN


def _partition_piece_counts(cfg: EnvConfig, rng: random.Random) -> list[int]:
    """Distribute INI_PIECES across INI_BOARDS boards (reserve minimum, then
    distribute the remainder randomly among boards below the maximum)."""
    n_min, n_max = _min_pieces_per_board(cfg), _max_pieces_per_board(cfg)
    counts = [n_min] * cfg.INI_BOARDS
    for _ in range(cfg.INI_PIECES - cfg.INI_BOARDS * n_min):
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
        lo = max(cfg.MIN_BOARD_LEN_SUM, n * cfg.MIN_PIECE_LEN)
        hi = min(cfg.MAX_BOARD_LEN, n * cfg.MAX_PIECE_LEN)
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
        finished_beams=0,
        discarded_total=0,
        last_reward=0,
        terminated=False,
    )
