"""Synthesis loop: propose, validate, feed back, retry.

The loop is deliberately model-agnostic. A *proposer* is any callable that takes
a prompt and returns Python source; the VS Code extension supplies one backed by
``vscode.lm``, the CLI supplies one backed by an HTTP API, and tests supply a
deterministic stub.

The feedback step is what makes this "automatic" rather than one-shot: a
rejected candidate's verdict is rendered back into the conversation so the model
can see the concrete failure (a traceback, a feasible-rate number, a
too-small-neighborhood measurement) instead of guessing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .harness import AcceptancePolicy, Verdict, evaluate_candidate
from .prompts import OperatorSpec, build_system_prompt, build_user_prompt

Proposer = Callable[[list[dict[str, str]]], str]


class ProposerProtocol(Protocol):
    def __call__(self, messages: list[dict[str, str]]) -> str: ...


@dataclass
class Attempt:
    number: int
    source: str
    verdict: Verdict

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "source": self.source,
            "verdict": self.verdict.to_dict(),
        }


@dataclass
class SynthesisResult:
    accepted: bool
    source: str | None
    class_name: str | None
    attempts: list[Attempt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "class_name": self.class_name,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


_FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


def extract_code(response: str) -> str:
    """Pull the Python class out of a model response.

    Models wrap code in fences even when told not to, so this is tolerant: it
    prefers a fenced block, otherwise strips leading prose up to the first
    ``import``/``from``/``@``/``class`` line.
    """
    match = _FENCE.search(response)
    if match:
        return match.group(1).strip()

    lines = response.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("import ", "from ", "@", "class ")):
            return "\n".join(lines[index:]).strip()

    return response.strip()


def synthesize(
    index: Any,
    fingerprint: Any,
    spec: OperatorSpec,
    instance: str | Path,
    *,
    repo_root: str | Path,
    proposer: Proposer,
    policy: AcceptancePolicy | None = None,
    max_attempts: int = 3,
    examples: list[str] | None = None,
    run_kwargs: dict[str, Any] | None = None,
) -> SynthesisResult:
    """Propose, validate, and retry until a candidate is accepted."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(spec.kind)},
        {"role": "user", "content": build_user_prompt(index, fingerprint, spec, examples)},
    ]

    attempts: list[Attempt] = []

    for attempt_number in range(1, max_attempts + 1):
        response = proposer(messages)
        source = extract_code(response)

        verdict = evaluate_candidate(
            source,
            spec.kind,
            instance,
            repo_root=repo_root,
            policy=policy,
            **(run_kwargs or {}),
        )

        attempts.append(Attempt(number=attempt_number, source=source, verdict=verdict))

        if verdict.accepted:
            return SynthesisResult(
                accepted=True,
                source=source,
                class_name=verdict.static.class_name if verdict.static else None,
                attempts=attempts,
            )

        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": _feedback(verdict)})

    return SynthesisResult(accepted=False, source=None, class_name=None, attempts=attempts)


def _feedback(verdict: Verdict) -> str:
    """Render a rejection into actionable instructions."""
    lines = ["That candidate was rejected. Fix these problems and try again:", ""]

    for reason in verdict.reasons:
        lines.append(f"- {reason}")

    if verdict.metrics is not None and verdict.metrics.ok:
        metrics = verdict.metrics
        lines.append("")
        lines.append("Measured behaviour:")
        lines.append(f"- feasible candidate rate: {metrics.feasible_rate:.0%}")
        lines.append(f"- mean fraction of decisions cleared: {metrics.mean_cleared_fraction:.1%}")
        lines.append(f"- baseline score: {metrics.baseline_score}")
        lines.append(f"- best score reached: {metrics.best_score}")
        lines.append(f"- iterations: {metrics.iterations}")
        lines.append(f"- wall clock: {metrics.elapsed_seconds:.2f}s")

    lines.append("")
    lines.append("Return only the corrected Python class.")
    return "\n".join(lines)


def write_operator(
    result: SynthesisResult,
    destination: str | Path,
    *,
    problem_class: str,
    kind: str,
) -> Path:
    """Persist an accepted operator as a self-contained, self-registering module.

    The validated source already carries its own imports; a registration footer
    is appended so importing the file (``load_generated_directory``) makes the
    operator available to ``create_destroy``/``create_repair`` by class name.

    If the class name is already taken (a built-in, or a different operator
    written earlier), the class is renamed with a numeric suffix and
    ``result.class_name``/``result.source`` are updated to match, so callers
    reference the name that actually got registered.
    """
    if not result.accepted or result.source is None or result.class_name is None:
        raise ValueError("cannot write a rejected synthesis result")

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    class_name, source = _unique_class(result.class_name, result.source, destination)
    result.class_name, result.source = class_name, source

    path = destination / f"{_snake_case(class_name)}.py"
    register = "register_destroy" if kind == "destroy" else "register_repair"
    description = _class_docstring(source, class_name)

    header = (
        f'"""Generated {kind} operator for {problem_class}.\n\n'
        f"Produced by operator-synthesis and validated by the harness.\n"
        f'"""\n\n'
    )
    footer = (
        "\n\n# --- registration (added when the operator was accepted) ---\n"
        f"from large_neighborhood_search.registry import {register} as _register  # noqa: E402\n\n"
        f"_register(\n"
        f"    {class_name!r},\n"
        f"    problem={problem_class!r},\n"
        f"    description={description!r},\n"
        f"    generated=True,\n"
        f")({class_name})\n"
    )
    path.write_text(header + source.strip() + footer, encoding="utf-8")
    return path


def _unique_class(class_name: str, source: str, destination: Path) -> tuple[str, str]:
    """Pick a class name that collides with neither the registry nor a file."""
    from large_neighborhood_search import builtin_operators  # noqa: F401 - populate registry
    from large_neighborhood_search.registry import describe

    def taken(name: str) -> bool:
        path = destination / f"{_snake_case(name)}.py"
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            # Re-writing the identical operator is not a collision.
            return source.strip() not in existing
        return describe(name) is not None

    candidate = class_name
    suffix = 2
    while taken(candidate):
        candidate = f"{class_name}{suffix}"
        suffix += 1

    if candidate != class_name:
        source = re.sub(rf"\b{re.escape(class_name)}\b", candidate, source)
    return candidate, source


def _class_docstring(source: str, class_name: str) -> str:
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            doc = ast.get_docstring(node) or ""
            return doc.strip().splitlines()[0] if doc.strip() else ""
    return ""


def _snake_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def write_report(result: SynthesisResult, path: str | Path) -> None:
    Path(path).write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
