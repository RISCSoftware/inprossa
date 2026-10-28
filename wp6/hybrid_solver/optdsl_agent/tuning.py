"""Self-tuning: measure the gap, diagnose it, synthesize an operator, keep it if it wins.

The loop is bounded and autonomous. It never asks for approval mid-run, because
the point is to run unattended; instead it is bounded by an attempt budget and a
wall-clock budget, and it writes a report explaining every decision.

The acceptance rule is the part that matters. An operator that improves one
instance on one seed has not been shown to be useful — it may have memorized
that instance. So a candidate is only kept if it beats the incumbent operator set
on **held-out seeds**, which are never used during synthesis.
"""

from __future__ import annotations

import ast
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from operator_synthesis.harness import AcceptancePolicy, RunMetrics, run_candidate
from operator_synthesis.prompts import OperatorSpec
from operator_synthesis.synthesize import extract_code, synthesize, write_operator
from optdsl_tooling.analysis import analyze
from optdsl_tooling.fingerprint import fingerprint, problem_key, problem_label

from .config import AgentConfig
from .digest import model_digest
from .initializer import (
    InitializerArtifact,
    check_initializer,
    extract_initializer_code,
    static_check_initializer,
    write_initializer,
)
from .llm import ChatClient, LLMError
from .lns_config import TunedLNSConfig, config_path, load_tuned_config, save_tuned_config
from .lns_runner import LNSRunConfig, LNSRunResult, run_lns
from .operator_loader import load_generated_operators
from .prompts import (
    INITIALIZER_SITUATION_IMPROVE,
    INITIALIZER_SITUATION_INFEASIBLE,
    build_diagnosis_prompt,
    build_initializer_prompt,
)


@dataclass
class TuningBudget:
    """Limits for one tuning run."""

    max_attempts: int = 4
    max_wall_seconds: float = 900.0
    #: Seeds used to synthesize and validate a candidate.
    train_seeds: tuple[int, ...] = (0, 1)
    #: Seeds used only to decide whether to keep it.
    holdout_seeds: tuple[int, ...] = (7, 11)
    iterations: int = 200
    #: Retries for synthesizing a feasible initializer when LNS cannot reach
    #: feasibility on its own.
    max_initializer_attempts: int = 3


@dataclass
class OperatorScore:
    """Aggregate measurement for one operator across instances and seeds."""

    name: str
    kind: str
    mean_improvement: float
    mean_feasible_rate: float
    runs: int
    per_run: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "meanImprovement": round(self.mean_improvement, 4),
            "meanFeasibleRate": round(self.mean_feasible_rate, 4),
            "runs": self.runs,
            "perRun": self.per_run,
        }


@dataclass
class TuningAttempt:
    """One synthesis attempt and its verdict."""

    number: int
    kind: str
    request: str
    accepted: bool
    class_name: str | None = None
    source: str | None = None
    train: OperatorScore | None = None
    holdout: OperatorScore | None = None
    reasons: list[str] = field(default_factory=list)
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "kind": self.kind,
            "request": self.request,
            "accepted": self.accepted,
            "className": self.class_name,
            "train": self.train.to_dict() if self.train else None,
            "holdout": self.holdout.to_dict() if self.holdout else None,
            "reasons": self.reasons,
            "path": self.path,
        }


@dataclass
class TuningReport:
    """Everything a tuning run learned."""

    instances: list[str]
    baseline_lns: dict[str, Any] = field(default_factory=dict)
    exact: dict[str, Any] = field(default_factory=dict)
    diagnosis: str = ""
    attempts: list[TuningAttempt] = field(default_factory=list)
    accepted: list[str] = field(default_factory=list)
    stopped_reason: str = "completed"
    elapsed_seconds: float = 0.0
    initializer: dict[str, Any] | None = None
    initializer_error: str | None = None
    #: Whether the (final) LNS baseline was feasible. When False, candidates
    #: are judged in progress mode: by how much they reduce the infeasibility
    #: penalty rather than by their feasible-candidate rate.
    baseline_feasible: bool | None = None
    #: Formulation identity the tuned artifacts are keyed by.
    problem_key: str = ""
    problem_label: str = ""
    #: The tuned LNS configuration written by this run (``None`` when nothing
    #: new was accepted), its path, and the verification run that used it.
    lns_config: dict[str, Any] | None = None
    lns_config_path: str | None = None
    tuned_lns: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instances": self.instances,
            "problemKey": self.problem_key,
            "problemLabel": self.problem_label,
            "baselineLns": self.baseline_lns,
            "exact": self.exact,
            "diagnosis": self.diagnosis,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "accepted": self.accepted,
            "stoppedReason": self.stopped_reason,
            "elapsedSeconds": round(self.elapsed_seconds, 2),
            "initializer": self.initializer,
            "initializerError": self.initializer_error,
            "baselineFeasible": self.baseline_feasible,
            "lnsConfig": self.lns_config,
            "lnsConfigPath": self.lns_config_path,
            "tunedLns": self.tuned_lns,
        }

    def to_markdown(self) -> str:
        lines = ["# LNS tuning report", ""]
        lines.append(f"Instances: {', '.join(Path(i).name for i in self.instances)}")
        if self.problem_key:
            lines.append(f"Problem: {self.problem_label or self.problem_key} (key `{self.problem_key}`)")
        lines.append(f"Elapsed: {self.elapsed_seconds:.1f}s")
        lines.append(f"Stopped: {self.stopped_reason}")
        lines.append("")

        if self.exact:
            lines.append("## Exact baseline")
            lines.append(
                f"- objective: {self.exact.get('objectiveValue')} "
                f"({self.exact.get('status')})"
            )
            lines.append("")

        if self.baseline_lns:
            lines.append("## LNS baseline")
            lines.append(f"- objective: {self.baseline_lns.get('objectiveValue')}")
            lines.append(f"- feasible: {self.baseline_lns.get('feasible')}")
            lines.append(f"- iterations: {self.baseline_lns.get('iterations')}")
            if self.baseline_feasible is False:
                lines.append(
                    "- _infeasible start_: candidates are judged by how much they "
                    "reduce the infeasibility penalty (progress mode), not by "
                    "their feasible-candidate rate"
                )
            lines.append("")

        if self.initializer:
            lines.append("## Construction heuristic")
            lines.append(f"- class: `{self.initializer.get('class_name')}`")
            if self.initializer.get("path"):
                lines.append(f"- file: `{self.initializer['path']}`")
            if self.initializer.get("reason"):
                lines.append(f"- {self.initializer['reason']}")
            lines.append("")
        elif self.initializer_error:
            lines.append("## Construction heuristic")
            lines.append(f"- _not adopted_: {self.initializer_error}")
            lines.append("")

        if self.diagnosis:
            lines.append("## Diagnosis")
            lines.append(self.diagnosis)
            lines.append("")

        lines.append("## Attempts")
        if not self.attempts:
            lines.append("- none")
        for attempt in self.attempts:
            verdict = "accepted" if attempt.accepted else "rejected"
            lines.append(f"### {attempt.number}. {attempt.kind} — {verdict}")
            if attempt.class_name:
                lines.append(f"- class: `{attempt.class_name}`")
            if attempt.train:
                lines.append(
                    f"- train improvement: {attempt.train.mean_improvement:g} "
                    f"over {attempt.train.runs} run(s)"
                )
            if attempt.holdout:
                lines.append(
                    f"- holdout improvement: {attempt.holdout.mean_improvement:g} "
                    f"over {attempt.holdout.runs} run(s)"
                )
            for reason in attempt.reasons:
                lines.append(f"- {reason}")
            lines.append("")

        lines.append("## Accepted operators")
        if self.accepted:
            for name in self.accepted:
                lines.append(f"- `{name}`")
        else:
            lines.append("- none")

        lines.append("")
        lines.append("## Tuned LNS config")
        if self.lns_config:
            config = self.lns_config
            initializer = config.get("initializer") or {}
            lines.append(f"- file: `{self.lns_config_path}`")
            lines.append(f"- construction: `{initializer.get('class_name', 'auto')}`")
            lines.append(f"- destroys: {', '.join(f'`{n}`' for n in config.get('destroys', [])) or 'default'}")
            lines.append(f"- repairs: {', '.join(f'`{n}`' for n in config.get('repairs', [])) or 'default'}")
            lines.append(f"- adaptive selection: {config.get('adaptive')}")
            if self.tuned_lns:
                before = (config.get("baseline") or {}).get("objectiveValue")
                lines.append(
                    f"- verification run: objective {self.tuned_lns.get('objectiveValue')} "
                    f"(feasible {self.tuned_lns.get('feasible')}) vs {before} before tuning"
                )
            lines.append("- `/lns` uses this config automatically for this model.")
        else:
            lines.append("- unchanged (nothing new was accepted)")

        return "\n".join(lines)


def evaluate_operator_multi(
    source: str,
    kind: str,
    instances: list[str | Path],
    seeds: tuple[int, ...],
    *,
    repo_root: str | Path,
    iterations: int = 200,
    policy: AcceptancePolicy | None = None,
    initializer: str = "auto",
    partner: str | None = None,
    initializer_source: str | None = None,
    initializer_class: str | None = None,
    operator_dir: str | Path | None = None,
) -> OperatorScore:
    """Measure a candidate across every instance and seed.

    Each measurement runs in the harness subprocess, so a candidate that hangs or
    crashes costs one run rather than the whole tuning session.

    *partner* names the operator the candidate is paired with: a repair for a
    destroy candidate, a destroy for a repair candidate. The harness default is
    the generic ``SampledRepair``, which is too weak on structured problems to
    show whether a destroy operator is any good.
    """
    from operator_synthesis.harness import static_check

    static = static_check(source, kind)
    if not static.ok or static.class_name is None:
        return OperatorScore(
            name="<invalid>",
            kind=kind,
            mean_improvement=0.0,
            mean_feasible_rate=0.0,
            runs=0,
            per_run=[{"error": "; ".join(static.errors)}],
        )

    per_run: list[dict[str, Any]] = []
    improvements: list[float] = []
    feasible_rates: list[float] = []

    # A destroy candidate is paired with a repair and vice versa, so the
    # partner keyword depends on the candidate's kind.
    partner_kwargs: dict[str, str] = {}
    if partner:
        partner_kwargs["repair" if kind == "destroy" else "destroy"] = partner

    for instance in instances:
        for seed in seeds:
            metrics: RunMetrics = run_candidate(
                source,
                static.class_name,
                kind,
                instance,
                repo_root=repo_root,
                seed=seed,
                iterations=iterations,
                initializer=initializer,
                initializer_source=initializer_source,
                initializer_class=initializer_class,
                operator_dir=operator_dir,
                **partner_kwargs,
            )
            per_run.append(
                {
                    "instance": Path(instance).name,
                    "seed": seed,
                    "ok": metrics.ok,
                    "error": metrics.error,
                    "improvement": round(metrics.improvement, 4),
                    "feasibleRate": round(metrics.feasible_rate, 4),
                }
            )
            if metrics.ok:
                improvements.append(metrics.improvement)
                feasible_rates.append(metrics.feasible_rate)

    return OperatorScore(
        name=static.class_name,
        kind=kind,
        mean_improvement=sum(improvements) / len(improvements) if improvements else 0.0,
        mean_feasible_rate=sum(feasible_rates) / len(feasible_rates) if feasible_rates else 0.0,
        runs=len(per_run),
        per_run=per_run,
    )


def diagnose(
    digest: str,
    lns: LNSRunResult | dict[str, Any] | None,
    exact: dict[str, Any] | None,
    client: ChatClient | None = None,
) -> tuple[str, str]:
    """Explain the gap and describe the operator to build.

    Returns ``(diagnosis, operator_request)``. Without a client, falls back to a
    deterministic summary so the loop still produces something actionable.
    """
    measurements = _measurements(lns, exact)

    if client is None:
        return _fallback_diagnosis(measurements), ""

    try:
        response = client.chat(
            [{"role": "user", "content": build_diagnosis_prompt(digest, measurements)}]
        )
    except LLMError as exc:
        return f"diagnosis unavailable ({exc})", ""

    payload = _parse_json_object(response.content)
    if payload is None:
        return response.content.strip()[:2000], ""

    return (
        str(payload.get("diagnosis", "")).strip(),
        str(payload.get("operator_request", "")).strip(),
    )


def tune(
    instances: list[str | Path],
    config: AgentConfig,
    *,
    client: ChatClient | None = None,
    budget: TuningBudget | None = None,
    kinds: tuple[str, ...] | None = None,
    progress: Any = None,
) -> TuningReport:
    """Run the bounded self-tuning loop.

    Steps: exact baseline; LNS baseline (from this model's existing tuned
    config, if any); construction-heuristic synthesis; diagnosis; then repeated
    synthesize → train → holdout → keep-or-discard until the budget runs out.

    Everything accepted is persisted as self-contained, importable modules plus
    a tuned LNS config (``<problem_key>.lns.json``) in ``config.operator_dir``,
    which ``/lns`` applies automatically to every instance of the model.
    """
    budget = budget or TuningBudget()
    started = time.perf_counter()
    instance_paths = [Path(instance) for instance in instances]
    report = TuningReport(instances=[str(path) for path in instance_paths])

    def say(message: str) -> None:
        if progress is not None:
            progress(message)

    if not instance_paths:
        report.stopped_reason = "no instances"
        return report

    primary = instance_paths[0]
    source = primary.read_text(encoding="utf-8")
    digest = model_digest(source)
    index = analyze(source)
    problem = fingerprint(index)
    key = problem_key(index, problem)
    label = problem_label(index, problem)
    # Problem-specific adapters/partners only apply to a full structural match.
    known_class = problem.best.name if problem.best is not None and problem.matched else None
    report.problem_key, report.problem_label = key, label

    load_generated_operators(config.operator_dir)
    existing = load_tuned_config(config.operator_dir, key)
    construction = existing.initializer_artifact(config.operator_dir) if existing else None
    base_destroys = _resolvable(existing.destroys) if existing else []
    base_repairs = _resolvable(existing.repairs) if existing else []
    base_adaptive = bool(existing and existing.adaptive)
    generated: list[dict[str, str]] = []
    for entry in existing.generated if existing else []:
        if all(seen.get("name") != entry.get("name") for seen in generated):
            generated.append(entry)
    if existing is not None:
        say(
            f"continuing from tuned LNS config "
            f"{config_path(config.operator_dir, key).name}: {existing.describe()}"
        )

    def run_with(initializer_artifact: InitializerArtifact | None) -> LNSRunResult:
        return run_lns(
            LNSRunConfig(
                instance=primary,
                seed=budget.train_seeds[0],
                iterations=budget.iterations,
                initializer=(
                    initializer_artifact.instantiate()
                    if initializer_artifact is not None
                    else config.lns_initializer
                ),
                destroys=list(base_destroys),
                repairs=list(base_repairs),
                adaptive=base_adaptive,
                record_trajectory=True,
            )
        )

    # --- baselines --------------------------------------------------------
    report.exact = _exact_baseline(source, config)
    baseline = run_with(construction)
    initial_baseline = baseline
    report.baseline_lns = baseline.to_dict()
    say(f"baseline LNS objective: {baseline.objective_value}, feasible: {baseline.feasible}")

    # --- construction heuristic -------------------------------------------
    # A problem-specific construction is part of the tuned configuration. When
    # the baseline is infeasible it is required (generic initializers cannot
    # reach the feasible region of tightly-coupled models); when it is feasible
    # a candidate is only adopted if LNS does strictly better from its start.
    construction_changed = False
    can_synthesize = client is not None and not config.dry_run
    if can_synthesize and not (baseline.feasible and _gap_closed(baseline, report.exact)):
        assert client is not None
        outcome = _develop_construction(
            primary,
            instance_paths,
            source,
            config,
            client,
            budget,
            progress,
            baseline=baseline,
            run_with=run_with,
        )
        if outcome.accepted and outcome.artifact is not None:
            artifact = outcome.artifact
            try:
                config.ensure_directories()
                artifact.path = write_initializer(
                    artifact.source, config.operator_dir, problem_stem=key
                )
            except Exception as exc:  # noqa: BLE001 - persistence must not abort tuning
                say(f"construction accepted but could not be persisted: {exc}")
            construction = artifact
            construction_changed = artifact.path is not None
            report.initializer = {
                "class_name": artifact.class_name,
                "path": str(artifact.path) if artifact.path else None,
                "reason": outcome.reason,
            }
            baseline = outcome.run if outcome.run is not None else run_with(construction)
            report.baseline_lns = baseline.to_dict()
            say(
                f"baseline LNS with construction {artifact.class_name}: "
                f"objective {baseline.objective_value}, feasible {baseline.feasible}"
            )
        else:
            report.initializer_error = outcome.reason

    # --- diagnosis --------------------------------------------------------
    # Record whether the tune loop operates from a feasible baseline. When it
    # does not, candidates are accepted/rejected in progress mode.
    report.baseline_feasible = baseline.feasible

    # In dry-run mode the stub client would only echo a placeholder, so use the
    # deterministic diagnosis instead: it is derived from the measurements.
    diagnosis_client = None if config.dry_run else client
    report.diagnosis, operator_request = diagnose(
        digest, baseline, report.exact, diagnosis_client
    )
    say(f"diagnosis: {report.diagnosis[:200]}")

    def finish(reason: str | None = None) -> TuningReport:
        if reason is not None:
            report.stopped_reason = reason
        new_operators = len(report.accepted) > 0
        if construction_changed or new_operators:
            _write_tuned_config(
                report,
                config=config,
                key=key,
                label=label,
                primary=primary,
                instances=instance_paths,
                budget=budget,
                construction=construction,
                generated=generated,
                base_destroys=base_destroys,
                base_repairs=base_repairs,
                initial_baseline=initial_baseline,
                say=say,
            )
        report.elapsed_seconds = time.perf_counter() - started
        return report

    if client is None:
        return finish("no model client; diagnosis only")

    if config.dry_run:
        # The stub client cannot write an operator, so synthesizing would only
        # produce a syntax error. Report the baselines and stop.
        return finish("dry run; baselines and diagnosis only")

    # Nothing to tune when LNS already matches the exact solver: any accepted
    # operator would be noise, and the holdout test would reject it anyway.
    if _gap_closed(baseline, report.exact):
        return finish("LNS already matches the exact solver")

    # --- synthesis loop ---------------------------------------------------
    layout = _decision_layout(primary)
    incumbent = baseline.objective_value
    if kinds is None:
        # Without a strong problem-specific partner, a destroy candidate would
        # be judged next to a random repair that cannot keep a coupled model
        # feasible. Synthesizing the repair first gives later destroy
        # candidates a meaningful partner.
        kinds = ("destroy", "repair") if known_class in _PARTNERS else ("repair", "destroy")

    for attempt_number in range(1, budget.max_attempts + 1):
        if time.perf_counter() - started >= budget.max_wall_seconds:
            report.stopped_reason = "wall clock budget exhausted"
            break

        kind = kinds[(attempt_number - 1) % len(kinds)]
        request = operator_request or f"Improve the {kind} neighborhood for this {label}."
        partner = _choose_partner(kind, generated, known_class)

        attempt = _attempt(
            number=attempt_number,
            kind=kind,
            request=request,
            source=source,
            index=index,
            problem=problem,
            label=label,
            key=key,
            layout=layout,
            diagnosis=report.diagnosis,
            partner=partner,
            instances=instance_paths,
            config=config,
            budget=budget,
            client=client,
            incumbent=incumbent,
            initializer_source=construction.source if construction is not None else None,
            initializer_class=construction.class_name if construction is not None else None,
            baseline_feasible=baseline.feasible,
            progress=progress,
        )
        report.attempts.append(attempt)
        say(f"attempt {attempt_number} ({kind}): {'accepted' if attempt.accepted else 'rejected'}")

        if attempt.accepted and attempt.class_name:
            report.accepted.append(attempt.class_name)
            if attempt.path and all(entry.get("name") != attempt.class_name for entry in generated):
                entry = {"name": attempt.class_name, "kind": kind, "file": Path(attempt.path).name}
                if partner:
                    # The operator it was validated with must be in the pool too.
                    entry["partner"] = partner
                generated.append(entry)
            if attempt.holdout is not None and baseline.feasible:
                # Only project the incumbent when the baseline is feasible:
                # from an infeasible start the penalty is not an objective we
                # can meaningfully project forward.
                incumbent = _improved_objective(incumbent, attempt.holdout, baseline)

    if report.stopped_reason == "completed" and len(report.attempts) >= budget.max_attempts:
        report.stopped_reason = "attempt budget exhausted"

    return finish()


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _attempt(
    *,
    number: int,
    kind: str,
    request: str,
    source: str,
    index: Any,
    problem: Any,
    instances: list[Path],
    config: AgentConfig,
    budget: TuningBudget,
    client: ChatClient,
    incumbent: float | None,
    progress: Callable[[str], None] | None = None,
    initializer_source: str | None = None,
    initializer_class: str | None = None,
    baseline_feasible: bool | None = None,
    label: str | None = None,
    key: str | None = None,
    layout: list[str] | None = None,
    diagnosis: str = "",
    partner: str | None = None,
) -> TuningAttempt:
    """Synthesize one candidate and decide whether to keep it."""
    attempt_label = f"attempt {number} ({(kind or 'operator').lower()})"

    def say(message: str) -> None:
        if progress is not None:
            progress(f"{attempt_label}: {message}")

    problem_name = label or (problem.best.name if problem.best else "custom optimisation model")
    notes = request
    if diagnosis and diagnosis not in request:
        notes = f"{request}\n\nDiagnosis of the current LNS run: {diagnosis}"
    if partner:
        notes += (
            f"\n\nThe candidate is evaluated together with the {'repair' if kind == 'destroy' else 'destroy'} "
            f"operator `{partner}`."
        )

    spec = OperatorSpec(
        kind=kind,
        problem_class=problem_name,
        objective=(
            f"{index.objective.sense} {index.objective.expression}"
            if index.objective
            else "satisfaction"
        ),
        target_variables=[name for name, var in index.variables.items() if var.is_decision],
        hyperparameters={"fraction": 0.2} if kind == "destroy" else {},
        invariants=[],
        notes=notes,
        model_source=source,
        decision_layout=list(layout or []),
    )

    def proposer(messages: list[dict[str, Any]]) -> str:
        return client.chat(messages).content

    # No feasible start was available: judge candidates by how much they reduce
    # the infeasibility penalty rather than by their feasible-candidate rate.
    progress_mode = baseline_feasible is False

    # The quality gate must pair the candidate with the same partner as the
    # train/holdout evaluation; the harness default (a random repair/destroy)
    # makes good operators on structured problems look infeasible.
    partner_kwargs: dict[str, str] = {}
    if partner:
        partner_kwargs["repair" if kind == "destroy" else "destroy"] = partner

    say(f"synthesizing with the model{f' (partner {partner})' if partner else ''} ...")
    result = synthesize(
        index,
        problem,
        spec,
        instances[0],
        repo_root=config.repo_root,
        proposer=proposer,
        max_attempts=2,
        policy=AcceptancePolicy(feasibility_progress_mode=progress_mode) if progress_mode else None,
        run_kwargs={
            "iterations": budget.iterations,
            "seed": budget.train_seeds[0],
            "initializer": "auto",
            "initializer_source": initializer_source,
            "initializer_class": initializer_class,
            "operator_dir": config.operator_dir,
            **partner_kwargs,
        },
    )

    if not result.accepted or result.source is None or result.class_name is None:
        reasons = []
        if result.attempts:
            reasons = result.attempts[-1].verdict.reasons
        say("synthesis produced no candidate that passed the quality gate")
        return TuningAttempt(
            number=number,
            kind=kind,
            request=request,
            accepted=False,
            reasons=reasons or ["no candidate passed the quality gate"],
        )

    # --- train: does it work at all? --------------------------------------
    say(
        f"synthesized {result.class_name}; training on {len(instances)} instance(s) "
        f"x {len(budget.train_seeds)} seed(s) ..."
    )
    train = evaluate_operator_multi(
        result.source,
        kind,
        instances,
        budget.train_seeds,
        repo_root=config.repo_root,
        iterations=budget.iterations,
        partner=partner,
        initializer_source=initializer_source,
        initializer_class=initializer_class,
        operator_dir=config.operator_dir,
    )
    say(
        f"train: mean improvement {train.mean_improvement:g}, "
        f"feasible rate {train.mean_feasible_rate:.0%}"
    )

    # --- holdout: does it generalize? -------------------------------------
    say(f"holdout on {len(budget.holdout_seeds)} seed(s) ...")
    holdout = evaluate_operator_multi(
        result.source,
        kind,
        instances,
        budget.holdout_seeds,
        repo_root=config.repo_root,
        iterations=budget.iterations,
        partner=partner,
        initializer_source=initializer_source,
        initializer_class=initializer_class,
        operator_dir=config.operator_dir,
    )
    say(
        f"holdout: mean improvement {holdout.mean_improvement:g}, "
        f"feasible rate {holdout.mean_feasible_rate:.0%}"
    )

    reasons: list[str] = []
    if train.mean_improvement <= 0:
        reasons.append(f"no improvement on training seeds ({train.mean_improvement:g})")
    if holdout.mean_improvement <= 0:
        reasons.append(f"no improvement on held-out seeds ({holdout.mean_improvement:g})")
    if progress_mode:
        # Without a feasible baseline, "improvement" is measured in penalty
        # units (fewer failed constraints). A candidate that cuts the penalty
        # on held-out seeds is valuable even if it does not reach a fully
        # feasible candidate 50% of the time.
        if holdout.mean_improvement > 0:
            say(
                f"progress mode: holdout reduced the infeasibility penalty by "
                f"{holdout.mean_improvement:g}"
            )
        elif not reasons:
            reasons.append(
                "the candidate does not reduce the infeasibility penalty on "
                "held-out seeds"
            )
    elif holdout.mean_feasible_rate < 0.5:
        reasons.append(f"held-out feasible rate {holdout.mean_feasible_rate:.0%} is too low")

    accepted = not reasons

    attempt = TuningAttempt(
        number=number,
        kind=kind,
        request=request,
        accepted=accepted,
        class_name=result.class_name,
        source=result.source,
        train=train,
        holdout=holdout,
        reasons=reasons,
    )

    if accepted:
        config.ensure_directories()
        # write_operator may rename the class to avoid a registry collision;
        # it updates result.class_name/source to the persisted version.
        written = write_operator(
            result,
            config.operator_dir,
            problem_class=key or problem_name,
            kind=kind,
        )
        attempt.path = str(written)
        attempt.class_name = result.class_name
        attempt.source = result.source
        load_generated_operators(config.operator_dir)
        say(f"accepted; written to {written.name} and registered as {result.class_name}")

    return attempt


def _resolvable(names: list[str]) -> list[str]:
    """Keep operator names the registry can instantiate (generated ones loaded)."""
    import large_neighborhood_search.builtin_operators  # noqa: F401 - populate registry
    from large_neighborhood_search.registry import describe

    return [name for name in names if describe(name) is not None]


def _unique(names: list[str]) -> list[str]:
    seen: set[str] = set()
    return [name for name in names if not (name in seen or seen.add(name))]


def _choose_partner(kind: str, generated: list[dict[str, str]], known_class: str | None) -> str | None:
    """The operator a new candidate of *kind* is evaluated with.

    The most recently accepted generated operator of the opposite kind wins:
    it is problem-specific by construction. Otherwise the built-in partner for
    a known problem class; otherwise the harness default.
    """
    opposite = "repair" if kind == "destroy" else "destroy"
    for entry in reversed(generated):
        if entry.get("kind") == opposite and _resolvable([entry["name"]]):
            return entry["name"]
    return _partner_for(known_class, kind)


def _decision_layout(instance: Path) -> list[str]:
    """Describe the runtime decision keys per variable, for the operator prompt."""
    try:
        from large_neighborhood_search.lns import read_problem_for_lns

        _, context = read_problem_for_lns(instance)
    except Exception:  # noqa: BLE001 - the prompt simply omits the section
        return []

    domains = context.extra.get("decision_domains", {})
    lines: list[str] = []
    for name, keys in context.extra.get("keys_by_variable", {}).items():
        if not keys:
            continue
        sample = ", ".join(repr(key) for key in keys[:3])
        low = min(domains[key][0] for key in keys)
        high = max(domains[key][1] for key in keys)
        lines.append(f"`{name}`: {len(keys)} keys like {sample}; values in {low}..{high}")
    return lines


def _brief(run: LNSRunResult) -> dict[str, Any]:
    return {
        "objectiveValue": run.objective_value,
        "feasible": run.feasible,
        "iterations": run.iterations,
        "seed": run.seed,
        "initializer": run.initializer_name,
        "neighborhoods": run.neighborhoods,
    }


def _default_operator_names(run: LNSRunResult) -> tuple[list[str], list[str]]:
    """The registry names of the destroy/repair operators a run used."""
    destroys: list[str] = []
    repairs: list[str] = []
    for pair in run.neighborhoods:
        destroy, _, repair = pair.partition("+")
        destroys.append(destroy)
        repairs.append(repair)
    return _resolvable(_unique(destroys)), _resolvable(_unique(repairs))


def _write_tuned_config(
    report: TuningReport,
    *,
    config: AgentConfig,
    key: str,
    label: str,
    primary: Path,
    instances: list[Path],
    budget: TuningBudget,
    construction: InitializerArtifact | None,
    generated: list[dict[str, str]],
    base_destroys: list[str],
    base_repairs: list[str],
    initial_baseline: LNSRunResult,
    say: Callable[[str], None],
) -> None:
    """Persist the tuned LNS config and verify it with one LNS run."""
    default_destroys, default_repairs = _default_operator_names(initial_baseline)
    generated_destroys = [g["name"] for g in generated if g.get("kind") == "destroy"]
    generated_repairs = [g["name"] for g in generated if g.get("kind") == "repair"]
    # Partners a generated operator was validated with (e.g. the built-in
    # 2D-packing repair for a generated destroy) belong in the opposite pool.
    partner_destroys = [g["partner"] for g in generated if g.get("kind") == "repair" and g.get("partner")]
    partner_repairs = [g["partner"] for g in generated if g.get("kind") == "destroy" and g.get("partner")]

    # Generated operators first; the previous operators stay in the pool so the
    # adaptive selector can fall back on them where they work better.
    destroys = _resolvable(
        _unique(generated_destroys + partner_destroys + (base_destroys or default_destroys))
    )
    repairs = _resolvable(
        _unique(generated_repairs + partner_repairs + (base_repairs or default_repairs))
    )

    tuned = TunedLNSConfig(
        problem_key=key,
        problem_label=label,
        initializer=(
            {"class_name": construction.class_name, "file": construction.path.name}
            if construction is not None and construction.path is not None
            else None
        ),
        destroys=destroys,
        repairs=repairs,
        generated=generated,
        adaptive=len(destroys) * len(repairs) > 1,
        instances=[str(path) for path in instances],
        baseline=_brief(initial_baseline),
    )

    verification = run_lns(
        LNSRunConfig(
            instance=primary,
            seed=budget.train_seeds[0],
            iterations=budget.iterations,
            initializer=construction.instantiate() if construction is not None else config.lns_initializer,
            destroys=list(destroys),
            repairs=list(repairs),
            adaptive=tuned.adaptive,
            record_trajectory=False,
        )
    )
    tuned.tuned = _brief(verification)

    try:
        path = save_tuned_config(tuned, config.operator_dir)
    except OSError as exc:
        say(f"could not write the tuned LNS config: {exc}")
        return

    report.lns_config = tuned.to_dict()
    report.lns_config_path = str(path)
    report.tuned_lns = {
        k: v for k, v in verification.to_dict().items() if k not in {"rendered", "trajectory"}
    }
    say(f"tuned LNS config written to {path.name}: {tuned.describe()}")
    say(
        f"verification LNS with the tuned config: objective {verification.objective_value}, "
        f"feasible {verification.feasible} (initial baseline {initial_baseline.objective_value}, "
        f"feasible {initial_baseline.feasible})"
    )


def _exact_baseline(source: str, config: AgentConfig) -> dict[str, Any]:
    """Run the exact solver, tolerating a missing MiniZinc installation."""
    try:
        from src.optdsl.solver.DSL_solver import DSLSolver

        raw = DSLSolver(
            source,
            solver_name=config.solver_name,
            timelimit=config.solve_timelimit,
            dsl_index_base=config.dsl_index_base,
        ).run()
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}

    objectives = raw.get("objectives") or []
    return {
        "available": True,
        "objectiveValue": objectives[-1] if objectives else None,
        "objectiveBound": raw.get("objective_bound"),
        "status": str(raw.get("status", "unknown")),
        "totalTime": raw.get("total_time"),
    }


def _measurements(
    lns: LNSRunResult | dict[str, Any] | None,
    exact: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the numbers the diagnosis prompt reasons about."""
    if isinstance(lns, LNSRunResult):
        lns_payload = lns.to_dict()
    else:
        lns_payload = lns or {}

    measurements: dict[str, Any] = {
        "lns": {
            "objective": lns_payload.get("objectiveValue"),
            "feasible": lns_payload.get("feasible"),
            "iterations": lns_payload.get("iterations"),
            "accepted": lns_payload.get("accepted"),
            "improvements": lns_payload.get("improvements"),
            "infeasibleCandidates": lns_payload.get("infeasibleCandidates"),
            "stopReason": lns_payload.get("stopReason"),
            "elapsedSeconds": lns_payload.get("elapsedSeconds"),
        }
    }

    if exact and exact.get("available"):
        measurements["exact"] = {
            "objective": exact.get("objectiveValue"),
            "bound": exact.get("objectiveBound"),
            "status": exact.get("status"),
        }
        lns_value = lns_payload.get("objectiveValue")
        exact_value = exact.get("objectiveValue")
        if lns_value is not None and exact_value is not None:
            measurements["gap"] = lns_value - exact_value
            if exact_value:
                measurements["relativeGap"] = (lns_value - exact_value) / abs(exact_value)

    trajectory = lns_payload.get("trajectory") or []
    if trajectory:
        measurements["stagnation"] = _stagnation(trajectory)

    return measurements


def _stagnation(trajectory: list[dict[str, Any]]) -> dict[str, Any]:
    """Find where the search stopped improving.

    A run that improves for 10 iterations and then flatlines for 490 is a
    different problem from one that never improves at all, and the operator to
    build differs too.
    """
    best = None
    last_improvement = 0
    for point in trajectory:
        incumbent = point.get("incumbent")
        if incumbent is None:
            continue
        if best is None or incumbent < best:
            best = incumbent
            last_improvement = point.get("iteration", 0)

    total = trajectory[-1].get("iteration", 0) if trajectory else 0
    return {
        "lastImprovementIteration": last_improvement,
        "totalIterations": total,
        "stagnantFraction": (
            (total - last_improvement) / total if total else 0.0
        ),
    }


def _fallback_diagnosis(measurements: dict[str, Any]) -> str:
    """Deterministic diagnosis when no model is available."""
    lns = measurements.get("lns", {})
    parts = [
        f"LNS reached objective {lns.get('objective')} "
        f"in {lns.get('iterations')} iterations "
        f"({lns.get('improvements')} improvements, "
        f"{lns.get('infeasibleCandidates')} infeasible candidates)."
    ]

    gap = measurements.get("gap")
    if gap is None:
        parts.append("No exact reference was available, so the gap is unknown.")
    elif gap <= 0:
        # Matching or beating the exact solver means there is nothing to fix.
        # Reporting stagnation here would send the tuning loop after a
        # non-problem and produce operators that cannot improve anything.
        parts.append(
            f"The exact solver reached {measurements['exact'].get('objective')}, "
            "so LNS is already at the reference value and no operator is needed."
        )
        return " ".join(parts)
    else:
        parts.append(
            f"The exact solver reached {measurements['exact'].get('objective')}, "
            f"a gap of {gap:g}."
        )

    stagnation = measurements.get("stagnation")
    if stagnation and stagnation.get("stagnantFraction", 0) > 0.5:
        parts.append(
            f"The search stopped improving at iteration "
            f"{stagnation['lastImprovementIteration']} of "
            f"{stagnation['totalIterations']}, so the neighborhood is too narrow "
            "to escape the incumbent."
        )

    return " ".join(parts)


def _improved_objective(
    incumbent: float | None,
    holdout: OperatorScore,
    baseline: LNSRunResult,
) -> float | None:
    """Project the incumbent objective forward by the measured improvement."""
    if incumbent is None:
        return None
    return incumbent - holdout.mean_improvement


def _extract_initializer_source(reply: str) -> str:
    """Extract the initializer class source from a model reply.

    The prompt asks for ``{"source": "<python>", "class_name": ...}`` JSON, but
    models often wrap it in a markdown fence or return bare (fenced) code;
    tolerate all of these.
    """
    text = (reply or "").strip()
    if not text:
        return ""

    # Unwrap a markdown fence whatever language it declares (json, python or
    # none). ``extract_initializer_code`` only handles ```/```python, so a
    # ```json fence would otherwise fall through as raw markdown and fail
    # every static check.
    fenced = re.search(r"```(?:json|python)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("source"), str):
            return payload["source"]
    except json.JSONDecodeError:
        pass
    return _coerce_to_standalone_class(extract_initializer_code(text))


def _coerce_to_standalone_class(text: str) -> str:
    """Trim trailing lines until the remainder parses as a module with a class.

    Models sometimes emit the ``"source"`` value with literal newlines (invalid
    JSON), leaving a ``"}``/````` fragment after the class body. Rather than
    hand that fragment to the static check, keep the longest prefix that is a
    parseable Python module containing a class.
    """
    lines = text.splitlines()
    for cut in range(len(lines), 0, -1):
        candidate = "\n".join(lines[:cut])
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            continue
        if any(isinstance(node, ast.ClassDef) for node in tree.body):
            return candidate
    return text


@dataclass
class _ConstructionOutcome:
    accepted: bool
    reason: str
    artifact: InitializerArtifact | None = None
    #: LNS run from the candidate's start (feasible-baseline case only).
    run: LNSRunResult | None = None


def _develop_construction(
    primary: Path,
    instances: list[Path],
    source: str,
    config: AgentConfig,
    client: ChatClient,
    budget: TuningBudget,
    progress: Callable[[str], None] | None,
    *,
    baseline: LNSRunResult,
    run_with: Callable[[InitializerArtifact | None], LNSRunResult],
) -> _ConstructionOutcome:
    """Synthesize a construction heuristic and decide whether to adopt it."""
    if baseline.feasible:
        situation = INITIALIZER_SITUATION_IMPROVE.replace(
            "__CURRENT__",
            f"the {baseline.initializer_name or 'default'} construction, after which "
            f"{baseline.iterations} LNS iterations reach objective {baseline.objective_value}",
        )
    else:
        situation = INITIALIZER_SITUATION_INFEASIBLE

    artifact = _synthesize_feasible_initializer(
        primary,
        source,
        config,
        client,
        budget,
        progress,
        instances=instances,
        situation=situation,
        persist=False,
    )
    if artifact is None:
        if baseline.feasible:
            return _ConstructionOutcome(
                False,
                "no synthesized construction was feasible on every instance and seed; "
                "kept the current construction",
            )
        return _ConstructionOutcome(
            False,
            "could not synthesize a feasible initializer; LNS stays infeasible "
            "and candidate operators will be measured from a penalty baseline",
        )

    checked = len(instances) * len(set(budget.train_seeds) | set(budget.holdout_seeds))
    if not baseline.feasible:
        return _ConstructionOutcome(
            True,
            f"the generic start was infeasible; this construction is feasible on all "
            f"{checked} instance/seed combination(s)",
            artifact,
        )

    # Feasible baseline: adopt only when LNS does strictly better from it.
    run = run_with(artifact)
    if progress is not None:
        progress(
            f"LNS from construction {artifact.class_name}: objective {run.objective_value} "
            f"(current construction: {baseline.objective_value})"
        )
    if run.feasible and _strictly_better(run.objective_value, baseline.objective_value, run.objective_sense):
        return _ConstructionOutcome(
            True,
            f"LNS reaches {run.objective_value} from this construction vs "
            f"{baseline.objective_value} from {baseline.initializer_name or 'the previous one'}",
            artifact,
            run,
        )
    return _ConstructionOutcome(
        False,
        f"candidate {artifact.class_name} is feasible but LNS does not improve from it "
        f"({run.objective_value} vs {baseline.objective_value}); kept the current construction",
    )


def _strictly_better(candidate: float | None, reference: float | None, sense: str) -> bool:
    if candidate is None:
        return False
    if reference is None:
        return True
    return candidate > reference if sense == "maximize" else candidate < reference


def _synthesize_feasible_initializer(
    instance: Path,
    source: str,
    config: AgentConfig,
    client: ChatClient,
    budget: TuningBudget,
    progress: Callable[[str], None] | None,
    *,
    instances: list[Path] | None = None,
    situation: str = INITIALIZER_SITUATION_INFEASIBLE,
    persist: bool = True,
    problem_stem: str | None = None,
) -> InitializerArtifact | None:
    """Ask the model for a construction heuristic and verify it.

    The candidate must produce a feasible assignment on every instance and on
    every train and holdout seed (a construction that only works for one RNG
    state is not a construction). Failures are fed back with the failing
    constraint and loop values, so retries are targeted. With *persist* the
    accepted module is written to the generated package.
    """
    # The model must reason about the constraint *bodies* (e.g. a cumulative
    # no-backlog invariant) to construct a feasible assignment, so the digest
    # includes the full source, not just one-line predicate signatures.
    digest = model_digest(source, include_source=True)
    attempts = max(1, budget.max_initializer_attempts)
    targets = list(instances) if instances else [instance]
    seeds = list(dict.fromkeys(tuple(budget.train_seeds) + tuple(budget.holdout_seeds)))
    feedback = ""

    for attempt in range(1, attempts + 1):
        if progress is not None:
            progress(f"synthesizing a construction heuristic (attempt {attempt}/{attempts})")
        try:
            response = client.chat(
                [
                    {
                        "role": "user",
                        "content": build_initializer_prompt(
                            digest,
                            feedback,
                            attempt=attempt,
                            max_attempts=attempts,
                            situation=situation,
                        ),
                    }
                ]
            )
        except LLMError as exc:
            feedback = f"the model call failed: {exc}"
            continue

        code = _extract_initializer_source(response.content)
        ok, class_name, static_errors = static_check_initializer(code)
        if not ok or class_name is None:
            feedback = "static check failed:\n- " + "\n- ".join(static_errors)
            continue

        failure: str | None = None
        last_outcome: dict[str, Any] = {}
        for target in targets:
            for seed in seeds:
                outcome = check_initializer(
                    code, class_name, target, seed=seed, repo_root=config.repo_root
                )
                last_outcome = outcome
                where = f"on {target.name} with seed {seed}"
                if not outcome.get("ok"):
                    failure = f"initializer failed {where}: {outcome.get('error', 'unknown error')}"
                elif not outcome.get("feasible"):
                    failure = f"{where}:\n" + _initializer_feedback(outcome)
                if failure:
                    break
            if failure:
                break

        if failure is not None:
            feedback = failure
            continue

        artifact = InitializerArtifact(source=code, class_name=class_name)
        if persist:
            try:
                config.ensure_directories()
                artifact.path = write_initializer(
                    code, config.operator_dir, problem_stem=problem_stem or instance.stem
                )
            except Exception as exc:  # noqa: BLE001 - persistence must not abort tuning
                if progress is not None:
                    progress(f"initializer accepted but could not be persisted: {exc}")
        if progress is not None:
            progress(
                f"construction '{class_name}' is feasible on {len(targets)} instance(s) x "
                f"{len(seeds)} seed(s) ({last_outcome.get('diagnostic', '')})"
            )
        return artifact

    if progress is not None:
        progress("could not synthesize a feasible construction heuristic")
    return None


def _initializer_feedback(outcome: dict[str, Any]) -> str:
    """Render the infeasibility outcome into specific, actionable feedback.

    Names the failing constraint(s) and the loop-variable values at the first
    failing assertion, so the model can fix the plan instead of guessing.
    """
    lines = ["initializer ran but was NOT feasible. Fix the plan so every assert "
             "in the model holds. The failing constraints were:"]
    details = outcome.get("failed_details") or []
    if not details:
        lines.append(f"- (no per-constraint detail) {outcome.get('diagnostic', '')}")
        return "\n".join(lines)

    for failed in details:
        where = failed.get("error")
        if where:
            lines.append(f"- {failed.get('constraint')}: {where}")
        else:
            at = failed.get("at") or {}
            suffix = f" at {at}" if at else ""
            line_info = f" (model line {failed.get('line')})" if failed.get("line") else ""
            lines.append(f"- {failed.get('constraint')}{suffix}{line_info}")

    lines.append(
        "Reason about the specific values above (for example 'inv became negative in "
        "period t' means produce more earlier; a capacity overflow means spread "
        "production earlier; a missing setup means set the flag)."
    )
    return "\n".join(lines)


def _gap_closed(baseline: LNSRunResult, exact: dict[str, Any]) -> bool:
    """True when LNS already reached the exact solver's objective.

    A zero or negative gap means there is nothing for a new operator to fix.
    """
    if not exact.get("available"):
        return False
    exact_value = exact.get("objectiveValue")
    lns_value = baseline.objective_value
    if exact_value is None or lns_value is None:
        return False
    if baseline.objective_sense == "maximize":
        return lns_value >= exact_value
    return lns_value <= exact_value


#: A strong partner per problem class, so a candidate is judged in a
#: neighborhood that can actually produce feasible solutions.
_PARTNERS: dict[str, dict[str, str]] = {
    "cvrp": {"destroy": "CVRPInsertionRepair", "repair": "CVRPShawDestroy"},
    "jssp": {"destroy": "JSSPGanttRepair", "repair": "JSSPJobLevelDestroy"},
    "2dbp": {"destroy": "DBPGreedyPlacementRepair", "repair": "DBPClearItemsDestroy"},
    "cutting_packing": {
        "destroy": "CuttingPackingInsertionRepair",
        "repair": "CuttingPackingPieceDestroy",
    },
    "woodcutting": {
        "destroy": "WoodcuttingCutRepair",
        "repair": "WoodcuttingCutDestroy",
    },
}


def _partner_for(problem_class: str | None, kind: str) -> str | None:
    """The operator a candidate of *kind* should be paired with.

    Returns ``None`` when the problem class has no known strong partner, in
    which case the harness default applies.
    """
    if problem_class is None:
        return None
    return _PARTNERS.get(problem_class, {}).get(kind)


def _parse_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from a model reply."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
