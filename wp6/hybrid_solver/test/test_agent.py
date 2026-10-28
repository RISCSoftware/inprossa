"""Tests for the OptDSL agent harness.

Everything here runs offline. The model is replaced by a scripted stub, so the
suite exercises the agent loop, the tool layer, the LNS wrapper and the tuning
loop without a network call or an API key.

Run with::

    .venv\\Scripts\\python.exe -m pytest test/test_agent.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for extra in ("", "optdsl-lsp", "operator-synthesis"):
    candidate = str(REPO_ROOT / extra) if extra else str(REPO_ROOT)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from optdsl_agent.agent import AgentLoop  # noqa: E402
from optdsl_agent.config import AgentConfig, Budget  # noqa: E402
from optdsl_agent.digest import model_digest, model_summary  # noqa: E402
from optdsl_agent.llm import LLMResponse, StubClient, ToolCall  # noqa: E402
from optdsl_agent.lns_runner import LNSRunConfig, run_lns  # noqa: E402
from optdsl_agent.operator_loader import list_operators, load_generated_operators  # noqa: E402
from optdsl_agent.session import Session  # noqa: E402
from optdsl_agent.tools import build_registry  # noqa: E402
from optdsl_agent.tuning import TuningBudget, evaluate_operator_multi, tune  # noqa: E402

CVRP = REPO_ROOT / "problem_instances" / "cvrp" / "random_euclidean_cvrp_8.dsl"
JSSP = REPO_ROOT / "problem_instances" / "jssp" / "jssp_2x2.dsl"


@pytest.fixture()
def config(tmp_path: Path) -> AgentConfig:
    """A config whose output goes to a temp directory, never the repo."""
    return AgentConfig(
        output_dir=tmp_path / "out",
        operator_dir=tmp_path / "generated",
        repo_root=REPO_ROOT,
        lns_iterations=20,
    )


@pytest.fixture()
def session(config: AgentConfig) -> Session:
    return Session.from_file(CVRP, config)


# ---------------------------------------------------------------------------
# digest
# ---------------------------------------------------------------------------


def test_digest_reports_decisions_and_objective() -> None:
    digest = model_digest(CVRP.read_text(encoding="utf-8"))
    assert "cvrp" in digest
    assert "arcs" in digest
    assert "minimize" in digest
    assert "Decision indices:" in digest


def test_digest_marks_uninvoked_predicates() -> None:
    """A predicate that is never called has no effect; the digest must say so."""
    source = (
        "N : int = 2\n"
        "x: DSList(N, DSInt(0, 1))\n"
        "def unused(x: DSList(N, DSInt(0, 1))):\n"
        "    assert x[0] == 1\n"
        "objective: DSInt(0, 10) = 0\n"
        "minimize(objective)\n"
    )
    assert "NOT INVOKED" in model_digest(source)


def test_digest_reports_syntax_errors_instead_of_raising() -> None:
    digest = model_digest("def broken(:\n")
    assert "does not parse" in digest


def test_summary_is_json_serialisable() -> None:
    summary = model_summary(CVRP.read_text(encoding="utf-8"))
    json.dumps(summary.to_dict())  # must not raise


def test_summary_confidence_is_clamped() -> None:
    """The fingerprint adds an optional-marker bonus, so the raw score can exceed 1."""
    digest = model_digest(CVRP.read_text(encoding="utf-8"))
    assert "101%" not in digest


# ---------------------------------------------------------------------------
# LNS runner
# ---------------------------------------------------------------------------


def test_run_lns_returns_objective_and_feasibility() -> None:
    result = run_lns(LNSRunConfig(instance=CVRP, iterations=20, initializer="auto"))
    assert result.ok
    assert result.feasible
    assert result.objective_value is not None
    assert result.iterations > 0


def test_run_lns_records_trajectory() -> None:
    result = run_lns(
        LNSRunConfig(instance=CVRP, iterations=20, initializer="auto", record_trajectory=True)
    )
    assert result.trajectory
    assert {"iteration", "incumbent", "accepted"} <= set(result.trajectory[0])


def test_run_lns_reports_missing_instance_without_raising() -> None:
    result = run_lns(LNSRunConfig(instance=REPO_ROOT / "does_not_exist.dsl"))
    assert not result.ok
    assert "could not read instance" in (result.error or "")


def test_run_lns_rejects_unknown_operator() -> None:
    result = run_lns(
        LNSRunConfig(instance=CVRP, iterations=5, destroys=["NoSuchDestroy"])
    )
    assert not result.ok
    assert "NoSuchDestroy" in (result.error or "")


def test_run_lns_uses_problem_specific_defaults() -> None:
    """The generic random pair is a poor baseline on CVRP; the default must adapt."""
    result = run_lns(LNSRunConfig(instance=CVRP, iterations=50, initializer="auto"))
    assert result.ok
    assert result.infeasible_candidates < result.iterations


def test_run_lns_result_is_json_serialisable() -> None:
    result = run_lns(LNSRunConfig(instance=CVRP, iterations=10, initializer="auto"))
    json.dumps(result.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# operator registry
# ---------------------------------------------------------------------------


def test_list_operators_includes_builtins() -> None:
    operators = list_operators("cvrp")
    names = {operator["name"] for operator in operators}
    assert "CVRPShawDestroy" in names
    assert "RandomFractionDestroy" in names


def test_load_generated_operators_ignores_missing_directory(tmp_path: Path) -> None:
    assert load_generated_operators(tmp_path / "nope") == []


def test_load_generated_operators_registers_a_module(tmp_path: Path) -> None:
    module = tmp_path / "my_destroy.py"
    module.write_text(
        "from dataclasses import dataclass\n"
        "from large_neighborhood_search.components import DestroyOperator\n"
        "from large_neighborhood_search.registry import register_destroy\n"
        "\n"
        "@register_destroy('TestOnlyDestroy', generated=True)\n"
        "def _make(**kwargs):\n"
        "    return TestOnlyDestroy(**kwargs)\n"
        "\n"
        "@dataclass\n"
        "class TestOnlyDestroy(DestroyOperator):\n"
        "    def destroy(self, assignment, context):\n"
        "        return assignment\n",
        encoding="utf-8",
    )

    added = load_generated_operators(tmp_path)
    assert "TestOnlyDestroy" in added

    from large_neighborhood_search.registry import clear_generated

    clear_generated()


def test_load_generated_operators_skips_broken_modules(tmp_path: Path) -> None:
    """One broken generated file must not make the others unreachable."""
    (tmp_path / "broken.py").write_text("this is not python(\n", encoding="utf-8")
    (tmp_path / "good.py").write_text(
        "from dataclasses import dataclass\n"
        "from large_neighborhood_search.components import DestroyOperator\n"
        "from large_neighborhood_search.registry import register_destroy\n"
        "\n"
        "@register_destroy('SurvivesBrokenNeighbour', generated=True)\n"
        "def _make(**kwargs):\n"
        "    return SurvivesBrokenNeighbour(**kwargs)\n"
        "\n"
        "@dataclass\n"
        "class SurvivesBrokenNeighbour(DestroyOperator):\n"
        "    def destroy(self, assignment, context):\n"
        "        return assignment\n",
        encoding="utf-8",
    )

    added = load_generated_operators(tmp_path)
    assert "SurvivesBrokenNeighbour" in added

    from large_neighborhood_search.registry import clear_generated

    clear_generated()


# ---------------------------------------------------------------------------
# tools
# ---------------------------------------------------------------------------


def test_analyze_tool_returns_digest(session: Session) -> None:
    result = build_registry().call("analyze_model", session, {})
    assert result["ok"]
    assert "arcs" in result["digest"]


def test_unknown_tool_is_reported_not_raised(session: Session) -> None:
    result = build_registry().call("no_such_tool", session, {})
    assert not result["ok"]
    assert "unknown tool" in result["error"]


def test_bad_arguments_are_reported_not_raised(session: Session) -> None:
    result = build_registry().call("analyze_model", session, {"nonsense": 1})
    assert not result["ok"]
    assert "bad arguments" in result["error"]


def test_write_file_refuses_path_traversal(session: Session) -> None:
    result = build_registry().call(
        "write_file", session, {"name": "../escaped.txt", "content": "x"}
    )
    assert not result["ok"]
    assert "refusing to write" in result["error"]


def test_write_file_stays_inside_output_dir(session: Session) -> None:
    result = build_registry().call("write_file", session, {"name": "notes.txt", "content": "hi"})
    assert result["ok"]
    assert Path(result["path"]).parent == session.config.output_dir.resolve()


def test_add_constraints_writes_a_new_file_and_keeps_the_source(session: Session) -> None:
    original = session.source
    constraint = {
        "name": "depot_only_once",
        "code": (
            "def depot_only_once(vehicle_used: DSList(N_VEHICLES, DSInt(0, 1))):\n"
            "    assert sum(vehicle_used) >= 1\n"
        ),
        "invocation": "depot_only_once(vehicle_used)",
    }

    result = build_registry().call("add_constraints", session, {"constraints": [constraint]})

    assert result["ok"], result.get("error")
    assert session.source != original
    assert "depot_only_once" in session.source
    assert CVRP.read_text(encoding="utf-8") == original
    assert Path(result["path"]).exists()


def test_add_constraints_rejects_a_vacuous_constraint(session: Session) -> None:
    constraint = {
        "name": "always_true",
        "code": "def always_true(arcs: DSList(N_ARCS, DSInt(0, 1))):\n    assert True\n",
        "invocation": "always_true(arcs)",
    }
    result = build_registry().call("add_constraints", session, {"constraints": [constraint]})
    assert not result["ok"]
    assert "does not constrain anything" in result["error"]


def test_run_lns_tool_captures_warm_start(session: Session) -> None:
    """A feasible LNS run stores a transient warm start for the next /solve."""
    original_source = session.source

    result = build_registry().call(
        "run_lns", session, {"iterations": 60, "initializer": "cvrp"}
    )

    assert result["ok"], result.get("error")
    assert result["warmStartSaved"] is True
    assert session.warm_start is not None
    assert session.warm_start["hints"]
    assert session.warm_start["upper_bound"] == result["objectiveValue"]
    assert session.warm_start_path is not None
    assert session.warm_start_path.exists()
    # The original problem file and the session source are untouched.
    assert session.path.read_text(encoding="utf-8") == original_source
    assert session.source == original_source


def test_solve_minizinc_applies_session_warm_start(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """solve_minizinc hands the captured warm start to the backend."""
    from hybrid.warm_start import spec_from_assignment

    captured: dict[str, object] = {}

    class FakeSolver:
        def __init__(self, code, **kwargs):
            captured["code"] = code
            captured["kwargs"] = kwargs

        def run(self):
            return {
                "objectives": [5.0],
                "objective_bound": 5.0,
                "status": "OPTIMAL_SOLUTION",
                "total_time": 0.1,
                "best_solution": {"x": 1},
                "statistics": {},
            }

    monkeypatch.setattr("src.optdsl.solver.DSL_solver.DSLSolver", FakeSolver)

    session.warm_start = spec_from_assignment(
        {"arcs": [1]}, score=7, objective_sense="minimize"
    )

    result = build_registry().call("solve_minizinc", session, {})
    assert result["ok"]
    assert result["warmStart"] is True
    assert captured["kwargs"]["warm_start"] == session.warm_start

    # Without a warm start the backend gets None.
    session.warm_start = None
    result = build_registry().call("solve_minizinc", session, {})
    assert result["ok"]
    assert result["warmStart"] is False
    assert captured["kwargs"]["warm_start"] is None


def test_compare_runs_needs_both_runs(session: Session) -> None:
    result = build_registry().call("compare_runs", session, {})
    assert not result["ok"]
    assert "no LNS run" in result["error"]


def test_compare_runs_computes_a_gap(session: Session) -> None:
    session.last_lns = {"objectiveValue": 120.0, "objectiveSense": "minimize", "feasible": True}
    session.last_solve = {"objectiveValue": 100.0, "status": "OPTIMAL_SOLUTION"}

    result = build_registry().call("compare_runs", session, {})
    assert result["ok"]
    assert result["gap"] == 20.0
    assert result["relativeGap"] == pytest.approx(0.2)


def test_compare_runs_flips_the_sign_for_maximization(session: Session) -> None:
    session.last_lns = {"objectiveValue": 80.0, "objectiveSense": "maximize", "feasible": True}
    session.last_solve = {"objectiveValue": 100.0, "status": "OPTIMAL_SOLUTION"}

    result = build_registry().call("compare_runs", session, {})
    assert result["gap"] == 20.0


def test_compare_runs_reports_lower_bound_and_pct_gaps(session: Session) -> None:
    session.last_lns = {"objectiveValue": 120.0, "objectiveSense": "minimize", "feasible": True}
    session.last_solve = {"objectiveValue": 100.0, "objectiveBound": 90.0, "status": "OPTIMAL_SOLUTION"}

    result = build_registry().call("compare_runs", session, {})
    assert result["ok"]
    assert result["lowerBound"] == 90.0
    assert result["lnsVsSolvePct"] == pytest.approx(0.2)
    assert result["lnsVsBoundPct"] == pytest.approx((120 - 90) / 90)
    assert result["solveVsBoundPct"] == pytest.approx((100 - 90) / 90)


def test_compare_command_renders_the_report(session: Session) -> None:
    session.last_lns = {"objectiveValue": 120.0, "objectiveSense": "minimize", "feasible": True}
    session.last_solve = {"objectiveValue": 100.0, "objectiveBound": 90.0, "status": "OPTIMAL_SOLUTION"}

    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    report = run_command("/compare", session, loop, session.config)

    assert "LNS objective:    120" in report.text
    assert "solve objective:  100" in report.text
    assert "solve lower bound:90" in report.text
    assert "LNS vs solve: 20.00%" in report.text
    assert "LNS vs bound: 33.33%" in report.text
    assert "solve vs bound: 11.11%" in report.text


def test_turn_trace_renders_tool_activity() -> None:
    """The grey trace shows each tool call and the final reply, capped."""  # noqa: D400
    from optdsl_agent.agent import Turn
    from optdsl_agent.commands import _turn_trace

    turn = Turn(
        request="/add capacity",
        tool_calls=[
            {"name": "propose_constraints", "arguments": {"constraints": 2}, "ok": True,
             "summary": "constraints are valid"},
            {"name": "add_constraints", "arguments": {"constraints": 2}, "ok": True,
             "summary": "added 2 constraint(s)"},
        ],
        final_text="The capacity constraint is now enforced.",
    )
    trace = _turn_trace(turn)
    assert trace is not None
    assert "-> propose_constraints(constraints=2) ok" in trace
    assert "-> add_constraints(constraints=2) ok" in trace
    assert "added 2 constraint(s)" in trace
    assert "capacity constraint" in trace

    empty = _turn_trace(Turn(request="hi", tool_calls=[], final_text=""))
    assert empty is None


def test_add_command_returns_a_trace(session: Session) -> None:
    """``/add`` surfaces the agent's tool activity in a light-grey trace."""
    from optdsl_agent.commands import run_command

    client = StubClient(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="1",
                        name="propose_constraints",
                        arguments={"constraints": [{"name": "x"}]},
                    )
                ],
                finish_reason="tool_calls",
            ),
            LLMResponse(content="Added the constraint.", finish_reason="stop"),
        ]
    )
    loop = AgentLoop(session, client)
    result = run_command("/add enforce something", session, loop, session.config)

    assert "Added the constraint." in result.text
    assert result.trace is not None
    assert "propose_constraints" in result.trace


def test_solve_command_accepts_a_timelimit_argument(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``/solve 7.5`` forwards the timeout to the exact backend."""
    from optdsl_agent import tools
    from optdsl_agent.commands import run_command

    captured: dict[str, object] = {}

    def fake_solve(session_, *, solver=None, timelimit=None):
        captured["timelimit"] = timelimit
        return {"ok": True, "status": "OPTIMAL_SOLUTION", "objectiveValue": 1.0, "objectiveBound": 1.0}

    monkeypatch.setattr(tools, "_solve_minizinc", fake_solve)

    registry = build_registry()
    loop = AgentLoop(session, StubClient(), registry=registry)

    ok = run_command("/solve 7.5", session, loop, session.config)
    assert captured["timelimit"] == 7.5
    assert "OPTIMAL_SOLUTION" in ok.text

    default = run_command("/solve", session, loop, session.config)
    assert captured["timelimit"] is None

    bad = run_command("/solve not-a-number", session, loop, session.config)
    assert "not a number" in bad.text


def test_save_exports_model_and_transcript(session: Session) -> None:
    """``/save`` writes the model as a .dsl plus the session transcript."""
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    result = run_command("/save", session, loop, session.config)

    dsl_path = Path(result.artifacts[0])
    json_path = Path(result.artifacts[1])
    assert dsl_path.read_text(encoding="utf-8") == session.source
    assert json_path.exists()
    assert "random_euclidean_cvrp_8.dsl" in dsl_path.name
    assert dsl_path.name.endswith(".dsl")


def test_new_command_resets_to_an_empty_problem(session: Session) -> None:
    """``/new`` discards the model, results and warm start; keeps the budget."""
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    loop.run("preload some context")
    session.last_solve = {"ok": True}
    session.last_lns = {"ok": True}
    session.warm_start = {"hints": {"arcs": [1]}}
    session.warm_start_path = Path("out/ws.json")
    session.pending_constraints = [{"name": "c1"}]

    result = run_command("/new", session, loop, session.config)

    assert "new empty problem" in result.text
    assert session.source == ""
    assert session.path is None
    assert session.last_solve is None
    assert session.last_lns is None
    assert session.warm_start is None
    assert session.warm_start_path is None
    assert session.pending_constraints == []
    assert session.label == "new empty problem"
    # The agent conversation is cleared to just the system prompt.
    assert len(loop.messages) == 1


def test_describe_command_adopts_a_generated_model(session: Session) -> None:
    """/describe generates, validates, adopts and saves a new model."""
    from optdsl_agent.commands import run_command

    generated = (
        "N_ITEMS : int = 3\n"
        "BIN_CAPACITY : int = 5\n"
        "x: DSList(N_ITEMS, DSInt(0, 1))\n"
        "def all_inside(x: DSList(N_ITEMS, DSInt(0, 1))):\n"
        "    total = 0\n"
        "    for i in range(N_ITEMS):\n"
        "        total = total + x[i]\n"
        "    assert total <= BIN_CAPACITY\n"
        "all_inside(x)\n"
        "objective: DSInt(0, N_ITEMS) = 0\n"
        "minimize(objective)\n"
    )
    client = StubClient(
        [LLMResponse(content=json.dumps({"source": generated}), finish_reason="stop")]
    )
    loop = AgentLoop(session, client)
    result = run_command("/describe 3 items, capacity 5, minimize count", session, loop, session.config)

    assert "generated and adopted" in result.text
    assert session.source == generated
    assert session.path is None
    assert "N_ITEMS : int = 3" in Path(result.artifacts[0]).read_text(encoding="utf-8")
    assert session.last_solve is None


def test_describe_command_rejects_an_invalid_model(session: Session) -> None:
    """/describe surfaces validation errors instead of adopting garbage."""
    from optdsl_agent.commands import run_command

    client = StubClient(
        [LLMResponse(content=json.dumps({"source": "def broken(:\n  assert"}), finish_reason="stop")]
    )
    loop = AgentLoop(session, client)
    result = run_command("/describe a broken model", session, loop, session.config)

    assert "does not validate" in result.text
    assert session.source != ""  # still the previously loaded CVRP file
    assert "does not parse" in result.text


def test_describe_command_adopts_a_dsbool_model(session: Session) -> None:
    """/describe adopts a model whose binary flags are DSBool().

    The LNS importer normalises ``DSBool()`` to an integer {0, 1} decision
    domain (like ``DSInt(0, 1)``), so such a model is valid and must be
    adopted without any corrective retry.
    """
    from optdsl_agent.commands import run_command

    generated = (
        "N_ITEMS : int = 3\n"
        "BIN_CAPACITY : int = 5\n"
        "flag: DSList(N_ITEMS, DSBool())\n"
        "def count_ones(flag: DSList(N_ITEMS, DSBool())):\n"
        "    total = 0\n"
        "    for i in range(N_ITEMS):\n"
        "        total = total + flag[i]\n"
        "    return total\n"
        "def all_inside(flag: DSList(N_ITEMS, DSBool())):\n"
        "    total = 0\n"
        "    for i in range(N_ITEMS):\n"
        "        total = total + flag[i]\n"
        "    assert total <= BIN_CAPACITY\n"
        "all_inside(flag)\n"
        "objective: DSInt(0, N_ITEMS) = count_ones(flag)\n"
        "minimize(objective)\n"
    )
    client = StubClient(
        [LLMResponse(content=json.dumps({"source": generated}), finish_reason="stop")]
    )
    loop = AgentLoop(session, client)

    result = run_command("/describe 3 items with binary flags, capacity 5", session, loop, session.config)

    assert "generated and adopted" in result.text
    assert session.source == generated
    assert len(client.calls) == 1  # adopted directly, no corrective retry
    assert result.artifacts

    # And the adopted model is actually searchable by LNS.
    from optdsl_agent.lns_runner import LNSRunConfig, run_lns

    materialised = session.config.output_dir / "describe.dsl"
    session.config.ensure_directories()
    materialised.write_text(session.source, encoding="utf-8")
    outcome = run_lns(LNSRunConfig(instance=materialised, seed=0, iterations=20, initializer="auto"))
    assert outcome.feasible


def test_extract_model_source_handles_common_replies() -> None:
    from optdsl_agent.commands import _extract_model_source

    # Plain JSON
    assert _extract_model_source('{"source": "N : int = 1\\nminimize(0)"}') == "N : int = 1\nminimize(0)"
    # Fenced JSON
    fenced = '```json\n{"source": "objective: DSInt(0, 1) = 0\\nminimize(objective)"}\n```'
    src = _extract_model_source(fenced)
    assert src == "objective: DSInt(0, 1) = 0\nminimize(objective)"
    # Bare fenced DSL
    assert "N : int" in _extract_model_source("```\nN : int = 2\n```")
    # Garbage
    assert _extract_model_source("") is None
    assert _extract_model_source("sorry, could not") is None
    # JSON without a source key is treated as invalid (not adopted as text)
    assert _extract_model_source('{"nope": 1}') is None


def test_resolve_description_reads_inline_or_file(tmp_path: Path) -> None:
    """``/describe`` accepts inline text, a whole file, or one ``#``-headed section."""
    from optdsl_agent.commands import _extract_section, _resolve_description

    # Inline text is passed through untouched.
    assert _resolve_description("8 cities, 4 vehicles", cwd=tmp_path) == (
        "8 cities, 4 vehicles",
        None,
    )

    examples = tmp_path / "examples.txt"
    examples.write_text(
        "# cutting stock\nrandom small cutting stock problem\n\n"
        "# Capacitated lot-sizing\nA plant makes 3 products over 4 periods.\n"
        "Total production per period <= 8.\n",
        encoding="utf-8",
    )

    whole, label = _resolve_description(f"@{examples}", cwd=tmp_path)
    assert label == str(examples)
    assert "random small cutting stock problem" in whole
    assert "Total production per period <= 8." in whole

    section, label = _resolve_description(f"@{examples}:Capacitated lot-sizing", cwd=tmp_path)
    assert label == str(examples)
    assert section == "A plant makes 3 products over 4 periods.\nTotal production per period <= 8."
    assert "cutting stock" not in section

    # Section titles are matched case-insensitively.
    section, _ = _resolve_description(f"@{examples}:capacitated lot-sizing", cwd=tmp_path)
    assert section.startswith("A plant makes")

    # Missing file / missing section produce user-facing errors.
    with pytest.raises(FileNotFoundError):
        _resolve_description("@nope.txt", cwd=tmp_path)
    with pytest.raises(ValueError, match="not found"):
        _resolve_description(f"@{examples}:NoSuch", cwd=tmp_path)


def test_extract_section_empty_file_raises(tmp_path: Path) -> None:
    from optdsl_agent.commands import _extract_section

    with pytest.raises(ValueError):
        _extract_section("just prose, no headers", "anything")


def test_describe_command_reads_a_multiline_file(session: Session, tmp_path: Path) -> None:
    """/describe @file:Section feeds the file body to the model and adopts it."""
    from optdsl_agent.commands import run_command

    description_file = tmp_path / "examples.txt"
    description_file.write_text(
        "# Capacitated lot-sizing\n"
        "A plant makes 3 products over 4 periods.\n"
        "Total production per period may not exceed 8 units.\n",
        encoding="utf-8",
    )

    generated = (
        "N_ITEMS : int = 3\n"
        "BIN_CAPACITY : int = 5\n"
        "x: DSList(N_ITEMS, DSInt(0, 1))\n"
        "def capacity_ok(x: DSList(N_ITEMS, DSInt(0, 1))):\n"
        "    total = 0\n"
        "    for i in range(N_ITEMS):\n"
        "        total = total + x[i]\n"
        "    assert total <= BIN_CAPACITY\n"
        "capacity_ok(x)\n"
        "objective: DSInt(0, N_ITEMS) = 0\n"
        "minimize(objective)\n"
    )
    client = StubClient(
        [LLMResponse(content=json.dumps({"source": generated}), finish_reason="stop")]
    )
    loop = AgentLoop(session, client)
    result = run_command(
        f"/describe @{description_file}:Capacitated lot-sizing",
        session,
        loop,
        session.config,
    )

    assert "generated and adopted" in result.text
    assert session.source == generated
    assert "model generated from" in result.trace
    assert str(description_file) in result.trace


def test_describe_command_reports_a_missing_file(session: Session, tmp_path: Path) -> None:
    """/describe @missing.txt is reported, not raised."""
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    result = run_command("/describe @does_not_exist.txt", session, loop, session.config)

    assert "could not load description" in result.text
    assert "not found" in result.text


def test_translator_rejects_unannotated_list_parameters() -> None:
    """A predicate parameter used as a list but left unannotated must fail
    with a clear message instead of producing broken MiniZinc."""
    from src.optdsl.solver.DSL_solver import DSLSolver

    source = (
        "N : int = 2\n"
        "x: DSList(N, DSInt(0, 5))\n"
        "def bad(x):\n"  # no annotation, but subscripted below
        "    total = 0\n"
        "    for i in range(N):\n"
        "        total = total + x[i]\n"
        "    assert total >= 0\n"
        "bad(x)\n"
        "objective: DSInt(0, 50) = 0\n"
        "minimize(objective)\n"
    )
    with pytest.raises(ValueError, match="used as a list in the body but has no type annotation"):
        DSLSolver(source).translate()

    # The same predicate with the parameter annotated translates fine.
    fixed = source.replace(
        "def bad(x):\n",
        "def bad(x: DSList(N, DSInt(0, 5))):\n",
    )
    assert "predicate bad" in DSLSolver(fixed).translate()


def test_model_prompt_demands_annotated_parameters() -> None:
    """Generation prompts must require explicit OptDSL parameter annotations."""
    from optdsl_agent.prompts import build_constraint_prompt, build_model_prompt

    assert "MUST carry an explicit OptDSL type annotation" in build_model_prompt("x")
    assert "explicit OptDSL type annotation" in build_constraint_prompt("digest", "request")


def test_model_prompt_demands_optdsl_not_other_languages() -> None:
    """The /describe prompt must pin the output format to OptDSL."""
    from optdsl_agent.prompts import build_constraint_prompt, build_model_prompt

    prompt = build_model_prompt("bin packing")

    # Positive requirements.
    for need in ("OptDSL", "DSList", "DSInt", "minimize(", "assert", "Index base is 0"):
        assert need in prompt
    # Foreign formats must be explicitly forbidden.
    for forbidden in ("var int", "solve minimize", "array[1.."):
        assert forbidden in prompt
    # Loops: `range` is allowed in OptDSL formulations.
    assert "range(N_ITEMS)" in prompt
    assert "never use `range`" not in prompt
    assert "never use `range`" not in build_constraint_prompt("digest", "request")

    # The embedded working example must itself be valid OptDSL: it parses
    # cleanly and translates to MiniZinc.
    from optdsl_tooling.analysis import analyze
    from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator

    example = (
        "N_ITEMS : int = 3\n"
        "BIN_CAPACITY : int = 5\n"
        "x: DSList(N_ITEMS, DSInt(0, 1))\n"
        "def capacity_ok(x: DSList(N_ITEMS, DSInt(0, 1))):\n"
        "    total = 0\n"
        "    for i in range(N_ITEMS):\n"
        "        total = total + x[i]\n"
        "    assert total <= BIN_CAPACITY\n"
        "capacity_ok(x)\n"
        "objective: DSInt(0, N_ITEMS) = 0\n"
        "minimize(objective)\n"
    )
    assert analyze(example).syntax_error is None
    MiniZincTranslator(example, dsl_index_base=0).unroll_translation()  # must not raise


# ---------------------------------------------------------------------------
# agent loop
# ---------------------------------------------------------------------------


def test_agent_loop_dispatches_a_tool_call(session: Session) -> None:
    client = StubClient(
        [
            LLMResponse(
                tool_calls=[ToolCall(id="1", name="analyze_model", arguments={})],
                finish_reason="tool_calls",
            ),
            LLMResponse(content="The model is a CVRP.", finish_reason="stop"),
        ]
    )

    turn = AgentLoop(session, client).run("What is this model?")

    assert turn.final_text == "The model is a CVRP."
    assert turn.tool_calls[0]["name"] == "analyze_model"
    assert turn.tool_calls[0]["ok"]


def test_agent_loop_feeds_tool_results_back(session: Session) -> None:
    client = StubClient(
        [
            LLMResponse(
                tool_calls=[ToolCall(id="1", name="analyze_model", arguments={})],
                finish_reason="tool_calls",
            ),
            LLMResponse(content="done", finish_reason="stop"),
        ]
    )

    AgentLoop(session, client).run("analyse")

    tool_messages = [m for m in client.calls[-1] if m.get("role") == "tool"]
    assert tool_messages
    assert "arcs" in tool_messages[0]["content"]


def test_agent_loop_stops_when_the_llm_budget_is_exhausted(session: Session) -> None:
    session.config.budget = Budget(max_llm_calls=0)
    turn = AgentLoop(session, StubClient()).run("anything")
    assert turn.stopped_reason == "max_llm_calls"


def test_agent_loop_stops_after_too_many_tool_steps(session: Session) -> None:
    """A model that never concludes must not loop forever."""
    script = [
        LLMResponse(
            tool_calls=[ToolCall(id=str(i), name="analyze_model", arguments={})],
            finish_reason="tool_calls",
        )
        for i in range(20)
    ]
    turn = AgentLoop(session, StubClient(script)).run("loop forever")
    assert turn.stopped_reason == "max_steps"


def test_agent_loop_reports_llm_errors(session: Session) -> None:
    class Failing:
        def chat(self, messages, tools=None):
            from optdsl_agent.llm import LLMError

            raise LLMError("endpoint down")

    turn = AgentLoop(session, Failing()).run("hello")
    assert turn.stopped_reason == "llm_error"
    assert "endpoint down" in turn.final_text


def test_agent_loop_reset_keeps_the_model(session: Session) -> None:
    loop = AgentLoop(session, StubClient())
    loop.run("hello")
    loop.reset()
    assert len(loop.messages) == 1
    assert session.source


# ---------------------------------------------------------------------------
# tuning
# ---------------------------------------------------------------------------


def test_evaluate_operator_multi_rejects_invalid_source(config: AgentConfig) -> None:
    score = evaluate_operator_multi(
        "not python(", "destroy", [CVRP], (0,), repo_root=config.repo_root
    )
    assert score.runs == 0
    assert score.mean_improvement == 0.0


def test_evaluate_operator_multi_measures_a_real_operator(config: AgentConfig) -> None:
    source = (
        "from dataclasses import dataclass\n"
        "from large_neighborhood_search.components import DestroyOperator\n"
        "from large_neighborhood_search._utils import set_decision_value\n"
        "\n"
        "@dataclass\n"
        "class HalfDestroy(DestroyOperator):\n"
        "    fraction: float = 0.3\n"
        "\n"
        "    def destroy(self, assignment, context):\n"
        "        rng = context.extra['rng']\n"
        "        keys = list(context.extra['decision_keys'])\n"
        "        count = max(1, int(len(keys) * self.fraction))\n"
        "        for key in rng.sample(keys, count):\n"
        "            set_decision_value(assignment, key, None)\n"
        "        return assignment\n"
    )

    score = evaluate_operator_multi(
        source, "destroy", [CVRP], (0,), repo_root=config.repo_root, iterations=20
    )
    assert score.runs == 1
    assert score.name == "HalfDestroy"


def test_tune_without_a_client_reports_baselines(config: AgentConfig) -> None:
    report = tune([CVRP], config, client=None, budget=TuningBudget(iterations=20))
    assert report.baseline_lns
    assert report.diagnosis
    assert report.stopped_reason == "no model client; diagnosis only"


def test_tune_dry_run_stops_before_synthesis(config: AgentConfig) -> None:
    config.dry_run = True
    report = tune([CVRP], config, client=StubClient(), budget=TuningBudget(iterations=20))
    assert report.stopped_reason == "dry run; baselines and diagnosis only"
    assert report.attempts == []


def test_tune_report_renders_markdown(config: AgentConfig) -> None:
    report = tune([CVRP], config, client=None, budget=TuningBudget(iterations=20))
    markdown = report.to_markdown()
    assert "# LNS tuning report" in markdown
    assert "## Diagnosis" in markdown


def test_tune_report_is_json_serialisable(config: AgentConfig) -> None:
    report = tune([CVRP], config, client=None, budget=TuningBudget(iterations=20))
    json.dumps(report.to_dict())  # must not raise


def test_tune_reports_baseline_and_diagnosis_progress(config: AgentConfig) -> None:
    """Long tuning phases stream progress messages instead of hanging silently."""
    messages: list[str] = []
    tune([CVRP], config, client=None, budget=TuningBudget(iterations=20), progress=messages.append)

    assert any("baseline LNS objective" in message for message in messages)
    assert any("diagnosis" in message for message in messages)


def test_tune_command_forwards_progress_and_budget(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/tune hands the progress callback and attempt count to the tuner."""
    from optdsl_agent import commands
    from optdsl_agent.commands import run_command
    from optdsl_agent.tuning import TuningReport

    seen: list[str] = []
    captured: dict[str, object] = {}

    def fake_tune(instances, config, *, client=None, budget=None, progress=None, **kwargs):
        captured["instances"] = instances
        captured["budget"] = budget
        captured["client"] = client
        if progress is not None:
            progress("plan: step 1")
            progress("plan: step 2")
        return TuningReport(instances=[str(path) for path in instances])

    monkeypatch.setattr(commands, "tune", fake_tune)

    loop = AgentLoop(session, StubClient())
    result = run_command("/tune 3", session, loop, session.config, progress=seen.append)

    assert seen[0].startswith("tuning plan:")
    assert seen[1:] == ["plan: step 1", "plan: step 2"]
    assert captured["instances"] == [session.path]
    assert captured["budget"].max_attempts == 3  # type: ignore[union-attr]
    assert captured["budget"].max_wall_seconds == 900  # type: ignore[union-attr]
    assert "# LNS tuning report" in result.text

    # Unsaved edits: /tune must tune the in-memory model (the one /lns keys its
    # tuned config by), not the stale file on disk.
    session.source = session.source + "\n# edited in the session\n"
    run_command("/tune 1", session, loop, session.config, progress=seen.append)
    tuned_path = captured["instances"][0]  # type: ignore[index]
    assert tuned_path != session.path
    assert Path(tuned_path).read_text(encoding="utf-8") == session.source


# ---------------------------------------------------------------------------
# harness regression: objective sense
# ---------------------------------------------------------------------------


def test_run_metrics_improvement_is_sense_aware() -> None:
    """A maximization improvement must be positive, not negative."""
    from operator_synthesis.harness import RunMetrics

    minimize = RunMetrics(ok=True, baseline_score=100.0, best_score=80.0)
    assert minimize.improvement == 20.0

    maximize = RunMetrics(
        ok=True, baseline_score=80.0, best_score=100.0, objective_sense="maximize"
    )
    assert maximize.improvement == 20.0


def test_contract_reference_lists_context_keys() -> None:
    """The prompt contract must name real context keys, not docstring characters."""
    from operator_synthesis.prompts import contract_reference

    keys = contract_reference()["context_keys"]
    assert "decision_keys" in keys
    assert "rng" in keys


def test_harness_auto_initializer_is_feasible_on_cvrp() -> None:
    """The generic greedy initializer cannot build a feasible CVRP assignment.

    With it, the baseline score is a penalty and no candidate can ever show an
    improvement, so every operator is rejected for the wrong reason.
    """
    from operator_synthesis.harness import run_candidate

    source = (
        "from dataclasses import dataclass\n"
        "from large_neighborhood_search.components import DestroyOperator\n"
        "from large_neighborhood_search._utils import set_decision_value\n"
        "\n"
        "@dataclass\n"
        "class NoopDestroy(DestroyOperator):\n"
        "    def destroy(self, assignment, context):\n"
        "        return assignment\n"
    )

    auto = run_candidate(
        source, "NoopDestroy", "destroy", CVRP,
        repo_root=REPO_ROOT, iterations=10, initializer="auto",
    )
    greedy = run_candidate(
        source, "NoopDestroy", "destroy", CVRP,
        repo_root=REPO_ROOT, iterations=10, initializer="greedy",
    )

    assert auto.ok and greedy.ok
    # The auto baseline is a real objective; the greedy one is a penalty.
    assert auto.baseline_score is not None and auto.baseline_score < 1e9
    assert greedy.baseline_score is not None and greedy.baseline_score >= 1e9


def test_evaluate_operator_multi_threads_the_partner() -> None:
    """The partner operator must actually reach the harness run."""
    from optdsl_agent.tuning import evaluate_operator_multi

    source = (
        "from dataclasses import dataclass\n"
        "from large_neighborhood_search.components import RepairOperator\n"
        "from large_neighborhood_search._utils import get_decision_value, set_decision_value\n"
        "\n"
        "@dataclass\n"
        "class ArcFillRepair(RepairOperator):\n"
        "    def repair(self, partial_assignment, context):\n"
        "        rng = context.extra['rng']\n"
        "        domains = context.extra['decision_domains']\n"
        "        for key in context.extra['decision_keys']:\n"
        "            if get_decision_value(partial_assignment, key) is None:\n"
        "                lo, hi = domains[key]\n"
        "                set_decision_value(partial_assignment, key, rng.randint(lo, hi))\n"
        "        return partial_assignment\n"
    )

    default = evaluate_operator_multi(
        source, "repair", [CVRP], (0,), repo_root=REPO_ROOT, iterations=20
    )
    partnered = evaluate_operator_multi(
        source, "repair", [CVRP], (0,), repo_root=REPO_ROOT, iterations=20,
        partner="NoSuchPartnerDestroy",
    )

    assert default.runs == 1 and partnered.runs == 1
    assert default.per_run[0]["ok"], default.per_run
    # The run resolves the partner by name inside the harness subprocess, so an
    # unknown name must fail there; a successful run would mean the partner
    # argument was silently ignored.
    assert not partnered.per_run[0]["ok"]
    assert "NoSuchPartnerDestroy" in (partnered.per_run[0]["error"] or "")


def test_partner_for_known_problem_classes() -> None:
    from optdsl_agent.tuning import _partner_for

    assert _partner_for("cvrp", "destroy") == "CVRPInsertionRepair"
    assert _partner_for("cvrp", "repair") == "CVRPShawDestroy"
    assert _partner_for("unknown", "destroy") is None
    assert _partner_for(None, "destroy") is None


# ---------------------------------------------------------------------------
# model configuration
# ---------------------------------------------------------------------------


def test_harness_progress_mode_accepts_penalty_reduction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """In feasibility-progress mode, a candidate that cuts the infeasibility
    penalty is accepted even at a low feasible-candidate rate."""
    from operator_synthesis import harness as h
    from operator_synthesis.harness import AcceptancePolicy, RunMetrics, evaluate_candidate

    source = (
        "from large_neighborhood_search.components import DestroyOperator\n"
        "class TrivialDestroy(DestroyOperator):\n"
        "    def destroy(self, assignment, context):\n"
        "        return dict(assignment)\n"
    )
    # Candidate run: penalty 100 -> 50 (positive improvement), but never feasible.
    monkeypatch.setattr(
        h,
        "run_candidate",
        lambda *a, **k: RunMetrics(
            ok=True,
            iterations=10,
            feasible_candidates=0,
            infeasible_candidates=10,
            baseline_score=100.0,
            best_score=50.0,
            mean_cleared_fraction=0.4,
            mean_completion_fraction=1.0,
            elapsed_seconds=0.1,
        ),
    )

    instance = tmp_path / "m.dsl"
    instance.write_text("N : int = 2\nx: DSList(N, DSInt(0, 5))\nminimize(0)\n", encoding="utf-8")

    strict = evaluate_candidate(
        source, "destroy", instance, repo_root=REPO_ROOT,
        policy=AcceptancePolicy(min_feasible_rate=0.5),
    )
    assert not strict.accepted
    assert any("feasible candidate rate" in r for r in strict.reasons)

    progress = evaluate_candidate(
        source, "destroy", instance, repo_root=REPO_ROOT,
        policy=AcceptancePolicy(feasibility_progress_mode=True),
    )
    assert progress.accepted, progress.reasons

    # No penalty reduction => still rejected in progress mode.
    monkeypatch.setattr(
        h,
        "run_candidate",
        lambda *a, **k: RunMetrics(
            ok=True,
            iterations=10,
            feasible_candidates=0,
            infeasible_candidates=10,
            baseline_score=100.0,
            best_score=100.0,
            mean_cleared_fraction=0.4,
            mean_completion_fraction=1.0,
            elapsed_seconds=0.1,
        ),
    )
    stagnant = evaluate_candidate(
        source, "destroy", instance, repo_root=REPO_ROOT,
        policy=AcceptancePolicy(feasibility_progress_mode=True),
    )
    assert not stagnant.accepted
    assert any("infeasibility penalty" in r for r in stagnant.reasons)


def test_api_key_flag_reaches_the_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """--api-key must override the environment, not be ignored."""
    from optdsl_agent.cli import main

    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    captured: dict[str, object] = {}

    original = AgentConfig.from_env.__func__

    def spy(cls, **overrides):
        config = original(cls, **overrides)
        captured["api_key"] = config.api_key
        return config

    monkeypatch.setattr(AgentConfig, "from_env", classmethod(spy))

    main(["explain", str(JSSP), "--dry-run", "--api-key", "sk-from-flag"])
    assert captured["api_key"] == "sk-from-flag"


def test_chat_and_tui_can_start_without_a_file(config: AgentConfig) -> None:
    """Omit the file to start from an empty problem."""
    from argparse import Namespace

    from optdsl_agent.cli import _load_session

    empty = _load_session(Namespace(file=None), config)
    assert empty.path is None
    assert empty.source == ""
    assert empty.label == "new empty problem"

    loaded = _load_session(Namespace(file=JSSP), config)
    assert loaded.path == JSSP
    assert "minimize" in loaded.source or len(loaded.source) > 0


def test_cli_parser_accepts_chat_and_tui_without_a_file() -> None:
    """/`chat` and /`tui` no longer require a formulation argument."""
    from optdsl_agent.cli import _build_parser

    parser = _build_parser()
    assert parser.parse_args(["chat"]).file is None
    assert parser.parse_args(["tui"]).file is None
    assert parser.parse_args(["chat", "model.dsl"]).file.name == "model.dsl"


def test_api_key_env_is_provider_neutral(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPTDSL_AGENT_API_KEY is preferred over the OpenAI-named variable."""
    monkeypatch.setenv("OPTDSL_AGENT_API_KEY", "sk-neutral")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    assert AgentConfig.from_env().api_key == "sk-neutral"


def test_openai_api_key_still_works_as_a_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPTDSL_AGENT_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    assert AgentConfig.from_env().api_key == "sk-openai"


def test_api_key_is_redacted_in_serialised_config() -> None:
    config = AgentConfig(api_key="sk-secret")
    assert config.to_dict()["api_key"] == "***"
    assert "sk-secret" not in json.dumps(config.to_dict())


def test_client_sends_the_key_as_a_bearer_header() -> None:
    """The key must reach the wire, not just the config object."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from optdsl_agent.llm import LLMClient

    seen: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - stdlib naming
            seen["path"] = self.path
            seen["auth"] = self.headers.get("Authorization", "")
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            body = json.dumps(
                {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        config = AgentConfig(
            base_url=f"http://127.0.0.1:{port}/v1", api_key="sk-header-test", model="m"
        )
        response = LLMClient(config).chat([{"role": "user", "content": "hi"}])
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert response.content == "ok"
    assert seen["path"] == "/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-header-test"


def test_local_endpoint_needs_no_key() -> None:
    """A non-default base URL counts as configured, so Ollama works without a key."""
    config = AgentConfig(base_url="http://localhost:11434/v1", api_key=None)
    assert config.has_credentials


def test_default_endpoint_without_a_key_is_not_configured() -> None:
    config = AgentConfig(api_key=None)
    assert not config.has_credentials


# ---------------------------------------------------------------------------
# stored settings
# ---------------------------------------------------------------------------


@pytest.fixture()
def settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the settings module at a temp file so tests never touch the real one."""
    path = tmp_path / "settings.json"
    monkeypatch.setenv("OPTDSL_AGENT_SETTINGS", str(path))
    for variable in ("OPTDSL_AGENT_MODEL", "OPTDSL_AGENT_BASE_URL",
                     "OPTDSL_AGENT_API_KEY", "OPENAI_API_KEY", "OPTDSL_AGENT_PROFILE"):
        monkeypatch.delenv(variable, raising=False)
    return path


def test_settings_round_trip(settings_file: Path) -> None:
    from optdsl_agent.settings import Profile, Settings

    settings = Settings()
    settings.set_profile(
        "risc",
        Profile(model="m", base_url="http://host/v1", api_key="sk-1234567890"),
    )
    settings.default_profile = "risc"
    settings.save()

    loaded = Settings.load()
    assert loaded.default_profile == "risc"
    assert loaded.profile("risc").model == "m"
    assert loaded.profile("risc").api_key == "sk-1234567890"


def test_settings_missing_file_is_empty(settings_file: Path) -> None:
    from optdsl_agent.settings import Settings

    settings = Settings.load()
    assert settings.profiles == {}
    assert settings.profile("nope").is_empty()


def test_settings_corrupt_file_is_treated_as_empty(settings_file: Path) -> None:
    """A malformed file must not make the CLI unusable."""
    from optdsl_agent.settings import Settings

    settings_file.write_text("{not json", encoding="utf-8")
    assert Settings.load().profiles == {}


def test_settings_redacts_the_key(settings_file: Path) -> None:
    from optdsl_agent.settings import Profile, Settings

    settings = Settings()
    settings.set_profile("p", Profile(api_key="sk-abcdefghijkl"))
    payload = settings.to_dict(redact=True)
    assert payload["profiles"]["p"]["api_key"] == "sk-a...ijkl"
    assert "sk-abcdefghijkl" not in json.dumps(payload)


def test_settings_short_key_is_fully_masked(settings_file: Path) -> None:
    from optdsl_agent.settings import Profile

    assert Profile(api_key="short").to_dict(redact=True)["api_key"] == "***"


def test_stored_profile_is_used_when_nothing_else_is_set(settings_file: Path) -> None:
    from optdsl_agent.settings import Profile, Settings

    settings = Settings()
    settings.set_profile("p", Profile(model="stored-model", base_url="http://stored/v1"))
    settings.default_profile = "p"
    settings.save()

    config = AgentConfig.from_env()
    assert config.model == "stored-model"
    assert config.base_url == "http://stored/v1"


def test_environment_beats_the_stored_profile(
    settings_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CI job must be able to override a saved profile without editing it."""
    from optdsl_agent.settings import Profile, Settings

    settings = Settings()
    settings.set_profile("p", Profile(model="stored-model", api_key="sk-stored"))
    settings.default_profile = "p"
    settings.save()

    monkeypatch.setenv("OPTDSL_AGENT_MODEL", "env-model")
    monkeypatch.setenv("OPTDSL_AGENT_API_KEY", "sk-env")

    config = AgentConfig.from_env()
    assert config.model == "env-model"
    assert config.api_key == "sk-env"


def test_cli_flag_beats_the_stored_profile(settings_file: Path) -> None:
    from optdsl_agent.settings import Profile, Settings

    settings = Settings()
    settings.set_profile("p", Profile(model="stored-model"))
    settings.default_profile = "p"
    settings.save()

    assert AgentConfig.from_env(model="flag-model").model == "flag-model"


def test_named_profile_can_be_selected(settings_file: Path) -> None:
    from optdsl_agent.settings import Profile, Settings

    settings = Settings()
    settings.set_profile("a", Profile(model="model-a"))
    settings.set_profile("b", Profile(model="model-b"))
    settings.default_profile = "a"
    settings.save()

    assert AgentConfig.from_env().model == "model-a"
    assert AgentConfig.from_env(profile="b").model == "model-b"


def test_settings_cli_set_and_show(
    settings_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from optdsl_agent.cli import main

    assert main([
        "settings", "set", "risc",
        "--model", "m", "--base-url", "http://host/v1", "--api-key", "sk-1234567890",
    ]) == 0

    capsys.readouterr()
    assert main(["settings", "show"]) == 0
    output = capsys.readouterr().out
    assert "[risc]" in output
    assert "sk-1234567890" not in output
    assert "sk-1...7890" in output


def test_settings_cli_use_and_unset(
    settings_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from optdsl_agent.cli import main
    from optdsl_agent.settings import Settings

    main(["settings", "set", "a", "--model", "model-a"])
    main(["settings", "set", "b", "--model", "model-b"])

    assert main(["settings", "use", "b"]) == 0
    assert Settings.load().default_profile == "b"

    assert main(["settings", "unset", "b"]) == 0
    assert "b" not in Settings.load().profiles


def test_settings_cli_rejects_unknown_profile(
    settings_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from optdsl_agent.cli import main

    assert main(["settings", "use", "nope"]) == 1
    assert "no profile named" in capsys.readouterr().err


def test_settings_cli_set_requires_a_value(
    settings_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from optdsl_agent.cli import main

    assert main(["settings", "set", "empty"]) == 1
    assert "nothing to store" in capsys.readouterr().err


def test_settings_cli_path(settings_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from optdsl_agent.cli import main

    assert main(["settings", "path"]) == 0
    assert str(settings_file) in capsys.readouterr().out


# ---------------------------------------------------------------------------
# shared slash commands
# ---------------------------------------------------------------------------


def test_commands_are_shared_between_repl_and_tui(session: Session) -> None:
    """Both front-ends must produce identical output for the same command."""
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    result = run_command("/analyze", session, loop, session.config)
    assert "arcs" in result.text
    assert not result.unknown


def test_unknown_command_is_flagged(session: Session) -> None:
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    result = run_command("/nope", session, loop, session.config)
    assert result.unknown
    assert "unknown command" in result.text


def test_quit_command_signals_exit(session: Session) -> None:
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    assert run_command("/quit", session, loop, session.config).quit


def test_diff_reports_an_unchanged_model(session: Session) -> None:
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    assert "unchanged" in run_command("/diff", session, loop, session.config).text


def test_diff_shows_added_constraints(session: Session) -> None:
    from optdsl_agent.commands import run_command

    session.replace_source(session.source + "\n# a new comment\n")
    loop = AgentLoop(session, StubClient())
    diff = run_command("/diff", session, loop, session.config).text
    assert "+# a new comment" in diff


# ---------------------------------------------------------------------------
# TUI
# ---------------------------------------------------------------------------


def test_tui_reports_a_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without textual the CLI must explain how to install it, not crash."""
    import optdsl_agent.tui as tui_module

    monkeypatch.setattr(tui_module, "textual_available", lambda: False)
    assert tui_module.run_tui(None, None, AgentConfig()) == 2  # type: ignore[arg-type]


def test_tui_mounts_and_runs_a_slash_command(session: Session) -> None:
    """Mount the app headlessly and drive one command through it."""
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> tuple[bool, str]:
        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one("#prompt").value = "/analyze"
            await pilot.press("enter")
            await pilot.pause()
            log = app.query_one("#conversation")
            return bool(app.query_one("#digest-text").render()), "\n".join(
                str(line) for line in log.lines
            )

    digest_rendered, conversation = asyncio.run(drive())
    assert digest_rendered
    assert "arcs" in conversation


def test_tui_left_pane_toggles_between_digest_and_source(session: Session) -> None:
    """F4 swaps the left pane from the summary to the full source and back."""
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> tuple[str, str, str, bool, bool]:
        async with app.run_test() as pilot:
            await pilot.pause()
            text = app.query_one("#digest-text")
            pane = app.query_one("#digest")
            initial = text.render().plain
            assert app._left_view == "digest"

            await pilot.press("f4")
            await pilot.pause()
            source_view = text.render().plain
            in_source_state = app._left_view == "source"
            wide = pane.has_class("source-view")
            focusable = pane.can_focus

            await pilot.press("f4")
            await pilot.pause()
            back_to_digest = text.render().plain

            return initial, source_view, back_to_digest, wide, focusable

    initial, source_view, back_to_digest, wide, focusable = asyncio.run(drive())

    assert "Constants:" in initial
    assert "minimize `objective`" in initial
    assert "N_CITIES : int = 8" in source_view
    assert "# Random Euclidean CVRP instance" in source_view
    assert wide, "source view should widen the left pane"
    assert focusable, "the left pane must be focusable so it can be scrolled"
    assert "Constants:" in back_to_digest
    assert "N_CITIES : int = 8" not in back_to_digest


# ---------------------------------------------------------------------------
# command completion
# ---------------------------------------------------------------------------


def test_command_table_is_the_single_source_of_truth() -> None:
    """Help text must be generated from the table, not hand-maintained."""
    from optdsl_agent.commands import COMMANDS, HELP_TEXT

    for spec in COMMANDS:
        assert spec.signature in HELP_TEXT
        assert spec.help in HELP_TEXT


def test_matching_commands_with_empty_prefix_returns_all() -> None:
    from optdsl_agent.commands import COMMANDS, matching_commands

    assert len(matching_commands("/")) == len(COMMANDS)


def test_matching_commands_filters_by_prefix() -> None:
    from optdsl_agent.commands import matching_commands

    names = [spec.name for spec in matching_commands("/s")]
    assert names == ["solve", "solution", "save"]

    assert [spec.name for spec in matching_commands("/so")] == ["solve", "solution"]
    assert [spec.name for spec in matching_commands("/solv")] == ["solve"]


def test_matching_commands_accepts_a_bare_prefix() -> None:
    from optdsl_agent.commands import matching_commands

    assert [spec.name for spec in matching_commands("ln")] == ["lns"]


def test_matching_commands_is_case_insensitive() -> None:
    from optdsl_agent.commands import matching_commands

    assert [spec.name for spec in matching_commands("/LN")] == ["lns"]


def test_matching_commands_returns_nothing_for_an_unknown_prefix() -> None:
    from optdsl_agent.commands import matching_commands

    assert matching_commands("/zzz") == []


def test_complete_returns_the_common_prefix() -> None:
    """Tab should narrow the input, not cycle blindly."""
    from optdsl_agent.commands import complete

    replacement, matches = complete("/s")
    assert replacement == "/s"          # solve, solution and save share only "/s"
    assert len(matches) == 3

    replacement, matches = complete("/solv")
    assert replacement == "/solve"
    assert len(matches) == 1


def test_complete_ignores_arguments() -> None:
    """Once there is a space the user is writing an argument, not a command."""
    from optdsl_agent.commands import complete

    assert complete("/lns 500") == ("/lns 500", [])


def test_complete_ignores_plain_text() -> None:
    from optdsl_agent.commands import complete

    assert complete("why is this slow") == ("why is this slow", [])


def test_aliases_resolve_to_canonical_names() -> None:
    from optdsl_agent.commands import canonical_name

    assert canonical_name("/exit") == "quit"
    assert canonical_name("/quit") == "quit"
    assert canonical_name("/lns") == "lns"


def test_exit_alias_quits(session: Session) -> None:
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    assert run_command("/exit", session, loop, session.config).quit


def test_tui_popup_opens_on_slash(session: Session) -> None:
    """Typing '/' must show every command with its help."""
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.commands import COMMANDS
    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> tuple[bool, int, list[str]]:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("/")
            await pilot.pause()
            popup = app.query_one("#completions")
            return popup.has_class("visible"), popup.option_count, app._completion_names

    visible, count, names = asyncio.run(drive())
    assert visible
    assert count == len(COMMANDS)
    assert "analyze" in names


def test_tui_popup_filters_as_you_type(session: Session) -> None:
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> list[str]:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("/", "s")
            await pilot.pause()
            return app._completion_names

    assert asyncio.run(drive()) == ["solve", "solution", "save"]


def test_tui_popup_hides_for_arguments_and_unknown_prefixes(session: Session) -> None:
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> tuple[bool, bool]:
        async with app.run_test() as pilot:
            await pilot.pause()
            popup = app.query_one("#completions")

            await pilot.press("/", "l", "n", "s", " ", "5")
            await pilot.pause()
            hidden_with_args = not popup.has_class("visible")

            for _ in range(6):
                await pilot.press("backspace")
            await pilot.press("z", "z", "z")
            await pilot.pause()
            hidden_for_unknown = not popup.has_class("visible")

            return hidden_with_args, hidden_for_unknown

    hidden_with_args, hidden_for_unknown = asyncio.run(drive())
    assert hidden_with_args
    assert hidden_for_unknown


def test_tui_popup_navigates_and_accepts_with_tab(session: Session) -> None:
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> tuple[int, str, bool]:
        async with app.run_test() as pilot:
            await pilot.pause()
            popup = app.query_one("#completions")
            prompt = app.query_one("#prompt")

            await pilot.press("/")
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()
            highlighted = popup.highlighted

            await pilot.press("tab")
            await pilot.pause()
            return highlighted, prompt.value, not popup.has_class("visible")

    highlighted, value, hidden = asyncio.run(drive())
    assert highlighted == 1
    assert value == "/explain "
    assert hidden


def test_tui_popup_escape_dismisses_without_changing_input(session: Session) -> None:
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> tuple[bool, str]:
        async with app.run_test() as pilot:
            await pilot.pause()
            popup = app.query_one("#completions")
            prompt = app.query_one("#prompt")

            await pilot.press("/")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            return not popup.has_class("visible"), prompt.value

    hidden, value = asyncio.run(drive())
    assert hidden
    assert value == "/"


# ---------------------------------------------------------------------------
# event-loop safety
# ---------------------------------------------------------------------------


def test_solver_runs_inside_a_running_event_loop() -> None:
    """The TUI runs on an event loop; ``asyncio.run`` inside it used to fail.

    ``MiniZincRunner.run`` called ``asyncio.run`` directly, which raises
    "asyncio.run() cannot be called from a running event loop" whenever the
    solver is invoked from an async application.
    """
    import asyncio

    from src.optdsl.solver.DSL_solver import DSLSolver

    source = JSSP.read_text(encoding="utf-8")

    async def solve_inside_loop() -> dict:
        return DSLSolver(source, solver_name="cp-sat", timelimit=10).run()

    try:
        result = asyncio.run(solve_inside_loop())
    except Exception as exc:  # noqa: BLE001 - MiniZinc may be absent
        pytest.skip(f"MiniZinc unavailable: {exc}")

    assert result["status"] is not None
    assert result["objectives"]


def test_solver_still_runs_synchronously() -> None:
    """The fix must not break the ordinary CLI path."""
    from src.optdsl.solver.DSL_solver import DSLSolver

    source = JSSP.read_text(encoding="utf-8")
    try:
        result = DSLSolver(source, solver_name="cp-sat", timelimit=10).run()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"MiniZinc unavailable: {exc}")

    assert result["status"] is not None


def test_tui_solve_command_succeeds(session: Session) -> None:
    """``/solve`` in the TUI must produce a result, not an event-loop error."""
    pytest.importorskip("textual")
    import asyncio

    from optdsl_agent.tui import build_app

    app = build_app(session, StubClient(), session.config)

    async def drive() -> str:
        async with app.run_test() as pilot:
            await pilot.pause()
            for char in "/solve":
                await pilot.press(char)
            await pilot.press("enter")
            # The command runs on a worker thread; wait for it to finish.
            for _ in range(200):
                await pilot.pause(0.02)
                if not app._busy:
                    break
            log = app.query_one("#conversation")
            return "\n".join(str(line) for line in log.lines)

    conversation = asyncio.run(drive())
    if "MiniZinc" in conversation and "failed" in conversation:
        pytest.skip("MiniZinc unavailable in this environment")

    assert "asyncio.run() cannot be called" not in conversation
    assert "status" in conversation


def test_tui_commands_run_off_the_event_loop(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blocking command must not freeze the UI.

    ``/lns`` takes as long as the search runs. If it executed on the event loop
    the app could not repaint. A deliberately slow command makes that
    observable: the busy flag is set while the worker runs, and the UI keeps
    processing messages meanwhile.
    """
    pytest.importorskip("textual")
    import asyncio
    import time

    import optdsl_agent.tui as tui_module
    from optdsl_agent.commands import CommandResult
    from optdsl_agent.tui import build_app

    def slow_command(line, session_, loop_, config_, progress=None):
        time.sleep(0.3)
        if progress is not None:
            progress("slow command progress")
        return CommandResult(text="slow command finished")

    monkeypatch.setattr(tui_module, "run_command", slow_command)

    app = build_app(session, StubClient(), session.config)

    async def drive() -> tuple[bool, bool, str]:
        async with app.run_test() as pilot:
            await pilot.pause()
            for char in "/analyze":
                await pilot.press(char)
            await pilot.press("enter")
            await pilot.pause()

            busy_during = app._busy
            # The event loop must still be able to process messages while the
            # worker sleeps; if the command ran inline this would deadlock.
            await pilot.pause(0.05)
            responsive = app._busy

            for _ in range(200):
                await pilot.pause(0.02)
                if not app._busy:
                    break

            log = app.query_one("#conversation")
            return busy_during, responsive, "\n".join(str(line) for line in log.lines)

    busy_during, responsive, conversation = asyncio.run(drive())
    assert busy_during, "the command should have been dispatched to a worker"
    assert responsive, "the UI should stay responsive while the worker runs"
    assert "slow command finished" in conversation


# ---------------------------------------------------------------------------
# solution printers
# ---------------------------------------------------------------------------


def test_printers_cover_every_known_problem_class() -> None:
    """Every class the fingerprint can detect should have a printer."""
    from optdsl_tooling.fingerprint import PROBLEM_CLASSES

    from optdsl_agent.printers import supported_classes

    known = {problem.name for problem in PROBLEM_CLASSES}
    missing = known - set(supported_classes())
    assert not missing, f"no printer for: {sorted(missing)}"


def test_generic_printer_is_the_fallback() -> None:
    from optdsl_agent.printers import format_solution

    text = format_solution({"x": [1, 2, 3]}, {}, problem_class=None)
    assert "x (3 values)" in text


def test_generic_printer_truncates_long_vectors() -> None:
    from optdsl_agent.printers import format_solution

    text = format_solution({"x": list(range(500))}, {}, problem_class=None)
    assert "more" in text
    assert len(text) < 500


def test_printer_falls_back_when_constants_are_missing() -> None:
    """A printer that cannot interpret the data must not raise."""
    from optdsl_agent.printers import format_solution

    text = format_solution({"arcs": [0, 1]}, {}, problem_class="cvrp")
    assert "arcs" in text          # generic dump, not a crash


def test_cvrp_printer_shows_routes_and_loads() -> None:
    from optdsl_agent.printers import format_solution

    # Two cities, one vehicle: depot 0 -> customer 1 -> depot.
    # The arc matrix is indexed as arcs[vehicle * n * n + from * n + to].
    n, nv = 2, 1
    arcs = [0] * (nv * n * n)
    arcs[0 * n + 1] = 1          # 0 -> 1
    arcs[1 * n + 0] = 1          # 1 -> 0

    constants = {
        "N_CITIES": n,
        "N_VEHICLES": nv,
        "DEPOT": 0,
        "DEMANDS": [0, 4],
        "VEHICLE_CAPACITY": 10,
        "DISTANCE_MATRIX": [[0, 7], [7, 0]],
    }

    text = format_solution({"arcs": arcs}, constants, problem_class="cvrp")
    assert "vehicle 0: 0 -> 1 -> 0" in text
    assert "load 4/10" in text
    assert "distance 14" in text


def test_cvrp_printer_flags_capacity_violations() -> None:
    from optdsl_agent.printers import format_solution

    n, nv = 2, 1
    arcs = [0] * (nv * n * n)
    arcs[0 * n + 1] = 1
    arcs[1 * n + 0] = 1

    constants = {
        "N_CITIES": n,
        "N_VEHICLES": nv,
        "DEPOT": 0,
        "DEMANDS": [0, 99],
        "VEHICLE_CAPACITY": 10,
        "DISTANCE_MATRIX": [[0, 1], [1, 0]],
    }

    text = format_solution({"arcs": arcs}, constants, problem_class="cvrp")
    assert "OVER CAPACITY" in text


def test_jssp_printer_shows_a_valid_schedule() -> None:
    """The rendered schedule must match the completion matrix it came from."""
    from optdsl_agent.printers import format_solution

    constants = {
        "N_JOBS": 2,
        "N_MACHINES": 2,
        "PROCESSING_TIMES": [[3, 2], [2, 4]],
        "MACHINE_SEQUENCE": [[0, 1], [1, 0]],
    }
    completion = [[45, 47], [51, 53]]

    text = format_solution({"completion": completion}, constants, problem_class="jssp")

    assert "makespan 53" in text
    # Job 0 op 0 runs on machine 0 for 3 units, ending at 45.
    assert "J0.0[42-45]" in text
    # Job 1 op 0 runs on machine 1 for 4 units (PROCESSING_TIMES[1][1]), ending at 51.
    assert "J1.0[47-51]" in text


def test_jssp_printer_does_not_overlap_operations_on_a_machine() -> None:
    """A schedule with overlapping operations would be a lie; check the render."""
    from optdsl_agent.printers import format_solution

    constants = {
        "N_JOBS": 2,
        "N_MACHINES": 2,
        "PROCESSING_TIMES": [[3, 2], [2, 4]],
        "MACHINE_SEQUENCE": [[0, 1], [1, 0]],
    }
    completion = [[45, 47], [51, 53]]

    text = format_solution({"completion": completion}, constants, problem_class="jssp")

    import re

    for line in text.splitlines():
        if not line.strip().startswith("machine"):
            continue
        spans = [
            (int(start), int(end))
            for start, end in re.findall(r"\[(\d+)-(\d+)\]", line)
        ]
        spans.sort()
        for (_, end), (next_start, _) in zip(spans, spans[1:]):
            assert end <= next_start, f"overlap on {line}"


def test_1dbp_printer_groups_items_by_bin() -> None:
    from optdsl_agent.printers import format_solution

    constants = {
        "ITEM_WEIGHTS": [3, 2, 5],
        "BOX_CAPACITIES": [5, 5],
    }
    text = format_solution(
        {"assignments": [0, 0, 1]}, constants, problem_class="1dbp"
    )
    assert "bin 0: load 5/5" in text
    assert "bin 1: load 5/5" in text


def test_2dbp_printer_shows_placements() -> None:
    from optdsl_agent.printers import format_solution

    constants = {
        "ITEM_WIDTHS": [2, 3],
        "ITEM_HEIGHTS": [2, 3],
        "BOX_WIDTH_CAPACITIES": [10],
        "BOX_HEIGHT_CAPACITIES": [10],
    }
    text = format_solution(
        {"assignments": [0, 0], "x_positions": [0, 2], "y_positions": [0, 0]},
        constants,
        problem_class="2dbp",
    )
    assert "box 0 (10x10" in text
    assert "item 0 at (0,0) size 2x2" in text


def test_cutting_packing_printer_derives_pieces_from_cuts() -> None:
    from optdsl_agent.printers import format_solution

    constants = {
        "N_SEGMENTS": 1,
        "N_CUTS_PER_SEGMENT": 2,
        "N_PIECES_PER_SEGMENT": 3,
        "SEGMENT_LENGTHS": [10],
    }
    text = format_solution(
        {"cut_positions": [3, 7]}, constants, problem_class="cutting_packing"
    )
    assert "pieces [3, 4, 3]" in text


def test_lns_result_carries_a_rendered_solution() -> None:
    result = run_lns(LNSRunConfig(instance=CVRP, iterations=50, initializer="auto"))
    assert result.ok
    assert result.rendered
    assert "vehicle" in result.rendered
    assert "rendered" in result.to_dict()


def test_lns_rendered_solution_can_be_suppressed(session: Session) -> None:
    result = build_registry().call(
        "run_lns", session, {"iterations": 20, "show_solution": False}
    )
    assert result["ok"]
    assert "rendered" not in result


def test_solution_command_reports_when_there_is_nothing_yet(session: Session) -> None:
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    text = run_command("/solution", session, loop, session.config).text
    assert "no solution yet" in text


def test_solution_command_uses_the_lns_rendering(session: Session) -> None:
    from optdsl_agent.commands import run_command

    loop = AgentLoop(session, StubClient())
    run_command("/lns 50", session, loop, session.config)

    text = run_command("/solution", session, loop, session.config).text
    assert "vehicle" in text


def test_printer_flags_infeasible_solutions() -> None:
    """A degenerate assignment renders plausibly; the header must say so."""
    from optdsl_agent.printers import format_solution

    text = format_solution(
        {"x": [0]}, {}, problem_class=None, objective_value=None, feasible=False
    )
    assert "INFEASIBLE" in text


def test_printer_does_not_flag_feasible_solutions() -> None:
    from optdsl_agent.printers import format_solution

    text = format_solution(
        {"x": [0]}, {}, problem_class=None, objective_value=1.0, feasible=True
    )
    assert "INFEASIBLE" not in text


def test_woodcutting_printer_handles_record_shaped_cuts() -> None:
    """``cuts_list_list`` is a list of records, not a list of lists."""
    from optdsl_agent.printers import format_solution

    constants = {
        "GIVEN_INITIAL_BOARDS": [{"length": 10}],
        "MAX_N_CUTS_PER_BOARD": 3,
    }
    assignment = {"cuts_list_list": [{"position_list": [3, 7]}]}

    text = format_solution(assignment, constants, problem_class="woodcutting")
    assert "board 0: cuts [3, 7]" in text
    assert "pieces [3, 4, 3]" in text
    assert "total 10/10" in text


def test_woodcutting_printer_accepts_bare_lists_too() -> None:
    from optdsl_agent.printers import format_solution

    constants = {"GIVEN_INITIAL_BOARDS": [{"length": 10}]}
    text = format_solution(
        {"cuts_list_list": [[3, 7]]}, constants, problem_class="woodcutting"
    )
    assert "pieces [3, 4, 3]" in text


def test_lns_rendering_marks_infeasible_runs() -> None:
    """The 2DBP instance has no feasible solution with the generic operators."""
    result = run_lns(
        LNSRunConfig(
            instance=REPO_ROOT / "problem_instances" / "2dbp" / "random_2dbp_zero_based.dsl",
            iterations=20,
            initializer="auto",
        )
    )
    assert result.ok
    if not result.feasible:
        assert "INFEASIBLE" in (result.rendered or "")
