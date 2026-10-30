"""The tool surface the model is allowed to call.

Design rules, all of which exist to keep an autonomous loop safe:

* **Every tool returns a dict and never raises.** A failure is
  ``{"ok": False, "error": "..."}``, which the model can read and react to. An
  exception would abort the conversation and lose the context that explains it.
* **Writes are confined.** ``write_file`` refuses any path outside the
  configured output directory, and no tool ever mutates the source ``.dsl``.
* **Results are JSON-serialisable.** The same dict is used for the model, for
  ``--json`` output, and for the report, so there is one representation to
  trust rather than three that can drift.

The schemas are hand-written rather than generated from signatures: the model
reads them, so the descriptions matter as much as the types.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from optdsl_tooling.analysis import analyze
from optdsl_tooling.constraint_validation import append_constraints, validate_constraints
from optdsl_tooling.fingerprint import fingerprint

from .digest import model_digest, model_summary
from .lns_runner import LNSRunConfig, run_lns
from .operator_loader import list_operators, load_generated_operators
from .session import Session

ToolHandler = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class Tool:
    """One callable capability, with the schema the model sees."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Name -> tool, with dispatch that converts exceptions into results."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def describe(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    def call(self, name: str, session: Session, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"ok": False, "error": f"unknown tool '{name}'; available: {', '.join(self.names())}"}
        try:
            result = tool.handler(session, **arguments)
        except TypeError as exc:
            return {"ok": False, "error": f"bad arguments for '{name}': {exc}"}
        except Exception as exc:  # noqa: BLE001 - a tool must never abort the loop
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        session.record(name, arguments, result)
        return result


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def _analyze_model(session: Session, *, include_source: bool = False) -> dict[str, Any]:
    summary = model_summary(session.source)
    if summary.syntax_error:
        return {"ok": False, "error": f"the formulation does not parse: {summary.syntax_error}"}
    return {
        "ok": True,
        "summary": (
            f"{summary.problem_class or 'unknown'} problem, "
            f"{summary.decision_count} decision indices, "
            f"{len(summary.predicates)} predicates"
        ),
        "model": summary.to_dict(),
        "digest": model_digest(session.source, include_source=include_source),
    }


def _translate_model(session: Session) -> dict[str, Any]:
    from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator

    translator = MiniZincTranslator(session.source, dsl_index_base=session.config.dsl_index_base)
    model = translator.unroll_translation()
    return {"ok": True, "summary": f"{len(model.splitlines())} lines of MiniZinc", "model": model}


# ---------------------------------------------------------------------------
# exact backend
# ---------------------------------------------------------------------------


def _solve_minizinc(
    session: Session,
    *,
    solver: str | None = None,
    timelimit: float | None = None,
) -> dict[str, Any]:
    """Run the exact backend.

    MiniZinc is an optional external dependency, so a missing installation is
    reported as a normal failure rather than an exception. The tuning loop
    degrades to LNS-only comparison in that case.
    """
    try:
        from src.optdsl.solver.DSL_solver import DSLSolver
    except ImportError as exc:
        return {"ok": False, "error": f"MiniZinc backend unavailable: {exc}"}

    solver_name = solver or session.config.solver_name
    limit = float(timelimit if timelimit is not None else session.config.solve_timelimit)

    # A warm start captured from a previous LNS run decorates this solve. The
    # source text is never touched: hints live in the spec and are merged into
    # the translated model only.
    warm_start = session.warm_start
    try:
        runner = DSLSolver(
            session.source,
            solver_name=solver_name,
            timelimit=limit,
            dsl_index_base=session.config.dsl_index_base,
            warm_start=warm_start,
        )
        raw = runner.run()
    except Exception as exc:  # noqa: BLE001 - includes "MiniZinc not installed"
        return {
            "ok": False,
            "error": (
                f"MiniZinc solve failed ({type(exc).__name__}: {exc}). "
                "Is MiniZinc installed and on PATH?"
            ),
        }

    objectives = raw.get("objectives") or []
    best = objectives[-1] if objectives else None
    status = str(raw.get("status", "unknown"))
    bound = raw.get("objective_bound")

    result = {
        "ok": True,
        "summary": (
            f"{status}, objective {best}"
            f"{' (warm start applied)' if warm_start else ''}"
        ),
        "solver": solver_name,
        "status": status,
        "objectiveValue": best,
        "objectiveBound": bound,
        "warmStart": warm_start is not None,
        "totalTime": raw.get("total_time"),
        "solution": raw.get("best_solution"),
        "objectiveHistory": objectives,
        "statistics": raw.get("statistics", {}),
    }
    session.last_solve = result
    return result


def _estimate_bound(session: Session, *, timelimit: float | None = None) -> dict[str, Any]:
    """Exact-solver bound, used as the reference for the optimality gap."""
    from hybrid.lower_bound import estimate_lower_bound

    if session.path is None:
        return {"ok": False, "error": "a bound needs a file path; this session has none"}

    try:
        result = estimate_lower_bound(
            session.path,
            timelimit=float(timelimit if timelimit is not None else session.config.solve_timelimit),
            solver_name=session.config.solver_name,
            dsl_index_base=session.config.dsl_index_base,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"bound estimation failed: {type(exc).__name__}: {exc}"}

    return {
        "ok": True,
        "summary": f"bound {result['lower_bound']}, best {result['best_objective']}",
        "lowerBound": result["lower_bound"],
        "bestObjective": result["best_objective"],
        "status": result["status"],
    }


# ---------------------------------------------------------------------------
# constraints
# ---------------------------------------------------------------------------


def _propose_constraints(
    session: Session,
    *,
    constraints: list[dict[str, str]],
    samples: int = 200,
) -> dict[str, Any]:
    """Validate proposed constraints without writing anything."""
    report = validate_constraints(session.source, constraints, samples=samples)
    return {
        "ok": bool(report.get("ok")),
        "summary": (
            "constraints are valid"
            if report.get("ok")
            else "; ".join(report.get("errors", []))[:300]
        ),
        **report,
    }


def _add_constraints(
    session: Session,
    *,
    constraints: list[dict[str, str]],
    write: bool = True,
    verify: bool = True,
) -> dict[str, Any]:
    """Validate, then append constraints and write a new model file.

    The source file is never modified. The constrained model is written next to
    the output directory as ``<stem>.constrained.dsl`` so the user can diff it
    and adopt it deliberately.
    """
    report = validate_constraints(session.source, constraints)
    if not report.get("ok"):
        return {
            "ok": False,
            "error": "; ".join(report.get("errors", ["validation failed"])),
            "validation": report,
        }

    combined = append_constraints(session.source, constraints)

    # A constraint that validates can still make the model infeasible. Checking
    # the translation catches structural breakage cheaply, before a solve.
    if verify:
        try:
            from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator

            MiniZincTranslator(combined, dsl_index_base=session.config.dsl_index_base).unroll_translation()
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": f"the constrained model does not translate: {type(exc).__name__}: {exc}",
                "validation": report,
            }

    session.replace_source(combined)
    session.pending_constraints.extend(constraints)

    result: dict[str, Any] = {
        "ok": True,
        "summary": f"added {len(constraints)} constraint(s)",
        "added": [constraint.get("name") for constraint in constraints],
        "validation": report,
        "source": combined,
    }

    if write:
        session.config.ensure_directories()
        target = session.config.output_dir / f"{session.stem}.constrained.dsl"
        target.write_text(combined, encoding="utf-8")
        session.add_artifact("constrained-model", target, f"{len(constraints)} added constraint(s)")
        result["path"] = str(target)

    return result


# ---------------------------------------------------------------------------
# heuristic backend
# ---------------------------------------------------------------------------


def _run_lns_tool(
    session: Session,
    *,
    iterations: int | None = None,
    seed: int | None = None,
    destroys: list[str] | None = None,
    repairs: list[str] | None = None,
    initializer: str | None = None,
    acceptance: str | None = None,
    adaptive: bool = False,
    record_trajectory: bool = False,
    show_solution: bool = True,
) -> dict[str, Any]:
    """Run LNS on the session's current model.

    The session's model text is written to a temporary file when it differs from
    the on-disk source, because the LNS reader takes a path.
    """
    path = _materialise(session)
    if path is None:
        return {"ok": False, "error": "could not materialise the model for LNS"}

    load_generated_operators(session.config.operator_dir)

    from .initializer import discover_initializer
    from .lns_config import resolve_run_settings

    effective_initializer = initializer or session.config.lns_initializer
    # A tuned LNS config written by /tune for this model's formulation supplies
    # the construction heuristic and operators unless they are given explicitly.
    settings = resolve_run_settings(
        session.source,
        session.config.operator_dir,
        destroys=destroys,
        repairs=repairs,
        initializer=effective_initializer,
        adaptive=adaptive,
    )
    lns_initializer: object = settings.initializer
    if settings.log.get("source") == "default" and effective_initializer == "auto":
        # Legacy: a construction persisted per file stem by older /tune runs.
        synthesized = discover_initializer(session.config.operator_dir, path.stem)
        if synthesized is not None:
            lns_initializer = synthesized.instantiate()

    config = LNSRunConfig(
        instance=path,
        seed=int(seed if seed is not None else session.config.lns_seed),
        iterations=int(iterations if iterations is not None else session.config.lns_iterations),
        initializer=lns_initializer,
        acceptance=acceptance or "improving",
        destroys=list(settings.destroys),
        repairs=list(settings.repairs),
        adaptive=settings.adaptive,
        record_trajectory=record_trajectory,
    )
    result = run_lns(config)
    payload = result.to_dict()
    payload["lnsConfig"] = settings.log
    if not show_solution:
        payload.pop("rendered", None)
    if result.ok and result.feasible:
        _capture_warm_start(session, result)
        if session.warm_start_path is not None:
            payload["warmStartSaved"] = True
            payload["warmStartPath"] = str(session.warm_start_path)
    if result.ok:
        session.last_lns = payload
    return payload


def _capture_warm_start(session: Session, result: Any) -> None:
    """Persist the feasible incumbent as a transient warm-start snapshot.

    The session's source is left untouched — only a small JSON document is
    written next to the other outputs. ``/solve`` and the ``solve_minizinc``
    tool read ``session.warm_start`` from memory and inject it into the
    translated model.
    """
    from hybrid.warm_start import save_warm_start, spec_from_assignment

    objective_value = (
        result.objective_value if result.objective_value is not None else result.score
    )
    spec = spec_from_assignment(
        result.assignment,
        score=objective_value,
        objective_sense=result.objective_sense,
        problem=str(result.instance),
    )
    session.warm_start = spec

    session.config.ensure_directories()
    target = session.config.output_dir / f"{session.stem}.warmstart.json"
    save_warm_start(target, spec)
    session.warm_start_path = target


def _evaluate_operator(
    session: Session,
    *,
    source: str,
    kind: str,
    iterations: int = 200,
    seed: int = 0,
    require_improvement: bool = True,
) -> dict[str, Any]:
    """Run the operator quality gate on a candidate class."""
    from operator_synthesis.harness import AcceptancePolicy, evaluate_candidate

    path = _materialise(session)
    if path is None:
        return {"ok": False, "error": "could not materialise the model for evaluation"}

    verdict = evaluate_candidate(
        source,
        kind,
        path,
        repo_root=session.config.repo_root,
        policy=AcceptancePolicy(require_improvement=require_improvement),
        iterations=iterations,
        seed=seed,
        initializer="auto",
    )
    payload = verdict.to_dict()
    return {
        "ok": True,
        "accepted": verdict.accepted,
        "summary": "accepted" if verdict.accepted else "; ".join(verdict.reasons)[:300],
        **payload,
    }


def _synthesize_operator(
    session: Session,
    *,
    kind: str,
    request: str = "",
    attempts: int = 3,
    iterations: int = 200,
    seed: int = 0,
    write: bool = True,
) -> dict[str, Any]:
    """Propose, validate and retry an operator using the model as the proposer.

    Reuses ``operator_synthesis.synthesize`` so the retry/feedback behaviour is
    identical to the CLI and the VS Code extension.
    """
    from operator_synthesis.prompts import OperatorSpec
    from operator_synthesis.synthesize import synthesize, write_operator

    from .llm import LLMClient

    if session.config.dry_run:
        return {"ok": False, "error": "operator synthesis needs a model; --dry-run disables it"}
    if not session.config.has_credentials:
        return {
            "ok": False,
            "error": (
                "no model credentials: set OPTDSL_AGENT_API_KEY (or OPENAI_API_KEY), "
                "pass --api-key, or pass --base-url for a local endpoint"
            ),
        }

    path = _materialise(session)
    if path is None:
        return {"ok": False, "error": "could not materialise the model for synthesis"}

    index = analyze(session.source)
    problem = fingerprint(index)
    spec = OperatorSpec(
        kind=kind,
        problem_class=problem.best.name if problem.best else "unknown",
        objective=(
            f"{index.objective.sense} {index.objective.expression}"
            if index.objective
            else "satisfaction"
        ),
        target_variables=[name for name, var in index.variables.items() if var.is_decision],
        hyperparameters={"fraction": 0.2},
        invariants=[],
        notes=request,
    )

    client = LLMClient(session.config)

    def proposer(messages: list[dict[str, Any]]) -> str:
        session.llm_calls += 1
        return client.chat(messages).content

    result = synthesize(
        index,
        problem,
        spec,
        path,
        repo_root=session.config.repo_root,
        proposer=proposer,
        max_attempts=attempts,
        run_kwargs={"iterations": iterations, "seed": seed, "initializer": "auto"},
    )

    payload: dict[str, Any] = {
        "ok": True,
        "accepted": result.accepted,
        "summary": (
            f"accepted {result.class_name}"
            if result.accepted
            else f"no candidate accepted after {len(result.attempts)} attempt(s)"
        ),
        "class_name": result.class_name,
        "attempts": [attempt.to_dict() for attempt in result.attempts],
    }

    if result.accepted and write:
        session.config.ensure_directories()
        written = write_operator(
            result,
            session.config.operator_dir,
            problem_class=spec.problem_class,
            kind=kind,
        )
        session.add_artifact("operator", written, f"{kind} operator {result.class_name}")
        payload["path"] = str(written)
        payload["registered"] = load_generated_operators(session.config.operator_dir)

    return payload


# ---------------------------------------------------------------------------
# comparison
# ---------------------------------------------------------------------------


def _compare_runs(session: Session) -> dict[str, Any]:
    """Compare the last LNS run against the last exact solve.

    Reports the LNS objective, the exact objective, the exact solve's lower
    bound (when available), and the percentage quality gaps between every pair
    (LNS vs solve, LNS vs bound, solve vs bound). For maximization problems the
    sign convention is flipped so a positive percentage always means "the first
    value is worse than the second".
    """
    lns = session.last_lns
    exact = session.last_solve
    if lns is None:
        return {"ok": False, "error": "no LNS run recorded; call run_lns first"}
    if exact is None:
        return {"ok": False, "error": "no exact solve recorded; call solve_minizinc first"}

    lns_value = lns.get("objectiveValue")
    exact_value = exact.get("objectiveValue")
    if lns_value is None or exact_value is None:
        return {
            "ok": False,
            "error": "one of the runs has no objective value (infeasible or no solution)",
            "lns": lns.get("objectiveValue"),
            "exact": exact.get("objectiveValue"),
        }

    sense = lns.get("objectiveSense", "minimize")
    if sense == "maximize":
        gap = exact_value - lns_value
    else:
        gap = lns_value - exact_value
    relative = (gap / abs(exact_value)) if exact_value else None

    bound_value = exact.get("objectiveBound")
    bound_value = float(bound_value) if bound_value is not None else None

    def _worse_fraction(value: float, reference: float | None) -> float | None:
        """Fraction by which *value* is worse than *reference* (None if unknown/invalid)."""
        if value is None or reference is None or reference == 0:
            return None
        if sense == "maximize":
            return (reference - value) / abs(reference)
        return (value - reference) / abs(reference)

    lns_vs_bound = _worse_fraction(lns_value, bound_value)
    solve_vs_bound = _worse_fraction(exact_value, bound_value)

    summary = f"gap {gap:g}"
    if relative is not None:
        summary += f" ({relative:.1%})"
    if bound_value is not None:
        summary += (
            f", lower bound {bound_value:g}"
            + (f", solve gap {solve_vs_bound:.1%}" if solve_vs_bound is not None else "")
        )

    return {
        "ok": True,
        "summary": summary,
        "objectiveSense": sense,
        "lnsObjective": lns_value,
        "exactObjective": exact_value,
        "lowerBound": bound_value,
        "gap": gap,
        "relativeGap": relative,
        "lnsVsSolvePct": relative,
        "lnsVsBoundPct": lns_vs_bound,
        "solveVsBoundPct": solve_vs_bound,
        "lnsFeasible": lns.get("feasible"),
        "lnsIterations": lns.get("iterations"),
        "lnsElapsedSeconds": lns.get("elapsedSeconds"),
        "exactStatus": exact.get("status"),
    }


# ---------------------------------------------------------------------------
# filesystem
# ---------------------------------------------------------------------------


def _write_file(session: Session, *, name: str, content: str) -> dict[str, Any]:
    """Write a file inside the configured output directory.

    Path traversal is rejected rather than sanitised: silently rewriting a
    requested path would hide a bug in the caller.
    """
    session.config.ensure_directories()
    root = session.config.output_dir.resolve()
    target = (root / name).resolve()
    if root not in target.parents and target != root:
        return {"ok": False, "error": f"refusing to write outside {root}"}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    session.add_artifact("report", target, "written by the agent")
    return {"ok": True, "summary": f"wrote {target.name}", "path": str(target)}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _materialise(session: Session) -> Path | None:
    """Return a path holding the session's current model text.

    When the session still matches its source file, that file is used directly
    so operator evaluation sees the real instance path. Otherwise the text is
    written to the output directory, because the LNS reader and the operator
    harness both take paths.
    """
    if session.path is not None:
        try:
            if session.path.read_text(encoding="utf-8") == session.source:
                return session.path
        except OSError:
            pass

    session.config.ensure_directories()
    target = session.config.output_dir / f"{session.stem}.current.dsl"
    target.write_text(session.source, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

_CONSTRAINT_SCHEMA = {
    "type": "array",
    "description": "Constraints to add, each with a predicate definition and its invocation.",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Predicate name, e.g. 'capacity_limit'."},
            "code": {
                "type": "string",
                "description": "A Python function definition using `assert` for the constraint.",
            },
            "invocation": {
                "type": "string",
                "description": "The top-level call that activates it, e.g. 'capacity_limit(assignments)'.",
            },
        },
        "required": ["name", "code", "invocation"],
    },
}


def build_registry() -> ToolRegistry:
    """Construct the default tool set."""
    return ToolRegistry(
        [
            Tool(
                name="analyze_model",
                description=(
                    "Summarise the current formulation: problem class, decision variables and "
                    "domains, constants, predicates, objective, and diagnostics. Call this first."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "include_source": {
                            "type": "boolean",
                            "description": "Include the full model source in the digest.",
                        }
                    },
                },
                handler=_analyze_model,
            ),
            Tool(
                name="translate_model",
                description="Translate the formulation to MiniZinc source text.",
                parameters={"type": "object", "properties": {}},
                handler=_translate_model,
            ),
            Tool(
                name="solve_minizinc",
                description=(
                    "Solve the formulation exactly with MiniZinc. Returns the objective value, "
                    "status, bound and solution. Use this as the reference for LNS quality."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "solver": {
                            "type": "string",
                            "description": "MiniZinc solver name, e.g. 'cp-sat', 'gecode', 'chuffed'.",
                        },
                        "timelimit": {"type": "number", "description": "Time limit in seconds."},
                    },
                },
                handler=_solve_minizinc,
            ),
            Tool(
                name="estimate_bound",
                description="Estimate an objective bound with the exact solver, for gap analysis.",
                parameters={
                    "type": "object",
                    "properties": {"timelimit": {"type": "number"}},
                },
                handler=_estimate_bound,
            ),
            Tool(
                name="propose_constraints",
                description=(
                    "Validate proposed constraints without changing the model. Checks that they "
                    "parse, are not vacuous, and do not make the model trivially infeasible."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "constraints": _CONSTRAINT_SCHEMA,
                        "samples": {"type": "integer", "description": "Random samples to test."},
                    },
                    "required": ["constraints"],
                },
                handler=_propose_constraints,
            ),
            Tool(
                name="add_constraints",
                description=(
                    "Validate and add constraints to the model, writing a new .constrained.dsl "
                    "file. The original file is never modified."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "constraints": _CONSTRAINT_SCHEMA,
                        "write": {"type": "boolean", "description": "Write the new model to disk."},
                        "verify": {
                            "type": "boolean",
                            "description": "Check that the constrained model still translates.",
                        },
                    },
                    "required": ["constraints"],
                },
                handler=_add_constraints,
            ),
            Tool(
                name="list_operators",
                description="List available LNS destroy and repair operators for this problem class.",
                parameters={
                    "type": "object",
                    "properties": {
                        "problem": {
                            "type": "string",
                            "description": "Filter by problem class; omit for all operators.",
                        }
                    },
                },
                handler=lambda session, problem=None: {
                    "ok": True,
                    "summary": "operators listed",
                    "operators": list_operators(problem),
                },
            ),
            Tool(
                name="run_lns",
                description=(
                    "Run large neighborhood search on the current model. Returns the objective, "
                    "feasibility, statistics and optionally a per-iteration trajectory."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "iterations": {"type": "integer"},
                        "seed": {"type": "integer"},
                        "destroys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Destroy operator names; omit for the default.",
                        },
                        "repairs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Repair operator names; omit for SampledRepair.",
                        },
                        "initializer": {
                            "type": "string",
                            "description": "'auto', 'greedy', 'random', 'mcmc', or a problem name.",
                        },
                        "acceptance": {"type": "string", "description": "'improving' or 'sa'."},
                        "adaptive": {
                            "type": "boolean",
                            "description": "Use adaptive operator selection.",
                        },
                        "record_trajectory": {
                            "type": "boolean",
                            "description": "Record per-iteration scores for diagnosis.",
                        },
                        "show_solution": {
                            "type": "boolean",
                            "description": (
                                "Include a problem-specific rendering of the solution "
                                "(routes, schedule, bin contents). Default true."
                            ),
                        },
                    },
                },
                handler=_run_lns_tool,
            ),
            Tool(
                name="evaluate_operator",
                description=(
                    "Run the operator quality gate on a candidate class: static checks, contract "
                    "probes, and a measured LNS run against the baseline initializer."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Python class source."},
                        "kind": {"type": "string", "enum": ["destroy", "repair"]},
                        "iterations": {"type": "integer"},
                        "seed": {"type": "integer"},
                        "require_improvement": {"type": "boolean"},
                    },
                    "required": ["source", "kind"],
                },
                handler=_evaluate_operator,
            ),
            Tool(
                name="synthesize_operator",
                description=(
                    "Ask the model to write a new LNS operator for this formulation, validate it "
                    "with the quality gate, and save it if accepted."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": ["destroy", "repair"]},
                        "request": {
                            "type": "string",
                            "description": "What the neighborhood should do, in natural language.",
                        },
                        "attempts": {"type": "integer"},
                        "iterations": {"type": "integer"},
                        "seed": {"type": "integer"},
                        "write": {"type": "boolean"},
                    },
                    "required": ["kind"],
                },
                handler=_synthesize_operator,
            ),
            Tool(
                name="compare_runs",
                description=(
                    "Compare the last LNS run with the last exact solve: objective gap, relative "
                    "gap, and feasibility."
                ),
                parameters={"type": "object", "properties": {}},
                handler=_compare_runs,
            ),
            Tool(
                name="write_file",
                description="Write a file inside the agent output directory.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Relative file name."},
                        "content": {"type": "string"},
                    },
                    "required": ["name", "content"],
                },
                handler=_write_file,
            ),
        ]
    )


def tool_result_json(result: dict[str, Any]) -> str:
    """Serialise a tool result for the model, dropping bulky fields.

    The model does not need a full solution vector or the whole model text to
    decide what to do next, and including them crowds out the conversation.
    """
    trimmed = {
        key: value
        for key, value in result.items()
        if key not in {"source", "solution", "assignment", "trajectory"}
    }
    return json.dumps(trimmed, default=str)
