"""
Training entry point for Bin-Packing AlphaZero (ptree).

Usage:
    python -m bin_packing_mcts.entry.train_alphazero [--seed SEED] [--max-env-step N]

Switch to ctree for faster training by passing --ctree on the command line,
or by setting mcts_ctree=True / alphazero_mcts_ctree=True in the config.

Observation note:
    AlphaZero's ResNet model requires a (C, H, W) observation shape.
    The bin-packing env (or a wrapper) must reshape its flat (2*max_items,)
    output to (1, 2, max_items) before returning from step() / reset().
    See bin_packing_alphazero_config.py for the expected layout.
"""

import argparse

from lzero.entry import train_alphazero

from bin_packing_mcts.config.bin_packing_alphazero_config import (
    main_config,
    create_config,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train BinPacking with AlphaZero")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument(
        "--max-env-step",
        type=int,
        default=int(2e5),
        help="Maximum environment steps for training",
    )
    parser.add_argument(
        "--ctree",
        action="store_true",
        help="Use the fast C++ MCTS backend (ctree) instead of pure-Python (ptree)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    cfg = main_config
    create_cfg = create_config

    if args.ctree:
        cfg.policy.mcts_ctree = True
        cfg.env.alphazero_mcts_ctree = True

    train_alphazero(
        [cfg, create_cfg],
        seed=args.seed,
        max_env_step=args.max_env_step,
    )


if __name__ == "__main__":
    main()
