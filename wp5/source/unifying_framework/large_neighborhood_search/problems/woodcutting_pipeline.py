"""Woodcutting "rich" pipeline model LNS operators.

Targets the 5-machine pipeline model (Board/Interval/Piece/CutList DSRecords
plus reordering/cutting/filtering/checking "machines" with genuine
module-level data flow — see ``ParsedOptDSLModel.is_pipeline_model``).

Decision variables:

* ``swapping_decisions_boards`` : DSList(N_BOARDS - 1, bool)
* ``cuts_list_list``            : DSList(N_BOARDS, CutList)
  (``CutList.position_list`` : DSList(MAX_N_CUTS_PER_BOARD, DSInt(...)))
* ``keep_decisions``            : DSList(N_PIECES, bool)
* ``swapping_decisions``        : DSList(N_PIECES - 1, bool)

The hard structural constraints (``cutting_machine``'s ``cut_list[0] == 0``,
``cut_list[-1] == board.length``, curved-interval coverage; ``filtering_machine``'s
"never keep a bad-quality piece") are effectively impossible to satisfy by
uniform random sampling — generic LNS operators get stuck at ``cutting_machine``
on the very first evaluation. These operators build/repair ``cuts_list_list``
and ``keep_decisions`` by construction so those constraints always hold,
leaving only ``checking_machine``'s beam-packing/sequencing constraints
(addressed via a bounded local search over the reordering ``swapping_decisions*``
bits, since they never break the earlier hard constraints on their own).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..components import DestroyOperator, Initializer, RepairOperator
from ..models import LNSContext
from .._expr_eval import DSRecord
from .._utils import clone_assignment, get_decision_value, is_better_score, set_decision_value


REQUIRED_CONSTANTS = (
    "N_BOARDS",
    "MAX_BOARD_LENGTH",
    "MAX_N_CUTS_PER_BOARD",
    "N_PIECES",
    "BEAM_LENGTH",
    "BEAM_DEPTH",
    "GIVEN_INITIAL_BOARDS",
)
REQUIRED_VARIABLES = (
    # "swapping_decisions_boards" is intentionally NOT required: it is only
    # present in the board-reordering variant of the model.  The no-reorder
    # variant (Tools/convert_woodcutting_benchmarks_noreorder.py) omits it
    # (board reordering is what made MiniZinc crash), and the pipeline
    # operators must work on both.
    # "swapping_decisions" (piece reordering) is likewise optional: the
    # --no-piece-reorder converter variant omits it (checking reads
    # filtered_pieces directly), so we only *require* it when present.
    "cuts_list_list",
    "keep_decisions",
)


def detect_woodcutting_pipeline_problem(context: LNSContext) -> bool:
    """Detect the rich woodcutting pipeline model by structural inspection."""
    constants = context.constants
    if not all(name in constants for name in REQUIRED_CONSTANTS):
        return False
    problem_data = context.extra.get("problem_data")
    if problem_data is None or not getattr(problem_data.parsed, "is_pipeline_model", False):
        return False
    variable_names = set(problem_data.variables.keys())
    return all(name in variable_names for name in REQUIRED_VARIABLES)
    # NOTE: swapping_decisions (piece reorder) is optional — guarded via
    # info["has_piece_reordering"] wherever it is used.


def _get_woodcutting_info(context: LNSContext):
    if not detect_woodcutting_pipeline_problem(context):
        return None
    constants = context.constants
    boards = constants.get("GIVEN_INITIAL_BOARDS")
    if not isinstance(boards, list):
        return None
    max_cuts = int(constants["MAX_N_CUTS_PER_BOARD"])
    forbidden_raw = constants.get("FORBIDDEN_INTERVALS", [])
    forbidden_intervals = [(int(lo), int(hi)) for lo, hi in forbidden_raw] if isinstance(forbidden_raw, list) else []
    problem_data = context.extra.get("problem_data")
    variable_names = set(problem_data.variables.keys()) if problem_data is not None else set()
    return {
        "n_boards": int(constants["N_BOARDS"]),
        "max_cuts": max_cuts,
        "n_pieces": int(constants["N_PIECES"]),
        "boards": boards,
        "pieces_per_board": max_cuts - 1,
        "beam_length": int(constants["BEAM_LENGTH"]),
        "forbidden_intervals": forbidden_intervals,
        "beam_depth": int(constants.get("BEAM_DEPTH", 1)),
        "n_beams": int(constants.get("N_BEAMS", 1)),
        # Unusable margins at the start/end of each board (and each beam): the
        # gold-standard model asserts cut_list[0] == BEAM_SKIP_START and
        # cut_list[-1] == board.length - BEAM_SKIP_END, and checking_machine
        # forbids seams inside these margins.  The initializer must place cuts
        # inside the usable [BEAM_SKIP_START, board.length - BEAM_SKIP_END]
        # window or every construction is infeasible.
        "beam_skip_start": int(constants.get("BEAM_SKIP_START", 0)),
        "beam_skip_end": int(constants.get("BEAM_SKIP_END", 0)),
        # Whether this model has the board-reordering decision variable.  The
        # no-reorder variant omits it, so we must not add that key to the
        # assignment (an undeclared variable would be rejected by the
        # evaluator / empty-assignment builder).
        "has_board_reordering": "swapping_decisions_boards" in variable_names,
        # Whether this model has the piece-reordering decision variable.  The
        # --no-piece-reorder converter variant omits it (checking consumes
        # filtered_pieces directly), so assignments must not include it there.
        "has_piece_reordering": "swapping_decisions" in variable_names,
    }


def _is_strict_model(info: dict) -> bool:
    """True when the model's checking_machine is the strict variant.

    The gold-standard / noreorder models enforce ``cut_list[0] ==
    BEAM_SKIP_START``, ``cut_list[-1] == board.length - BEAM_SKIP_END`` and the
    strict stream end-state (``total_depth == N_BEAMS * BEAM_DEPTH``, no
    dangling partial layer) — signalled here by non-zero beam skip margins
    (only a strict model carries them; the loose variant uses margins of 0).
    For such models the keep-selection must only keep pieces that *exactly*
    complete a layer (strict exact-fill), otherwise CHECKING_MACHINE rejects
    the construction (overflow or a dangling partial layer).
    """
    return bool(info.get("beam_skip_start", 0) or info.get("beam_skip_end", 0))


def _base_woodcutting_assignment(
    positions_all: list[list[int]],
    keep_decisions: list[int],
    n_boards: int,
    n_pieces: int,
    info: dict,
) -> dict[str, object]:
    """Build the shared part of a woodcutting assignment (cuts + keep).

    ``swapping_decisions_boards`` is only added when the model declares it
    (the no-reorder variant omits it).  ``swapping_decisions`` is initialized
    to all-zero here; callers may override it with a randomized bit vector.
    """
    assignment: dict[str, object] = {
        "cuts_list_list": [DSRecord({"position_list": p}) for p in positions_all],
        "keep_decisions": keep_decisions,
    }
    if info.get("has_piece_reordering", False):
        assignment["swapping_decisions"] = [0] * max(0, n_pieces - 1)
    if info.get("has_board_reordering", False):
        assignment["swapping_decisions_boards"] = [0] * max(0, n_boards - 1)
    return assignment


def _plan_cuts(
    boards: list[dict],
    max_cuts: int,
    beam_length: int,
    rng: random.Random,
    randomized: bool = False,
    complementary_index: int | None = None,
    beam_skip_start: int = 0,
    beam_skip_end: int = 0,
) -> list[list[int]]:
    """Build position lists for every board.

    Cutting every board identically (one full BEAM_LENGTH piece + a fixed
    remainder R) strands each board's remainder in isolation: nothing else
    in the stream is sized to combine with it into a full layer, so it is
    always waste. If complementary_index is given, that one board is cut
    at (BEAM_LENGTH - R) instead (R = the other boards' standard remainder)
    so its first piece combines with one other board's remainder to
    complete an extra layer, at the cost of a differently-shaped remainder
    of its own — the combined keep/swap search decides which remainders end
    up actually used.
    """
    standard_remainder: int | None = None
    if complementary_index is not None and not randomized:
        for board in boards:
            length = int(board["length"])
            if length >= beam_length:
                standard_remainder = length % beam_length
                break

    all_positions: list[list[int]] = []
    for board_index, board in enumerate(boards):
        first_piece_override = None
        if board_index == complementary_index and standard_remainder is not None:
            candidate = beam_length - standard_remainder
            length = int(board["length"])
            if 0 < candidate < length:
                first_piece_override = candidate
        positions = _build_cut_positions_for_board(
            board,
            max_cuts,
            beam_length,
            rng,
            randomized=randomized,
            first_piece_override=first_piece_override,
            beam_skip_start=beam_skip_start,
            beam_skip_end=beam_skip_end,
        )
        all_positions.append(positions)
    return all_positions


def _build_cut_positions_for_board(
    board: dict,
    max_cuts: int,
    beam_length: int,
    rng: random.Random,
    randomized: bool = False,
    first_piece_override: int | None = None,
    beam_skip_start: int = 0,
    beam_skip_end: int = 0,
) -> list[int]:
    """Build a feasible ``position_list`` for one board.

    Always satisfies ``position_list[0] == beam_skip_start``,
    ``position_list[-1] == board.length - beam_skip_end``, and (best-effort)
    coverage of every curved interval by at least one cut.  Non-randomized
    cuts prefer full ``BEAM_LENGTH``-sized pieces within the usable window
    (mirrors the unified cutting/packing model's strategy) so the greedy
    keep-selection has large, cleanly-fitting chunks to work with instead of
    arbitrary remainders.  ``first_piece_override``, if given, replaces the
    size of the first piece (see ``_plan_cuts``'s ``complementary_index``).
    """
    length = int(board["length"])
    lo0 = beam_skip_start
    hi0 = length - beam_skip_end
    usable = hi0 - lo0
    interior_count = max(0, max_cuts - 2)

    if randomized and interior_count > 0:
        interior = sorted(rng.randint(lo0, hi0) for _ in range(interior_count))
    elif interior_count > 0:
        # Cut off as many full BEAM_LENGTH segments as fit within the usable
        # window; once the remainder is too short for another full segment,
        # pad with `hi0` (not the last cursor) so any resulting zero-length
        # piece sits at the very end — `cutting_machine` only allows a
        # zero-length piece there.
        interior = []
        cursor = lo0
        remaining = usable
        first_size = beam_length
        if first_piece_override is not None and 0 < first_piece_override < usable:
            first_size = first_piece_override
        for slot in range(interior_count):
            take = first_size if slot == 0 else beam_length
            if remaining >= take:
                cursor += take
                remaining -= take
                interior.append(cursor)
            else:
                interior.append(hi0)
    else:
        interior = []

    positions = [lo0] + interior + [hi0]

    for interval in board["curved_intervals"]:
        start = max(0, min(length, int(interval["start"])))
        end = max(0, min(length, int(interval["end"])))
        if start > end:
            start, end = end, start
        # Skip degenerate (0,0) sentinel intervals — the converter pads empty
        # curved lists with them (MiniZinc-safe), and covering a zero-width
        # interval would corrupt a real cut.
        if start >= end:
            continue
        if any(start <= p <= end for p in positions):
            continue
        interior_indices = list(range(1, len(positions) - 1))
        if not interior_indices:
            continue
        target = (start + end) // 2
        target = max(lo0, min(hi0, target))
        closest = min(interior_indices, key=lambda i, t=target: abs(positions[i] - t))
        positions[closest] = target

    positions.sort()
    positions[0] = lo0
    positions[-1] = hi0
    return positions


def _pieces_from_positions(board: dict, positions: list) -> list[tuple[int, int]]:
    """Replicate ``cutting_machine``'s piece length/quality computation."""
    bad_intervals = board["bad_intervals"]
    pieces: list[tuple[int, int]] = []
    for idx in range(1, len(positions)):
        start, end = positions[idx - 1], positions[idx]
        length = end - start
        quality = 1 if all(iv["start"] >= end or start >= iv["end"] for iv in bad_intervals) else 0
        pieces.append((length, quality))
    return pieces


def _carry_threaded_assignment(
    info: dict,
    desired_layers: int,
    offset: int,
) -> tuple[list[list[int]], list[int]] | None:
    """Thread a running carry through the boards *in the order given* (no
    reordering at all) so consecutive kept pieces sum exactly to
    ``beam_length`` ``desired_layers`` times.

    Works in the stream of *usable* material: each board contributes
    ``board.length - BEAM_SKIP_START - BEAM_SKIP_END`` usable length, and the
    model's fixed cuts sit at ``BEAM_SKIP_START`` and
    ``board.length - BEAM_SKIP_END``.  Cuts are placed where a layer boundary
    (``offset + k * beam_length``) falls strictly inside a board's usable
    window.  Leftover usable material outside the window — and the unusable
    edge margins — is discarded.  Realizes the volume-optimal waste
    (``usable_material - desired_layers * beam_length``) whenever geometrically
    possible.  Returns ``None`` if this offset is infeasible.
    """
    boards = info["boards"]
    max_cuts = info["max_cuts"]
    beam_length = info["beam_length"]
    forbidden_intervals = info["forbidden_intervals"]
    skip_start = int(info.get("beam_skip_start", 0))
    skip_end = int(info.get("beam_skip_end", 0))

    usable_lengths = [max(0, int(b["length"]) - skip_start - skip_end) for b in boards]
    total_usable = sum(usable_lengths)
    window_end = offset + desired_layers * beam_length
    if offset < 0 or window_end > total_usable:
        return None

    boundary_set = {offset, window_end}
    boundary_set.update(offset + k * beam_length for k in range(1, desired_layers))

    # Board-local positions, in usable coordinates first, then mapped back.
    positions_all: list[list[int]] = []
    cursor_u = 0
    for board, usable_len in zip(boards, usable_lengths):
        lo_u, hi_u = cursor_u, cursor_u + usable_len
        length = int(board["length"])
        interior_u = sorted(b for b in boundary_set if lo_u < b < hi_u)
        if len(interior_u) > max_cuts - 2:
            return None
        # Map usable offset -> board-local position (shift by skip_start).
        positions = [skip_start] + [skip_start + (p - lo_u) for p in interior_u] + [length - skip_end]
        positions.sort()
        # Pad to exactly MAX_N_CUTS_PER_BOARD entries with the board's end cut
        # (duplicate end -> zero-length tail pieces), so every board yields
        # exactly max_cuts-1 pieces (matching cutting_machine / N_PIECES).
        end_cut = length - skip_end
        while len(positions) < max_cuts:
            positions.append(end_cut)
        positions_all.append(positions)
        cursor_u = hi_u

    # Keep decisions: a piece (between consecutive board-local positions) is
    # kept iff its usable-coordinate span lies inside [offset, window_end], and
    # kept pieces must carry-thread into exact layers (overflow is infeasible,
    # as is a bad-quality kept piece inside the window).
    keep_decisions: list[int] = []
    running = 0
    cursor_u = 0
    for board, positions, usable_len in zip(boards, positions_all, usable_lengths):
        lo_u = cursor_u
        # Positive pieces in usable coordinates: consecutive position pairs.
        # pairs = [(start_u, end_u), ...] derived from positions.
        pieces_u: list[tuple[int, int, int]] = []  # (start_u, end_u, length)
        prev = skip_start
        prev_u = lo_u
        for pos in positions[1:]:
            plen = pos - prev
            end_u = prev_u + plen
            pieces_u.append((prev_u, end_u, plen))
            prev = pos
            prev_u = end_u
        board_keep = 0
        for (ps_u, pe_u, plen) in pieces_u:
            # quality is recomputed accurately in the final pass below; here we
            # only decide keep (in_window) and the carry-thread validity.
            in_window = plen == 0 or (ps_u >= offset and pe_u <= window_end)
            keep_decisions.append(1 if in_window else 0)
            board_keep += 1
            if not in_window:
                continue
            running += plen
            if running == beam_length:
                running = 0
            elif running > beam_length:
                return None
            elif any(lo_f <= running <= hi_f for lo_f, hi_f in forbidden_intervals):
                return None
        # Pad keep entries to max_cuts-1 per board (zero-length padding pieces
        # are always discarded) — but only if fewer pieces than needed.
        pieces_per = max_cuts - 1
        if len(pieces_u) < pieces_per:
            keep_decisions.extend([0] * (pieces_per - len(pieces_u)))
        elif len(pieces_u) > pieces_per:
            # too many pieces for one board under max_cuts
            return None
        cursor_u = hi_u

    # Quality check: inside the window, no kept piece may be bad quality.
    # (recompute with the accurate _pieces_from_positions)
    all_pieces = []
    for board, positions in zip(boards, positions_all):
        all_pieces.extend(_pieces_from_positions(board, positions))
    # compare lengths against keep decisions (they must align)
    if len(all_pieces) != len(keep_decisions):
        # padding produced mismatch — pad all_pieces with (0,1) to match
        while len(all_pieces) < len(keep_decisions):
            all_pieces.append((0, 1))
        all_pieces = all_pieces[: len(keep_decisions)]
    for kd, (_, quality) in zip(keep_decisions, all_pieces):
        if kd == 1 and quality != 1:
            return None

    return positions_all, keep_decisions



def _find_carry_threaded_assignment(
    info: dict, rng: random.Random | None = None
) -> tuple[list[list[int]], list[int]] | None:
    """Search offsets for a feasible no-reordering carry-threaded construction.

    Every feasible offset wastes the same amount (the volume argument fixes
    total waste at ``total_material - desired_layers * beam_length``
    regardless of where the leftover sits) — this only needs to find *one*
    offset that doesn't hit a forbidden-interval or per-board cut-count
    collision. ``desired_layers`` is capped at ``n_beams * beam_depth`` so
    the construction never aims for more layers than ``checking_machine``
    expects.
    """
    boards = info["boards"]
    beam_length = info["beam_length"]
    total_usable = sum(
        max(0, int(b["length"]) - int(info.get("beam_skip_start", 0)) - int(info.get("beam_skip_end", 0)))
        for b in boards
    )
    max_layers_by_volume = total_usable // beam_length
    max_layers_wanted = info["n_beams"] * info["beam_depth"]
    desired_layers = min(max_layers_by_volume, max_layers_wanted)
    if desired_layers <= 0:
        return None
    waste_budget = total_usable - desired_layers * beam_length

    offsets = list(range(0, waste_budget + 1))
    if rng is not None:
        rng.shuffle(offsets)
    for offset in offsets:
        result = _carry_threaded_assignment(info, desired_layers, offset)
        if result is not None:
            return result
    return None


def _pieces_from_cuts_list(boards: list, cuts_list_list: list, pieces_per_board: int) -> list[tuple[int, int]]:
    all_pieces: list[tuple[int, int]] = []
    for board, record in zip(boards, cuts_list_list):
        positions = record.get("position_list") if isinstance(record, dict) else None
        if not isinstance(positions, list) or any(p is None for p in positions):
            all_pieces.extend([(0, 0)] * pieces_per_board)
            continue
        all_pieces.extend(_pieces_from_positions(board, positions))
    return all_pieces


def _simulate_keep_decisions(
    all_pieces: list[tuple[int, int]],
    existing: list,
    beam_length: int,
    forbidden_intervals: list[tuple[int, int]],
    strict: bool = False,
) -> list[int]:
    """Simulate ``checking_machine``'s running length, deciding undestroyed (``None``) entries greedily.

    Entries already fixed (0 or 1) in ``existing`` are kept as-is (their
    contribution still updates the running length so later greedy decisions
    stay consistent); ``None`` entries are decided the same way as a fresh
    construction: keep only if it doesn't exceed ``BEAM_LENGTH`` and (when not
    landing exactly on a layer boundary) doesn't fall inside a forbidden
    interval — this is always feasible by construction (discarding is always
    safe) while wasting far less material than discarding everything.

    With ``strict=True`` (used for the strict checking_machine that requires
    ``total_depth == N_BEAMS * BEAM_DEPTH`` and forbids dangling partial
    layers), a piece is kept only if it *exactly completes* a layer
    (``length + piece_length == beam_length``).  This guarantees every kept
    piece lands in a completed layer, so the strict end-state assertions hold
    by construction.  Non-completing good pieces are discarded (their length
    becomes the objective), which is always feasible.
    """
    result: list[int] = []
    length = 0
    for idx, (piece_length, quality) in enumerate(all_pieces):
        fixed = existing[idx] if idx < len(existing) else None
        if fixed == 1:
            length = length + piece_length
            if length == beam_length:
                length = 0
            result.append(1)
            continue
        if fixed == 0:
            result.append(0)
            continue

        if quality != 1 or piece_length <= 0:
            result.append(0)
            continue
        candidate = length + piece_length
        if candidate > beam_length:
            result.append(0)
            continue
        if strict:
            # Strict exact-fill: only keep if this completes a layer.
            if candidate == beam_length:
                result.append(1)
                length = 0
            else:
                result.append(0)
            continue
        if candidate == beam_length:
            result.append(1)
            length = 0
            continue
        if any(lo <= candidate <= hi for lo, hi in forbidden_intervals):
            result.append(0)
            continue
        result.append(1)
        length = candidate
    return result


def _greedy_keep_decisions(
    all_pieces: list[tuple[int, int]],
    beam_length: int,
    forbidden_intervals: list[tuple[int, int]],
    strict: bool = False,
) -> list[int]:
    """Greedily select which pieces to keep, mirroring ``checking_machine`` (fresh construction)."""
    return _simulate_keep_decisions(
        all_pieces, [None] * len(all_pieces), beam_length, forbidden_intervals, strict=strict
    )


def _random_fill_missing(assignment: dict, context: LNSContext) -> dict:
    rng: random.Random = context.extra["rng"]
    for key in context.extra["decision_keys"]:
        if get_decision_value(assignment, key) is None:
            lo, hi = context.extra["decision_domains"][key]
            set_decision_value(assignment, key, rng.randint(lo, hi))
    return assignment


@dataclass
class WoodcuttingPipelineInitializer(Initializer):
    """Constructive initializer for the rich woodcutting pipeline model.

    Builds feasible cuts and greedily keeps every good-quality piece, then
    runs a bounded local search over the piece-reordering ``swapping_decisions``
    bits (the only remaining lever, since it never breaks the cutting/filtering
    constraints) to try to satisfy ``checking_machine``'s beam-packing checks.
    """

    restarts: int = 8
    swap_search_steps: int = 600

    def initialize(self, context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        evaluator = context.extra.get("evaluator")
        if info is None:
            from ..lns import RandomAssignmentInitializer
            return RandomAssignmentInitializer().initialize(context)

        rng: random.Random = context.extra["rng"]
        best_assignment: dict[str, object] | None = None
        best_failed = 10**9
        best_score: float | None = None

        # A no-reordering "carry-threaded" construction (see
        # ``_find_carry_threaded_assignment``) realizes the volume-optimal
        # waste directly, whenever the boards' own order permits it — try it
        # first since it is far cheaper than the swap/keep hill-climb below
        # and, when it applies, no amount of local search over the other
        # strategies reaches the same waste.
        carry_result = _find_carry_threaded_assignment(info, rng)
        if carry_result is not None:
            positions_all, keep_decisions = carry_result
            n_boards = info["n_boards"]
            n_pieces = info["n_pieces"]
            assignment = _base_woodcutting_assignment(positions_all, keep_decisions, n_boards, n_pieces, info)
            if evaluator is None:
                return assignment
            assignment, failed, score = self._search_keep_and_swap_decisions(assignment, info, context, evaluator, rng)
            best_assignment, best_failed, best_score = assignment, failed, score

        # Cutting every board identically strands each board's own remainder
        # in isolation (nothing else is sized to combine with it into a full
        # layer). Rotating which board gets a "complementary" cut (sized to
        # combine with another board's remainder) across attempts lets the
        # search discover much lower-waste combinations than any single fixed
        # cut structure can reach on its own.
        n_boards = info["n_boards"]
        candidate_indices: list[int | None] = [None, *range(n_boards)]

        for attempt in range(max(1, self.restarts)):
            randomized = attempt >= len(candidate_indices)
            complementary_index = None if randomized else candidate_indices[attempt]
            assignment = self._build_base_assignment(
                info, rng, randomized=randomized, complementary_index=complementary_index
            )
            if evaluator is None:
                return assignment

            assignment, failed, score = self._search_keep_and_swap_decisions(assignment, info, context, evaluator, rng)

            if failed < best_failed or (
                failed == best_failed
                and score is not None
                and (best_score is None or is_better_score(score, best_score, context.objective_sense))
            ):
                best_assignment, best_failed, best_score = assignment, failed, score

        if best_assignment is not None:
            return best_assignment
        from ..lns import RandomAssignmentInitializer
        return RandomAssignmentInitializer().initialize(context)

    def _build_base_assignment(
        self,
        info: dict,
        rng: random.Random,
        randomized: bool,
        complementary_index: int | None = None,
    ) -> dict[str, object]:
        n_boards = info["n_boards"]
        boards = info["boards"]
        max_cuts = info["max_cuts"]
        n_pieces = info["n_pieces"]
        beam_length = info["beam_length"]

        positions_all = _plan_cuts(
            boards,
            max_cuts,
            beam_length,
            rng,
            randomized=randomized,
            complementary_index=complementary_index,
            beam_skip_start=info.get("beam_skip_start", 0),
            beam_skip_end=info.get("beam_skip_end", 0),
        )
        all_pieces: list[tuple[int, int]] = []
        for board, positions in zip(boards, positions_all):
            all_pieces.extend(_pieces_from_positions(board, positions))

        keep_decisions = _greedy_keep_decisions(
            all_pieces, beam_length, info["forbidden_intervals"], strict=_is_strict_model(info)
        )
        swapping_decisions = (
            [rng.randint(0, 1) for _ in range(n_pieces - 1)] if randomized else [0] * max(0, n_pieces - 1)
        )
        assignment: dict[str, object] = _base_woodcutting_assignment(
            positions_all, keep_decisions, n_boards, n_pieces, info
        )
        if info.get("has_piece_reordering", False):
            assignment["swapping_decisions"] = swapping_decisions
        return assignment

    def _search_keep_and_swap_decisions(
        self,
        assignment: dict[str, object],
        info: dict,
        context: LNSContext,
        evaluator,
        rng: random.Random,
    ) -> tuple[dict[str, object], int, float | None]:
        """Hill-climb over both keep and swap decisions, cuts held fixed.

        Unlike a pure feasibility search, this keeps looking for a *lower
        objective* even after reaching a feasible assignment (waste can
        almost always be reduced further by re-partitioning which pieces are
        kept/where they land), stopping only when the step budget is spent.
        """
        n_pieces = info["n_pieces"]
        detail = evaluator.evaluate_detailed(assignment, context)
        current, current_failed, current_score = assignment, detail.failed_constraints, detail.objective_value
        best = clone_assignment(assignment)
        best_failed = detail.failed_constraints
        best_score = detail.objective_value

        if n_pieces <= 1:
            return best, best_failed, best_score

        for _ in range(max(0, self.swap_search_steps)):
            trial = clone_assignment(current)
            roll = rng.random()
            has_swap = info.get("has_piece_reordering", False) and "swapping_decisions" in trial
            if has_swap and roll < 0.1:
                trial["swapping_decisions"] = [rng.randint(0, 1) for _ in range(n_pieces - 1)]
            elif roll < 0.2:
                trial["keep_decisions"] = [rng.randint(0, 1) for _ in range(n_pieces)]
            elif has_swap and roll < 0.6:
                idx = rng.randrange(n_pieces - 1)
                trial["swapping_decisions"][idx] = 1 - trial["swapping_decisions"][idx]
            else:
                idx = rng.randrange(n_pieces)
                trial["keep_decisions"][idx] = 1 - trial["keep_decisions"][idx]

            trial_detail = evaluator.evaluate_detailed(trial, context)
            trial_failed = trial_detail.failed_constraints
            trial_score = trial_detail.objective_value

            # Accept sideways (equal-objective) moves too, not just strict
            # improvements — plateau moves are how the search escapes local
            # optima here (a pure hill-climb gets stuck far short of the true
            # optimum on this model).
            accept = trial_failed < current_failed or (
                trial_failed == current_failed
                and trial_score is not None
                and (current_score is None or not is_better_score(current_score, trial_score, context.objective_sense))
            )
            if accept:
                current, current_failed, current_score = trial, trial_failed, trial_score
                if trial_failed < best_failed or (
                    trial_failed == best_failed
                    and trial_score is not None
                    and (best_score is None or is_better_score(trial_score, best_score, context.objective_sense))
                ):
                    best, best_failed, best_score = clone_assignment(trial), trial_failed, trial_score

        return best, best_failed, best_score


@dataclass
class WoodcuttingCutDestroy(DestroyOperator):
    """Clear the cut positions of randomly selected boards."""

    board_count: int = 1

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        if info is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        n_boards = info["n_boards"]
        max_cuts = info["max_cuts"]

        cuts_list_list = assignment.get("cuts_list_list")
        if not isinstance(cuts_list_list, list) or len(cuts_list_list) != n_boards:
            return assignment

        k = min(max(1, self.board_count), n_boards)
        for b in rng.sample(range(n_boards), k):
            record = cuts_list_list[b]
            if isinstance(record, dict):
                record["position_list"] = [None] * max_cuts
        return assignment


@dataclass
class WoodcuttingCutRepair(RepairOperator):
    """Reconstruct feasible cuts for any board whose positions were destroyed."""

    randomized: bool = False

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        if info is None:
            return partial_assignment
        rng: random.Random = context.extra["rng"]
        boards = info["boards"]
        max_cuts = info["max_cuts"]
        beam_length = info["beam_length"]

        cuts_list_list = partial_assignment.get("cuts_list_list")
        if not isinstance(cuts_list_list, list):
            return partial_assignment

        for i, record in enumerate(cuts_list_list):
            if not isinstance(record, dict) or i >= len(boards):
                continue
            positions = record.get("position_list")
            if isinstance(positions, list) and any(p is None for p in positions):
                record["position_list"] = _build_cut_positions_for_board(
                    boards[i],
                    max_cuts,
                    beam_length,
                    rng,
                    randomized=self.randomized,
                    beam_skip_start=info.get("beam_skip_start", 0),
                    beam_skip_end=info.get("beam_skip_end", 0),
                )
        return partial_assignment


@dataclass
class WoodcuttingKeepDestroy(DestroyOperator):
    """Unassign a random fraction of ``keep_decisions``."""

    fraction: float = 0.3

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        if info is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        n_pieces = info["n_pieces"]

        keep_decisions = assignment.get("keep_decisions")
        if not isinstance(keep_decisions, list) or len(keep_decisions) != n_pieces:
            return assignment

        n_destroy = max(1, int(round(n_pieces * max(0.0, min(1.0, self.fraction)))))
        for idx in rng.sample(range(n_pieces), min(n_destroy, n_pieces)):
            keep_decisions[idx] = None
        return assignment


@dataclass
class WoodcuttingKeepRepair(RepairOperator):
    """Recompute destroyed ``keep_decisions`` from the current cuts (quality-aware).

    Always keeps a positive-length, good-quality piece and discards the rest —
    satisfies ``filtering_machine``'s "never keep a bad piece" assert by
    construction, regardless of what the current ``cuts_list_list`` looks like.
    """

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        if info is None:
            return partial_assignment

        boards = info["boards"]
        cuts_list_list = partial_assignment.get("cuts_list_list")
        keep_decisions = partial_assignment.get("keep_decisions")
        if not isinstance(cuts_list_list, list) or not isinstance(keep_decisions, list):
            return partial_assignment

        all_pieces = _pieces_from_cuts_list(boards, cuts_list_list, info["pieces_per_board"])
        updated = _simulate_keep_decisions(
            all_pieces, keep_decisions, info["beam_length"], info["forbidden_intervals"],
            strict=_is_strict_model(info),
        )
        partial_assignment["keep_decisions"] = updated
        return partial_assignment


@dataclass
class WoodcuttingSwapDestroy(DestroyOperator):
    """Unassign a random fraction of the piece (and optionally board) reordering bits."""

    fraction: float = 0.3
    include_board_swaps: bool = False

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        if info is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        n_pieces = info["n_pieces"]

        swaps = assignment.get("swapping_decisions")
        if isinstance(swaps, list) and len(swaps) == max(0, n_pieces - 1) and swaps:
            n_destroy = max(1, int(round(len(swaps) * max(0.0, min(1.0, self.fraction)))))
            for idx in rng.sample(range(len(swaps)), min(n_destroy, len(swaps))):
                swaps[idx] = None

        if self.include_board_swaps and info.get("has_board_reordering", False):
            n_boards = info["n_boards"]
            board_swaps = assignment.get("swapping_decisions_boards")
            if isinstance(board_swaps, list) and board_swaps and len(board_swaps) == n_boards - 1:
                board_swaps[rng.randrange(len(board_swaps))] = None

        return assignment


@dataclass
class WoodcuttingCarryThreadDestroy(DestroyOperator):
    """Clear all cuts/keep decisions to force a fresh carry-threaded rebuild.

    Pairs with :class:`WoodcuttingCarryThreadRepair`. Reordering bits are left
    untouched by ``destroy`` — the repair always resets them to all-zero
    itself, since the carry-threaded construction never needs reordering.
    """

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        if info is None:
            return assignment
        max_cuts = info["max_cuts"]

        cuts_list_list = assignment.get("cuts_list_list")
        if isinstance(cuts_list_list, list) and len(cuts_list_list) == info["n_boards"]:
            for record in cuts_list_list:
                if isinstance(record, dict):
                    record["position_list"] = [None] * max_cuts

        keep_decisions = assignment.get("keep_decisions")
        if isinstance(keep_decisions, list):
            for idx in range(len(keep_decisions)):
                keep_decisions[idx] = None

        return assignment


@dataclass
class WoodcuttingCarryThreadRepair(RepairOperator):
    """Rebuild cuts/keep decisions via the no-reordering carry-threading
    construction (see ``_find_carry_threaded_assignment``).

    Tries offsets in random order each call so repeated LNS iterations
    explore different (equally volume-optimal) offsets instead of always
    landing on the same one. Falls back to the generic constructive cut
    strategy (and greedy keep) if no offset realizes the full-layer
    construction (e.g. it needs more cuts per board than allowed, or every
    offset collides with a forbidden interval).
    """

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        if info is None:
            return _random_fill_missing(partial_assignment, context)
        rng: random.Random = context.extra["rng"]

        result = _find_carry_threaded_assignment(info, rng)
        if result is None:
            boards = info["boards"]
            max_cuts = info["max_cuts"]
            beam_length = info["beam_length"]
            positions_all = _plan_cuts(
                boards,
                max_cuts,
                beam_length,
                rng,
                beam_skip_start=info.get("beam_skip_start", 0),
                beam_skip_end=info.get("beam_skip_end", 0),
            )
            all_pieces: list[tuple[int, int]] = []
            for board, positions in zip(boards, positions_all):
                all_pieces.extend(_pieces_from_positions(board, positions))
            keep_decisions = _greedy_keep_decisions(
                all_pieces, beam_length, info["forbidden_intervals"], strict=_is_strict_model(info)
            )
        else:
            positions_all, keep_decisions = result

        partial_assignment["cuts_list_list"] = [DSRecord({"position_list": p}) for p in positions_all]
        partial_assignment["keep_decisions"] = keep_decisions
        if info.get("has_piece_reordering", False):
            partial_assignment["swapping_decisions"] = [0] * max(0, info["n_pieces"] - 1)
        if info.get("has_board_reordering", False):
            partial_assignment["swapping_decisions_boards"] = [0] * max(0, info["n_boards"] - 1)
        return partial_assignment


@dataclass
class WoodcuttingSwapRepair(RepairOperator):
    """Sample several random completions of destroyed reordering bits, keep the best.

    Reordering bits never violate the cutting/filtering constraints on their
    own, so any completion is "safe" — sampling several and scoring with the
    evaluator is a cheap way to improve on a single random guess.
    """

    samples: int = 12

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_woodcutting_info(context)
        evaluator = context.extra.get("evaluator")
        if info is None or evaluator is None:
            return _random_fill_missing(partial_assignment, context)

        best: dict[str, object] | None = None
        best_failed = 10**9
        best_score: float | None = None

        for _ in range(max(1, self.samples)):
            trial = clone_assignment(partial_assignment)
            _random_fill_missing(trial, context)
            detail = evaluator.evaluate_detailed(trial, context)

            if (
                best is None
                or detail.failed_constraints < best_failed
                or (
                    detail.failed_constraints == best_failed
                    and detail.objective_value is not None
                    and (best_score is None or is_better_score(detail.objective_value, best_score, context.objective_sense))
                )
            ):
                best, best_failed, best_score = trial, detail.failed_constraints, detail.objective_value
            if best_failed == 0:
                break

        return best if best is not None else partial_assignment
