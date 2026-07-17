"""Invariant assertions and spec-completeness rollouts for the glulam env.

Every assertion here is an executable spec clause. Runnable directly
(``uv run python -m mcts.glulam.test_env``) or via pytest.
"""

from __future__ import annotations

import random
from collections import defaultdict

from mcts.glulam.configs import EXAMPLE_CONFIGS
from mcts.glulam.env import (
    EnvConfig,
    GlulamState,
    check_feasibility,
    current_layer_len,
    legal_actions,
    reset,
    step,
)
from mcts.glulam.policy import action_weights, uniform_policy, weighted_policy

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


def _check_state_invariants(state: GlulamState, cfg: EnvConfig) -> None:
    cll = current_layer_len(state)
    assert 0 <= cll <= cfg.LAYER_LEN, "layer overfilled"
    left = cfg.LAYER_LEN - cll
    assert not (0 < left < cfg.MIN_PIECE_LEN), "unfillable layer gap"
    for board in state.queue:
        assert board, "empty board not dropped"
        for p in board:
            assert p.length >= cfg.MIN_PIECE_LEN, "queue piece below MIN_PIECE_LEN"
    for layer in state.beam[: state.current_layer]:
        assert sum(p.length for p in layer) == cfg.LAYER_LEN, "completed layer not exactly full"


def run_checked_episode(
    cfg: EnvConfig, policy_seed: int, policy=weighted_policy, max_steps: int = 100_000
) -> tuple[int, GlulamState]:
    """Roll out a policy, asserting all invariants at every step."""
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

    while not state.terminated:
        assert steps < max_steps, "episode did not terminate"
        mask = legal_actions(state, cfg)
        assert any(mask), "deadlock: not terminated but no legal action"
        action = policy(rng, cfg, mask)
        prev = state
        state, reward = step(prev, cfg, action)

        # Attribute waste to its origin piece_id.
        if reward != 0:
            if action <= n:  # cut waste: sub-MIN remainder of the saw piece
                pid = prev.queue[-1][-1].piece_id
            elif action == n + 4:
                pid = prev.out_piece.piece_id
            else:
                assert action == n + 5
                pid = prev.buf_piece.piece_id
            discarded_by_pid[pid] += -reward

        _check_state_invariants(state, cfg)

        # Aggregate length conservation.
        locked_in_finished = state.finished_beams * cfg.NUM_LAYERS * cfg.LAYER_LEN
        assert input_total == locked_in_finished + state.discarded_total + _total_length(state), (
            "length conservation violated"
        )

        # Per-lineage conservation (locked fragments vanish, hence <=).
        for pid, live in _live_by_pid(state).items():
            assert live + discarded_by_pid[pid] <= origin_len[pid], "lineage exceeds origin length"

        steps += 1

    # Termination: queue, out_pos, buf_pos all empty.
    assert not state.queue and state.out_piece is None and state.buf_piece is None

    # No mutation: the initial state must be unchanged after the full rollout.
    assert _total_length(s0) == input_total, "states[0] was mutated by later steps"
    assert s0.queue[-1][-1].length == origin_len[0], "initial saw piece was mutated"

    return steps, state


def test_rollouts() -> None:
    for policy_name, policy in POLICIES.items():
        for name, cfg in EXAMPLE_CONFIGS.items():
            for policy_seed in POLICY_SEEDS:
                steps, final = run_checked_episode(cfg, policy_seed, policy)
                print(
                    f"{policy_name:>8} {name:>14} pol_seed={policy_seed}: {steps:4d} steps, "
                    f"{final.finished_beams} beams, discarded {final.discarded_total}"
                )


def test_action_weights() -> None:
    cfg = EXAMPLE_CONFIGS["small"]
    n = cfg.MAX_PIECE_LEN
    size = n + 6

    # cut_layer_finish legal alongside two ordinary cuts: 0.70 + 2 x 0.15.
    mask = [False] * size
    mask[2] = mask[5] = mask[n] = True
    w = action_weights(cfg, mask)
    assert abs(sum(w) - 1.0) < 1e-9
    assert abs(w[n] - 0.70) < 1e-9
    assert abs(w[2] - 0.15) < 1e-9 and abs(w[5] - 0.15) < 1e-9
    assert all(w[i] == 0.0 for i in range(size) if not mask[i])

    # Discards + put_buf: 0.05 each, put_buf takes the remaining 0.90.
    mask = [False] * size
    mask[n + 1] = mask[n + 4] = mask[n + 5] = True
    w = action_weights(cfg, mask)
    assert abs(w[n + 4] - 0.05) < 1e-9 and abs(w[n + 5] - 0.05) < 1e-9
    assert abs(w[n + 1] - 0.90) < 1e-9

    # Forced discard (only special actions legal): normalized to 50/50.
    mask = [False] * size
    mask[n + 4] = mask[n + 5] = True
    w = action_weights(cfg, mask)
    assert abs(w[n + 4] - 0.5) < 1e-9 and abs(w[n + 5] - 0.5) < 1e-9


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
