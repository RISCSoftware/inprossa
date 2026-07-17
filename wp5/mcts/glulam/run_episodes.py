"""Run random-policy episodes and save each as a set of PNG frames plus a GIF.

Usage:
    uv run python -m mcts.glulam.run_episodes

For every planned config (set of constants) and every policy seed, one episode
is rolled out (the input data is fixed by the config's env seed, so the same
instance is replayed with different random policies). Each episode's frames go
into its own directory under logs/glulam/, together with an animated
episode.gif showing all steps (seconds per step configurable per episode).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from mcts.glulam.configs import EXAMPLE_CONFIGS
from mcts.glulam.env import EnvConfig, action_name, current_layer_left
from mcts.glulam.policy import run_episode, weighted_policy
from mcts.glulam.visualization import VizConfig, compute_layout, render

OUT_ROOT = Path("logs/glulam/weighted")  # weighted random policy runs

# (config name, policy seeds, seconds per step in the GIF, PNG dpi).
# Smaller episodes get 0.5 s per step, the larger ones 0.2 s.
EPISODE_PLAN: list[tuple[str, list[int], float, int]] = [
    ("small", [0, 1, 2], 0.5, 110),
    ("medium", [0, 1, 2], 0.5, 110),
    ("narrow_window", [0, 1, 2], 0.5, 110),
    ("large_50", [0, 1, 2], 0.2, 100),
    ("xlarge_200", [0], 0.2, 90),  # ~2000 steps; one policy seed keeps output manageable
]


def _figsize(layout) -> tuple[float, float]:
    """Aspect-preserving figure size with a 14-inch cap on the larger dimension."""
    x_span = layout.xlim[1] - layout.xlim[0]
    y_span = layout.ylim[1] - layout.ylim[0]
    ratio = y_span / x_span
    if ratio <= 1.0:
        return 14.0, max(2.0, 14.0 * ratio + 0.6)
    return max(4.0, 14.0 / ratio), 14.0


def _write_gif(gif_path: Path, frame_paths: list[Path], frame_seconds: float, max_px: int = 900) -> None:
    """Assemble the saved PNG frames into an animated GIF (downscaled)."""

    def load(path: Path) -> Image.Image:
        img = Image.open(path)
        img.thumbnail((max_px, max_px), Image.LANCZOS)
        return img.convert("P", palette=Image.ADAPTIVE)

    first = load(frame_paths[0])
    rest = (load(p) for p in frame_paths[1:])  # lazy: keeps memory flat for long episodes
    first.save(
        gif_path,
        save_all=True,
        append_images=rest,
        duration=int(frame_seconds * 1000),
        loop=0,
    )


def save_episode(
    name: str,
    cfg: EnvConfig,
    policy_seed: int,
    frame_seconds: float = 0.5,
    dpi: int = 110,
    out_root: Path = OUT_ROOT,
) -> Path:
    states, actions, rewards = run_episode(cfg, policy_seed, policy=weighted_policy)
    layout = compute_layout(states[0], cfg)
    viz = VizConfig()

    ep_dir = out_root / f"{name}_env{cfg.seed}_pol{policy_seed}"
    ep_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=_figsize(layout))
    frame_paths = []
    for t, state in enumerate(states):
        if t == 0:
            head = "reset"
        else:
            head = f"{action_name(cfg, actions[t - 1])}  r={rewards[t - 1]}"
        title = (
            f"{name} pol_seed={policy_seed}  step {t}/{len(actions)}  {head}  |  "
            f"layer {state.current_layer} left {current_layer_left(state, cfg)}  |  "
            f"beams {state.finished_beams}  discarded {state.discarded_total}"
        )
        ax.clear()
        render(ax, state, cfg, layout, viz, title=title)
        frame_path = ep_dir / f"frame_{t:04d}.png"
        fig.savefig(frame_path, dpi=dpi, bbox_inches="tight")
        frame_paths.append(frame_path)
    plt.close(fig)

    _write_gif(ep_dir / "episode.gif", frame_paths, frame_seconds)

    total_reward = sum(rewards)
    print(
        f"{ep_dir}: {len(states)} frames + episode.gif ({frame_seconds} s/step), "
        f"{states[-1].finished_beams} beams, discarded {states[-1].discarded_total}, "
        f"return {total_reward}",
        flush=True,
    )
    return ep_dir


def main() -> None:
    for name, policy_seeds, frame_seconds, dpi in EPISODE_PLAN:
        cfg = EXAMPLE_CONFIGS[name]
        for policy_seed in policy_seeds:
            save_episode(name, cfg, policy_seed, frame_seconds=frame_seconds, dpi=dpi)


if __name__ == "__main__":
    main()
