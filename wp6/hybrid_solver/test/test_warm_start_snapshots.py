"""Tests for warm-start snapshot files and the MiniZinc backend integration.

Run with::

    .venv\\Scripts\\python.exe -m pytest test\\test_warm_start_snapshots.py -q
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hybrid import (  # noqa: E402
    estimate_lower_bound,
    load_warm_start,
    save_warm_start,
    spec_from_assignment,
    warm_start_block,
)
from hybrid.warm_start import WARM_START_VERSION, inject_warm_start, normalise_hints  # noqa: E402


# ---------------------------------------------------------------------------
# Signal processing helpers
# ---------------------------------------------------------------------------

def _parse_warm_start_block(code: str) -> tuple[dict, ast.AST]:
    """Extract hints/bounds from an injected block the way the translator does.

    Mirrors ``MiniZincTranslator._parse_warm_start_function``: find the
    ``@warm_start``-decorated function and literal-eval its returned dict.
    """
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if isinstance(deco, ast.Name) and deco.id == "warm_start":
                ret = next(s for s in node.body if isinstance(s, ast.Return))
                return ast.literal_eval(ret.value), deco
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name) and deco.func.id == "warm_start":
                ret = next(s for s in node.body if isinstance(s, ast.Return))
                return ast.literal_eval(ret.value), deco
    return None, None


def _decorator_bounds(deco: ast.AST) -> dict:
    if not isinstance(deco, ast.Call):
        return {}
    return {kw.arg: ast.literal_eval(kw.value) for kw in deco.keywords if kw.arg is not None}


# ---------------------------------------------------------------------------
# normalisation
# ---------------------------------------------------------------------------

def test_normalise_hints_drops_unusable_values() -> None:
    hints = normalise_hints(
        {
            "x": [0, 1, 2],
            "y": 5,
            "z": None,             # unassigned
            "completion_0": 3,     # per-row helper key
            "completion": [[1, 2], [3, 4]],  # nested array
        }
    )
    assert hints == {"x": [0, 1, 2], "y": 5}


def test_spec_from_assignment_bounds_by_sense() -> None:
    minim = spec_from_assignment({"x": 1}, score=10.5, objective_sense="minimize")
    assert minim["lower_bound"] is None
    assert minim["upper_bound"] == 10.5

    maxim = spec_from_assignment({"x": 1}, score=7.0, objective_sense="maximize")
    assert maxim["lower_bound"] == 7.0
    assert maxim["upper_bound"] is None

    plain = spec_from_assignment({"x": 1})
    assert plain["lower_bound"] is None and plain["upper_bound"] is None


# ---------------------------------------------------------------------------
# JSON snapshot files
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    spec = spec_from_assignment(
        {"assignments": [0, 1, 0, 1, 0]},
        score=2,
        objective_sense="minimize",
        objective_variable="objective",
        problem="problems/p.dsl",
        event="incumbent_update",
        iteration=3,
    )
    path = tmp_path / "ws.json"
    save_warm_start(path, spec)
    loaded = load_warm_start(path)

    assert loaded["hints"] == {"assignments": [0, 1, 0, 1, 0]}
    assert loaded["upper_bound"] == 2.0
    assert loaded["score"] == 2
    assert loaded["objective_sense"] == "minimize"
    assert loaded["problem"] == "problems/p.dsl"
    assert loaded["event"] == "incumbent_update"
    assert loaded["iteration"] == 3
    assert loaded["lower_bound"] is None


def test_load_rejects_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"version": 99, "hints": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        load_warm_start(path)


def test_load_rejects_missing_hints(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(f'{{"version": {WARM_START_VERSION}}}', encoding="utf-8")
    with pytest.raises(ValueError, match="hints"):
        load_warm_start(path)


# ---------------------------------------------------------------------------
# DSL injection
# ---------------------------------------------------------------------------

def test_warm_start_block_is_literal_parseable() -> None:
    spec = spec_from_assignment(
        {"assignments": [0, 1, 0, 1, 0], "objective": 2},
        score=2,
        objective_sense="minimize",
        objective_variable="objective",
    )
    code = warm_start_block(spec)
    hints, deco = _parse_warm_start_block("def m():\n    pass\n" + code)
    assert hints == {"assignments": [0, 1, 0, 1, 0], "objective": 2}
    assert _decorator_bounds(deco) == {"upper_bound": 2.0}


def test_inject_warm_start_noops_without_hints() -> None:
    empty = inject_warm_start("x = 1\n", {"hints": {}})
    assert empty == "x = 1\n"
    none = inject_warm_start("x = 1\n", None)
    assert none == "x = 1\n"


# ---------------------------------------------------------------------------
# API level
# ---------------------------------------------------------------------------

def test_estimate_lower_bound_accepts_warm_assignment_path(monkeypatch, tmp_path) -> None:
    import hybrid.lower_bound as lb

    calls: dict = {}

    class FakeSolver:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

        def run(self):
            return {"objectives": [3.0], "objective_bound": 1.5, "status": "OPTIMAL_SOLUTION"}

    monkeypatch.setattr(lb, "DSLSolver", FakeSolver)

    dsl_path = REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl"

    path = tmp_path / "ws.json"
    save_warm_start(
        path,
        spec_from_assignment(
            {"x": [1, 0]}, score=3, objective_sense="minimize", objective_variable="obj"
        ),
    )

    result = estimate_lower_bound(dsl_path, warm_assignment=path)

    assert result["lower_bound"] == 1.5
    assert result["best_objective"] == 3.0
    spec = calls["kwargs"]["warm_start"]
    assert spec["hints"] == {"x": [1, 0]}
    assert spec["upper_bound"] == 3.0
    assert spec["problem"] == str(dsl_path)


def test_estimate_lower_bound_plain_assignment_keeps_compat(monkeypatch) -> None:
    import hybrid.lower_bound as lb

    calls: dict = {}

    class FakeSolver:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

        def run(self):
            return {"objectives": [], "objective_bound": None, "status": "UNKNOWN"}

    monkeypatch.setattr(lb, "DSLSolver", FakeSolver)

    dsl_path = REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl"

    estimate_lower_bound(dsl_path, warm_assignment={"x": 2})

    spec = calls["kwargs"]["warm_start"]
    assert spec["hints"] == {"x": 2}
    assert spec["lower_bound"] is None and spec["upper_bound"] is None


# ---------------------------------------------------------------------------
# Full translation via the DSLSolver backend (uses only the translator)
# ---------------------------------------------------------------------------

def test_dslsolver_translate_emits_warm_start_for_1dbp() -> None:
    from src.optdsl.solver.DSL_solver import DSLSolver

    dsl_path = REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl"
    if not dsl_path.exists():
        pytest.skip("1dbp instance not present")
    code = dsl_path.read_text(encoding="utf-8")

    spec = spec_from_assignment(
        {"assignments": [0, 1, 0, 1, 0], "objective": 2},
        score=2,
        objective_sense="minimize",
        objective_variable="objective",
    )
    mzn = DSLSolver(code, warm_start=spec).translate()

    assert "assignments_hint" in mzn
    assert "warm_start(assignments[1], assignments_hint)" in mzn
    assert "constraint objective[1] <= 2.0" in mzn


def test_run_minizinc_cli_dump_mzn_applies_warm_start_file(tmp_path: Path) -> None:
    dsl_path = REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl"
    if not dsl_path.exists():
        pytest.skip("1dbp instance not present")

    ws_path = tmp_path / "ws.json"
    save_warm_start(
        ws_path,
        spec_from_assignment(
            {"assignments": [0, 1, 0, 1, 0], "objective": 2},
            score=2,
            objective_sense="minimize",
            objective_variable="objective",
        ),
    )
    out_path = tmp_path / "model.mzn"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "run_minizinc.py"),
            str(dsl_path),
            "--dump-mzn",
            str(out_path),
            "--warm-start",
            str(ws_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    mzn = out_path.read_text(encoding="utf-8")
    assert "assignments_hint" in mzn
    assert "warm_start(assignments[1], assignments_hint)" in mzn
