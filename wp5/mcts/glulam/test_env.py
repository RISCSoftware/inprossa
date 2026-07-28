"""Invariant assertions and spec-completeness rollouts for the glulam env.

Every assertion here is an executable spec clause. Runnable directly
(``uv run python -m mcts.glulam.test_env``) or via pytest.
"""

from __future__ import annotations

import random
from collections import defaultdict
from itertools import accumulate

from mcts.glulam.configs import EXAMPLE_CONFIGS
from mcts.glulam.env import (
    EnvConfig,
    GlulamState,
    _forbidden_globally,
    _reachable,
    assemble_legal,
    assemble_legal_mask,
    check_feasibility,
    current_layer_len,
    current_meet_positions,
    legal_actions,
    max_observable_pieces,
    observe,
    prev_meet_positions,
    reset,
    step,
)
from mcts.glulam.policy import PolicyConfig, uniform_policy, weighted_policy

POLICY_SEEDS = [0, 1, 2]
POLICIES = {"uniform": uniform_policy, "weighted": weighted_policy}


def _total_length(state: GlulamState) -> int:
    """Wood length live in the state: queue + out + buf + open beam."""
    total = sum(p.length for board in state.queue for p in board)
    total += state.out_piece.length if state.out_piece else 0
    total += state.buf_piece.length if state.buf_piece else 0
    total += sum(p.length for layer in state.beam for p in layer)
    return total


def _live_by_pid(state: GlulamState) -> dict[int, int]:
    live: dict[int, int] = defaultdict(int)
    pieces = [p for board in state.queue for p in board]
    pieces += [p for layer in state.beam for p in layer]
    pieces += [p for p in (state.out_piece, state.buf_piece) if p is not None]
    for p in pieces:
        live[p.piece_id] += p.length
    return live


def _finished_pieces_by_pid(state: GlulamState) -> dict[int, int]:
    finished: dict[int, int] = defaultdict(int)
    for beam in state.finished_beams:
        for layer in beam:
            for p in layer:
                finished[p.piece_id] += p.length
    return finished


def _check_state_invariants(state: GlulamState, cfg: EnvConfig) -> None:
    cll = current_layer_len(state)
    assert 0 <= cll <= cfg.LAYER_LEN, "layer overfilled"
    left = cfg.LAYER_LEN - cll
    assert not (0 < left < cfg.MIN_PIECE_LEN), "unfillable layer gap"

    # Every queue piece is at least MIN_PIECE_LEN (entry guarantee + remainder-removal).
    for board in state.queue:
        assert board, "empty board not dropped"
        for p in board:
            assert p.length >= cfg.MIN_PIECE_LEN, "queue piece below MIN_PIECE_LEN"

    # Completed layers sum to exactly LAYER_LEN.
    for layer in state.beam[: state.current_layer]:
        assert sum(p.length for p in layer) == cfg.LAYER_LEN, "completed layer not exactly full"

    # No meeting position in any layer of the current beam or any finished beam falls
    # inside any FORBIDDEN_INTERVALS interval.
    all_layers = list(state.beam) + [layer for beam in state.finished_beams for layer in beam]
    for layer in all_layers:
        meets = {p for p in accumulate(p.length for p in layer) if 0 < p < cfg.LAYER_LEN}
        for m in meets:
            assert not _forbidden_globally(m, cfg), f"meeting {m} in FORBIDDEN_INTERVALS"

    # Previous-layer forbidden: check all consecutive layer pairs in the current beam
    # and all consecutive pairs in each finished beam.
    h = cfg.PREV_MEET_FORBIDDEN_HALF

    def _check_prev_forbidden(lower_meets: set[int], upper_meets: set[int]) -> None:
        for m in upper_meets:
            for p in lower_meets:
                assert not (p - h < m < p + h), f"meeting {m} in prev-forbidden interval of {p}"

    # Current beam: each layer vs its predecessor.
    for i in range(1, len(state.beam)):
        lower = {p for p in accumulate(p.length for p in state.beam[i - 1]) if 0 < p < cfg.LAYER_LEN}
        upper = {p for p in accumulate(p.length for p in state.beam[i]) if 0 < p < cfg.LAYER_LEN}
        if lower or upper:
            _check_prev_forbidden(lower, upper)

    # Finished beams: each layer vs its predecessor.
    for beam in state.finished_beams:
        for i in range(1, len(beam)):
            lower = {p for p in accumulate(p.length for p in beam[i - 1]) if 0 < p < cfg.LAYER_LEN}
            upper = {p for p in accumulate(p.length for p in beam[i]) if 0 < p < cfg.LAYER_LEN}
            if lower or upper:
                _check_prev_forbidden(lower, upper)

    # Current layer is always finishable (using constraints 2-3 only).
    prev_meets = prev_meet_positions(state, cfg) if state.current_layer > 0 else set()
    assert _reachable(cll, prev_meets, cfg), "current layer not finishable"

    # Next layer is always finishable (or is a new beam's layer 0 with no prev constraints).
    if state.current_layer == cfg.NUM_LAYERS - 1:
        assert _reachable(0, set(), cfg), "new beam's layer 0 not finishable"
    else:
        cur_meets = current_meet_positions(state, cfg)
        assert _reachable(0, cur_meets, cfg), "next layer not finishable"

    # current_layer_len == max(current_meet_positions) when non-empty (and 0 when empty).
    cur_meets = current_meet_positions(state, cfg)
    assert (not cur_meets and cll == 0) or (cur_meets and max(cur_meets) == cll), "current_meet_positions mismatch"

    # assemble_legal_mask consistency.
    mask = assemble_legal_mask(state, cfg)
    for k in range(1, cfg.MAX_PIECE_LEN + 1):
        expected = assemble_legal(state, cfg, k)
        assert mask[k - 1] == expected, f"mask[{k-1}] = {mask[k - 1]} != assemble_legal = {expected}"

    # observable_pieces length bound.
    assert len(observe(state, cfg)["observable_pieces"]) <= max_observable_pieces(cfg), "observable_pieces too long"


def run_checked_episode(
    cfg: EnvConfig, policy_seed: int, policy, max_steps: int = 100_000
) -> tuple[int, GlulamState, int]:
    """Roll out a policy, asserting all invariants at every step.

    Returns (steps, final_state, stuck_geometry_steps).
    """
    s0 = reset(cfg)
    input_total = _total_length(s0)
    origin_len = {p.piece_id: p.length for board in s0.queue for p in board}
    assert len(origin_len) == cfg.INI_PIECES, "piece_id enumeration not 0..INI_PIECES-1"
    assert sorted(origin_len) == list(range(cfg.INI_PIECES))
    assert s0.queue[-1][-1].piece_id == 0 and s0.queue[-1][-1].board_id == 0, "rightmost ids must be 0"

    discarded_by_pid: dict[int, int] = defaultdict(int)
    rng = random.Random(policy_seed)
    state = s0
    n = cfg.MAX_PIECE_LEN
    steps = 0
    stuck_geometry_steps = 0

    while not state.terminated:
        assert steps < max_steps, "episode did not terminate"
        mask = legal_actions(state, cfg)
        assert any(mask), "deadlock: not terminated but no legal action"

        # Stuck-geometry counter (observational): assemble_legal_mask is all False.
        if not any(assemble_legal_mask(state, cfg)):
            stuck_geometry_steps += 1

        prev = state
        action = policy(rng, cfg, mask, state)
        state, reward = step(prev, cfg, action)

        # Attribute waste to its origin piece_id.
        if reward != 0:
            if action < n:
                discarded_by_pid[prev.queue[-1][-1].piece_id] += -reward
            elif action == n + 3:
                discarded_by_pid[prev.out_piece.piece_id] += -reward
            elif action == n + 4:
                discarded_by_pid[prev.buf_piece.piece_id] += -reward
            else:  # discard_beam
                for p in [p for layer in prev.beam for p in layer]:
                    discarded_by_pid[p.piece_id] += p.length

        _check_state_invariants(state, cfg)

        # Aggregate length conservation.
        locked_in_finished = len(state.finished_beams) * cfg.NUM_LAYERS * cfg.LAYER_LEN
        assert input_total == locked_in_finished + state.discarded_total + _total_length(
            state
        ), "length conservation violated"

        # Waste conservation: discarded_pieces total matches discarded_total.
        assert sum(p.length for p in state.discarded_pieces) == state.discarded_total, (
            "discarded_pieces total != discarded_total"
        )

        # Per-lineage conservation (equality including finished beams).
        finished = _finished_pieces_by_pid(state)
        for pid in origin_len:
            live = _live_by_pid(state).get(pid, 0)
            assert (
                live + finished.get(pid, 0) + discarded_by_pid[pid] == origin_len[pid]
            ), f"lineage {pid}: {live} + {finished.get(pid, 0)} + {discarded_by_pid[pid]} != {origin_len[pid]}"

        steps += 1

    # Termination: queue, out_pos, buf_pos all empty.
    assert not state.queue and state.out_piece is None and state.buf_piece is None

    # No mutation: initial state unchanged.
    assert _total_length(s0) == input_total, "states[0] was mutated by later steps"
    assert s0.queue[-1][-1].length == origin_len[0], "initial saw piece was mutated"

    return steps, state, stuck_geometry_steps


def test_rollouts() -> None:
    for policy_name, policy in POLICIES.items():
        for name, cfg in EXAMPLE_CONFIGS.items():
            for policy_seed in POLICY_SEEDS:
                steps, final, stuck_geo = run_checked_episode(cfg, policy_seed, policy)
                print(
                    f"{policy_name:>8} {name:>14} pol_seed={policy_seed}: {steps:4d} steps, "
                    f"{len(final.finished_beams)} beams, discarded {final.discarded_total}, "
                    f"{stuck_geo} stuck-geometry steps"
                )


def test_action_weights() -> None:
    from mcts.glulam.policy import action_weights

    cfg = EXAMPLE_CONFIGS["small"]
    n = cfg.MAX_PIECE_LEN
    size = n + 6
    pc = PolicyConfig()

    # Cut + put_buf (P_CUT + P_PUT_BUF are the only live groups, renormalized to 1.0).
    mask = [False] * size
    mask[3] = mask[5] = mask[n] = True  # two ordinary cuts + put_buf legal
    asm = [False] * n  # no preferred cuts
    w = action_weights(mask, asm, pc)
    assert abs(sum(w) - 1.0) < 1e-9
    total = pc.P_CUT + pc.P_PUT_BUF
    assert abs(w[n] - pc.P_PUT_BUF / total) < 1e-9
    assert abs(sum(w[:n]) - pc.P_CUT / total) < 1e-9
    assert abs(w[3] - (pc.P_CUT / total) / 2) < 1e-9 and abs(w[5] - (pc.P_CUT / total) / 2) < 1e-9

    # Cuts only, three-way partition: group normalized to 1.0, split
    # P_LONGEST_PREF_CUT / P_REMAINING_PREF_CUTS / the rest.
    mask = [False] * size
    mask[2] = mask[5] = mask[8] = True
    asm = [False] * n
    asm[5] = asm[8] = True  # cut_6 and cut_9 preferred, so cut_9 is the longest preferred
    w = action_weights(mask, asm, pc)
    assert abs(w[8] - pc.P_LONGEST_PREF_CUT) < 1e-9
    assert abs(w[5] - pc.P_REMAINING_PREF_CUTS) < 1e-9
    assert abs(w[2] - (1.0 - pc.P_LONGEST_PREF_CUT - pc.P_REMAINING_PREF_CUTS)) < 1e-9

    # Only one preferred cut: the "other preferred" subgroup is empty, so its mass is
    # renormalized over the non-empty siblings (longest preferred and non-preferred).
    mask = [False] * size
    mask[2] = mask[5] = True
    asm = [False] * n
    asm[5] = True  # cut_6 is the only preferred cut
    w = action_weights(mask, asm, pc)
    live = pc.P_LONGEST_PREF_CUT + (1.0 - pc.P_LONGEST_PREF_CUT - pc.P_REMAINING_PREF_CUTS)
    assert abs(w[5] - pc.P_LONGEST_PREF_CUT / live) < 1e-9
    assert abs(w[2] - (1.0 - pc.P_LONGEST_PREF_CUT - pc.P_REMAINING_PREF_CUTS) / live) < 1e-9

    # Assembles only: group normalized to 1.0; out 0.80, buf 0.20.
    mask = [False] * size
    mask[n + 1] = mask[n + 2] = True
    w = action_weights(mask, [False] * n, pc)
    assert abs(w[n + 1] - 0.80) < 1e-9
    assert abs(w[n + 2] - 0.20) < 1e-9

    # Discard beam alone: normalized to 1.0.
    mask = [False] * size
    mask[n + 5] = True
    w = action_weights(mask, [False] * n, pc)
    assert abs(w[n + 5] - 1.0) < 1e-9


def test_reset_is_deterministic() -> None:
    cfg = EXAMPLE_CONFIGS["small"]
    assert reset(cfg) == reset(cfg)


def test_infeasible_config_raises() -> None:
    cfg = EXAMPLE_CONFIGS["small"]
    bad = EnvConfig(**{**cfg.__dict__, "INI_PIECES": cfg.INI_BOARDS - 1})
    try:
        check_feasibility(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for infeasible config")


if __name__ == "__main__":
    test_reset_is_deterministic()
    test_infeasible_config_raises()
    test_action_weights()
    test_rollouts()
    print("All checks passed.")
