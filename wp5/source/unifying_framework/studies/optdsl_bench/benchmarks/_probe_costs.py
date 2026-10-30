"""Measure per-instance translation + solve cost for the size study.

The DSL->MiniZinc translation is the dominant cost (deepcopy blow-up in the
translator's loop unrolling), so the feasible instance size is decided by
`translate_time + solve_time`.  This script measures both precisely.

For each input DSL it:
  1. translates to a temporary .mzn and times the translation
  2. solves the .mzn with the requested solver and times the solve
     - cp-sat: uses `--params "max_time_in_seconds:N"` (its `-t`/`--time-limit`
       flag is not wired in the solver config, so the standard flag is ignored)
     - gecode / others: uses `--time-limit`
  3. parses status/objective/bound and writes one CSV row

Example:
    python studies/optdsl_bench/benchmarks/_probe_costs.py \
        --solver cp-sat --timeout 30 --out output/size_sets/_probe_costs.csv \
        output/size_sets/jssp/small/*.dsl
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from _comparison_common import mod_gen_opt_root


def _translate(dsl_path: Path, root: Path) -> tuple[str, float]:
    import sys
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from src import DSLSolver

    dsl_solver = DSLSolver(
        dsl_path.read_text(encoding="utf-8"),
        solver_name="gecode",  # translation only; solver name is irrelevant here
        timelimit=1,
    )
    t0 = time.time()
    mzn = dsl_solver.translate()
    return mzn, time.time() - t0


def _minizinc_cli() -> str:
    # Resolve the MiniZinc driver executable the same way the solver lib does.
    import minizinc
    driver = getattr(minizinc, "default_driver", None)
    exe = getattr(driver, "_executable", None) or getattr(driver, "executable", None)
    return str(exe) if exe else "minizinc"


def _solve_cli(mzn_text: str, solver: str, timeout: float) -> tuple[str, str, float]:
    fd, tmp_path = tempfile.mkstemp(suffix=".mzn", prefix="mzprobe_")
    with os.fdopen(fd, "w", encoding="utf-8") as tmp:
        tmp.write(mzn_text)

    cmd = [_minizinc_cli(), "--solver", solver, "--output-mode", "json", "--output-time"]
    if solver == "cp-sat":
        # cp-sat's msc has no `-t` stdFlag; enforce the budget through its own param.
        cmd += ["--params", f"max_time_in_seconds: {int(float(timeout))}"]
    else:
        cmd += ["--time-limit", str(int(float(timeout) * 1000))]
    cmd.append(tmp_path)

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=max(30.0, float(timeout) + 120.0),
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "", time.time() - t0
    solve_s = time.time() - t0
    out = proc.stdout + proc.stderr

    status = "UNKNOWN"
    if "OPTIMAL_SOLUTION" in out:
        status = "OPTIMAL"
    elif "==========" in out:
        status = "OPTIMAL"
    elif "SATISFIED" in out or "----------" in out:
        status = "SAT"
    elif "UNSATISFIABLE" in out:
        status = "UNSAT"

    obj_match = re.search(r'"objective"\s*:\s*(\d+)', proc.stdout)
    bound_match = re.search(r'"bound"\s*:\s*(\d+)', proc.stdout)
    objective = obj_match.group(1) if obj_match else ""
    bound = bound_match.group(1) if bound_match else ""
    return status, objective, solve_s


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--solver", default="cp-sat")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--out", type=Path, default=Path("output/size_sets/_probe_costs.csv"))
    args = parser.parse_args()

    root = mod_gen_opt_root()
    rows = []
    for dsl in args.files:
        dsl = dsl.resolve()
        try:
            mzn, tr_s = _translate(dsl, root)
        except Exception as exc:  # noqa: BLE001
            print(f"{dsl.name:40s} translate ERROR: {type(exc).__name__}: {str(exc)[:80]}")
            rows.append({"instance": dsl.name, "translate_s": "", "solve_s": "",
                         "status": "TRANSLATE_ERROR", "objective": "", "bound": "",
                         "mzn_kb": ""})
            continue
        status, objective, solve_s = _solve_cli(mzn, args.solver, args.timeout)
        print(f"{dsl.name:40s} translate={tr_s:8.1f}s solve={solve_s:8.1f}s "
              f"status={status:9s} obj={objective}")
        rows.append({
            "instance": dsl.name,
            "translate_s": round(tr_s, 2),
            "solve_s": round(solve_s, 2),
            "status": status,
            "objective": objective,
            "bound": "",
            "mzn_kb": round(len(mzn) / 1024, 1),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
