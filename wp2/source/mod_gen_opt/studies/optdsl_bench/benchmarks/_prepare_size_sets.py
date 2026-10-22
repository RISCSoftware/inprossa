"""Assemble and validate the Small/Medium instance sets for the size study.

Reads ``studies/optdsl_bench/benchmarks/instance_sets.json`` (paths relative to
the mod_gen_opt root), copies/produces the selected instances into
``output/size_sets/<class>/<set>/`` and — with ``--screen`` — runs one short
MiniZinc job per instance (via ``run_minizinc.py``) to confirm suitability and
report runtime along with the exact bound / gap.

Examples:
    # Materialize all sets:
    python studies/optdsl_bench/benchmarks/_prepare_size_sets.py

    # Materialize and screen only the 2dbp medium set with a 120 s budget:
    python studies/optdsl_bench/benchmarks/_prepare_size_sets.py \
        --class 2dbp --set medium --screen --timeout 120

Output:
    output/size_sets/<class>/<set>/*.dsl        assembled instances
    output/size_sets/_summary.csv               screening table (with --screen)
    output/size_sets/_summary.md                human-readable table (with --screen)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Reuse the harness helpers (same repo conventions).
from _comparison_common import (
    mod_gen_opt_root,
    parse_main_output,
    run_minizinc,
)


def _project_python(root: Path) -> str:
    """Resolve an interpreter that can import ``minizinc`` for subprocesses.

    Mirrors the logic in ``_comparison_common._minizinc_python``.
    """
    try:
        import minizinc  # noqa: F401
        return sys.executable
    except Exception:
        pass
    for candidate in (
        root.parents[2] / ".venv/Scripts/python.exe",  # repo-root venv (uv)
        root / ".venv/Scripts/python.exe",             # project-local venv
        root.parents[2] / ".venv/bin/python",
        root / ".venv/bin/python",
    ):
        if not candidate.exists():
            continue
        try:
            probe = subprocess.run(
                [str(candidate), "-c", "import minizinc"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        if probe.returncode == 0:
            return str(candidate)
    return sys.executable


def _load_manifest(root: Path) -> dict:
    manifest_path = root / "studies/optdsl_bench/benchmarks/instance_sets.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _copy_instances(root: Path, out_dir: Path, instances: list[dict]) -> list[Path]:
    """Copy referenced instance files into the set folder; skip missing ones with a warning."""
    dst_files: list[Path] = []
    for entry in instances:
        src = (root / entry["file"]).resolve()
        if not src.exists():
            print(f"  [WARN] missing instance file: {src}")
            continue
        dst = out_dir / src.name
        shutil.copyfile(src, dst)
        dst_files.append(dst)
    return dst_files


def _run_generated(root: Path, out_dir: Path, generated: dict) -> list[Path]:
    """Run the declared generator into its own outdir, then copy results into the set."""
    tool = (root / generated["tool"]).resolve()
    gen_out = (root / generated["args"][-1]).resolve()
    if not tool.exists():
        print(f"  [WARN] generator tool not found: {tool}")
        return []
    subprocess.run(
        [_project_python(root), str(tool), *generated["args"]],
        cwd=root,
        check=False,
    )
    dst_files: list[Path] = []
    for src in sorted(gen_out.glob("*.dsl")):
        dst = out_dir / src.name
        shutil.copyfile(src, dst)
        dst_files.append(dst)
    return dst_files


def _screen_instances(files: list[Path], solver: str, timeout: float) -> list[dict]:
    rows: list[dict] = []
    for path in files:
        t0 = time.time()
        quality, bound, runtime = run_minizinc(path, timeout, solver)
        if runtime == 0.0:
            runtime = round(time.time() - t0, 3)
        rows.append(
            {
                "instance": path.name,
                "runtime_s": runtime,
                "quality": quality,
                "bound": bound,
            }
        )
        print(f"    {path.name:60s} t={runtime:7.2f}s  quality={quality}  bound={bound}")
    return rows


def _write_summary(root: Path, table: list[dict], headers: list[str]) -> None:
    out_dir = root / "output/size_sets"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _fmt(row: dict) -> list[str]:
        return [str(row.get(h, "")) for h in headers]

    with (out_dir / "_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv_writer(fh)
        writer.writerow(headers)
        for row in table:
            writer.writerow(_fmt(row))

    lines = ["# Size-study instance screening", "", "| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in table:
        lines.append("| " + " | ".join(_fmt(row)) + " |")
    (out_dir / "_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def csv_writer(fh):
    import csv
    return csv.writer(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--class", dest="cls", choices=["cvrp", "jssp", "2dbp"], default=None,
                        help="Problem class (default: all)")
    parser.add_argument("--set", choices=["small", "medium"], default=None,
                        help="Size set within each class (default: all)")
    parser.add_argument("--screen", action="store_true",
                        help="Also run one MiniZinc job per instance to validate suitability")
    parser.add_argument("--solver", default="cp-sat")
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="MiniZinc time budget per instance (s) when screening")
    parser.add_argument("--minizinc-path", default=None,
                        help="Optional --minizinc-path forwarded to run_minizinc.py")
    args = parser.parse_args()

    root = mod_gen_opt_root()
    manifest = _load_manifest(root)
    class_defs = manifest["classes"]
    if args.cls:
        class_defs = {args.cls: class_defs[args.cls]}

    table_headers = ["class", "set", "instance", "runtime_s", "quality", "bound"]
    table: list[dict] = []

    for class_name, class_def in class_defs.items():
        for set_name, set_def in class_def["sets"].items():
            if args.set and args.set != set_name:
                continue
            out_dir = root / "output/size_sets" / class_name / set_name
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"=== {class_name} / {set_name} -> {out_dir} ===")

            files = _copy_instances(root, out_dir, set_def.get("instances", []))

            if "generated" in set_def:
                print("  generating additional size-scaled instances ...")
                files += _run_generated(root, out_dir, set_def["generated"])

            if not files:
                print("  [WARN] no instances assembled for this set")
                continue

            budget = set_def.get("expected_budget_s", manifest.get("timeout_default_s", 60))
            print(f"  {len(files)} instance(s); expected budget ~{budget}s per run")

            if args.screen:
                rows = _screen_instances(files, args.solver, args.timeout)
                for row in rows:
                    row["class"] = class_name
                    row["set"] = set_name
                    table.append(row)

    if args.screen and table:
        _write_summary(root, table, table_headers)
        print(f"\nSummary written to output/size_sets/_summary.csv and _summary.md")


if __name__ == "__main__":
    main()
