"""Tests for LLM-synthesized feasibility initializers (LNS bootstrap)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for extra in ("", "operator-synthesis"):
    candidate = str(REPO_ROOT / extra) if extra else str(REPO_ROOT)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from optdsl_agent.initializer import (  # noqa: E402
    InitializerArtifact,
    check_initializer,
    discover_initializer,
    static_check_initializer,
    write_initializer,
)
from optdsl_agent.lns_runner import LNSRunConfig, run_lns  # noqa: E402

# A lot-sizing model with LNS-compatible binary flags (DSInt(0, 1), not
# DSBool): MiniZinc-optimum production/setup plan shown feasible by the solver.
LOADSIZING_DSL = """\
N_PRODUCTS : int = 3
N_PERIODS : int = 4
CAPACITY : int = 8
DEMAND : DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt())) = [[2, 1, 3, 2], [1, 4, 2, 1], [2, 1, 5, 1]]
prod: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))
setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))
def setup_required(prod: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY))), setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))):
    for p in range(N_PRODUCTS):
        for t in range(N_PERIODS):
            assert prod[p][t] == 0 or setup[p][t]
setup_required(prod, setup)
def capacity_ok(prod: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))):
    for t in range(N_PERIODS):
        tot = 0
        for p in range(N_PRODUCTS):
            tot = tot + prod[p][t]
        assert tot <= CAPACITY
capacity_ok(prod)
def demand_met(prod: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))):
    for p in range(N_PRODUCTS):
        inv = 0
        for t in range(N_PERIODS):
            inv = inv + prod[p][t] - DEMAND[p][t]
            assert inv >= 0
demand_met(prod)
def total_cost(prod, setup):
    total = 0
    for p in range(N_PRODUCTS):
        inv = 0
        for t in range(N_PERIODS):
            total = total + 1 * prod[p][t] + 1 * setup[p][t]
            inv = inv + prod[p][t] - DEMAND[p][t]
            total = total + 1 * inv
    return total
objective: DSInt(0, 10000) = total_cost(prod, setup)
minimize(objective)
"""


@pytest.fixture()
def lot_sizing(tmp_path: Path) -> Path:
    path = tmp_path / "lot_sizing.dsl"
    path.write_text(LOADSIZING_DSL, encoding="utf-8")
    return path


FEASIBLE_INITIALIZER = '''
from large_neighborhood_search.components import Initializer
from large_neighborhood_search.lns import _build_empty_assignment
from large_neighborhood_search._utils import set_decision_value

class LotSizingFeasible(Initializer):
    def initialize(self, context):
        assignment = _build_empty_assignment(context)
        plan = {(0, 0): 3, (0, 2): 3, (0, 3): 2, (1, 0): 1, (1, 1): 7, (2, 0): 4, (2, 2): 5}
        for key in context.extra["decision_keys"]:
            name, idx = key
            if name == "prod":
                set_decision_value(assignment, key, plan.get(idx, 0))
            elif name == "setup":
                set_decision_value(assignment, key, 1 if plan.get(idx, 0) else 0)
        return assignment
'''


def test_static_check_initializer_accepts_and_rejects() -> None:
    ok, class_name, errors = static_check_initializer(FEASIBLE_INITIALIZER)
    assert ok and class_name == "LotSizingFeasible" and not errors

    bad = "class X:\n    pass\n"
    ok, _, errors = static_check_initializer(bad)
    assert not ok and any("Initializer" in e for e in errors)

    importing = "from os import system\nclass Y(Initializer):\n    def initialize(self, c): return {}\n"
    ok, _, errors = static_check_initializer(importing)
    assert not ok and any("not allowed" in e for e in errors)


def test_check_initializer_judges_feasibility(lot_sizing: Path) -> None:
    ok_result = check_initializer(FEASIBLE_INITIALIZER, "LotSizingFeasible", lot_sizing, repo_root=REPO_ROOT)
    assert ok_result["ok"] is True
    assert ok_result["feasible"] is True
    assert ok_result["score"] < 1e9

    # A do-nothing initializer leaves the assignment unassigned / infeasible.
    empty = "\n".join(FEASIBLE_INITIALIZER.splitlines()[:2]) + "\nclass DoNothing(Initializer):\n    def initialize(self, context):\n        from large_neighborhood_search.lns import _build_empty_assignment\n        return _build_empty_assignment(context)\n"
    bad = check_initializer(empty, "DoNothing", lot_sizing, repo_root=REPO_ROOT)
    assert bad["ok"] is True
    assert bad["feasible"] is False


def test_check_initializer_reports_which_constraint_failed(lot_sizing: Path) -> None:
    """Infeasible output must name the failing predicate and the values at the
    failing assert, so the synthesis loop can give the model specific feedback."""
    # Produce zero for every product/period -> demand_met immediately fails:
    # product 0 period 0 needs demand 2 but inventory goes negative.
    all_zero = '''
from large_neighborhood_search.components import Initializer
from large_neighborhood_search.lns import _build_empty_assignment
from large_neighborhood_search._utils import set_decision_value

class AllZero(Initializer):
    def initialize(self, context):
        assignment = _build_empty_assignment(context)
        for key in context.extra["decision_keys"]:
            set_decision_value(assignment, key, 0)
        return assignment
'''
    outcome = check_initializer(all_zero, "AllZero", lot_sizing, repo_root=REPO_ROOT)
    assert outcome["ok"] is True
    assert outcome["feasible"] is False

    failed = outcome.get("failed_details") or []
    assert failed, "expected per-constraint failure detail"
    names = {entry.get("constraint") for entry in failed}
    assert "demand_met" in names
    # The failing frame carries loop/index locals that identify the location.
    demand = next(e for e in failed if e.get("constraint") == "demand_met")
    assert demand.get("line") is not None
    at = demand.get("at") or {}
    assert any(k in at for k in ("p", "t", "inv")), f"expected loop locals, got {at}"


def test_initializer_drives_the_lns_baseline_to_feasibility(lot_sizing: Path) -> None:
    # 1) Generic LNS cannot reach feasibility for this model.
    generic = run_lns(LNSRunConfig(instance=lot_sizing, seed=0, iterations=30, initializer="auto"))
    assert not generic.feasible

    # 2) With the synthesized initializer instance, the baseline becomes feasible.
    boosted = run_lns(
        LNSRunConfig(
            instance=lot_sizing,
            seed=0,
            iterations=30,
            initializer=InitializerArtifact(FEASIBLE_INITIALIZER, "LotSizingFeasible").instantiate(),
        )
    )
    assert boosted.feasible
    assert boosted.objective_value is not None
    assert boosted.objective_value < 1e8


def test_dsbool_lot_sizing_flags_are_searchable(tmp_path: Path) -> None:
    """DSBool() setup flags become integer {0, 1} decisions for LNS.

    This is the model shape /describe used to emit (and that previously could
    never be feasible): the importer had no DSBool branch, so the setup flags
    silently vanished from the decision indices. After normalisation each flag
    is a 0..1 decision, assignable by set_decision_value and readable by the
    evaluator exactly like a DSInt(0, 1) flag.
    """
    dsl = LOADSIZING_DSL.replace("DSInt(0, 1)", "DSBool()")
    path = tmp_path / "lot_sizing_dsbool.dsl"
    path.write_text(dsl, encoding="utf-8")

    from large_neighborhood_search.problem_reader import read_problem

    problem = read_problem(path, compile_runtime=False)
    setup_indices = [d for d in problem.decision_indices if d.variable_name == "setup"]
    assert setup_indices, "DSBool() setup flags must be enumerated as decisions"
    assert all(d.domain.lower == 0 and d.domain.upper == 1 for d in setup_indices)
    prod_indices = [d for d in problem.decision_indices if d.variable_name == "prod"]
    assert prod_indices

    # Assigning is the same path LNS uses: empty skeleton + set_decision_value.
    from large_neighborhood_search._utils import set_decision_value
    from large_neighborhood_search.components import Initializer
    from large_neighborhood_search.lns import _build_empty_assignment

    class Feasible(Initializer):
        def initialize(self, context):
            assignment = _build_empty_assignment(context)
            plan = {(0, 0): 3, (0, 2): 3, (0, 3): 2, (1, 0): 1, (1, 1): 7, (2, 0): 4, (2, 2): 5}
            for key in context.extra["decision_keys"]:
                name, idx = key
                if name == "prod":
                    set_decision_value(assignment, key, plan.get(idx, 0))
                elif name == "setup":
                    set_decision_value(assignment, key, 1 if plan.get(idx, 0) else 0)
            return assignment

    # The flags are now in the neighborhood, so a plan that sets them drives the
    # DSBool-backed model to a feasible run with a real objective (generic LNS
    # still cannot reach this tightly-coupled model by itself — that is what the
    # /tune feasibility bootstrap exists for).
    boosted = run_lns(
        LNSRunConfig(
            instance=path,
            seed=0,
            iterations=30,
            initializer=Feasible(),
        )
    )
    assert boosted.feasible
    assert boosted.objective_value is not None
    assert boosted.objective_value < 1e8


def test_write_and_discover_initializer(tmp_path: Path) -> None:
    written = write_initializer(FEASIBLE_INITIALIZER, tmp_path, problem_stem="lot_sizing")
    found = discover_initializer(tmp_path, "lot_sizing")
    assert found is not None
    assert found.class_name == "LotSizingFeasible"
    assert found.path == written
    assert discover_initializer(tmp_path, "other_problem") is None


def test_tune_bootstraps_a_feasible_initializer(lot_sizing: Path, tmp_path: Path) -> None:
    """When the LNS baseline is infeasible, tune asks the model for an
    initializer, verifies it, and re-measures the baseline from a feasible start."""
    from optdsl_agent.config import AgentConfig
    from optdsl_agent.llm import LLMResponse, StubClient
    from optdsl_agent.tuning import TuningBudget, tune

    config = AgentConfig(
        repo_root=REPO_ROOT,
        output_dir=tmp_path / "out",
        operator_dir=tmp_path / "generated",
        lns_initializer="auto",
        lns_iterations=20,
    )
    client = StubClient([LLMResponse(content=FEASIBLE_INITIALIZER, finish_reason="stop")])
    report = tune(
        [lot_sizing],
        config,
        client=client,
        budget=TuningBudget(
            max_attempts=0,  # stop before operator synthesis; bootstrap is the scope
            iterations=20,
            max_wall_seconds=60,
        ),
    )

    assert report.initializer is not None
    assert report.initializer["class_name"] == "LotSizingFeasible"
    assert report.baseline_lns.get("feasible") is True
    assert report.baseline_lns.get("objectiveValue") is not None
    # The initializer is persisted so later /lns runs reuse it.
    assert Path(report.initializer["path"]).exists()


def test_initializer_prompt_shows_constraint_bodies(lot_sizing: Path, tmp_path: Path) -> None:
    """The feasibility-initializer digest must include the full DSL source.

    The model can only construct a feasible assignment if it can see the
    constraint *bodies* (e.g. the cumulative no-backlog invariant and the
    shared per-period capacity), not just one-line predicate signatures.
    """
    from optdsl_agent.config import AgentConfig
    from optdsl_agent.llm import LLMResponse, StubClient
    from optdsl_agent.tuning import TuningBudget, _synthesize_feasible_initializer

    config = AgentConfig(
        repo_root=REPO_ROOT,
        output_dir=tmp_path / "out",
        operator_dir=tmp_path / "generated",
        lns_initializer="auto",
        lns_iterations=20,
    )
    client = StubClient([LLMResponse(content=FEASIBLE_INITIALIZER, finish_reason="stop")])
    source = lot_sizing.read_text(encoding="utf-8")

    _synthesize_feasible_initializer(
        lot_sizing,
        source,
        config,
        client,
        TuningBudget(max_wall_seconds=60),
        None,
    )

    prompt = client.calls[0][0]["content"]
    assert "Predicates:" in prompt
    # The model must see the def bodies, not only `demand_met(prod) [invoked]`.
    assert "def demand_met" in prompt
    assert "assert inv" in prompt
    assert "setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))" in prompt


def test_extract_initializer_source_tolerates_fenced_json() -> None:
    """A ```json-wrapped reply must parse; DeepSeek-style models wrap the
    requested JSON in a fence, and the old scanner only knew ```/```python."""
    from optdsl_agent.tuning import _extract_initializer_source

    reply = (
        "```json\n"
        '{"class_name": "Fenced", "source": "from large_neighborhood_search.components '
        'import Initializer\\nclass Fenced(Initializer):\\n    def initialize(self, '
        'context):\\n        return {}\\n"}'
        "\n```"
    )
    source = _extract_initializer_source(reply)
    ok, class_name, _ = static_check_initializer(source)
    assert ok and class_name == "Fenced"

    # Literal newlines inside the JSON "source" value make the overall reply
    # invalid JSON; the extraction should coerce to the standalone class body.
    code = (
        "from large_neighborhood_search.components import Initializer\n"
        "class Loose(Initializer):\n"
        "    def initialize(self, context):\n"
        "        return {}\n"
    )
    sloppy = (
        "```json\n"
        '{"class_name": "Loose", "source": "'
        + code.replace("\n", "\\n")
        + '"\n}\n```'
    )
    source = _extract_initializer_source(sloppy)
    ok, class_name, _ = static_check_initializer(source)
    assert ok and class_name == "Loose"


# ---------------------------------------------------------------------------
# end to end: /tune develops construction + operators, /lns uses the config
# ---------------------------------------------------------------------------

#: The capacitated lot-sizing model from problem_lot_sizing.txt (typed, so the
#: exact backend can translate it).
LOT_SIZING_FULL_DSL = """\
N_PRODUCTS : int = 3
N_PERIODS : int = 4
CAPACITY : int = 8

DEMAND : DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt())) = [
    [2, 1, 3, 2],
    [1, 4, 2, 1],
    [2, 1, 5, 1],
]

PROD_COST : DSList(N_PRODUCTS, DSInt()) = [1, 2, 2]
SETUP_COST : DSList(N_PRODUCTS, DSInt()) = [6, 9, 7]
HOLD_COST : DSList(N_PRODUCTS, DSInt()) = [1, 1, 1]

production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))
setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))

def capacity_ok(production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))):
    for t in range(N_PERIODS):
        total = 0
        for p in range(N_PRODUCTS):
            total = total + production[p][t]
        assert total <= CAPACITY
capacity_ok(production)

def setup_ok(production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY))),
             setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))):
    for p in range(N_PRODUCTS):
        for t in range(N_PERIODS):
            assert production[p][t] <= CAPACITY * setup[p][t]
setup_ok(production, setup)

def demand_ok(production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))):
    for p in range(N_PRODUCTS):
        cum_prod = 0
        cum_dem = 0
        for t in range(N_PERIODS):
            cum_prod = cum_prod + production[p][t]
            cum_dem = cum_dem + DEMAND[p][t]
            assert cum_prod >= cum_dem
demand_ok(production)

def total_cost(production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY))),
               setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))) -> DSInt():
    cost = 0
    for p in range(N_PRODUCTS):
        cum_prod = 0
        cum_dem = 0
        for t in range(N_PERIODS):
            cum_prod = cum_prod + production[p][t]
            cum_dem = cum_dem + DEMAND[p][t]
            cost = cost + PROD_COST[p] * production[p][t]
            cost = cost + SETUP_COST[p] * setup[p][t]
            cost = cost + HOLD_COST[p] * (cum_prod - cum_dem)
    return cost

objective: DSInt() = total_cost(production, setup)
minimize(objective)
"""

E2E_CONSTRUCTION = '''from large_neighborhood_search.components import Initializer
from large_neighborhood_search.lns import _build_empty_assignment
from large_neighborhood_search._utils import set_decision_value


class LotForLotShiftBack(Initializer):
    """Lot-for-lot production; capacity overflow is shifted to earlier periods."""

    def initialize(self, context):
        rng = context.extra["rng"]
        demand = context.constants["DEMAND"]
        capacity = context.constants["CAPACITY"]
        n_products, n_periods = len(demand), len(demand[0])
        plan = [[demand[p][t] for t in range(n_periods)] for p in range(n_products)]
        for t in range(n_periods - 1, 0, -1):
            excess = sum(plan[p][t] for p in range(n_products)) - capacity
            order = list(range(n_products))
            rng.shuffle(order)
            while excess > 0:
                for p in order:
                    if excess > 0 and plan[p][t] > 0:
                        plan[p][t] -= 1
                        plan[p][t - 1] += 1
                        excess -= 1
        assignment = _build_empty_assignment(context)
        for key in context.extra["decision_keys"]:
            name, (p, t) = key
            value = plan[p][t] if name == "production" else int(plan[p][t] > 0)
            set_decision_value(assignment, key, value)
        return assignment
'''

E2E_REPAIR = '''from dataclasses import dataclass

from large_neighborhood_search.components import RepairOperator
from large_neighborhood_search._utils import get_decision_value, set_decision_value


@dataclass
class CoverDemandRepair(RepairOperator):
    """Re-plan unassigned production to cover cumulative demand within capacity."""

    early_probability: float = 0.5

    def repair(self, partial_assignment, context):
        rng = context.extra["rng"]
        demand = context.constants.get("DEMAND")
        capacity = context.constants.get("CAPACITY")
        if demand is None or capacity is None:
            return partial_assignment
        n_products, n_periods = len(demand), len(demand[0])
        missing = {k for k in context.extra["decision_keys"] if get_decision_value(partial_assignment, k) is None}
        prod = [[get_decision_value(partial_assignment, ("production", (p, t))) or 0 for t in range(n_periods)] for p in range(n_products)]
        load = [sum(prod[p][t] for p in range(n_products)) for t in range(n_periods)]
        products = list(range(n_products))
        rng.shuffle(products)
        for p in products:
            early = rng.random() < self.early_probability
            cum_prod = cum_dem = 0
            for t in range(n_periods):
                cum_prod += prod[p][t]
                cum_dem += demand[p][t]
                short = cum_dem - cum_prod
                slots = [s for s in range(t + 1) if ("production", (p, s)) in missing]
                if not early:
                    slots.reverse()
                for s in slots:
                    if short <= 0:
                        break
                    add = min(short, capacity - load[s])
                    if add > 0:
                        prod[p][s] += add
                        load[s] += add
                        cum_prod += add
                        short -= add
        for key in missing:
            name, (p, t) = key
            value = prod[p][t] if name == "production" else int(prod[p][t] > 0)
            set_decision_value(partial_assignment, key, value)
        return partial_assignment
'''

E2E_DESTROY = '''from dataclasses import dataclass

from large_neighborhood_search.components import DestroyOperator
from large_neighborhood_search._utils import set_decision_value


@dataclass
class ProductWindowDestroy(DestroyOperator):
    """Unassign production and setup of one product over a window of periods."""

    width: int = 2

    def destroy(self, assignment, context):
        rng = context.extra["rng"]
        keys = context.extra["decision_keys"]
        products = sorted({idx[0] for _, idx in keys})
        periods = sorted({idx[1] for _, idx in keys})
        if not products or not periods:
            return assignment
        product = rng.choice(products)
        start = rng.randrange(len(periods))
        window = set(periods[start:start + self.width])
        for key in keys:
            if key[1][0] == product and key[1][1] in window:
                set_decision_value(assignment, key, None)
        return assignment
'''


class _ScriptedModel:
    """Answers each prompt type of the tuning loop with a fixed, realistic reply."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def chat(self, messages, tools=None):
        import json

        from optdsl_agent.llm import LLMResponse

        system, last = messages[0]["content"], messages[-1]["content"]
        if "neighborhood operators" in system:
            kind = "repair" if "subclass RepairOperator" in system else "destroy"
            self.prompts.append(kind)
            return LLMResponse(content=E2E_REPAIR if kind == "repair" else E2E_DESTROY)
        if "construction heuristic" in last:
            self.prompts.append("construction")
            return LLMResponse(
                content=json.dumps({"class_name": "LotForLotShiftBack", "source": E2E_CONSTRUCTION})
            )
        self.prompts.append("diagnosis")
        return LLMResponse(
            content=json.dumps({"diagnosis": "few setups are shared", "operator_request": "consolidate lots"})
        )


def test_tune_develops_a_config_that_lns_uses(tmp_path: Path) -> None:
    from optdsl_agent.agent import AgentLoop
    from optdsl_agent.commands import run_command
    from optdsl_agent.config import AgentConfig
    from optdsl_agent.llm import StubClient
    from optdsl_agent.lns_config import load_tuned_config
    from optdsl_agent.session import Session
    from optdsl_agent.tuning import TuningBudget, tune

    instance = tmp_path / "lot_sizing.dsl"
    instance.write_text(LOT_SIZING_FULL_DSL, encoding="utf-8")
    config = AgentConfig(
        repo_root=REPO_ROOT,
        output_dir=tmp_path / "out",
        operator_dir=tmp_path / "generated",
        solve_timelimit=10,
    )
    model = _ScriptedModel()
    report = tune(
        [instance],
        config,
        client=model,
        budget=TuningBudget(max_attempts=2, iterations=200, max_wall_seconds=300),
    )

    # Unknown formulation: keyed by structure, not mislabelled as a known class.
    assert report.problem_key.startswith("production_setup_")
    assert model.prompts[0] == "construction"
    # Without a strong built-in partner the repair is synthesized first and
    # then serves as the partner of the destroy candidate.
    assert [a.kind for a in report.attempts] == ["repair", "destroy"]
    assert report.initializer is not None, report.initializer_error
    assert report.accepted == ["CoverDemandRepair", "ProductWindowDestroy"], [
        a.reasons for a in report.attempts
    ]

    # Every artifact is a self-contained module on disk.
    generated = tmp_path / "generated"
    for name in ("cover_demand_repair.py", "product_window_destroy.py"):
        text = (generated / name).read_text(encoding="utf-8")
        assert "from large_neighborhood_search.components import" in text
        assert "_register(" in text
    construction_file = generated / f"{report.problem_key}_initializer.py"
    assert "from large_neighborhood_search.components import Initializer" in construction_file.read_text(
        encoding="utf-8"
    )

    tuned = load_tuned_config(generated, report.problem_key)
    assert tuned is not None
    assert tuned.initializer == {"class_name": "LotForLotShiftBack", "file": construction_file.name}
    assert tuned.destroys[0] == "ProductWindowDestroy"
    assert tuned.repairs[0] == "CoverDemandRepair"
    # The destroy was validated with the generated repair as its partner.
    destroy_entry = next(g for g in tuned.generated if g["name"] == "ProductWindowDestroy")
    assert destroy_entry["partner"] == "CoverDemandRepair"
    assert tuned.tuned["feasible"] is True
    assert "## Tuned LNS config" in report.to_markdown()

    # /lns on another file of the same model picks the config up and logs it.
    other = tmp_path / "another_instance.dsl"
    other.write_text(LOT_SIZING_FULL_DSL, encoding="utf-8")
    session = Session.from_file(other, config)
    result = run_command("/lns 200", session, AgentLoop(session, StubClient()), config)
    assert result.text.startswith("LNS config: tuned")
    assert "LotForLotShiftBack" in result.text
    last = session.last_lns or {}
    assert last["lnsConfig"]["source"] == "tuned"
    assert last["initializer"] == "LotForLotShiftBack"
    assert "ProductWindowDestroy+CoverDemandRepair" in last["neighborhoods"]
    assert last["feasible"] is True
