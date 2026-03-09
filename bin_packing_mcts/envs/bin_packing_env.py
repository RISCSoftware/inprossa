"""
1D Bin-Packing environment for LightZero (MuZero / ptree backend).

Ground-truth state:
    _assignment : int32 array, shape (n_items,)
                  _assignment[i] = stable bin id (≥ 0) once item i is placed,
                  -1 while unplaced.
    _bin_caps   : float32 array, shape (max_items,)
                  Remaining capacity indexed by stable bin id (unsorted).
                  Unused slots (index >= _n_bins) hold 1.0.
    _bin_idx    : int32 array, shape (_n_bins,)
                  _bin_idx[j] = stable bin id at sorted-descending position j.
                  Kept up-to-date after every step.
    _n_bins     : number of bins opened so far.
    _step       : index of the next item to place.

Observation (dict):
    'bins'        : float32 array (max_items,) — remaining capacities of open
                    bins sorted **descending**, zero-padded on the right.
    'items'       : float32 array (max_items,) — sizes of unplaced items
                    sorted **descending**, zero-padded on the right.
    'action_mask' : int8 array (max_items,) — 1 = legal, 0 = illegal.
    'to_play'     : -1 (single-player).

Action (int, 0 … max_items-1):
    0 … n_bins-1 → place next item in the bin at sorted-descending position i.
    n_bins        → open a fresh bin for the next item.
    All other indices are illegal; the action_mask enforces this.

Reward:
    0.0 at every non-terminal step.
    -n_bins (float) at the terminal step.
    Maximising return ↔ minimising the number of bins used.
"""

from typing import Dict, Optional

import gymnasium as gym
import numpy as np
from ding.envs import BaseEnvTimestep
from ding.utils import ENV_REGISTRY
from easydict import EasyDict
from gymnasium import spaces


@ENV_REGISTRY.register("bin_packing")
class BinPackingEnv(gym.Env):
    """1D Bin-Packing environment compatible with LightZero's MuZero pipeline."""

    # Default configuration — will be overridden by cfg passed to __init__
    config = dict(
        env_id="bin_packing",
        max_items=10,  # upper bound on items per episode (fixes obs / action dim)
        min_items=3,  # lower bound on items per episode
        max_item_size=0.9,  # item sizes are in [min_item_size, max_item_size]
        min_item_size=0.1,
    )

    _CAP_TOL: float = 1e-9  # tolerance for capacity-fit comparisons

    def __init__(self, cfg: EasyDict) -> None:
        self._cfg = EasyDict(self.config)
        self._cfg.update(cfg)

        self.max_items: int = int(self._cfg.max_items)
        self.min_items: int = int(self._cfg.min_items)
        self.max_item_size: float = float(self._cfg.max_item_size)
        self.min_item_size: float = float(self._cfg.min_item_size)

        self.observation_space = spaces.Dict(
            {
                "bins": spaces.Box(low=0.0, high=1.0, shape=(self.max_items,), dtype=np.float32),
                "items": spaces.Box(low=0.0, high=1.0, shape=(self.max_items,), dtype=np.float32),
            }
        )
        self.action_space = spaces.Discrete(self.max_items)
        self.reward_space = spaces.Box(low=float(-self.max_items), high=0.0, shape=(1,), dtype=np.float32)

        self._rng = np.random.RandomState()
        self._initialized = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def create_collector_env_cfg(cfg: dict) -> list:
        collector_env_num = cfg.pop('collector_env_num')
        return [cfg for _ in range(collector_env_num)]

    @staticmethod
    def create_evaluator_env_cfg(cfg: dict) -> list:
        evaluator_env_num = cfg.pop('evaluator_env_num')
        return [cfg for _ in range(evaluator_env_num)]

    def seed(self, seed: Optional[int] = None, seed1: Optional[int] = None) -> None:
        self._rng = np.random.RandomState(seed)

    def reset(self) -> Dict:
        """Sample a new problem instance and return the initial observation."""
        n = int(self._rng.randint(self.min_items, self.max_items + 1))
        sizes = self._rng.uniform(self.min_item_size, self.max_item_size, size=n)
        # Items are placed in descending order (largest first).
        self._items: np.ndarray = np.sort(sizes)[::-1].astype(np.float32)
        self._n_items: int = n

        # Ground-truth assignment: _assignment[i] = stable bin id, or -1 if unplaced.
        self._assignment: np.ndarray = np.full(n, -1, dtype=np.int32)

        # Remaining capacities indexed by stable bin id (unsorted); unused slots = 1.0.
        self._bin_caps: np.ndarray = np.ones(self.max_items, dtype=np.float32)
        # Sorted-descending index: _bin_idx[j] = stable bin id at position j.
        self._bin_idx: np.ndarray = np.empty(0, dtype=np.int32)
        self._n_bins: int = 0  # number of bins opened so far
        self._step: int = 0  # index of the next item to place

        self._initialized = True
        return self._obs()

    def step(self, action: int) -> BaseEnvTimestep:
        assert self._initialized, "Call reset() before step()."
        action = int(action)

        mask = self._make_mask()
        assert mask[action] == 1, (
            f"Illegal action {action}. Legal mask: {mask.tolist()}. "
            f"n_bins={self._n_bins}, next_item={self._items[self._step]:.3f}"
        )

        item_size = float(self._items[self._step])

        if action == self._n_bins:
            # Open a new bin.
            bin_id = self._n_bins
            self._n_bins += 1
        else:
            bin_id = int(self._bin_idx[action])
        self._bin_caps[bin_id] -= item_size
        # Keep _bin_idx up-to-date (argsort descending of open-bin capacities).
        self._bin_idx = np.argsort(self._bin_caps[: self._n_bins])[::-1]

        # Record stable bin id.
        self._assignment[self._step] = bin_id

        self._step += 1
        done = self._step == self._n_items

        reward = float(-self._n_bins) if done else 0.0

        obs = self._obs()
        info: Dict = {"n_bins": self._n_bins, "step": self._step}
        if done:
            info["eval_episode_return"] = reward
            info["assignment"] = self._assignment.copy()

        return BaseEnvTimestep(
            obs,
            np.array([reward], dtype=np.float32),
            done,
            info,
        )

    def render(self, mode: Optional[str] = None) -> None:
        print(
            f"[BinPacking] step={self._step}/{self._n_items}  "
            f"n_bins={self._n_bins}  "
            f"bin_caps={self._bin_caps[:self._n_bins].tolist()}  "
            f"remaining_items={self._items[self._step:].tolist()}  "
            f"assignment={self._assignment.tolist()}"
        )

    def close(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_mask(self) -> np.ndarray:
        """Binary action mask: 1 = legal, 0 = illegal."""
        mask = np.zeros(self.max_items, dtype=np.int8)
        if self._step >= self._n_items:
            return mask

        item_size = float(self._items[self._step])

        # Existing bins via sorted index.
        fits = self._bin_caps[self._bin_idx] >= item_size - self._CAP_TOL
        mask[: self._n_bins] = fits.astype(np.int8)

        # Open a new bin (always legal since max_item_size < 1.0).
        if self._n_bins < self.max_items:
            mask[self._n_bins] = 1

        return mask

    def _obs(self) -> Dict:
        """Build the observation dict required by LightZero."""
        # bins: capacities in sorted-descending order via _bin_idx; unused slots are 1.0.
        bins_vec = np.ones(self.max_items, dtype=np.float32)
        if self._n_bins > 0:
            bins_vec[: self._n_bins] = self._bin_caps[self._bin_idx]

        # items: remaining item sizes sorted descending, zero-padded.
        items_vec = np.zeros(self.max_items, dtype=np.float32)
        n_remaining = self._n_items - self._step
        if n_remaining > 0:
            items_vec[:n_remaining] = self._items[self._step : self._step + n_remaining]

        return {
            "bins": bins_vec,  # shape (max_items,)
            "items": items_vec,  # shape (max_items,)
            "action_mask": self._make_mask(),  # shape (max_items,)
            "to_play": -1,  # single-player: always -1
        }
