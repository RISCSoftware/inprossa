"""Command line interface: one-shot subcommands plus an interactive REPL.

Two surfaces, one implementation. Every subcommand is a thin wrapper over the
same tool functions the agent loop calls, so a scripted run and a conversational
run cannot diverge.

Subcommands that need a model (``explain``, ``add-constraint``, ``chat``) fail
with a clear message when no credentials are configured. Subcommands that do not
(``analyze``, ``solve``, ``lns``, ``operators``) work offline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .agent import AgentLoop
from .commands import (
    HELP_TEXT,
    _turn_trace,
    describe_session,
    is_command,
    run_command,
)
from .config import AgentConfig
from .digest import model_digest, model_summary
from .llm import LLMClient, StubClient
from .lns_runner import LNSRunConfig, run_lns
from .operator_loader import list_operators, load_generated_operators
from .prompts import build_constraint_prompt, build_explain_prompt
from .report import write_session_report, write_tuning_report
from .session import Session
from .settings import DEFAULT_PROFILE, Profile, Settings, warn_if_insecure
from .tools import build_registry
from .tuning import TuningBudget, tune


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config = AgentConfig.from_env(
        model=getattr(args, "model", None),
        base_url=getattr(args, "base_url", None),
        api_key=getattr(args, "api_key", None),
        profile=getattr(args, "profile", None),
        dry_run=getattr(args, "dry_run", False),
    )
    if getattr(args, "out", None):
        config.output_dir = Path(args.out)
    if getattr(args, "solver", None):
        config.solver_name = args.solver
    if getattr(args, "timelimit", None) is not None:
        config.solve_timelimit = float(args.timelimit)
    if getattr(args, "iterations", None) is not None:
        config.lns_iterations = int(args.iterations)

    handler = {
        "analyze": _cmd_analyze,
        "explain": _cmd_explain,
        "add-constraint": _cmd_add_constraint,
        "solve": _cmd_solve,
        "lns": _cmd_lns,
        "operators": _cmd_operators,
        "tune": _cmd_tune,
        "chat": _cmd_chat,
        "tui": _cmd_tui,
        "settings": _cmd_settings,
    }[args.command]

    try:
        return handler(args, config)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optdsl_agent",
        description=(
            "LLM harness for OptDSL: analyse, explain, extend, solve and tune "
            "formulations across the MiniZinc and LNS backends."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(
        sub: argparse.ArgumentParser, *, needs_model: bool = False, file_optional: bool = False
    ) -> None:
        sub.add_argument(
            "file",
            type=Path,
            nargs="?" if file_optional else None,
            help=(
                "OptDSL formulation to work on. "
                "(omit to start with an empty problem)"
                if file_optional
                else "OptDSL formulation to work on."
            ),
        )
        sub.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
        sub.add_argument("--out", help="Directory for generated artifacts.")
        if needs_model:
            sub.add_argument("--model", help="Model name (default: gpt-4o).")
            sub.add_argument("--base-url", help="OpenAI-compatible base URL.")
            sub.add_argument(
                "--api-key",
                help=(
                    "Bearer token for the endpoint. Prefer OPTDSL_AGENT_API_KEY or a "
                    "stored profile: a key passed on the command line is visible in "
                    "shell history and in the process list."
                ),
            )
            sub.add_argument(
                "--profile",
                help="Stored settings profile to use (see `optdsl_agent settings`).",
            )
            sub.add_argument(
                "--dry-run",
                action="store_true",
                help="Use a stub model; makes no network calls.",
            )

    analyze = subparsers.add_parser("analyze", help="Summarise the formulation.")
    add_common(analyze)
    analyze.add_argument("--source", action="store_true", help="Include the model source.")

    explain = subparsers.add_parser("explain", help="Explain the formulation in prose.")
    add_common(explain, needs_model=True)

    add_constraint = subparsers.add_parser(
        "add-constraint", help="Add constraints described in natural language."
    )
    add_common(add_constraint, needs_model=True)
    add_constraint.add_argument("request", help="What the constraint should enforce.")
    add_constraint.add_argument(
        "--no-write", action="store_true", help="Validate only; do not write a file."
    )

    solve = subparsers.add_parser("solve", help="Solve exactly with MiniZinc.")
    add_common(solve)
    solve.add_argument("--solver", help="MiniZinc solver name (default: cp-sat).")
    solve.add_argument("--timelimit", type=float, help="Time limit in seconds.")

    lns = subparsers.add_parser("lns", help="Solve heuristically with LNS.")
    add_common(lns)
    lns.add_argument("--iterations", type=int, help="Iteration budget.")
    lns.add_argument("--seed", type=int, default=0)
    lns.add_argument("--destroy", action="append", default=[], help="Destroy operator name.")
    lns.add_argument("--repair", action="append", default=[], help="Repair operator name.")
    lns.add_argument("--initializer", default="auto", help="Initializer name.")
    lns.add_argument("--acceptance", default="improving", choices=["improving", "sa"])
    lns.add_argument("--adaptive", action="store_true", help="Adaptive operator selection.")
    lns.add_argument(
        "--no-tuned",
        action="store_true",
        help="Ignore the tuned LNS config written by `tune` for this model.",
    )
    lns.add_argument("--trajectory", action="store_true", help="Include per-iteration scores.")
    lns.add_argument(
        "--solution",
        action="store_true",
        help="Print the solution in problem-specific form (routes, schedule, bins).",
    )

    operators = subparsers.add_parser("operators", help="List available LNS operators.")
    add_common(operators)
    operators.add_argument("--problem", help="Filter by problem class.")

    tune_parser = subparsers.add_parser(
        "tune", help="Compare LNS against MiniZinc and synthesize better operators."
    )
    tune_parser.add_argument("files", nargs="+", type=Path, help="Instances to tune on.")
    tune_parser.add_argument("--json", action="store_true")
    tune_parser.add_argument("--out", help="Directory for reports and operators.")
    tune_parser.add_argument("--model")
    tune_parser.add_argument("--base-url")
    tune_parser.add_argument(
        "--api-key",
        help=(
            "Bearer token for the endpoint. Prefer OPTDSL_AGENT_API_KEY or a "
            "stored profile: a key passed on the command line is visible in "
            "shell history and in the process list."
        ),
    )
    tune_parser.add_argument("--profile", help="Stored settings profile to use.")
    tune_parser.add_argument("--dry-run", action="store_true")
    tune_parser.add_argument("--attempts", type=int, default=4, help="Synthesis attempts.")
    tune_parser.add_argument("--iterations", type=int, default=200, help="LNS iterations per run.")
    tune_parser.add_argument("--budget-seconds", type=float, default=900.0)
    tune_parser.add_argument("--solver", help="MiniZinc solver name.")
    tune_parser.add_argument("--timelimit", type=float, help="Exact-solver time limit.")

    chat = subparsers.add_parser("chat", help="Interactive session over one formulation.")
    add_common(chat, needs_model=True, file_optional=True)

    tui = subparsers.add_parser(
        "tui", help="Full-screen terminal UI (needs the optional 'textual' dependency)."
    )
    add_common(tui, needs_model=True, file_optional=True)

    settings = subparsers.add_parser(
        "settings", help="Show or edit stored model profiles."
    )
    settings.add_argument(
        "action",
        nargs="?",
        default="show",
        choices=["show", "set", "use", "unset", "path"],
        help="show (default), set, use, unset, or path.",
    )
    settings.add_argument("name", nargs="?", help="Profile name.")
    settings.add_argument("--model", help="Model name to store.")
    settings.add_argument("--base-url", help="Endpoint to store.")
    settings.add_argument("--api-key", help="API key to store.")
    settings.add_argument("--temperature", type=float, help="Temperature to store.")
    settings.add_argument("--json", action="store_true", help="Emit JSON.")

    return parser


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def _cmd_analyze(args: argparse.Namespace, config: AgentConfig) -> int:
    session = Session.from_file(args.file, config)
    summary = model_summary(session.source)

    if summary.syntax_error:
        print(f"error: {summary.syntax_error}", file=sys.stderr)
        return 1

    if args.json:
        _print_json(summary.to_dict())
        return 0

    print(model_digest(session.source, include_source=args.source))
    return 0


def _cmd_explain(args: argparse.Namespace, config: AgentConfig) -> int:
    session = Session.from_file(args.file, config)

    if config.dry_run:
        # A stub model cannot explain anything, but the digest is a genuine
        # structural description, so print that rather than a placeholder.
        print(model_digest(session.source))
        return 0

    client = _client(config)
    if client is None:
        return 2

    prompt = build_explain_prompt(model_digest(session.source))
    loop = AgentLoop(session, client)
    turn = loop.run(prompt)

    if args.json:
        _print_json(turn.to_dict())
    else:
        print(turn.final_text)
    return 0 if turn.stopped_reason is None else 1


def _cmd_add_constraint(args: argparse.Namespace, config: AgentConfig) -> int:
    session = Session.from_file(args.file, config)

    if config.dry_run:
        print(
            "error: adding constraints needs a model; --dry-run cannot propose them.",
            file=sys.stderr,
        )
        return 2

    client = _client(config)
    if client is None:
        return 2

    prompt = build_constraint_prompt(model_digest(session.source), args.request)
    loop = AgentLoop(session, client)
    turn = loop.run(prompt)

    if args.json:
        _print_json(turn.to_dict())
    else:
        print(turn.final_text)
        for artifact in session.artifacts:
            print(f"\nwrote {artifact.kind}: {artifact.path}")

    if args.no_write:
        return 0
    return 0 if session.artifacts else 1


def _cmd_solve(args: argparse.Namespace, config: AgentConfig) -> int:
    session = Session.from_file(args.file, config)
    registry = build_registry()
    result = registry.call(
        "solve_minizinc",
        session,
        {"solver": args.solver, "timelimit": args.timelimit},
    )

    if args.json:
        _print_json(result)
    elif result.get("ok"):
        print(f"status:    {result['status']}")
        print(f"objective: {result['objectiveValue']}")
        if result.get("objectiveBound") is not None:
            print(f"bound:     {result['objectiveBound']}")
        print(f"time:      {result.get('totalTime')}s")
    else:
        print(f"error: {result.get('error')}", file=sys.stderr)

    return 0 if result.get("ok") else 1


def _cmd_lns(args: argparse.Namespace, config: AgentConfig) -> int:
    session = Session.from_file(args.file, config)
    load_generated_operators(config.operator_dir)

    from .lns_config import describe_run, resolve_run_settings

    settings = resolve_run_settings(
        session.source,
        config.operator_dir,
        destroys=list(args.destroy),
        repairs=list(args.repair),
        initializer=args.initializer,
        adaptive=args.adaptive,
        use_tuned=not args.no_tuned,
    )

    result = run_lns(
        LNSRunConfig(
            instance=args.file,
            seed=args.seed,
            iterations=args.iterations or config.lns_iterations,
            initializer=settings.initializer,
            acceptance=args.acceptance,
            destroys=list(settings.destroys),
            repairs=list(settings.repairs),
            adaptive=settings.adaptive,
            record_trajectory=args.trajectory,
        )
    )

    if args.json:
        _print_json({**result.to_dict(), "lnsConfig": settings.log})
    elif result.ok:
        print(describe_run(settings.log, result.to_dict()))
        print(f"objective:  {result.objective_value}")
        print(f"feasible:   {result.feasible}")
        print(f"iterations: {result.iterations}")
        print(f"improved:   {result.improvements}")
        print(f"time:       {result.elapsed_seconds:.2f}s")
        if result.operator_weights:
            print("weights:")
            for name, weight in sorted(result.operator_weights.items()):
                print(f"  {name}: {weight}")
        if args.solution and result.rendered:
            print()
            print(result.rendered)
    else:
        print(f"error: {result.error}", file=sys.stderr)

    return 0 if result.ok else 1


def _cmd_operators(args: argparse.Namespace, config: AgentConfig) -> int:
    load_generated_operators(config.operator_dir)
    problem = args.problem
    if problem is None:
        try:
            problem = model_summary(Session.from_file(args.file, config).source).problem_class
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    operators = list_operators(problem)
    if args.json:
        _print_json({"problem": problem, "operators": operators})
        return 0

    print(f"operators for {problem or 'any problem'}:")
    for kind in ("destroy", "repair"):
        names = [op["name"] for op in operators if op["kind"] == kind]
        print(f"\n{kind} ({len(names)}):")
        for name in names:
            print(f"  {name}")
    return 0


def _cmd_tune(args: argparse.Namespace, config: AgentConfig) -> int:
    client = _client(config)
    if client is None:
        return 2

    budget = TuningBudget(
        max_attempts=args.attempts,
        max_wall_seconds=args.budget_seconds,
        iterations=args.iterations,
    )

    report = tune(
        args.files,
        config,
        client=client,
        budget=budget,
        progress=None if args.json else (lambda message: print(f"  {message}")),
    )

    paths = write_tuning_report(report, config.output_dir, stem=args.files[0].stem)

    if args.json:
        _print_json({**report.to_dict(), "reports": paths})
    else:
        print()
        print(report.to_markdown())
        print(f"\nreport: {paths['markdown']}")

    return 0


def _cmd_chat(args: argparse.Namespace, config: AgentConfig) -> int:
    session = _load_session(args, config)
    client = _client(config)
    if client is None:
        return 2

    return _repl(session, client, config)

def _cmd_tui(args: argparse.Namespace, config: AgentConfig) -> int:
    """Start the full-screen UI."""
    from .tui import run_tui, textual_available

    if not textual_available():
        from .tui import INSTALL_HINT

        print(INSTALL_HINT, file=sys.stderr)
        return 2

    session = _load_session(args, config)
    client = _client(config)
    if client is None:
        return 2

    return run_tui(session, client, config)


def _load_session(args: argparse.Namespace, config: AgentConfig) -> Session:
    """Session for this invocation; omit the file to start from an empty problem."""
    if getattr(args, "file", None) is None:
        return Session.from_source("", config)
    return Session.from_file(args.file, config)


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


def _cmd_settings(args: argparse.Namespace, config: AgentConfig) -> int:
    """Show or edit stored model profiles."""
    settings = Settings.load()
    action = args.action

    if action == "path":
        print(Settings.path())
        return 0

    if action == "show":
        if args.json:
            _print_json(settings.to_dict())
            return 0
        _print_settings(settings)
        return 0

    if action == "use":
        name = args.name or DEFAULT_PROFILE
        if name not in settings.profiles:
            print(f"error: no profile named '{name}'", file=sys.stderr)
            return 1
        settings.default_profile = name
        path = settings.save()
        print(f"default profile is now '{name}' ({path})")
        return 0

    if action == "unset":
        name = args.name or DEFAULT_PROFILE
        if not settings.remove_profile(name):
            print(f"error: no profile named '{name}'", file=sys.stderr)
            return 1
        if settings.default_profile == name:
            settings.default_profile = DEFAULT_PROFILE
        path = settings.save()
        print(f"removed profile '{name}' ({path})")
        return 0

    # action == "set"
    name = args.name or settings.default_profile
    existing = settings.profile(name)
    profile = Profile(
        model=args.model if args.model is not None else existing.model,
        base_url=args.base_url if args.base_url is not None else existing.base_url,
        api_key=args.api_key if args.api_key is not None else existing.api_key,
        temperature=(
            args.temperature if args.temperature is not None else existing.temperature
        ),
    )
    if profile.is_empty():
        print(
            "error: nothing to store; pass --model, --base-url, --api-key or --temperature",
            file=sys.stderr,
        )
        return 1

    settings.set_profile(name, profile)
    path = settings.save()

    print(f"stored profile '{name}' in {path}")
    for key, value in profile.to_dict(redact=True).items():
        print(f"  {key}: {value}")

    if warning := warn_if_insecure(path):
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _print_settings(settings: Settings) -> None:
    path = Settings.path()
    print(f"settings file: {path}")
    if not path.exists():
        print("  (not created yet)")
    print(f"default profile: {settings.default_profile}")

    if not settings.profiles:
        print("\nno profiles stored. Create one with:")
        print("  optdsl_agent settings set --model gpt-4o --api-key ...")
        return

    print()
    for name, profile in sorted(settings.profiles.items()):
        marker = " (default)" if name == settings.default_profile else ""
        print(f"[{name}]{marker}")
        for key, value in profile.to_dict(redact=True).items():
            print(f"  {key}: {value}")

    if warning := warn_if_insecure(path):
        print(f"\nwarning: {warning}", file=sys.stderr)


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------


def _repl(session: Session, client: Any, config: AgentConfig) -> int:
    loop = AgentLoop(session, client)
    print(f"OptDSL agent - {session.label}")
    print(describe_session(session, config))
    print("Type /help for commands, /quit to exit. Type / to list them.\n")

    while True:
        try:
            line = input("optdsl> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue

        # A bare "/" lists the commands. There is no readline on Windows, so a
        # popup is not available here; listing is the equivalent affordance.
        if line == "/":
            print(HELP_TEXT)
            continue

        if is_command(line):
            result = run_command(line, session, loop, config, progress=lambda m: print(m))
            if result.quit:
                return 0
            if result.trace:
                print(result.trace)
            if result.text:
                print(result.text)
            for artifact in result.artifacts:
                print(f"wrote {artifact}")
            continue

        turn = loop.run(line)
        trace = _turn_trace(turn)
        if trace:
            print(trace)
        if turn.final_text:
            print(f"\n{turn.final_text}\n")
        if turn.stopped_reason:
            print(f"[stopped: {turn.stopped_reason}]\n")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _client(config: AgentConfig) -> Any:
    """Build a model client, or explain why one cannot be built."""
    if config.dry_run:
        return StubClient()
    if not config.has_credentials:
        print(
            "error: no model configured. Store one with `optdsl_agent settings set`, "
            "set OPTDSL_AGENT_API_KEY (or OPENAI_API_KEY), pass --api-key, pass "
            "--base-url for a local endpoint, or use --dry-run.",
            file=sys.stderr,
        )
        return None
    return LLMClient(config)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, default=str))
