"""Run the full size study (MiniZinc + LNS) across all calibrated sets and
merge per-class results into one final table (CSV + Markdown).

Reads the calibrated sets from ``instance_sets.json``, invokes the existing
per-class benchmark harness (which runs MiniZinc then LNS per instance), and
merges the per-class output CSVs into ``output/study_results.{csv,md}``.

Example:
    python studies/optdsl_bench/benchmarks/run_study.py \
        --solver cp-sat --timeout 120 --out output/study_results
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

from _comparison_common import mod_gen_opt_root


# class_name -> benchmark entry script
BENCHMARK_SCRIPTS = {
    "cvrp": "benchmark_cvrp.py",
    "jssp": "benchmark_jssp.py",
    "2dbp": "benchmark_2dbp.py",
}

OUTPUT_HEADERS = [
    "Class", "Set", "Instance", "Size", "MiniZinc Quality", "MiniZinc Bound",
    "MiniZinc Time (s)", "LNS Quality", "LNS Time (s)", "LNS Stop", "Gap (%)",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", default="cp-sat")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="MiniZinc time budget per instance (s)")
    parser.add_argument("--lns-timeout", type=float, default=None,
                        help="Optional LNS wall-clock cap (s)")
    parser.add_argument("--lns-iterations", type=int, default=None,
                        help="Optional LNS iteration override")
    parser.add_argument("--out", default="output/study_results",
                        help="Output stem (CSV and MD written as <stem>.csv/.md)")
    parser.add_argument("--class", dest="cls", choices=list(BENCHMARK_SCRIPTS), default=None)
    parser.add_argument("--set", choices=["small", "medium"], default=None)
    args = parser.parse_args()

    root = mod_gen_opt_root()
    manifest = json.loads(
        (root / "studies/optdsl_bench/benchmarks/instance_sets.json").read_text(encoding="utf-8")
    )

    classes = manifest["classes"]
    if args.cls:
        classes = {args.cls: classes[args.cls]}

    out_stem = Path(args.out)
    out_stem.parent.mkdir(parents=True, exist_ok=True)

    all_rows: list[list[str]] = []
    for class_name, class_def in classes.items():
        script = root / "studies/optdsl_bench/benchmarks" / BENCHMARK_SCRIPTS[class_name]
        for set_name, set_def in class_def["sets"].items():
            if args.set and args.set != set_name:
                continue
            bench_dir = root / "output/size_sets" / class_name / set_name
            if not bench_dir.is_dir():
                print(f"[skip] missing bench dir: {bench_dir}")
                continue

            budget = set_def.get("expected_budget_s", args.timeout)
            timeout = args.timeout
            out_csv = out_stem.with_name(f"{out_stem.name}__{class_name}_{set_name}.csv")
            out_md = out_stem.with_name(f"{out_stem.name}__{class_name}_{set_name}.md")

            cmd = [
                sys.executable, str(script), str(bench_dir),
                "--main-solver", args.solver,
                "--main-timeout", str(timeout),
                "--out-csv", str(out_csv),
                "--out-md", str(out_md),
            ]
            if args.lns_timeout is not None:
                cmd += ["--lns-timeout-seconds", str(args.lns_timeout)]
            if args.lns_iterations is not None:
                cmd += ["--lns-iterations", str(args.lns_iterations)]

            print(f"\n=== [{class_name} / {set_name}] running: {' '.join(cmd)} ===", flush=True)
            proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            print(proc.stdout[-4000:] if len(proc.stdout) > 4000 else proc.stdout)
            if proc.stderr:
                print("STDERR:", proc.stderr[-1500:])
            if proc.returncode != 0:
                print(f"[error] {class_name}/{set_name} exit={proc.returncode}; skipping merge")
                continue

            # Merge the per-class CSV into the unified table.
            with out_csv.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    instance = row.get("instance", "")
                    # metadata fields are the columns between instance and minizinc_quality
                    md_headers = class_def["metadata_headers"]
                    md_lower = [h.lower().replace(" ", "_") for h in md_headers]
                    size = " / ".join(row.get(h, "") for h in md_lower)
                    row_flat = [
                        class_name, set_name, instance, size,
                        row.get("minizinc_quality", ""),
                        row.get("minizinc_bound", ""),
                        row.get("minizinc_runtime_s", ""),
                        row.get("lns_quality", ""),
                        row.get("lns_runtime_s", ""),
                        row.get("lns_stop_reason", ""),
                        row.get("gap_pct", ""),
                    ]
                    all_rows.append(row_flat)

    # Write the merged final table.
    final_csv = out_stem.with_name(out_stem.name + ".csv")
    final_md = out_stem.with_name(out_stem.name + ".md")
    with final_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(OUTPUT_HEADERS)
        writer.writerows(all_rows)

    lines = ["# Size-study results: MiniZinc vs LNS", "",
             f"_Solver {args.solver}, MiniZinc budget {args.timeout}s/instance_", "",
             "| " + " | ".join(OUTPUT_HEADERS) + " |",
             "|" + "|".join(["---"] * len(OUTPUT_HEADERS)) + "|"]
    for row in all_rows:
        lines.append("| " + " | ".join(row) + " |")
    final_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote merged table: {final_csv} and {final_md}")


if __name__ == "__main__":
    main()
