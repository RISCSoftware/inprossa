import argparse
import json
import os
from datetime import timedelta
from enum import Enum

from src import DSLSolver


class TimedeltaEncoder(json.JSONEncoder):
    """Custom JSON encoder for MiniZinc result objects."""

    def default(self, o):
        if isinstance(o, timedelta):
            return o.total_seconds()
        if isinstance(o, Enum):
            return o.name
        if callable(o):
            return str(o)
        return super().default(o)


def main():
    parser = argparse.ArgumentParser(
        description="Run OptDSL model with MiniZinc backend."
    )
    parser.add_argument("filepath", help="Path to OptDSL file")
    parser.add_argument(
        "--dsl-index-base",
        type=int,
        choices=[0, 1],
        default=0,
        help="Index base used in DSL source code: 0 (Python style) or 1 (legacy mode)",
    )
    parser.add_argument(
        "--solver",
        default="gecode",  # "cp-sat",
        help="MiniZinc solver name (e.g. chuffed, cp-sat, gecode)",
    )
    parser.add_argument(
        "--timelimit",
        type=float,
        default=100.0,
        help="Solver time limit in seconds",
    )
    parser.add_argument(
        "--minizinc-path",
        default=None,
        help=(
            "Path to a custom MiniZinc executable (or its bin directory, e.g. "
            "`minizinc/MiniZincIDE-2.10.1-x86_64-linux-gnu/bin`). When given, "
            "this MiniZinc is used to check/solve the model instead of the "
            "default `minizinc` on PATH."
        ),
    )
    parser.add_argument(
        "--dump-mzn",
        nargs="?",
        const="",
        default=None,
        metavar="OUTPUT",
        help=(
            "Translate the DSL to MiniZinc and write it to OUTPUT "
            "(default: same basename with .mzn next to the .dsl); do not solve."
        ),
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print solver progress (each new intermediate objective, plus a heartbeat while solving).",
    )
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=5.0,
        help="Minimum seconds between progress lines (only with --progress).",
    )
    args = parser.parse_args()

    filepath = args.filepath
    with open(filepath, "r", encoding="utf-8") as f:
        dsl_code = f.read()

    solver = DSLSolver(
        dsl_code,
        solver_name=args.solver,
        timelimit=args.timelimit,
        dsl_index_base=args.dsl_index_base,
        minizinc_executable=args.minizinc_path,
        progress=args.progress,
        progress_interval=args.progress_interval,
    )

    if args.dump_mzn is not None:
        # Only translate: write the model, do not invoke MiniZinc.
        model = solver.translate()
        out_path = (
            args.dump_mzn if args.dump_mzn else os.path.splitext(filepath)[0] + ".mzn"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(model)
        print(f"Wrote MiniZinc model to {out_path}")
        return

    result = solver.run()
    print(json.dumps(result, cls=TimedeltaEncoder))


if __name__ == "__main__":
    main()
