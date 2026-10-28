"""Tests for the OptDSL tooling, registry, and synthesis harness.

Run with::

    .venv\\Scripts\\python.exe -m pytest test -q
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for extra in ("", "optdsl-lsp", "operator-synthesis"):
    candidate = str(REPO_ROOT / extra) if extra else str(REPO_ROOT)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from optdsl_tooling import analyze, analyze_file, check, fingerprint  # noqa: E402
from optdsl_tooling.diagnostics import Severity  # noqa: E402
from optdsl_tooling.positions import PositionMapper  # noqa: E402

INSTANCES = sorted((REPO_ROOT / "problem_instances").rglob("*.dsl"))


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def test_all_instances_analyze_without_errors() -> None:
    """Every shipped instance must be clean; a false positive here is a bug."""
    assert INSTANCES, "no instances found"
    for path in INSTANCES:
        index = analyze_file(path)
        assert index.syntax_error is None, f"{path.name}: {index.syntax_error}"
        errors = [d for d in check(index) if d.severity == Severity.ERROR]
        assert not errors, f"{path.name}: {[d.message for d in errors]}"


def test_decision_indices_match_runtime_reader() -> None:
    """The editor's decision set must equal the LNS runtime's decision set."""
    from large_neighborhood_search.problem_reader import read_problem

    for path in INSTANCES:
        index = analyze_file(path)
        problem = read_problem(path, compile_runtime=False)

        tooling = {(d.variable_name, d.index) for d in index.decisions}
        runtime = {(d.variable_name, d.index) for d in problem.decision_indices}
        assert tooling == runtime, f"{path.name}: decision sets diverged"


def test_analysis_never_executes_source() -> None:
    """A module with a side effect must not run it during analysis."""
    marker = REPO_ROOT / ".analysis_side_effect"
    if marker.exists():
        marker.unlink()

    source = f"""
from pathlib import Path
Path({str(marker)!r}).write_text("executed")

N : int = 3
x: DSList(N, DSInt(0, 1))
minimize(x)
"""
    index = analyze(source)
    assert index.syntax_error is None
    assert not marker.exists(), "analysis executed the source"


def test_syntax_error_is_captured_not_raised() -> None:
    index = analyze("def broken(:\n    pass\n")
    assert index.syntax_error is not None
    diagnostics = check(index)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "syntax-error"


def test_unknown_name_is_reported() -> None:
    source = """
N : int = 3
x: DSList(N, DSInt(0, 1))

def check_it(x: DSList(N, DSInt(0, 1))):
    assert x[0] <= MISSING_CONSTANT

check_it(x)
minimize(x)
"""
    codes = {d.code for d in check(analyze(source))}
    assert "unknown-name" in codes


def test_uninvoked_predicate_is_reported() -> None:
    source = """
N : int = 3
x: DSList(N, DSInt(0, 1))

def never_called(x: DSList(N, DSInt(0, 1))):
    assert x[0] == 1

minimize(x)
"""
    codes = {d.code for d in check(analyze(source))}
    assert "predicate-unused" in codes


def test_unbounded_domain_is_an_error() -> None:
    source = """
x: DSInt()
minimize(x)
"""
    errors = [d for d in check(analyze(source)) if d.severity == Severity.ERROR]
    assert any(d.code == "unbounded-domain" for d in errors)


def test_dsbool_decision_is_normalised_to_integer_domain() -> None:
    """``DSBool()`` decisions must become integer {0, 1} decisions for LNS.

    Previously the importer had no ``DSBool`` branch, so a boolean decision was
    silently treated as *not* a decision: it never appeared in the decision
    indices, could never be set by the search, and no LNS run was ever feasible
    over it. The parser now normalises it to ``DSInt(0, 1)`` so every consumer
    (decision expansion, empty-assignment placeholders, samplers) works.
    """
    source = """
N_PRODUCTS : int = 3
N_PERIODS : int = 4
CAPACITY : int = 8
setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSBool()))
production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))
objective: DSInt(0, 1000) = 0
minimize(objective)
"""
    index = analyze(source)

    # No longer a hard validation error — it is a first-class decision now.
    errors = [d for d in check(index) if d.severity == Severity.ERROR]
    assert not any(d.code == "decision-bool-domain" for d in errors)

    # The setup flags are enumerated as 0..1 decisions, exactly like DSInt(0, 1).
    setups = index.decisions_for("setup")
    assert setups, "DSBool() flags must be enumerated as decisions"
    assert all(d.domain.lower == 0 and d.domain.upper == 1 for d in setups)
    assert len(setups) == 3 * 4

    # Scalar DSBool() normalises to an int domain {0, 1} with no new "bool" kind.
    from large_neighborhood_search.problem_reader import (
        IntDomain,
        _parse_variable_domain,
    )

    scalar = _parse_variable_domain(ast.parse("DSBool()", mode="eval").body, {})
    assert scalar is not None
    assert scalar.kind == "int"
    assert scalar.int_domain == IntDomain(lower=0, upper=1)


def test_maximize_is_recognised() -> None:
    source = """
N : int = 3
x: DSList(N, DSInt(0, 1))
maximize(x)
"""
    index = analyze(source)
    assert index.objective is not None
    assert index.objective.sense == "maximize"


def test_duplicate_objective_is_reported() -> None:
    source = """
N : int = 3
x: DSList(N, DSInt(0, 1))
minimize(x)
maximize(x)
"""
    codes = {d.code for d in check(analyze(source))}
    assert "duplicate-objective" in codes


def test_warm_start_unknown_target_is_reported() -> None:
    source = """
N : int = 3
x: DSList(N, DSInt(0, 1))
minimize(x)

@warm_start(upper_bound=1)
def ws():
    return {"nope": [0, 1, 0]}
"""
    codes = {d.code for d in check(analyze(source))}
    assert "warm-start-unknown-target" in codes


# ---------------------------------------------------------------------------
# fingerprint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("instance", "expected"),
    [
        ("1dbp/problem_2_t_zero_based.dsl", "1dbp"),
        ("2dbp/random_2dbp_zero_based.dsl", "2dbp"),
        ("cvrp/random_euclidean_cvrp_8.dsl", "cvrp"),
        ("jssp/jssp_5x4.dsl", "jssp"),
        ("woodcutting/wc_test_mini.dsl", "woodcutting"),
    ],
)
def test_fingerprint_identifies_problem_class(instance: str, expected: str) -> None:
    index = analyze_file(REPO_ROOT / "problem_instances" / instance)
    result = fingerprint(index)
    assert result.best is not None
    assert result.best.name == expected
    assert result.matched


_LOT_SIZING = """\
N_PRODUCTS : int = 2
N_PERIODS : int = 3
CAPACITY : int = 8
DEMAND : DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt())) = [[2, 1, 3], [1, 4, 2]]
production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY)))
setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))
def setup_ok(production: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, CAPACITY))),
             setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))):
    for p in range(N_PRODUCTS):
        for t in range(N_PERIODS):
            assert production[p][t] <= CAPACITY * setup[p][t]
setup_ok(production, setup)
"""


def test_fingerprint_does_not_label_unrelated_models() -> None:
    """A model sharing no markers with any class must not be called e.g. '1dbp'."""
    from optdsl_tooling.fingerprint import problem_key, problem_label

    index = analyze(_LOT_SIZING)
    result = fingerprint(index)
    assert result.best is None
    assert not result.matched

    key = problem_key(index, result)
    assert key.startswith("production_setup_")
    assert "custom" in problem_label(index, result)
    # The key identifies the formulation, not the data: other demands, same key.
    other = analyze(_LOT_SIZING.replace("[[2, 1, 3], [1, 4, 2]]", "[[5, 0, 1], [2, 2, 2]]"))
    assert problem_key(other) == key
    # A structural change (new constraint) yields a different key.
    changed = analyze(_LOT_SIZING + "def extra(setup: DSList(N_PRODUCTS, DSList(N_PERIODS, DSInt(0, 1)))):\n    assert setup[0][0] == 0\nextra(setup)\n")
    assert problem_key(changed) != key


def test_problem_key_of_known_class_is_its_name() -> None:
    from optdsl_tooling.fingerprint import problem_key

    index = analyze_file(REPO_ROOT / "problem_instances" / "cvrp" / "random_euclidean_cvrp_8.dsl")
    assert problem_key(index) == "cvrp"


# ---------------------------------------------------------------------------
# positions
# ---------------------------------------------------------------------------


def test_position_mapper_handles_non_ascii() -> None:
    """ast columns are UTF-8 bytes; LSP wants UTF-16 code units."""
    source = 'x = "héllo wörld"  # ünïcode\ny = 1\n'
    mapper = PositionMapper(source)
    assert mapper.line_text(0) == 'x = "héllo wörld"  # ünïcode'
    assert mapper.line_text(1) == "y = 1"


def test_position_mapper_handles_astral_plane() -> None:
    """Emoji are one UTF-16 surrogate pair but four UTF-8 bytes."""
    source = 'x = "🎯"\ny = 1\n'
    mapper = PositionMapper(source)
    assert mapper.line_text(0) == 'x = "🎯"'


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def test_registry_populates_and_instantiates() -> None:
    import large_neighborhood_search.builtin_operators  # noqa: F401
    from large_neighborhood_search.registry import (
        available_destroys,
        available_repairs,
        create_destroy,
        create_repair,
    )

    assert len(available_destroys()) >= 20
    assert len(available_repairs()) >= 20

    destroy = create_destroy("RandomFractionDestroy", fraction=0.5)
    assert destroy.fraction == 0.5

    repair = create_repair("SampledRepair", samples=3)
    assert repair.samples == 3


def test_registry_rejects_duplicates() -> None:
    from large_neighborhood_search.registry import register_destroy

    with pytest.raises(ValueError):

        @register_destroy("RandomFractionDestroy")
        def _duplicate(**kwargs):  # pragma: no cover
            return None


def test_registry_unknown_name_raises() -> None:
    from large_neighborhood_search.registry import create_destroy

    with pytest.raises(KeyError):
        create_destroy("NoSuchOperator")


# ---------------------------------------------------------------------------
# synthesis harness
# ---------------------------------------------------------------------------

GOOD_DESTROY = '''
from dataclasses import dataclass

from large_neighborhood_search.components import DestroyOperator
from large_neighborhood_search._utils import set_decision_value


@dataclass
class GoodRandomDestroy(DestroyOperator):
    """Clear a random fraction of decisions."""

    fraction: float = 0.3

    def destroy(self, assignment, context):
        rng = context.extra["rng"]
        keys = context.extra["decision_keys"]
        count = max(1, int(len(keys) * self.fraction))
        for key in rng.sample(keys, min(count, len(keys))):
            set_decision_value(assignment, key, None)
        return assignment
'''

NOOP_DESTROY = '''
from dataclasses import dataclass

from large_neighborhood_search.components import DestroyOperator


@dataclass
class NoopDestroy(DestroyOperator):
    """Does nothing — must be rejected."""

    def destroy(self, assignment, context):
        return assignment
'''

CRASHING_DESTROY = '''
from dataclasses import dataclass

from large_neighborhood_search.components import DestroyOperator


@dataclass
class CrashingDestroy(DestroyOperator):
    """Raises on every call — must be rejected."""

    def destroy(self, assignment, context):
        raise RuntimeError("boom")
'''

FORBIDDEN_IMPORT = '''
import os
from dataclasses import dataclass

from large_neighborhood_search.components import DestroyOperator


@dataclass
class BadImportDestroy(DestroyOperator):
    def destroy(self, assignment, context):
        return assignment
'''


GOOD_REPAIR = '''
from dataclasses import dataclass

from large_neighborhood_search.components import RepairOperator
from large_neighborhood_search._utils import get_decision_value, set_decision_value


@dataclass
class GoodRandomRepair(RepairOperator):
    """Fill every unassigned decision with a random value."""

    def repair(self, partial_assignment, context):
        rng = context.extra["rng"]
        domains = context.extra["decision_domains"]
        for key in context.extra["decision_keys"]:
            if get_decision_value(partial_assignment, key) is None:
                lower, upper = domains[key]
                set_decision_value(partial_assignment, key, rng.randint(lower, upper))
        return partial_assignment
'''

NOOP_REPAIR = '''
from dataclasses import dataclass

from large_neighborhood_search.components import RepairOperator


@dataclass
class NoopRepair(RepairOperator):
    """Leaves the partial assignment untouched — must be rejected."""

    def repair(self, partial_assignment, context):
        return partial_assignment
'''


def test_static_check_accepts_good_operator() -> None:
    from operator_synthesis.harness import static_check

    result = static_check(GOOD_DESTROY, "destroy")
    assert result.ok, result.errors
    assert result.class_name == "GoodRandomDestroy"


def test_static_check_rejects_forbidden_import() -> None:
    from operator_synthesis.harness import static_check

    result = static_check(FORBIDDEN_IMPORT, "destroy")
    assert not result.ok
    assert any("os" in error for error in result.errors)


def test_static_check_rejects_missing_method() -> None:
    from operator_synthesis.harness import static_check

    source = '''
from dataclasses import dataclass
from large_neighborhood_search.components import DestroyOperator

@dataclass
class Incomplete(DestroyOperator):
    pass
'''
    result = static_check(source, "destroy")
    assert not result.ok
    assert any("destroy" in error for error in result.errors)


def test_static_check_requires_a_self_contained_module() -> None:
    """Generated operators are persisted and imported as-is, so a class that
    relies on names it never imports must be rejected before execution."""
    from operator_synthesis.harness import static_check

    source = '''
@dataclass
class NoImports(DestroyOperator):
    def destroy(self, assignment, context):
        return assignment
'''
    result = static_check(source, "destroy")
    assert not result.ok
    assert any("'dataclass'" in error and "self-contained" in error for error in result.errors)
    assert any("'DestroyOperator'" in error for error in result.errors)


def test_operator_prompt_asks_for_a_complete_module() -> None:
    from operator_synthesis.prompts import build_system_prompt

    prompt = build_system_prompt("repair")
    assert "self-contained Python module" in prompt
    assert "from large_neighborhood_search.components import RepairOperator" in prompt


def test_write_operator_produces_a_self_registering_module(tmp_path: Path) -> None:
    """The written file must import and register by itself, and must never
    shadow an existing operator name."""
    import importlib.util

    from large_neighborhood_search import builtin_operators  # noqa: F401
    from large_neighborhood_search.registry import create_destroy, describe, load_generated_directory
    from operator_synthesis.synthesize import SynthesisResult, write_operator

    result = SynthesisResult(accepted=True, source=GOOD_DESTROY, class_name="GoodRandomDestroy")
    path = write_operator(result, tmp_path, problem_class="test_problem", kind="destroy")
    assert path.name == "good_random_destroy.py"
    ast.parse(path.read_text(encoding="utf-8"))

    # Importable on its own, outside the harness namespace.
    spec = importlib.util.spec_from_file_location("standalone_good_random_destroy", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    if describe("GoodRandomDestroy") is None:
        spec.loader.exec_module(module)
    else:
        load_generated_directory(tmp_path)
    info = describe("GoodRandomDestroy")
    assert info is not None and info.generated and info.problem == "test_problem"
    assert create_destroy("GoodRandomDestroy") is not None

    # Same name, different code: renamed instead of overwriting/colliding.
    clash = SynthesisResult(
        accepted=True,
        source=GOOD_DESTROY.replace("fraction: float = 0.3", "fraction: float = 0.4"),
        class_name="GoodRandomDestroy",
    )
    second = write_operator(clash, tmp_path, problem_class="test_problem", kind="destroy")
    assert clash.class_name == "GoodRandomDestroy2"
    assert second.name == "good_random_destroy2.py"
    assert "class GoodRandomDestroy2(" in second.read_text(encoding="utf-8")

    # Built-in names are never shadowed.
    builtin = SynthesisResult(
        accepted=True,
        source=GOOD_DESTROY.replace("GoodRandomDestroy", "RandomFractionDestroy"),
        class_name="RandomFractionDestroy",
    )
    write_operator(builtin, tmp_path, problem_class="test_problem", kind="destroy")
    assert builtin.class_name == "RandomFractionDestroy2"


def test_harness_feasible_rate_counts_candidates_not_accepted_moves() -> None:
    """Every iteration yields one candidate, feasible or not."""
    from operator_synthesis.harness import run_candidate, static_check

    metrics = run_candidate(
        GOOD_DESTROY,
        static_check(GOOD_DESTROY, "destroy").class_name or "",
        "destroy",
        REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl",
        repo_root=REPO_ROOT,
        iterations=60,
    )
    assert metrics.ok, metrics.error
    assert metrics.feasible_candidates + metrics.infeasible_candidates == metrics.iterations


def test_harness_accepts_effective_operator() -> None:
    from operator_synthesis.harness import evaluate_candidate

    verdict = evaluate_candidate(
        GOOD_DESTROY,
        "destroy",
        REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl",
        repo_root=REPO_ROOT,
        iterations=100,
    )
    assert verdict.accepted, verdict.reasons


def test_harness_rejects_noop_operator() -> None:
    from operator_synthesis.harness import evaluate_candidate

    verdict = evaluate_candidate(
        NOOP_DESTROY,
        "destroy",
        REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl",
        repo_root=REPO_ROOT,
        iterations=50,
    )
    assert not verdict.accepted
    assert any("too small" in reason for reason in verdict.reasons)


def test_harness_rejects_crashing_operator() -> None:
    from operator_synthesis.harness import evaluate_candidate

    verdict = evaluate_candidate(
        CRASHING_DESTROY,
        "destroy",
        REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl",
        repo_root=REPO_ROOT,
        iterations=20,
    )
    assert not verdict.accepted
    assert verdict.metrics is not None
    assert not verdict.metrics.ok


def test_harness_accepts_effective_repair() -> None:
    """Repair operators must be validated, not silently skipped.

    Regression: the runner passed the destroy *name* (a string) where an
    operator instance was expected, so every repair candidate crashed.
    """
    from operator_synthesis.harness import evaluate_candidate

    verdict = evaluate_candidate(
        GOOD_REPAIR,
        "repair",
        REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl",
        repo_root=REPO_ROOT,
        iterations=100,
    )
    assert verdict.metrics is not None
    assert verdict.metrics.ok, verdict.metrics.error
    # It must actually restore what a destroy removed.
    assert verdict.metrics.mean_completion_fraction > 0.9


def test_harness_rejects_noop_repair() -> None:
    from operator_synthesis.harness import evaluate_candidate

    verdict = evaluate_candidate(
        NOOP_REPAIR,
        "repair",
        REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl",
        repo_root=REPO_ROOT,
        iterations=50,
    )
    assert not verdict.accepted
    assert any("restores" in reason for reason in verdict.reasons), verdict.reasons


def test_extract_code_handles_fences() -> None:
    from operator_synthesis.synthesize import extract_code

    response = "Here you go:\n```python\nclass X:\n    pass\n```\nHope that helps."
    assert extract_code(response) == "class X:\n    pass"


def test_synthesize_retries_until_accepted() -> None:
    """The loop must feed the rejection back and try again."""
    from operator_synthesis.harness import AcceptancePolicy
    from operator_synthesis.prompts import OperatorSpec
    from operator_synthesis.synthesize import synthesize

    responses = iter([NOOP_DESTROY, GOOD_DESTROY])
    seen: list[list[dict[str, str]]] = []

    def proposer(messages):
        seen.append(list(messages))
        return next(responses)

    index = analyze_file(REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl")
    result = synthesize(
        index,
        fingerprint(index),
        OperatorSpec(
            kind="destroy",
            problem_class="1dbp",
            objective="minimize objective",
            target_variables=["assignments"],
            hyperparameters={"fraction": 0.3},
            invariants=[],
        ),
        REPO_ROOT / "problem_instances" / "1dbp" / "problem_2_t_zero_based.dsl",
        repo_root=REPO_ROOT,
        proposer=proposer,
        policy=AcceptancePolicy(),
        max_attempts=3,
        run_kwargs={"iterations": 100},
    )

    assert result.accepted, [a.verdict.reasons for a in result.attempts]
    assert len(result.attempts) == 2
    # The second call must include the rejection feedback.
    assert len(seen[1]) > len(seen[0])
    assert "rejected" in seen[1][-1]["content"]
