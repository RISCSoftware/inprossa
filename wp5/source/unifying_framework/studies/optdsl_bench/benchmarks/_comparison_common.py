from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class BenchmarkConfig:
    title: str
    class_name: str
    default_bench_dir: str
    lns_runner: str
    default_main_timeout: float
    default_lns_iterations: int
    default_lns_seed: int
    output_stem: str
    metadata_headers: list[str]
    metadata_extractor: Callable[[Path], list[str]]


@dataclass
class BenchmarkResult:
    instance: str
    metadata: list[str]
    minizinc_quality: str
    minizinc_bound: str
    minizinc_runtime_s: float
    lns_quality: str
    lns_runtime_s: float
    lns_stop_reason: str = "unknown"
    gap_pct: str = ""  # (lns - mz_bound) / |mz_bound| * 100, if both numeric
    # Warm-start snapshot written from the LNS incumbent (empty when --save-warmstart not used).
    warmstart_dsl_path: str = ""
    # MiniZinc run on the warm-started DSL snapshot (empty when --mz-warmstart not used).
    mz_ws_quality: str = ""
    mz_ws_bound: str = ""
    mz_ws_runtime_s: float = 0.0
    mz_ws_gap_pct: str = ""  # (lns - mz_ws_bound) / |mz_ws_bound| * 100, if both numeric


def mod_gen_opt_root() -> Path:
    return Path(__file__).resolve().parents[3]


# Wall-clock allowance for the DSL->MiniZinc translation, which runs before the
# solver's ``--timelimit`` budget starts.  The translation is the dominant cost
# for large models (a 10x10 JSSP needs ~5 min), so the subprocess cap must not
# be derived from the solve budget alone.
TRANSLATION_ALLOWANCE_S = 900.0


def _study_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _safe_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def discover_dsl_files(bench_dir: Path, explicit_files: list[str] | None) -> list[Path]:
    if explicit_files:
        files = [Path(item).expanduser().resolve() for item in explicit_files]
    else:
        files = sorted(bench_dir.glob("*.dsl"))
    return [file for file in files if file.exists()]


def parse_main_output(stdout: str) -> tuple[str, str]:
    payload: dict[str, object] | None = None
    try:
        candidate = json.loads(stdout)
        if isinstance(candidate, dict):
            payload = candidate
    except json.JSONDecodeError:
        payload = None

    if payload is not None:
        bound_value = _safe_float(payload.get("objective_bound"))
        objective_value = _safe_float(payload.get("objective"))
        objectives = payload.get("objectives")
        if objective_value is None and isinstance(objectives, list) and objectives:
            objective_value = _safe_float(objectives[-1])
        # ``MiniZincRunner.run()`` reports the solution count and the objective
        # inside ``statistics`` (MiniZinc's own stat keys), not at the top
        # level.  Reading only the top level made ``n_solutions`` always None,
        # so the "no feasible solution" branch below was dead code.
        statistics = payload.get("statistics")
        n_solutions = payload.get("nSolutions")
        if n_solutions is None and isinstance(statistics, dict):
            n_solutions = statistics.get("nSolutions")
        if objective_value is not None:
            bound_text = str(bound_value) if bound_value is not None else ""
            return str(objective_value), bound_text
        # A degenerate objective_bound (e.g. 0) on an instance where NO
        # feasible solution was found is a lower bound, not a quality value.
        # Only report it as quality when there is an actual solution.
        if isinstance(n_solutions, int) and n_solutions > 0:
            return str(bound_value) if bound_value is not None else "<has_solution>", str(bound_value) if bound_value is not None else ""
        if bound_value is not None:
            return "<no_solution>", str(bound_value)
        return "<no_solution>", ""

    bound_match = re.search(r'"objective_bound"\s*:\s*([-+]?\d+(?:\.\d+)?)', stdout)
    objective_match = re.search(r'"objective"\s*:\s*([-+]?\d+(?:\.\d+)?)', stdout)
    objectives_match = re.search(r'"objectives"\s*:\s*\[(.*?)\]', stdout, re.DOTALL)

    quality = "<no_solution>"
    bound = ""
    if objective_match:
        quality = objective_match.group(1)
    elif objectives_match:
        values = [item.strip() for item in objectives_match.group(1).split(",") if item.strip()]
        if values:
            quality = values[-1]
    if bound_match:
        bound = bound_match.group(1)
        if quality == "<no_solution>":
            quality = bound
    return quality, bound


def _minizinc_python() -> str:
    """Return an interpreter that can actually run our MiniZinc stack.

    ``run_minizinc.py`` imports ``minizinc`` (python bindings), which must be
    present in the interpreter used to launch it.  Relying on ``sys.executable``
    is fragile: a system interpreter without the ``minizinc`` module crashes at
    import and yields empty output.  Prefer an interpreter that already imports
    ``minizinc``, falling back to the project venv, then to ``sys.executable``.
    """
    try:
        import minizinc  # noqa: F401
        return sys.executable
    except Exception:
        pass
    # The package root is .../wp2/source/mod_gen_opt; the venv `uv sync`
    # builds sits at the git repository root, i.e. 3 folders up.
    repo_root = mod_gen_opt_root().parents[2]
    venv_candidates = [
        repo_root / ".venv/Scripts/python.exe",
        mod_gen_opt_root() / ".venv/Scripts/python.exe",  # project-local venv
        repo_root / ".venv/bin/python",
        mod_gen_opt_root() / ".venv/bin/python",
    ]
    for candidate in venv_candidates:
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


def run_minizinc(dsl_path: Path, timelimit: float, solver: str) -> tuple[str, str, float]:
    root = mod_gen_opt_root()
    t0 = time.time()
    try:
        proc = subprocess.run(
            [
                _minizinc_python(),
                str(root / "run_minizinc.py"),
                str(dsl_path),
                "--timelimit",
                str(timelimit),
                "--solver",
                solver,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            # ``--timelimit`` only bounds the SOLVE.  The DSL->MiniZinc
            # translation runs before it and is not covered by that budget; for
            # a 10x10 JSSP it alone takes ~5 minutes.  A hard cap of
            # ``timelimit + 120`` therefore killed instances that would have
            # solved fine, reporting them as ERROR.  Allow a generous
            # translation allowance on top of the solve budget.
            timeout=timelimit + TRANSLATION_ALLOWANCE_S,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "ERROR", "", time.time() - t0

    runtime = time.time() - t0
    stdout = proc.stdout.strip()
    if not stdout:
        return "NO_OUTPUT", "", runtime

    quality, bound = parse_main_output(stdout)
    return quality, bound, runtime


def parse_lns_output(stdout: str) -> tuple[str, str]:
    """Return (quality, stop_reason) from LNS stdout."""
    stop_reason = "unknown"
    stop_match = re.search(r"Stop reason:\s*([^\r\n]+)", stdout)
    if stop_match:
        stop_reason = stop_match.group(1).strip()

    best_score_match = re.search(r"Best score:\s*([^\r\n]+)", stdout)
    if best_score_match:
        return best_score_match.group(1).strip(), stop_reason

    run_lines = [line for line in stdout.splitlines() if "[run " in line and " best=" in line]
    if run_lines:
        match = re.search(r"best=([^\s]+)", run_lines[-1])
        if match:
            return match.group(1), stop_reason

    result_match = re.search(r"Optimization result:\s*([^\r\n]+)", stdout)
    if result_match:
        return result_match.group(1).strip(), stop_reason

    if "Traceback" in stdout or "Exception" in stdout or "Error" in stdout:
        return "ERROR", "runtime_error"

    return "<no_best>", stop_reason


def _compute_gap(lns_quality: str, mz_bound: str) -> str:
    """Compute gap percentage: (lns - mz_bound) / |mz_bound| * 100. Empty string if not numeric."""
    lns_val = _safe_float(lns_quality)
    bound_val = _safe_float(mz_bound)
    if lns_val is None or bound_val is None:
        return ""
    if bound_val == 0.0:
        return "0.00" if lns_val == 0.0 else "inf"
    return f"{(lns_val - bound_val) / abs(bound_val) * 100:.2f}"


def run_lns_profile(
    runner_script: str,
    dsl_path: Path,
    iterations: int,
    seed: int,
    lns_timeout_seconds: float | None = None,
    lns_no_improvement_iterations: int | None = None,
    emit_feasible_dsl: str | None = None,
) -> tuple[str, float, str]:
    """Returns (quality, runtime_seconds, stop_reason).

    When *emit_feasible_dsl* is given, the LNS runner is asked to write the final
    best (incumbent) solution as a DSL file containing the original DSL plus a
    ``@warm_start`` decorator with the assignment hints. The path must contain
    no placeholders so the file is overwritten on each incumbent improvement and
    the final file reflects the best solution.
    """
    root = mod_gen_opt_root()
    runner_path = root / runner_script
    t0 = time.time()

    cmd = [
        sys.executable,
        str(runner_path),
        str(dsl_path),
        "--max-iterations",
        str(iterations),
        "--random-seed",
        str(seed),
        "--log-every",
        "0",
    ]
    if lns_timeout_seconds is not None:
        cmd.extend(["--max-runtime-seconds", str(lns_timeout_seconds)])
    if lns_no_improvement_iterations is not None:
        cmd.extend(["--no-improvement-iterations", str(lns_no_improvement_iterations)])
    if emit_feasible_dsl is not None:
        cmd.extend(["--emit-feasible-dsl", emit_feasible_dsl, "--emit-feasible-on", "incumbent"])

    # Subprocess timeout: hard cap at lns_timeout + buffer; else iteration-based estimate
    if lns_timeout_seconds is not None:
        proc_timeout = lns_timeout_seconds + 120
    else:
        proc_timeout = iterations * 3 + 120

    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=proc_timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "ERROR", time.time() - t0, "timeout_error"

    runtime = time.time() - t0
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    merged_output = (stdout + "\n" + stderr).strip()
    if not merged_output:
        return "NO_OUTPUT", runtime, "unknown"

    if proc.returncode != 0:
        # Preserve a compact but meaningful failure reason.
        traceback_match = re.search(r"Traceback[\s\S]*", merged_output)
        if traceback_match:
            return "ERROR", runtime, "runtime_error"
        return "ERROR", runtime, f"exit_{proc.returncode}"

    quality, stop_reason = parse_lns_output(merged_output)
    return quality, runtime, stop_reason


def write_csv(results: list[BenchmarkResult], output_path: Path, headers: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    warmstart_enabled = any(row.warmstart_dsl_path for row in results)
    mz_ws_enabled = any(row.mz_ws_quality for row in results)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in results:
            base_row = [
                row.instance,
                *row.metadata,
                row.minizinc_quality,
                row.minizinc_bound,
                f"{row.minizinc_runtime_s:.4f}",
                row.lns_quality,
                f"{row.lns_runtime_s:.4f}",
                row.lns_stop_reason,
                row.gap_pct,
            ]
            if warmstart_enabled:
                base_row.append(row.warmstart_dsl_path)
            if mz_ws_enabled:
                base_row.extend([
                    row.mz_ws_quality,
                    row.mz_ws_bound,
                    f"{row.mz_ws_runtime_s:.4f}",
                    row.mz_ws_gap_pct,
                ])
            writer.writerow(base_row)


def write_markdown(results: list[BenchmarkResult], output_path: Path, config: BenchmarkConfig) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    warmstart_enabled = any(row.warmstart_dsl_path for row in results)
    mz_ws_enabled = any(row.mz_ws_quality for row in results)
    columns = [
        "Instance",
        *config.metadata_headers,
        "MiniZinc Quality",
        "MiniZinc Bound",
        "MiniZinc Time (s)",
        "LNS Quality",
        "LNS Time (s)",
        "LNS Stop",
        "Gap (%)",
    ]
    if warmstart_enabled:
        columns.append("Warm-Start DSL")
    if mz_ws_enabled:
        columns.extend(["MZ+WS Quality", "MZ+WS Bound", "MZ+WS Time (s)", "MZ+WS Gap (%)"])
    lines = [f"# {config.title}\n", ""]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["-" * max(3, len(col)) for col in columns]) + "|")
    for row in results:
        values = [
            row.instance,
            *row.metadata,
            row.minizinc_quality,
            row.minizinc_bound,
            f"{row.minizinc_runtime_s:.2f}",
            row.lns_quality,
            f"{row.lns_runtime_s:.2f}",
            row.lns_stop_reason,
            row.gap_pct,
        ]
        if warmstart_enabled:
            values.append(row.warmstart_dsl_path or "-")
        if mz_ws_enabled:
            values.extend([
                row.mz_ws_quality,
                row.mz_ws_bound or "-",
                f"{row.mz_ws_runtime_s:.2f}",
                row.mz_ws_gap_pct,
            ])
        lines.append("| " + " | ".join(values) + " |")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_benchmark(config: BenchmarkConfig) -> None:
    parser = argparse.ArgumentParser(description=config.title)
    parser.add_argument(
        "bench_dir",
        nargs="?",
        default=str(mod_gen_opt_root() / config.default_bench_dir),
        help="Directory containing OptDSL benchmark instances (.dsl)",
    )
    parser.add_argument("--main-timeout", type=float, default=config.default_main_timeout)
    parser.add_argument("--main-solver", default="gecode")
    parser.add_argument("--lns-iterations", type=int, default=config.default_lns_iterations)
    parser.add_argument("--lns-seed", type=int, default=config.default_lns_seed)
    parser.add_argument(
        "--lns-timeout-seconds",
        type=float,
        default=None,
        help="Wall-clock time limit for LNS in seconds (default: no limit; use e.g. 3600 for 60 min)",
    )
    parser.add_argument(
        "--lns-no-improvement-iterations",
        type=int,
        default=None,
        help="Stop LNS early after this many consecutive non-improving iterations (default: no convergence stop)",
    )
    parser.add_argument(
        "--out-md",
        default=str(mod_gen_opt_root() / "output" / f"{config.output_stem}.md"),
        help="Output Markdown file",
    )
    parser.add_argument(
        "--out-csv",
        default=str(mod_gen_opt_root() / "output" / f"{config.output_stem}.csv"),
        help="Output CSV file",
    )
    parser.add_argument("--skip-main", action="store_true")
    parser.add_argument("--skip-lns", action="store_true")
    parser.add_argument("--files", nargs="+", default=None)
    parser.add_argument(
        "--save-warmstart",
        action="store_true",
        help=(
            "Save each instance's final best LNS solution as a DSL file containing "
            "the original DSL plus a @warm_start decorator with the assignment hints. "
            "Files are written to --warmstart-dir."
        ),
    )
    parser.add_argument(
        "--warmstart-dir",
        default=None,
        help=(
            "Directory for LNS warm-start DSL snapshots (default: sibling subdir of "
            "the Markdown output, e.g. output/benchmark_2dbp_study_warmstart/)."
        ),
    )
    parser.add_argument(
        "--mz-warmstart",
        action="store_true",
        help=(
            "Run MiniZinc on each instance's warm-started DSL snapshot in addition to "
            "the plain MiniZinc run, and report the result as extra columns "
            "(MZ+WS Quality, MZ+WS Bound, MZ+WS Time, MZ+WS Gap). Implies --save-warmstart."
        ),
    )
    args = parser.parse_args()

    # --mz-warmstart needs the snapshot, so auto-enable saving.
    save_warmstart: bool = args.save_warmstart or args.mz_warmstart
    if args.mz_warmstart and args.skip_lns:
        raise SystemExit("--mz-warmstart requires the LNS run (do not pass --skip-lns).")
    warmstart_dir: Path = (
        Path(args.warmstart_dir).expanduser().resolve()
        if args.warmstart_dir
        else Path(args.out_md).resolve().parent / f"{config.output_stem}_warmstart"
    )

    bench_dir = Path(args.bench_dir).expanduser().resolve()
    if not bench_dir.exists():
        raise FileNotFoundError(f"Benchmark directory does not exist: {bench_dir}")

    dsl_files = discover_dsl_files(bench_dir, args.files)
    if not dsl_files:
        raise FileNotFoundError(f"No .dsl files found in {bench_dir}")

    lns_timeout_seconds: float | None = getattr(args, "lns_timeout_seconds", None)
    lns_no_improvement_iterations: int | None = getattr(args, "lns_no_improvement_iterations", None)

    print(f"Benchmarking {len(dsl_files)} {config.class_name} instances")
    print(f"  MiniZinc: timeout={args.main_timeout}s solver={args.main_solver}")
    lns_time_info = f" timeout={lns_timeout_seconds}s" if lns_timeout_seconds else ""
    lns_conv_info = f" no-improve-stop={lns_no_improvement_iterations}" if lns_no_improvement_iterations else ""
    print(f"  LNS: iterations={args.lns_iterations} seed={args.lns_seed}{lns_time_info}{lns_conv_info} runner={config.lns_runner}")
    if save_warmstart:
        print(f"  Warm-start: saving LNS snapshots to {warmstart_dir}")
    if args.mz_warmstart:
        print("  MZ+WS: running MiniZinc on warm-started DSL snapshots (extra columns)")
    print("-" * 120)

    results: list[BenchmarkResult] = []
    for idx, dsl_file in enumerate(dsl_files, start=1):
        print(f"[{idx}/{len(dsl_files)}] {dsl_file.stem}", end="  ...  ")
        metadata = config.metadata_extractor(dsl_file)
        if args.skip_main:
            main_quality, main_bound, main_runtime = "—", "—", 0.0
        else:
            main_quality, main_bound, main_runtime = run_minizinc(dsl_file, args.main_timeout, args.main_solver)

        warmstart_snapshot_path: str = ""
        if args.skip_lns:
            lns_quality, lns_runtime, lns_stop_reason = "—", 0.0, "skipped"
        else:
            emit_feasible_dsl: str | None = None
            if save_warmstart:
                snapshot_path = warmstart_dir / f"{dsl_file.stem}.warmstart.dsl"
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                emit_feasible_dsl = str(snapshot_path)
                warmstart_snapshot_path = str(snapshot_path)
            lns_quality, lns_runtime, lns_stop_reason = run_lns_profile(
                config.lns_runner,
                dsl_file,
                args.lns_iterations,
                args.lns_seed,
                lns_timeout_seconds=lns_timeout_seconds,
                lns_no_improvement_iterations=lns_no_improvement_iterations,
                emit_feasible_dsl=emit_feasible_dsl,
            )

        # Optional MiniZinc run on the warm-started DSL snapshot.
        mz_ws_quality, mz_ws_bound, mz_ws_runtime = "", "", 0.0
        mz_ws_gap = ""
        if args.mz_warmstart and warmstart_snapshot_path and Path(warmstart_snapshot_path).exists():
            mz_ws_quality, mz_ws_bound, mz_ws_runtime = run_minizinc(
                Path(warmstart_snapshot_path), args.main_timeout, args.main_solver
            )
            mz_ws_gap = _compute_gap(lns_quality, mz_ws_bound)

        gap = _compute_gap(lns_quality, main_bound)
        console_line = (
            f"MZ={main_quality} bound={main_bound or '-'} ({main_runtime:.1f}s)  "
            f"LNS={lns_quality} ({lns_runtime:.1f}s) stop={lns_stop_reason}"
            + (f"  gap={gap}%" if gap else "")
        )
        if args.mz_warmstart and mz_ws_quality:
            console_line += (
                f"  MZ+WS={mz_ws_quality} bound={mz_ws_bound or '-'} ({mz_ws_runtime:.1f}s)"
                + (f"  ws_gap={mz_ws_gap}%" if mz_ws_gap else "")
            )
        if save_warmstart and warmstart_snapshot_path:
            console_line += f"  ws={warmstart_snapshot_path}"
        print(console_line)
        results.append(
            BenchmarkResult(
                instance=dsl_file.stem,
                metadata=metadata,
                minizinc_quality=main_quality,
                minizinc_bound=main_bound,
                minizinc_runtime_s=main_runtime,
                lns_quality=lns_quality,
                lns_runtime_s=lns_runtime,
                lns_stop_reason=lns_stop_reason,
                gap_pct=gap,
                warmstart_dsl_path=warmstart_snapshot_path,
                mz_ws_quality=mz_ws_quality,
                mz_ws_bound=mz_ws_bound,
                mz_ws_runtime_s=mz_ws_runtime,
                mz_ws_gap_pct=mz_ws_gap,
            )
        )

    headers = [
        "instance",
        *[header.lower().replace(" ", "_") for header in config.metadata_headers],
        "minizinc_quality",
        "minizinc_bound",
        "minizinc_runtime_s",
        "lns_quality",
        "lns_runtime_s",
        "lns_stop_reason",
        "gap_pct",
    ]
    warmstart_enabled = any(row.warmstart_dsl_path for row in results)
    mz_ws_enabled = any(row.mz_ws_quality for row in results)
    if warmstart_enabled:
        headers.append("warmstart_dsl_path")
    if mz_ws_enabled:
        headers.extend(["mz_ws_quality", "mz_ws_bound", "mz_ws_runtime_s", "mz_ws_gap_pct"])
    write_markdown(results, Path(args.out_md), config)
    write_csv(results, Path(args.out_csv), headers)
    print("-" * 120)
    print(f"Saved Markdown to: {args.out_md}")
    print(f"Saved CSV to: {args.out_csv}")
    if warmstart_enabled:
        print(f"Saved {sum(1 for r in results if r.warmstart_dsl_path)} warm-start DSL snapshots to: {warmstart_dir}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_2dbp_metadata(path: Path) -> list[str]:
    text = read_text(path)
    constants: dict[str, str] = {}
    for match in re.finditer(r"(NBOXES|NITEMS|MAX_BOX_WIDTH|MAX_BOX_HEIGHT|BOX_WIDTH|BOX_HEIGHT)\s*:\s*int\s*=\s*(\d+)", text):
        constants[match.group(1)] = match.group(2)
    box_size = f"{constants.get('MAX_BOX_WIDTH', '?')}x{constants.get('MAX_BOX_HEIGHT', '?')}"
    return [box_size, constants.get("NITEMS", "0")]


def extract_jssp_metadata(path: Path) -> list[str]:
    text = read_text(path)
    constants: dict[str, str] = {}
    for match in re.finditer(r"(N_JOBS|N_MACHINES)\s*:\s*int\s*=\s*(\d+)", text):
        constants[match.group(1)] = match.group(2)
    return [constants.get("N_JOBS", "0"), constants.get("N_MACHINES", "0")]


def extract_cvrp_metadata(path: Path) -> list[str]:
    text = read_text(path)
    constants: dict[str, str] = {}
    for match in re.finditer(r"(N_CITIES|N_VEHICLES|VEHICLE_CAPACITY)\s*:\s*int\s*=\s*(\d+)", text):
        constants[match.group(1)] = match.group(2)
    return [
        constants.get("N_CITIES", "0"),
        constants.get("N_VEHICLES", "0"),
        constants.get("VEHICLE_CAPACITY", "0"),
    ]


def extract_generic_size_metadata(path: Path) -> list[str]:
    text = read_text(path)
    decision_count = len(re.findall(r":\s*DS(?:List|Int)\(", text))
    return [str(decision_count)]
