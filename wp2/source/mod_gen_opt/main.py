import argparse
import sys
from src import DSLSolver

def main():
    parser = argparse.ArgumentParser(description="Run OptDSL model with MiniZinc backend.")
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
        default="chuffed",
        help="MiniZinc solver name (e.g. chuffed, cp-sat, gecode)",
    )
    parser.add_argument(
        "--timelimit",
        type=float,
        default=10.0,
        help="Solver time limit in seconds",
    )
    args = parser.parse_args()

    filepath = args.filepath
    with open(filepath, "r") as f:
        dsl_code = f.read()

    solver = DSLSolver(
        dsl_code,
        solver_name=args.solver,
        timelimit=args.timelimit,
        dsl_index_base=args.dsl_index_base,
    )
    result = solver.run()
    print(result)


if __name__ == "__main__":
    main()
