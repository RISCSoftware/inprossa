"""Command line interface for operator synthesis.

Examples
--------
Validate a hand-written operator without any model involvement::

    python -m operator_synthesis validate my_operator.py --kind destroy \
        --instance problem_instances/cvrp/random_euclidean_cvrp_8.dsl

Synthesize with an external model (any OpenAI-compatible endpoint)::

    python -m operator_synthesis generate --kind destroy \
        --instance problem_instances/cvrp/random_euclidean_cvrp_8.dsl \
        --model gpt-4o --attempts 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from optdsl_tooling import analyze_file, fingerprint

from .harness import AcceptancePolicy, evaluate_candidate, static_check
from .prompts import OperatorSpec
from .synthesize import synthesize, write_operator, write_report


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_spec(index, kind: str) -> OperatorSpec:
    problem = fingerprint(index)
    targets = [name for name, variable in index.variables.items() if variable.is_decision]
    return OperatorSpec(
        kind=kind,
        problem_class=problem.best.name if problem.best else "unknown",
        objective=(
            f"{index.objective.sense} {index.objective.expression}"
            if index.objective
            else "unspecified"
        ),
        target_variables=targets,
        hyperparameters={"fraction": 0.2},
        invariants=[],
    )


def _http_proposer(model: str, api_key: str | None, base_url: str | None):
    """Return a proposer backed by an OpenAI-compatible chat endpoint."""
    try:
        import urllib.request
    except ImportError:  # pragma: no cover
        raise SystemExit("urllib is unavailable")

    endpoint = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"

    def propose(messages: list[dict[str, str]]) -> str:
        body = json.dumps({"model": model, "messages": messages, "temperature": 0.2}).encode()
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key or ''}",
            },
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read())
        return payload["choices"][0]["message"]["content"]

    return propose


def _cmd_validate(args: argparse.Namespace) -> int:
    source = Path(args.file).read_text(encoding="utf-8")
    static = static_check(source, args.kind)
    if not static.ok:
        print(json.dumps({"static": {"ok": False, "errors": static.errors}}, indent=2))
        return 1

    verdict = evaluate_candidate(
        source,
        args.kind,
        args.instance,
        repo_root=_repo_root(),
        policy=AcceptancePolicy(require_improvement=not args.no_improvement_required),
        iterations=args.iterations,
        seed=args.seed,
    )
    print(json.dumps(verdict.to_dict(), indent=2))
    return 0 if verdict.accepted else 1


def _cmd_generate(args: argparse.Namespace) -> int:
    index = analyze_file(args.instance)
    problem = fingerprint(index)
    spec = _default_spec(index, args.kind)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and not args.base_url:
        print("error: set OPENAI_API_KEY or pass --base-url for a local endpoint", file=sys.stderr)
        return 2

    result = synthesize(
        index,
        problem,
        spec,
        args.instance,
        repo_root=_repo_root(),
        proposer=_http_proposer(args.model, api_key, args.base_url),
        max_attempts=args.attempts,
        run_kwargs={"iterations": args.iterations, "seed": args.seed},
    )

    if args.report:
        write_report(result, args.report)

    if not result.accepted:
        print(json.dumps(result.to_dict(), indent=2))
        print("no candidate was accepted", file=sys.stderr)
        return 1

    destination = Path(args.output) if args.output else _repo_root() / "large_neighborhood_search" / "problems" / "generated"
    path = write_operator(result, destination, problem_class=spec.problem_class, kind=args.kind)
    print(f"accepted {result.class_name} -> {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="operator_synthesis")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate an existing operator file")
    validate.add_argument("file")
    validate.add_argument("--kind", choices=["destroy", "repair"], required=True)
    validate.add_argument("--instance", required=True)
    validate.add_argument("--iterations", type=int, default=200)
    validate.add_argument("--seed", type=int, default=0)
    validate.add_argument("--no-improvement-required", action="store_true")
    validate.set_defaults(func=_cmd_validate)

    generate = subparsers.add_parser("generate", help="synthesize a new operator with a model")
    generate.add_argument("--kind", choices=["destroy", "repair"], required=True)
    generate.add_argument("--instance", required=True)
    generate.add_argument("--model", default="gpt-4o")
    generate.add_argument("--base-url", default=None)
    generate.add_argument("--attempts", type=int, default=3)
    generate.add_argument("--iterations", type=int, default=200)
    generate.add_argument("--seed", type=int, default=0)
    generate.add_argument("--output", default=None)
    generate.add_argument("--report", default=None)
    generate.set_defaults(func=_cmd_generate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
