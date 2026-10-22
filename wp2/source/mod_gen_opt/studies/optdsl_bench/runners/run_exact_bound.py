from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _mod_gen_opt_root() -> Path:
    # .../mod_gen_opt/studies/optdsl_bench/runners -> .../mod_gen_opt
    return Path(__file__).resolve().parents[3]


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _extract_bounds(payload: dict[str, Any]) -> tuple[float | None, float | None, str]:
    objective_bound = _safe_float(payload.get("objective_bound"))
    objective_value = _safe_float(payload.get("objective"))

    objectives = payload.get("objectives")
    if objective_value is None and isinstance(objectives, list) and objectives:
        objective_value = _safe_float(objectives[-1])

    n_solutions = payload.get("nSolutions")
    has_solution = isinstance(n_solutions, int) and n_solutions > 0

    if objective_bound is not None and has_solution:
        return objective_bound, objective_value, "bound_and_incumbent"
    if objective_bound is not None:
        return objective_bound, objective_value, "bound_only"
    if has_solution:
        return None, objective_value, "incumbent_only"
    return None, None, "no_bound"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MiniZinc backend and extract exact-solver bound metadata.")
    parser.add_argument("dsl_file", help="Path to OptDSL instance file")
    parser.add_argument("--timelimit", type=float, default=120.0, help="MiniZinc time limit in seconds")
    parser.add_argument("--solver", default="cp-sat", help="MiniZinc solver name")
    parser.add_argument("--dsl-index-base", type=int, choices=[0, 1], default=0)
    parser.add_argument("--output-json", default=None, help="Optional output path for bound metadata JSON")
    args = parser.parse_args()
    dsl_path = Path(args.dsl_file).expanduser().resolve()
    if not dsl_path.exists():
        raise FileNotFoundError(f"DSL file does not exist: {dsl_path}")

    root = _mod_gen_opt_root()
    command = [
        sys.executable,
        str(root / "run_minizinc.py"),
        str(dsl_path),
        "--timelimit",
        str(args.timelimit),
        "--solver",
        args.solver,
        "--dsl-index-base",
        str(args.dsl_index_base),
    ]

    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    parsed: dict[str, Any] | None = None
    if stdout:
        try:
            candidate = json.loads(stdout)
            if isinstance(candidate, dict):
                parsed = candidate
        except json.JSONDecodeError:
            parsed = None

    lower_bound: float | None = None
    incumbent: float | None = None
    bound_status = "no_bound"
    if parsed is not None:
        lower_bound, incumbent, bound_status = _extract_bounds(parsed)

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dsl_file": str(dsl_path),
        "solver": args.solver,
        "timelimit_s": args.timelimit,
        "exit_code": int(completed.returncode),
        "bound_status": bound_status,
        "lower_bound": lower_bound,
        "incumbent": incumbent,
        "raw_result": parsed,
        "stdout": stdout,
        "stderr": stderr,
    }

    output = json.dumps(result, indent=2)
    print(output)

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")

    return 0 if completed.returncode == 0 else int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
