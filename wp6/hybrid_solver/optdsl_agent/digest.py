"""Compact, prompt-ready descriptions of an OptDSL formulation.

Every prompt in this package needs the same thing: a short, accurate summary of
what the model contains. Building it in one place means the explanation prompt,
the constraint prompt and the operator prompt cannot disagree about the model.

The digest is deliberately *text*, not JSON. It is what a model reads, and a
token-efficient bullet list beats a nested object for that purpose. The
structured form is available separately via :func:`model_summary`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from optdsl_tooling.analysis import ModuleIndex, analyze
from optdsl_tooling.diagnostics import Severity, check
from optdsl_tooling.fingerprint import fingerprint

#: Constants longer than this are truncated in the digest.
_CONSTANT_PREVIEW = 120


@dataclass
class ModelSummary:
    """Structured view of a formulation, used by tools and reports."""

    problem_class: str | None = None
    problem_score: float = 0.0
    objective_sense: str | None = None
    objective_expression: str | None = None
    decision_count: int = 0
    decision_variables: dict[str, dict[str, Any]] = field(default_factory=dict)
    constants: dict[str, str] = field(default_factory=dict)
    predicates: dict[str, dict[str, Any]] = field(default_factory=dict)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    is_pipeline_model: bool = False
    syntax_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "problemClass": self.problem_class,
            "problemScore": round(self.problem_score, 4),
            "objective": (
                {"sense": self.objective_sense, "expression": self.objective_expression}
                if self.objective_sense
                else None
            ),
            "decisionCount": self.decision_count,
            "decisionVariables": self.decision_variables,
            "constants": self.constants,
            "predicates": self.predicates,
            "diagnostics": self.diagnostics,
            "isPipelineModel": self.is_pipeline_model,
            "syntaxError": self.syntax_error,
        }


def model_summary(source: str) -> ModelSummary:
    """Analyse *source* and return a structured summary.

    Never raises: a syntax error is reported in the summary instead, because the
    agent must be able to talk about a broken file rather than crash on it.
    """
    index = analyze(source)
    if index.syntax_error is not None:
        return ModelSummary(syntax_error=str(index.syntax_error))

    problem = fingerprint(index)
    summary = ModelSummary(
        problem_class=problem.best.name if problem.best else None,
        problem_score=problem.score,
        decision_count=index.decision_count,
        is_pipeline_model=index.is_pipeline_model,
    )

    if index.objective is not None:
        summary.objective_sense = index.objective.sense
        summary.objective_expression = index.objective.expression

    for name, variable in index.variables.items():
        if not variable.is_decision:
            continue
        summary.decision_variables[name] = {
            "annotation": variable.annotation_code,
            "indices": variable.decision_count,
            "domains": _domain_summary(index, name),
        }

    for name, constant in index.constants.items():
        summary.constants[name] = _preview(constant.value)

    for name, predicate in index.predicates.items():
        summary.predicates[name] = {
            "parameters": [parameter.name for parameter in predicate.parameters],
            "invoked": predicate.invoked_at_top_level,
            "objective": predicate.used_as_objective,
            "warmStart": predicate.is_warm_start,
        }

    summary.diagnostics = [
        {
            "code": diagnostic.code,
            "message": diagnostic.message,
            "severity": int(diagnostic.severity),
            "line": diagnostic.span.start_line,
        }
        for diagnostic in check(index)
    ]

    return summary


def model_digest(source: str, *, include_source: bool = False) -> str:
    """Render a formulation as a compact text block for a prompt."""
    index = analyze(source)
    if index.syntax_error is not None:
        return f"The formulation does not parse:\n{index.syntax_error}"

    problem = fingerprint(index)
    lines: list[str] = []

    class_name = problem.best.name if problem.best else "unknown"
    # The fingerprint adds a small bonus for optional markers, so the raw score
    # can exceed 1.0. Clamp it before presenting it as a confidence.
    confidence = min(1.0, max(0.0, problem.score))
    lines.append(f"Problem class: {class_name} (confidence {confidence:.0%})")
    if index.is_pipeline_model:
        lines.append("Model shape: pipeline (top-level statements thread values through)")

    if index.objective is not None:
        lines.append(
            f"Objective: {index.objective.sense} `{index.objective.expression}`"
        )
    else:
        lines.append("Objective: none (satisfaction problem)")

    lines.append(f"Decision indices: {index.decision_count}")

    lines.append("")
    lines.append("Decision variables:")
    decisions = index.decision_variables
    if not decisions:
        lines.append("- (none)")
    for name, variable in decisions.items():
        domains = _domain_summary(index, name)
        domain_text = _format_domains(domains)
        lines.append(
            f"- `{name}`: {variable.annotation_code} - "
            f"{variable.decision_count} indices{domain_text}"
        )

    derived = {
        name: variable
        for name, variable in index.variables.items()
        if not variable.is_decision
    }
    if derived:
        lines.append("")
        lines.append("Derived variables:")
        for name, variable in derived.items():
            value = variable.value_code or "(declared)"
            lines.append(f"- `{name}`: {variable.annotation_code} = `{value}`")

    if index.constants:
        lines.append("")
        lines.append("Constants:")
        for name, constant in index.constants.items():
            lines.append(f"- `{name}` = {_preview(constant.value)}")

    constraint_predicates = {
        name: predicate
        for name, predicate in index.predicates.items()
        if not predicate.is_warm_start
    }
    if constraint_predicates:
        lines.append("")
        lines.append("Predicates:")
        for name, predicate in constraint_predicates.items():
            parameters = ", ".join(parameter.name for parameter in predicate.parameters)
            flags = []
            if predicate.used_as_objective:
                flags.append("objective")
            elif predicate.invoked_at_top_level:
                flags.append("invoked")
            else:
                flags.append("NOT INVOKED - has no effect")
            lines.append(f"- `{name}({parameters})` [{', '.join(flags)}]")

    errors = [d for d in check(index) if d.severity == Severity.ERROR]
    warnings = [d for d in check(index) if d.severity == Severity.WARNING]
    if errors or warnings:
        lines.append("")
        lines.append("Diagnostics:")
        for diagnostic in errors + warnings:
            label = "error" if diagnostic.severity == Severity.ERROR else "warning"
            lines.append(f"- {label} (line {diagnostic.span.start_line}): {diagnostic.message}")

    if include_source:
        lines.append("")
        lines.append("Source:")
        lines.append("```python")
        lines.append(source.rstrip())
        lines.append("```")

    return "\n".join(lines)


def _domain_summary(index: ModuleIndex, variable_name: str) -> list[dict[str, Any]]:
    """Distinct domains for one decision variable, with how many indices use each."""
    buckets: dict[tuple[int | None, int | None], int] = {}
    for decision in index.decisions_for(variable_name):
        key = (decision.domain.lower, decision.domain.upper)
        buckets[key] = buckets.get(key, 0) + 1
    return [
        {"lower": lower, "upper": upper, "count": count}
        for (lower, upper), count in sorted(
            buckets.items(), key=lambda item: (item[0][0] or 0, item[0][1] or 0)
        )
    ]


def _format_domains(domains: list[dict[str, Any]]) -> str:
    if not domains:
        return ""
    parts = []
    for domain in domains[:4]:
        lower, upper, count = domain["lower"], domain["upper"], domain["count"]
        # ASCII only: Windows consoles with a legacy code page mangle the
        # multiplication sign and em dash.
        parts.append(f"{count}x[{lower}..{upper}]")
    if len(domains) > 4:
        parts.append(f"+{len(domains) - 4} more")
    return ", domains: " + ", ".join(parts)


def _preview(value: Any, limit: int = _CONSTANT_PREVIEW) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."
