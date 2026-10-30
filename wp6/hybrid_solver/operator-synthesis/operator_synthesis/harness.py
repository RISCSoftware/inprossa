"""Validation harness for generated LNS operators.

The harness is the only thing standing between an LLM proposal and the operator
registry, so it is deliberately adversarial. A candidate must survive four
independent gates:

1. **Static** — parses, imports only from an allowlist, subclasses the right
   ABC, and implements the required method.
2. **Contract** — returns a dict, does not mutate the input in place, and
   leaves the assignment structurally valid.
3. **Robustness** — never raises across many seeds and many iterations,
   including on a fully-assigned and a fully-empty assignment.
4. **Quality** — actually improves on the baseline initializer, and produces
   feasible candidates at a useful rate.

Gate 4 is the one that matters. A destroy operator that returns the assignment
unchanged passes gates 1–3 trivially, so the harness measures *effect*: the
fraction of decision keys it clears, and whether the resulting neighborhood
yields a better incumbent than the baseline.

All candidate code runs in a subprocess with a timeout. Generated code is
untrusted by construction.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Modules a generated operator may import.
ALLOWED_IMPORTS: frozenset[str] = frozenset(
    {
        "math",
        "random",
        "dataclasses",
        "typing",
        "collections",
        "itertools",
        "heapq",
        "large_neighborhood_search",
        "large_neighborhood_search.components",
        "large_neighborhood_search.models",
        "large_neighborhood_search._utils",
        "large_neighborhood_search.defaults",
    }
)

#: Names a generated operator must not reference.
FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {
        "eval", "exec", "compile", "__import__", "open", "input",
        "globals", "locals", "vars", "getattr", "setattr", "delattr",
        "breakpoint", "exit", "quit",
    }
)


@dataclass
class StaticCheckResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    class_name: str | None = None
    kind: str | None = None


@dataclass
class RunMetrics:
    """Outcome of executing a candidate operator."""

    ok: bool
    error: str | None = None
    iterations: int = 0
    feasible_candidates: int = 0
    infeasible_candidates: int = 0
    improvements: int = 0
    best_score: float | None = None
    baseline_score: float | None = None
    mean_cleared_fraction: float = 0.0
    mean_completion_fraction: float = 0.0
    elapsed_seconds: float = 0.0
    #: ``"minimize"`` or ``"maximize"``. Determines the sign of ``improvement``.
    objective_sense: str = "minimize"

    @property
    def feasible_rate(self) -> float:
        total = self.feasible_candidates + self.infeasible_candidates
        return self.feasible_candidates / total if total else 0.0

    @property
    def improvement(self) -> float:
        """How much better the run got than the baseline, in objective units.

        Positive always means "better", regardless of the objective sense. The
        engine negates scores for maximization problems, so a naive
        ``baseline - best`` would report a maximization improvement as negative
        and reject every good candidate.
        """
        if self.best_score is None or self.baseline_score is None:
            return 0.0
        if self.objective_sense == "maximize":
            return self.best_score - self.baseline_score
        return self.baseline_score - self.best_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error": self.error,
            "iterations": self.iterations,
            "feasible_candidates": self.feasible_candidates,
            "infeasible_candidates": self.infeasible_candidates,
            "feasible_rate": round(self.feasible_rate, 4),
            "improvements": self.improvements,
            "best_score": self.best_score,
            "baseline_score": self.baseline_score,
            "objective_sense": self.objective_sense,
            "improvement": round(self.improvement, 6),
            "mean_cleared_fraction": round(self.mean_cleared_fraction, 4),
            "mean_completion_fraction": round(self.mean_completion_fraction, 4),
            "elapsed_seconds": round(self.elapsed_seconds, 3),
        }


@dataclass
class Verdict:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    static: StaticCheckResult | None = None
    metrics: RunMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reasons": self.reasons,
            "static": (
                {
                    "ok": self.static.ok,
                    "errors": self.static.errors,
                    "warnings": self.static.warnings,
                    "class_name": self.static.class_name,
                    "kind": self.static.kind,
                }
                if self.static
                else None
            ),
            "metrics": self.metrics.to_dict() if self.metrics else None,
        }


# ---------------------------------------------------------------------------
# gate 1: static
# ---------------------------------------------------------------------------


def static_check(source: str, expected_kind: str) -> StaticCheckResult:
    """Parse and vet a candidate operator without executing it."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return StaticCheckResult(ok=False, errors=[f"syntax error: {exc.msg} (line {exc.lineno})"])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS:
                    errors.append(f"import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module not in ALLOWED_IMPORTS:
                errors.append(f"import from '{module}' is not allowed")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            errors.append(f"use of '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            errors.append(f"access to dunder attribute '{node.attr}' is not allowed")

    class_name: str | None = None
    kind: str | None = None
    base_name = "DestroyOperator" if expected_kind == "destroy" else "RepairOperator"
    method_name = "destroy" if expected_kind == "destroy" else "repair"

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {_base_name(base) for base in node.bases}
        if base_name not in bases:
            continue
        class_name = node.name
        kind = expected_kind
        methods = {child.name for child in node.body if isinstance(child, ast.FunctionDef)}
        if method_name not in methods:
            errors.append(f"class '{node.name}' does not implement '{method_name}'")
        break

    if class_name is None:
        errors.append(f"no class subclassing {base_name} found")
    else:
        errors.extend(_unbound_names(tree, class_name))

    return StaticCheckResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        class_name=class_name,
        kind=kind,
    )


def _module_bindings(tree: ast.Module) -> set[str]:
    """Names bound at module level by imports, definitions and assignments."""
    bound: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                bound.add(alias.asname or alias.name)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
    return bound


def _unbound_names(tree: ast.Module, class_name: str) -> list[str]:
    """Report base classes and decorators the module uses without importing.

    Generated operators are persisted and imported as standalone modules, so a
    class that relies on names injected by the caller would load in the harness
    but fail (or silently not register) everywhere else.
    """
    import builtins

    bound = _module_bindings(tree)
    errors: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        referenced: list[ast.expr] = list(node.bases)
        for decorator in node.decorator_list:
            referenced.append(decorator.func if isinstance(decorator, ast.Call) else decorator)
        for expr in referenced:
            root = expr
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id not in bound and not hasattr(builtins, root.id):
                errors.append(
                    f"'{root.id}' is used but never imported; the module must be "
                    "self-contained (add the import at the top)"
                )
    return errors


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


# ---------------------------------------------------------------------------
# gates 2-4: execution in a subprocess
# ---------------------------------------------------------------------------

_RUNNER = r'''
import json, sys, time, random, traceback
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
sys.path.insert(0, payload["repo_root"])

from large_neighborhood_search.lns import read_problem_for_lns, OptDSLEvaluator
from large_neighborhood_search.engine import LargeNeighborhoodSearchEngine
from large_neighborhood_search.defaults import (
    MaxIterationsStop, NeighborhoodPoolSelector, ImprovingAcceptance, SampledRepair,
)
from large_neighborhood_search._utils import clone_assignment, has_unassigned, get_decision_value
# Importing this module populates the operator registry; without it
# create_repair()/create_destroy() have nothing to resolve.
import large_neighborhood_search.builtin_operators  # noqa: F401
from large_neighborhood_search.registry import create_destroy, create_repair, load_generated_directory

# Generated operators (e.g. a partner accepted earlier in the same /tune run)
# are only reachable by name once their modules are imported.
if payload.get("operator_dir"):
    load_generated_directory(payload["operator_dir"])

source = payload["source"]
namespace = {"__name__": "generated_operator"}
exec(compile(source, "<generated>", "exec"), namespace)

class_name = payload["class_name"]
cls = namespace[class_name]
operator = cls()

problem_data, context = read_problem_for_lns(payload["instance"], random_seed=payload["seed"])
evaluator = OptDSLEvaluator(problem_data)
context.extra["evaluator"] = evaluator
context.extra["penalty_base"] = evaluator.penalty_base

decision_keys = context.extra["decision_keys"]

# --- gate 2: contract on synthetic assignments -------------------------
from large_neighborhood_search.lns import _build_empty_assignment
from large_neighborhood_search._utils import set_decision_value

empty = _build_empty_assignment(context)
full = _build_empty_assignment(context)
rng = random.Random(payload["seed"])
for key in decision_keys:
    lo, hi = context.extra["decision_domains"][key]
    set_decision_value(full, key, rng.randint(lo, hi))

for label, assignment in (("empty", empty), ("full", full)):
    probe = clone_assignment(assignment)
    try:
        result = operator.destroy(probe, context) if payload["kind"] == "destroy" else operator.repair(probe, context)
    except Exception:
        print(json.dumps({"ok": False, "error": f"{label} assignment raised:\n{traceback.format_exc()}"}))
        sys.exit(0)
    if not isinstance(result, dict):
        print(json.dumps({"ok": False, "error": f"{label} assignment: returned {type(result).__name__}, expected dict"}))
        sys.exit(0)

# --- gate 4: effect measurement ---------------------------------------
# A destroy operator is judged by how much it clears; a repair operator by how
# much of a deliberately-damaged assignment it restores.
cleared_fractions = []
completion_fractions = []

if payload["kind"] == "destroy":
    for _ in range(payload["probes"]):
        probe = clone_assignment(full)
        try:
            result = operator.destroy(probe, context)
        except Exception:
            print(json.dumps({"ok": False, "error": "probe raised:\n" + traceback.format_exc()}))
            sys.exit(0)
        cleared = sum(1 for key in decision_keys if get_decision_value(result, key) is None)
        cleared_fractions.append(cleared / max(1, len(decision_keys)))
else:
    # Damage the assignment with a real destroy operator, then measure how much
    # the candidate repair restores.
    damage = create_destroy(payload["destroy"])
    for _ in range(payload["probes"]):
        probe = clone_assignment(full)
        try:
            damaged = damage.destroy(probe, context)
        except Exception:
            print(json.dumps({"ok": False, "error": "damage operator raised:\n" + traceback.format_exc()}))
            sys.exit(0)
        missing_before = sum(1 for key in decision_keys if get_decision_value(damaged, key) is None)
        if missing_before == 0:
            continue
        try:
            repaired = operator.repair(clone_assignment(damaged), context)
        except Exception:
            print(json.dumps({"ok": False, "error": "probe raised:\n" + traceback.format_exc()}))
            sys.exit(0)
        missing_after = sum(1 for key in decision_keys if get_decision_value(repaired, key) is None)
        restored = max(0, missing_before - missing_after)
        completion_fractions.append(restored / missing_before)

# --- gate 3+4: run the engine -----------------------------------------
from large_neighborhood_search.lns import GreedyRandomizedInitializer

def _resolve_initializer(name):
    """Pick an initializer, honouring problem-specific ones when asked.

    The generic greedy initializer cannot construct a feasible CVRP or JSSP
    assignment, so on those problems the baseline score is a penalty and no
    candidate can ever show an improvement. ``"auto"`` selects the adapter that
    matches the detected problem class.
    """
    if name == "random":
        from large_neighborhood_search.lns import RandomAssignmentInitializer
        return RandomAssignmentInitializer()
    if name != "auto":
        return GreedyRandomizedInitializer()

    try:
        from large_neighborhood_search.problems import (
            CVRPRouteInitializer,
            CuttingPackingInitializer,
            JSSPScheduleInitializer,
            WoodcuttingPipelineInitializer,
            detect_2dbp_problem,
            detect_cutting_packing_problem,
            detect_cvrp_problem,
            detect_woodcutting_pipeline_problem,
            prepare_cvrp_assignment_for_evaluation,
        )
    except Exception:
        return GreedyRandomizedInitializer()

    if detect_cvrp_problem(context):
        context.extra["pre_evaluate_assignment_hook"] = prepare_cvrp_assignment_for_evaluation
        return CVRPRouteInitializer()
    if detect_cutting_packing_problem(context):
        return CuttingPackingInitializer()
    if detect_woodcutting_pipeline_problem(context):
        return WoodcuttingPipelineInitializer()
    if detect_2dbp_problem(context):
        return GreedyRandomizedInitializer(scoring_mode="objective")

    constants = context.constants
    if all(k in constants for k in ("N_JOBS", "N_MACHINES", "PROCESSING_TIMES", "MACHINE_SEQUENCE")):
        return JSSPScheduleInitializer()

    return GreedyRandomizedInitializer()

baseline_initializer = _resolve_initializer(payload.get("initializer", "greedy"))
initializer_source = payload.get("initializer_source")
if initializer_source:
    _initializer_ns = {"__name__": "generated_initializer"}
    exec(compile(initializer_source, "<generated_initializer>", "exec"), _initializer_ns)
    baseline_initializer = _initializer_ns[payload["initializer_class"]]()
baseline_initializer.reset_for_run(context)
baseline_assignment = baseline_initializer.initialize(context)
baseline_score = evaluator.evaluate(baseline_assignment, context)

from large_neighborhood_search.components import Initializer


class _FixedStart(Initializer):
    """Start the engine from exactly the assignment the baseline was scored on.

    Calling the initializer a second time would draw from an advanced RNG and
    yield a different start, making ``baseline - best`` meaningless (it could
    even come out negative for a run that never got worse).
    """

    def initialize(self, _context):
        return clone_assignment(baseline_assignment)


if payload["kind"] == "destroy":
    neighborhoods = [(operator, create_repair(payload["repair"]))]
else:
    neighborhoods = [(create_destroy(payload["destroy"]), operator)]

engine = LargeNeighborhoodSearchEngine(
    initializer=_FixedStart(),
    selector=NeighborhoodPoolSelector(neighborhoods=neighborhoods),
    evaluator=evaluator,
    acceptance=ImprovingAcceptance(),
    stop=MaxIterationsStop(payload["iterations"]),
)
started = time.perf_counter()
try:
    result = engine.run(context)
except Exception:
    print(json.dumps({"ok": False, "error": "engine raised:\n" + traceback.format_exc()}))
    sys.exit(0)
elapsed = time.perf_counter() - started

print(json.dumps({
    "ok": True,
    "iterations": result.stats.iterations,
    # `stats.accepted` counts accepted *moves* (infeasible ones included), so
    # it is not a feasibility count. Every iteration yields one candidate.
    "feasible_candidates": result.stats.iterations - result.stats.infeasible_candidates,
    "infeasible_candidates": result.stats.infeasible_candidates,
    "improvements": result.stats.improvements,
    "best_score": result.incumbent.score,
    "baseline_score": baseline_score,
    "objective_sense": context.objective_sense,
    "mean_cleared_fraction": sum(cleared_fractions) / len(cleared_fractions) if cleared_fractions else 0.0,
    "mean_completion_fraction": sum(completion_fractions) / len(completion_fractions) if completion_fractions else 0.0,
    "elapsed_seconds": elapsed,
}))
'''


def _get(assignment: dict[str, Any], key: tuple[str, Any]) -> Any:
    """Deprecated shim kept for external callers; use ``get_decision_value``."""
    from large_neighborhood_search._utils import get_decision_value

    return get_decision_value(assignment, key)


def run_candidate(
    source: str,
    class_name: str,
    kind: str,
    instance: str | Path,
    *,
    repo_root: str | Path,
    seed: int = 0,
    iterations: int = 200,
    probes: int = 20,
    repair: str = "SampledRepair",
    destroy: str = "RandomFractionDestroy",
    initializer: str = "greedy",
    initializer_source: str | None = None,
    initializer_class: str | None = None,
    operator_dir: str | Path | None = None,
    timeout: float = 120.0,
) -> RunMetrics:
    """Execute a candidate operator in an isolated subprocess.

    *operator_dir* makes generated operators resolvable as the ``repair`` /
    ``destroy`` partner by registry name.
    """
    payload = {
        "source": source,
        "class_name": class_name,
        "kind": kind,
        "instance": str(instance),
        "repo_root": str(repo_root),
        "seed": seed,
        "iterations": iterations,
        "probes": probes,
        "repair": repair,
        "destroy": destroy,
        "initializer": initializer,
        "initializer_source": initializer_source,
        "initializer_class": initializer_class,
        "operator_dir": str(operator_dir) if operator_dir else None,
    }

    with tempfile.TemporaryDirectory() as tmp:
        payload_path = Path(tmp) / "payload.json"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        runner_path = Path(tmp) / "runner.py"
        runner_path.write_text(_RUNNER, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, str(runner_path), str(payload_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(repo_root),
            )
        except subprocess.TimeoutExpired:
            return RunMetrics(ok=False, error=f"timed out after {timeout:.0f}s")

    if completed.returncode != 0:
        return RunMetrics(
            ok=False,
            error=f"runner exited {completed.returncode}\n{completed.stderr[-2000:]}",
        )

    try:
        data = json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return RunMetrics(ok=False, error=f"unparseable runner output:\n{completed.stdout[-2000:]}")

    if not data.get("ok"):
        return RunMetrics(ok=False, error=data.get("error", "unknown failure"))

    return RunMetrics(
        ok=True,
        iterations=data["iterations"],
        feasible_candidates=data["feasible_candidates"],
        infeasible_candidates=data["infeasible_candidates"],
        improvements=data["improvements"],
        best_score=data["best_score"],
        baseline_score=data["baseline_score"],
        mean_cleared_fraction=data["mean_cleared_fraction"],
        mean_completion_fraction=data.get("mean_completion_fraction", 0.0),
        elapsed_seconds=data["elapsed_seconds"],
        objective_sense=data.get("objective_sense", "minimize"),
    )


# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------


@dataclass
class AcceptancePolicy:
    """Thresholds for accepting a candidate."""

    min_feasible_rate: float = 0.5
    min_cleared_fraction: float = 0.01
    max_cleared_fraction: float = 0.95
    #: A repair must restore at least this fraction of what a destroy removed.
    min_completion_fraction: float = 0.5
    require_improvement: bool = True
    max_seconds_per_iteration: float = 0.5
    #: When the search cannot start from a feasible assignment, measure the
    #: candidate by how much it reduces the infeasibility penalty instead of by
    #: its feasible-candidate rate. Candidates that progress toward feasibility
    #: are then accepted even if they rarely reach it themselves.
    feasibility_progress_mode: bool = False


def evaluate_candidate(
    source: str,
    kind: str,
    instance: str | Path,
    *,
    repo_root: str | Path,
    policy: AcceptancePolicy | None = None,
    **run_kwargs: Any,
) -> Verdict:
    """Run every gate and return a verdict."""
    policy = policy or AcceptancePolicy()
    reasons: list[str] = []

    static = static_check(source, kind)
    if not static.ok:
        return Verdict(accepted=False, reasons=static.errors, static=static)

    assert static.class_name is not None
    metrics = run_candidate(
        source,
        static.class_name,
        kind,
        instance,
        repo_root=repo_root,
        **run_kwargs,
    )

    if not metrics.ok:
        return Verdict(accepted=False, reasons=[metrics.error or "execution failed"], static=static, metrics=metrics)

    if policy.feasibility_progress_mode:
        # No feasible start was available (tightly-coupled problem), so a
        # candidate is judged by whether it cuts the infeasibility penalty:
        # the engine minimizes failed constraints, so a positive score
        # improvement means the neighborhood moves toward feasibility.
        if (
            metrics.best_score is not None
            and metrics.baseline_score is not None
            and metrics.improvement <= 0
        ):
            reasons.append(
                f"no reduction in infeasibility penalty "
                f"(baseline {metrics.baseline_score}, best {metrics.best_score}); "
                "the operator does not move the search toward feasibility"
            )
    else:
        if metrics.feasible_rate < policy.min_feasible_rate:
            reasons.append(
                f"feasible candidate rate {metrics.feasible_rate:.0%} is below "
                f"{policy.min_feasible_rate:.0%}"
            )

        if policy.require_improvement and metrics.improvement <= 0:
            reasons.append(
                f"no improvement over the baseline initializer "
                f"(baseline {metrics.baseline_score}, best {metrics.best_score})"
            )

    # Neighborhood-shape gates apply in both regimes: a destroy must actually
    # clear something (but not everything), a repair must restore what a
    # destroy removed.
    if kind == "destroy":
        if metrics.mean_cleared_fraction < policy.min_cleared_fraction:
            reasons.append(
                f"destroys only {metrics.mean_cleared_fraction:.1%} of decisions on average; "
                "the neighborhood is too small to explore"
            )
        if metrics.mean_cleared_fraction > policy.max_cleared_fraction:
            reasons.append(
                f"destroys {metrics.mean_cleared_fraction:.0%} of decisions on average; "
                "this is a restart, not a neighborhood"
            )
    else:
        if metrics.mean_completion_fraction < policy.min_completion_fraction:
            reasons.append(
                f"restores only {metrics.mean_completion_fraction:.0%} of the decisions a destroy "
                f"removed; expected at least {policy.min_completion_fraction:.0%}"
            )

    if metrics.iterations > 0:
        per_iteration = metrics.elapsed_seconds / metrics.iterations
        if per_iteration > policy.max_seconds_per_iteration:
            reasons.append(
                f"{per_iteration:.3f}s per iteration exceeds the "
                f"{policy.max_seconds_per_iteration:.3f}s budget"
            )

    return Verdict(accepted=not reasons, reasons=reasons, static=static, metrics=metrics)
