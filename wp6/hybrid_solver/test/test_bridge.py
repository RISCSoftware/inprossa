"""Smoke-test the JSON bridge used by the VS Code extension."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def call(command: str, **payload) -> dict:
    request = json.dumps({"command": command, **payload})
    completed = subprocess.run(
        [sys.executable, "-m", "optdsl_tooling.bridge"],
        input=request,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    # The bridge signals failure through the JSON payload, not the exit code,
    # for protocol-level errors; only unhandled exceptions exit non-zero.
    assert completed.stdout.strip(), completed.stderr
    return json.loads(completed.stdout)


def test_bridge_analyze() -> None:
    source = (REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl").read_text(
        encoding="utf-8"
    )
    result = call("analyze", source=source)
    assert result["ok"] is True
    assert result["decisionCount"] == 5
    assert result["problemClass"] == "1dbp"
    assert result["objective"]["sense"] == "minimize"


def test_bridge_fingerprint() -> None:
    source = (REPO_ROOT / "problem_instances" / "jssp" / "jssp_5x4.dsl").read_text(encoding="utf-8")
    result = call("fingerprint", source=source)
    assert result["ok"] is True
    assert result["best"] == "jssp"
    assert result["matched"] is True


def test_bridge_translate() -> None:
    source = (REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl").read_text(
        encoding="utf-8"
    )
    result = call("translate", source=source)
    assert result["ok"] is True
    assert "constraint" in result["model"]
    assert "solve minimize" in result["model"]


def test_bridge_validate_constraint_rejects_vacuous() -> None:
    source = (
        "N : int = 4\n"
        "x: DSList(N, DSInt(0, 3))\n"
        "objective: DSInt(0, 100) = 0\n"
        "minimize(objective)\n"
    )
    result = call(
        "validateConstraint",
        source=source,
        constraints=[
            {
                "name": "vacuous",
                "code": "def vacuous(x: DSList(N, DSInt(0, 3))):\n"
                "    for i in range(N):\n"
                "        assert x[i] >= 0",
                "invocation": "vacuous(x)",
            }
        ],
    )
    # A vacuous constraint is not acceptable, so `ok` is false — but the
    # specific reason must be reported so the UI can explain it.
    assert result["ok"] is False
    assert result["vacuous"] is True
    assert result["violationRate"] == 0.0


def test_bridge_validate_constraint_accepts_useful() -> None:
    source = (
        "N : int = 4\n"
        "x: DSList(N, DSInt(0, 3))\n"
        "objective: DSInt(0, 100) = 0\n"
        "minimize(objective)\n"
    )
    result = call(
        "validateConstraint",
        source=source,
        constraints=[
            {
                "name": "no_two",
                "code": "def no_two(x: DSList(N, DSInt(0, 3))):\n"
                "    for i in range(N):\n"
                "        assert x[i] != 2",
                "invocation": "no_two(x)",
            }
        ],
    )
    assert result["ok"] is True
    assert result["vacuous"] is False
    assert 0.0 < result["violationRate"] < 1.0


def test_validate_route_constraint_not_falsely_over_constrained() -> None:
    """A structured route constraint must not be rejected as over-constrained.

    Random assignments never satisfy the routing model, so a constraint that
    references route structure (e.g. "nodes 2 and 3 on different routes") used
    to be flagged as "violated by every random assignment". When the sampler
    cannot reach feasible space it must downgrade to a review warning instead.
    """
    from optdsl_tooling.constraint_validation import validate_constraints

    source = (REPO_ROOT / "problem_instances" / "cvrp" / "random_euclidean_cvrp_8.dsl").read_text(
        encoding="utf-8"
    )
    constraint = {
        "name": "nodes_2_3_not_same_route",
        "code": (
            "def nodes_2_3_not_same_route(arcs: DSList(N_ARCS, DSInt(0, 1))):\n"
            "    for v in range(N_VEHICLES):\n"
            "        c2_on_v = 0\n"
            "        c3_on_v = 0\n"
            "        for i in range(N_CITIES):\n"
            "            c2_on_v = c2_on_v + arcs[v * N_CITIES * N_CITIES + 2 * N_CITIES + i]\n"
            "            c2_on_v = c2_on_v + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + 2]\n"
            "            c3_on_v = c3_on_v + arcs[v * N_CITIES * N_CITIES + 3 * N_CITIES + i]\n"
            "            c3_on_v = c3_on_v + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + 3]\n"
            "        assert not (c2_on_v > 0 and c3_on_v > 0)"
        ),
        "invocation": "nodes_2_3_not_same_route(arcs)",
    }
    result = validate_constraints(source, [constraint], samples=200)
    assert result["ok"] is True, result["errors"]
    assert result["overConstrained"] is False
    assert result["baselineFeasible"] == 0.0
    assert any("could not be measured" in w for w in result["warnings"])


def test_bridge_unknown_command() -> None:
    result = call("nope")
    assert result["ok"] is False
    assert "unknown command" in result["error"]
