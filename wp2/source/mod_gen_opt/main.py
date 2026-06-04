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
    args = parser.parse_args()

    filepath = args.filepath
    with open(filepath, "r") as f:
        dsl_code = f.read()

    solver = DSLSolver(
        dsl_code,
        solver_name="chuffed",
        timelimit=10,
        dsl_index_base=args.dsl_index_base,
    )
    result = solver.run()
    print(result)


if __name__ == "__main__":
    main()
