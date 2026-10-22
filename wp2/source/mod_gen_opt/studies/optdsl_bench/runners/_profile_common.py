from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProblemProfile:
    name: str
    initializer: str
    operator_profile: str = "generic"
    default_max_iterations: int = 3000
    default_log_every: int = 100
    extra_args: list[str] = field(default_factory=list)


def _mod_gen_opt_root() -> Path:
    # .../mod_gen_opt/studies/optdsl_bench/runners -> .../mod_gen_opt
    return Path(__file__).resolve().parents[3]


def build_command(profile: ProblemProfile, args: argparse.Namespace, passthrough: list[str]) -> list[str]:
    root = _mod_gen_opt_root()
    dsl_path = Path(args.dsl_file).expanduser().resolve()
    command: list[str] = [
        sys.executable,
        str(root / "example_lns.py"),
        str(dsl_path),
        "--initializer",
        profile.initializer,
        "--operator-profile",
        profile.operator_profile,
        "--max-iterations",
        str(args.max_iterations),
        "--random-seed",
        str(args.random_seed),
        "--log-every",
        str(args.log_every),
    ]

    if getattr(args, "max_runtime_seconds", None) is not None:
        command.extend(["--max-runtime-seconds", str(args.max_runtime_seconds)])
    if getattr(args, "no_improvement_iterations", None) is not None:
        command.extend(["--no-improvement-iterations", str(args.no_improvement_iterations)])

    command.extend(profile.extra_args)

    for extra in args.extra_arg:
        command.extend(shlex.split(extra))

    command.extend(passthrough)
    return command


def run_profile(profile: ProblemProfile) -> int:
    parser = argparse.ArgumentParser(
        description=(
            f"Run class-specific LNS profile '{profile.name}' with defaults and optional overrides."
        )
    )
    parser.add_argument("dsl_file", help="Path to an OptDSL instance file")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=profile.default_max_iterations,
        help="Maximum LNS iterations",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed passed to example_lns.py",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=profile.default_log_every,
        help="Logging interval passed to example_lns.py",
    )
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help=(
            "Additional argument string appended to example_lns.py, "
            "for example: --extra-arg \"--lns-run-restarts 5\""
        ),
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=None,
        help="Wall-clock time limit for LNS in seconds (default: no limit)",
    )
    parser.add_argument(
        "--no-improvement-iterations",
        type=int,
        default=None,
        help="Stop LNS early after this many consecutive non-improving iterations (default: no convergence stop)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved command without executing it",
    )

    args, passthrough = parser.parse_known_args()
    dsl_path = Path(args.dsl_file).expanduser().resolve()
    if not dsl_path.exists():
        raise FileNotFoundError(f"DSL file does not exist: {dsl_path}")

    args.dsl_file = str(dsl_path)
    command = build_command(profile, args, passthrough)

    print(f"[profile] {profile.name}")
    print("[command] " + " ".join(shlex.quote(part) for part in command))

    if args.dry_run:
        return 0

    completed = subprocess.run(command, cwd=_mod_gen_opt_root(), check=False)
    return int(completed.returncode)
