"""Random policies over the legal-action mask, plus a rollout helper."""

from __future__ import annotations

import random
from typing import Callable

from mcts.glulam.env import EnvConfig, GlulamState, legal_actions, reset, step

# A policy maps (rng, cfg, legal-action mask) to a legal action index.
Policy = Callable[[random.Random, EnvConfig, list[bool]], int]

P_CUT_LAYER_FINISH = 0.70
P_DISCARD = 0.05


def random_action(rng: random.Random, mask: list[bool]) -> int:
    """Uniform choice among legal actions. Note: cut_layer_finish overlaps a
    specific cut_k, so that cut length is slightly double-weighted; harmless
    for a random baseline."""
    legal = [i for i, m in enumerate(mask) if m]
    if not legal:
        raise ValueError("No legal action (terminated state?)")
    return rng.choice(legal)


def uniform_policy(rng: random.Random, cfg: EnvConfig, mask: list[bool]) -> int:
    return random_action(rng, mask)


def action_weights(
    cfg: EnvConfig,
    mask: list[bool],
    p_cut_layer_finish: float = P_CUT_LAYER_FINISH,
    p_discard: float = P_DISCARD,
) -> list[float]:
    """Per-action probabilities for the weighted random policy.

    Special actions get a reserved probability *if legal*: cut_layer_finish
    ``p_cut_layer_finish``, each discard ``p_discard``. The remaining mass is
    spread uniformly over the other legal actions. If a special action is
    illegal, its reserved mass flows into that rest pool; if only special
    actions are legal, their reserved weights are normalized instead.
    """
    n = cfg.MAX_PIECE_LEN
    special = {n: p_cut_layer_finish, n + 4: p_discard, n + 5: p_discard}
    legal = [i for i, m in enumerate(mask) if m]
    if not legal:
        raise ValueError("No legal action (terminated state?)")

    specials_present = [i for i in legal if i in special]
    rest = [i for i in legal if i not in special]
    special_mass = sum(special[i] for i in specials_present)

    weights = [0.0] * len(mask)
    if rest:
        for i in specials_present:
            weights[i] = special[i]
        for i in rest:
            weights[i] = (1.0 - special_mass) / len(rest)
    else:  # only special actions are legal: normalize their reserved weights
        for i in specials_present:
            weights[i] = special[i] / special_mass
    return weights


def weighted_policy(rng: random.Random, cfg: EnvConfig, mask: list[bool]) -> int:
    weights = action_weights(cfg, mask)
    return rng.choices(range(len(mask)), weights=weights, k=1)[0]


def run_episode(
    cfg: EnvConfig,
    policy_seed: int,
    policy: Policy = weighted_policy,
    max_steps: int = 100_000,
) -> tuple[list[GlulamState], list[int], list[int]]:
    """Roll out a policy to termination.

    Returns (states, actions, rewards) with len(states) == len(actions) + 1.
    """
    rng = random.Random(policy_seed)
    state = reset(cfg)
    states, actions, rewards = [state], [], []
    while not state.terminated:
        if len(actions) >= max_steps:
            raise RuntimeError(f"Episode exceeded {max_steps} steps")
        action = policy(rng, cfg, legal_actions(state, cfg))
        state, reward = step(state, cfg, action)
        states.append(state)
        actions.append(action)
        rewards.append(reward)
    return states, actions, rewards
