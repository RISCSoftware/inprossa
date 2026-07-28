"""Weighted random policies over the legal-action mask, plus a rollout helper."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from mcts.glulam.env import EnvConfig, GlulamState, legal_actions, reset, step

P_CUT = 0.64
P_LONGEST_PREF_CUT = 0.80
P_REMAINING_PREF_CUTS = 0.15
P_ASSEMBLE = 0.30
P_ASSEMBLE_OUT = 0.80
P_DISCARD_PIECE = 0.009
P_DISCARD_OUT = 0.25
P_DISCARD_BEAM = 0.001
P_PUT_BUF = 0.05


@dataclass(frozen=True)
class PolicyConfig:
    """Configurable weights for the weighted random policy."""

    P_CUT: float = P_CUT
    P_LONGEST_PREF_CUT: float = P_LONGEST_PREF_CUT
    P_REMAINING_PREF_CUTS: float = P_REMAINING_PREF_CUTS
    P_ASSEMBLE: float = P_ASSEMBLE
    P_ASSEMBLE_OUT: float = P_ASSEMBLE_OUT
    P_DISCARD_PIECE: float = P_DISCARD_PIECE
    P_DISCARD_OUT: float = P_DISCARD_OUT
    P_DISCARD_BEAM: float = P_DISCARD_BEAM
    P_PUT_BUF: float = P_PUT_BUF


def random_action(rng: random.Random, mask: list[bool]) -> int:
    """Uniform choice among legal actions."""
    legal = [i for i, m in enumerate(mask) if m]
    if not legal:
        raise ValueError("No legal action (terminated state?)")
    return rng.choice(legal)


def uniform_policy(rng: random.Random, cfg: EnvConfig, mask: list[bool], state: GlulamState | None = None) -> int:
    """Uniform choice among legal actions. The `state` arg is accepted for signature
    compatibility with `weighted_policy` but not used."""
    return random_action(rng, mask)


def action_weights(mask: list[bool], assemble_legal_mask: list[bool], pc: PolicyConfig) -> list[float]:
    """Per-action probabilities per the spec's weighted random policy.

    Groups: Cut (P_CUT), Put buffer (P_PUT_BUF), Assemble (P_ASSEMBLE),
    Discard piece (P_DISCARD_PIECE), Discard beam (P_DISCARD_BEAM).
    Cut mass splits three ways over a partition of the legal cuts: the single longest
    preferred cut (P_LONGEST_PREF_CUT), the other preferred cuts (P_REMAINING_PREF_CUTS),
    and the non-preferred ones (the rest), where "preferred" means flagged in
    assemble_legal_mask. Assemble mass splits between assemble_out and assemble_buf.
    Discard-piece mass splits between discard_out and discard_buf. Discard beam is a
    single-member group.
    Fallback: an empty subgroup's mass is renormalized among its non-empty siblings; an
    empty group's mass among the remaining non-empty groups.
    """
    n = len(mask) - 6  # MAX_PIECE_LEN
    legal = [i for i, m in enumerate(mask) if m]
    if not legal:
        raise ValueError("No legal action (terminated state?)")

    # Index groups. Action i is cut_(i+1), and assemble_legal_mask[i] flags length i+1, so the
    # longest preferred cut is the largest flagged index.
    legal_cuts = [i for i in legal if i < n]
    preferred_cuts = [i for i in legal_cuts if assemble_legal_mask[i]] if assemble_legal_mask else []
    longest_pref_cut = preferred_cuts[-1:]  # legal_cuts is ascending, so the last is the longest
    other_pref_cuts = preferred_cuts[:-1]
    non_pref_cuts = [i for i in legal_cuts if i not in set(preferred_cuts)]

    group_weights = {}
    if pc.P_CUT > 0 and legal_cuts:
        group_weights["cut"] = pc.P_CUT
    if pc.P_PUT_BUF > 0 and n in legal:
        group_weights["put_buf"] = pc.P_PUT_BUF
    if pc.P_ASSEMBLE > 0 and any(i in legal for i in (n + 1, n + 2)):
        group_weights["assemble"] = pc.P_ASSEMBLE
    if pc.P_DISCARD_PIECE > 0 and any(i in legal for i in (n + 3, n + 4)):
        group_weights["discard_piece"] = pc.P_DISCARD_PIECE
    if pc.P_DISCARD_BEAM > 0 and n + 5 in legal:
        group_weights["discard_beam"] = pc.P_DISCARD_BEAM

    # Normalize group weights.
    total = sum(group_weights.values())
    if total == 0:
        return uniform_weights(mask)
    for g in group_weights:
        group_weights[g] /= total

    weights = [0.0] * len(mask)

    def _spread(mass: float, subgroups: list[tuple[float, list[int]]]) -> None:
        """Split mass over (weight, actions) subgroups, uniformly within each subgroup.

        Empty subgroups drop out and the weights of the non-empty ones are renormalized, so
        their mass flows to the siblings — with two subgroups that is the spec's "flows to the
        sibling subgroup". If every subgroup with a positive weight is empty, the mass is spread
        uniformly over whatever actions the group does have.
        """
        live = [(w, acts) for w, acts in subgroups if acts and w > 0]
        total_w = sum(w for w, _ in live)
        if total_w <= 0:
            live = [(1.0, [a for _, acts in subgroups for a in acts])]
            total_w = 1.0
        for w, acts in live:
            if not acts:
                continue
            share = mass * w / total_w
            for a in acts:
                weights[a] = share / len(acts)

    # Cut: longest preferred, other preferred, non-preferred.
    if "cut" in group_weights:
        _spread(
            group_weights["cut"],
            [
                (pc.P_LONGEST_PREF_CUT, longest_pref_cut),
                (pc.P_REMAINING_PREF_CUTS, other_pref_cuts),
                (1.0 - pc.P_LONGEST_PREF_CUT - pc.P_REMAINING_PREF_CUTS, non_pref_cuts),
            ],
        )

    # Put buffer.
    if "put_buf" in group_weights:
        weights[n] = group_weights["put_buf"]

    # Assemble: out vs buf.
    if "assemble" in group_weights:
        _spread(
            group_weights["assemble"],
            [
                (pc.P_ASSEMBLE_OUT, [n + 1] if n + 1 in legal else []),
                (1.0 - pc.P_ASSEMBLE_OUT, [n + 2] if n + 2 in legal else []),
            ],
        )

    # Discard piece: out vs buf.
    if "discard_piece" in group_weights:
        _spread(
            group_weights["discard_piece"],
            [
                (pc.P_DISCARD_OUT, [n + 3] if n + 3 in legal else []),
                (1.0 - pc.P_DISCARD_OUT, [n + 4] if n + 4 in legal else []),
            ],
        )

    # Discard beam.
    if "discard_beam" in group_weights:
        weights[n + 5] = group_weights["discard_beam"]

    return weights


def uniform_weights(mask: list[bool]) -> list[float]:
    legal = [i for i, m in enumerate(mask) if m]
    w = [0.0] * len(mask)
    for i in legal:
        w[i] = 1.0 / len(legal)
    return w


def weighted_policy(rng: random.Random, cfg: EnvConfig, mask: list[bool], state: GlulamState) -> int:
    """Sample an action per the weighted policy (default PolicyConfig)."""
    from mcts.glulam.env import assemble_legal_mask

    weights = action_weights(mask, assemble_legal_mask(state, cfg), PolicyConfig())
    return rng.choices(range(len(mask)), weights=weights, k=1)[0]


def weighted_policy_with_config(
    pc: PolicyConfig,
) -> Callable[[random.Random, EnvConfig, list[bool], GlulamState], int]:
    """Return a weighted policy with a custom PolicyConfig."""

    def _policy(rng: random.Random, cfg: EnvConfig, mask: list[bool], state: GlulamState) -> int:
        from mcts.glulam.env import assemble_legal_mask

        weights = action_weights(mask, assemble_legal_mask(state, cfg), pc)
        return rng.choices(range(len(mask)), weights=weights, k=1)[0]

    return _policy


def run_episode(
    cfg: EnvConfig,
    policy_seed: int,
    policy: Callable[[random.Random, EnvConfig, list[bool], GlulamState], int] = weighted_policy,
    policy_config: PolicyConfig | None = None,
    max_steps: int = 100_000,
) -> tuple[list[GlulamState], list[int], list[int], int]:
    """Roll out a policy to termination.

    Returns (states, actions, rewards, stuck_progress_steps) with len(states) == len(actions) + 1.
    ``stuck_progress_steps`` counts steps where neither assemble_out nor assemble_buf was legal
    (the beam could not make progress) — accumulated from the masks already computed
    for the policy, with no extra DP passes.
    If ``policy_config`` is provided and ``policy`` is ``weighted_policy``, a weighted
    policy with that config is used instead.
    """
    if policy_config is not None and policy is weighted_policy:
        policy = weighted_policy_with_config(policy_config)
    n = cfg.MAX_PIECE_LEN
    rng = random.Random(policy_seed)
    state = reset(cfg)
    states, actions, rewards = [state], [], []
    stuck_progress_steps = 0
    while not state.terminated:
        if len(actions) >= max_steps:
            raise RuntimeError(f"Episode exceeded {max_steps} steps")
        mask = legal_actions(state, cfg)
        if not (mask[n + 1] or mask[n + 2]):
            stuck_progress_steps += 1
        action = policy(rng, cfg, mask, state)
        state, reward = step(state, cfg, action)
        states.append(state)
        actions.append(action)
        rewards.append(reward)
    return states, actions, rewards, stuck_progress_steps
