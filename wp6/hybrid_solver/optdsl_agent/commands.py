"""Slash commands, shared by the line REPL and the TUI.

Both front-ends must behave identically: a user who learns ``/lns 500`` in the
REPL should get the same thing in the TUI. So the commands live here, returning
text, and each front-end only decides how to display it.

Every handler returns a :class:`CommandResult` rather than printing. That is what
makes the TUI possible at all — a widget cannot capture ``print`` output.

The :data:`COMMANDS` table is the single source of truth for the command set. The
dispatcher, the help text and the completion popup all read it, so adding a
command in one place makes it appear everywhere.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .agent import AgentLoop
from .config import AgentConfig
from .digest import model_digest, model_summary
from .prompts import build_constraint_prompt, build_explain_prompt, build_model_prompt
from .report import write_session_report
from .session import Session
from .tuning import TuningBudget, tune


@dataclass(frozen=True)
class CommandSpec:
    """One slash command: its name, argument hint and one-line help."""

    name: str
    help: str
    usage: str = ""
    #: True when the command sends a request to the model.
    uses_model: bool = False

    @property
    def signature(self) -> str:
        """How the command is typed, e.g. ``/lns [iterations]``."""
        return f"/{self.name}" + (f" {self.usage}" if self.usage else "")


#: Every slash command, in the order the help text lists them.
COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec("analyze", "summarise the model"),
    CommandSpec("explain", "explain the model in prose", uses_model=True),
    CommandSpec(
        "describe",
        "generate a whole new OptDSL model from a description",
        usage="<problem> | @file[:section]",
        uses_model=True,
    ),
    CommandSpec(
        "add",
        "add constraints described in natural language",
        usage="<request>",
        uses_model=True,
    ),
    CommandSpec("solve", "solve exactly with MiniZinc", usage="[timelimit-s]"),
    CommandSpec("lns", "solve heuristically with LNS", usage="[iterations]"),
    CommandSpec("solution", "show the last solution in problem-specific form"),
    CommandSpec("compare", "compare the last LNS run with the last exact solve"),
    CommandSpec("operators", "list available operators"),
    CommandSpec("tune", "run the self-tuning loop", usage="[attempts]", uses_model=True),
    CommandSpec("diff", "show what changed since the file was loaded"),
    CommandSpec("save", "write the model (.dsl) and a session transcript"),
    CommandSpec(
        "new",
        "discard the current model and start from an empty problem",
    ),
    CommandSpec("reset", "clear the conversation, keep the model"),
    CommandSpec("help", "show this help"),
    CommandSpec("quit", "exit"),
)

#: Aliases that resolve to a canonical command.
ALIASES: dict[str, str] = {"/exit": "quit"}


def _help_text() -> str:
    """Render the help from the command table, so it cannot go stale."""
    width = max(len(spec.signature) for spec in COMMANDS)
    lines = ["Commands:"]
    for spec in COMMANDS:
        lines.append(f"  {spec.signature:<{width}}  {spec.help}")
    lines.append("")
    lines.append("Anything else is sent to the model as a request.")
    return "\n".join(lines)


HELP_TEXT = _help_text()


@dataclass
class CommandResult:
    """What a slash command produced."""

    text: str = ""
    #: True when the front-end should exit.
    quit: bool = False
    #: True when the command was not recognised.
    unknown: bool = False
    #: Files written as a side effect, for the front-end to report.
    artifacts: list[str] = field(default_factory=list)
    #: Optional concise trace of the agent's tool activity, rendered by the
    #: front-end as a light-grey block (e.g. after ``/add`` or ``/explain``).
    trace: str | None = None


def is_command(line: str) -> bool:
    return line.startswith("/")


def canonical_name(token: str) -> str:
    """Resolve an alias to its canonical command name, without the slash."""
    return ALIASES.get(token, token.lstrip("/"))


def matching_commands(prefix: str) -> list[CommandSpec]:
    """Commands whose name starts with *prefix*.

    *prefix* may be given with or without the leading slash. An empty prefix
    matches everything, which is what the popup shows right after ``/``.
    """
    needle = prefix.lstrip("/").lower()
    return [spec for spec in COMMANDS if spec.name.startswith(needle)]


def complete(line: str) -> tuple[str, list[CommandSpec]]:
    """Complete a partially typed command line.

    Returns ``(replacement, matches)``. ``replacement`` is the longest common
    prefix of the matches, so pressing Tab repeatedly narrows the input instead
    of cycling blindly.

    Completion only applies to the command word: once the user has typed a space
    they are writing an argument, and completing it would be wrong.
    """
    if not line.startswith("/") or " " in line:
        return line, []

    matches = matching_commands(line)
    if not matches:
        return line, []

    names = [f"/{spec.name}" for spec in matches]
    return _common_prefix(names), matches


def _common_prefix(values: list[str]) -> str:
    if not values:
        return ""
    shortest = min(values, key=len)
    for index, char in enumerate(shortest):
        if any(value[index] != char for value in values):
            return shortest[:index]
    return shortest


def run_command(
    line: str,
    session: Session,
    loop: AgentLoop,
    config: AgentConfig,
    progress: Callable[[str], None] | None = None,
) -> CommandResult:
    """Execute one slash command and return its output."""
    token, _, argument = line.partition(" ")
    command = canonical_name(token)
    argument = argument.strip()
    registry = loop.registry

    if command == "quit":
        return CommandResult(quit=True)

    if command == "help":
        return CommandResult(text=HELP_TEXT)

    if command == "reset":
        loop.reset()
        return CommandResult(text="conversation cleared")

    if command == "new":
        session.new_problem()
        loop.reset()
        return CommandResult(
            text="discarded the current model; starting from a new empty problem "
            "(label: new empty problem)"
        )

    if command == "save":
        paths = write_session_report(session)
        written = "\n".join(f"wrote {paths[key]}" for key in ("dsl", "json") if key in paths)
        return CommandResult(text=written, artifacts=[paths[k] for k in ("dsl", "json") if k in paths])

    if command == "diff":
        return CommandResult(text=_diff(session))

    if command == "analyze":
        result = registry.call("analyze_model", session, {})
        return CommandResult(text=result.get("digest") or result.get("error", ""))

    if command == "explain":
        turn = loop.run(build_explain_prompt(model_digest(session.source)))
        return CommandResult(text=turn.final_text, trace=_turn_trace(turn))

    if command == "describe":
        if not argument:
            return CommandResult(
                text=(
                    "usage: /describe <description …>  |  "
                    "/describe @file  |  /describe @file:Section"
                )
            )
        try:
            description, source_label = _resolve_description(argument)
        except (FileNotFoundError, ValueError) as exc:
            return CommandResult(text=f"could not load description: {exc}")

        turn = loop.run(build_model_prompt(description))
        source = _extract_model_source(turn.final_text)
        if source is None:
            return CommandResult(
                text=(
                    "the model did not return a usable OptDSL source; try rephrasing "
                    "the description and ensure the model reply is a JSON `{\"source\": ...}`"
                ),
                trace=_turn_trace(turn),
            )
        errors = _model_validation_errors(source)
        if errors:
            return CommandResult(
                text="the generated model does not validate:\n- " + "\n- ".join(errors),
                trace=_turn_trace(turn),
            )

        session.adopt_model(source)
        paths = write_session_report(session)
        origin = source_label or "inline description"
        return CommandResult(
            text=(
                "generated and adopted a new OptDSL model "
                f"({len(source.splitlines())} lines).\n"
                f"wrote {paths['dsl']}\n"
                "Run /analyze to inspect it, or /solve and /lns once you are happy."
            ),
            trace=f"model generated from {origin} ({len(source.splitlines())} lines) and validated",
            artifacts=[paths["dsl"]],
        )

    if command == "add":
        if not argument:
            return CommandResult(text="usage: /add <what the constraint should enforce>")
        turn = loop.run(build_constraint_prompt(model_digest(session.source), argument))
        written = [str(artifact.path) for artifact in session.artifacts[-3:]]
        return CommandResult(text=turn.final_text, trace=_turn_trace(turn), artifacts=written)

    if command == "solve":
        timelimit = _parse_float(argument)
        if argument and timelimit is None:
            return CommandResult(text=f"usage: /solve [timelimit-s]; '{argument}' is not a number")
        result = registry.call(
            "solve_minizinc", session, {} if timelimit is None else {"timelimit": timelimit}
        )
        if result.get("ok"):
            text = (
                f"status {result['status']}, objective {result['objectiveValue']}, "
                f"bound {result.get('objectiveBound')}"
            )
            if result.get("warmStart"):
                text += ", warm start applied"
            return CommandResult(text=text)
        return CommandResult(text=f"error: {result.get('error')}")

    if command == "lns":
        iterations = int(argument) if argument.isdigit() else config.lns_iterations
        result = registry.call("run_lns", session, {"iterations": iterations})
        if result.get("ok"):
            from .lns_config import describe_run

            text = (
                f"objective {result['objectiveValue']}, feasible {result['feasible']}, "
                f"{result['iterations']} iterations in {result['elapsedSeconds']}s"
            )
            config_line = describe_run(result.get("lnsConfig"), result)
            if config_line:
                text = config_line + "\n" + text
            if result.get("warmStartSaved"):
                text += (
                    f"\nwarm start saved to {result['warmStartPath']} — "
                    "the next /solve will reuse it"
                )
            if result.get("rendered"):
                text += "\n\n" + result["rendered"]
            return CommandResult(text=text)
        return CommandResult(text=f"error: {result.get('error')}")

    if command == "solution":
        return CommandResult(text=_solution(session))

    if command == "compare":
        result = registry.call("compare_runs", session, {})
        return CommandResult(text=_render_compare(result))

    if command == "operators":
        # Filter by the model's own problem class: listing every adapter's
        # operators is noise when the user is working on one formulation.
        problem = model_summary(session.source).problem_class
        result = registry.call("list_operators", session, {"problem": problem})
        lines = [f"operators for {problem or 'any problem'}:"]
        for operator in result.get("operators", []):
            lines.append(f"  {operator['kind']:7} {operator['name']}")
        return CommandResult(text="\n".join(lines))

    if command == "tune":
        attempts = int(argument) if argument.isdigit() else 2
        budget = TuningBudget(max_attempts=attempts)
        if progress:
            progress(
                "tuning plan: exact baseline, LNS baseline, diagnosis, then up to "
                f"{budget.max_attempts} synthesis attempt(s). Each attempt spends a model "
                f"call plus up to ~6 LNS runs of {budget.iterations} iterations; wall-clock "
                f"cap {budget.max_wall_seconds:.0f}s (Ctrl-C to abort)."
            )
        instances = _materialise_for_tune(session)
        report = tune(
            instances,
            config,
            client=loop.client,
            budget=budget,
            progress=progress,
        )
        return CommandResult(text=report.to_markdown())

    return CommandResult(text=f"unknown command {token}; try /help", unknown=True)


def _render_compare(result: dict[str, Any]) -> str:
    """Human-readable ``/compare`` report from the ``compare_runs`` payload.

    Shows the LNS objective, the exact objective, the exact solver's lower
    bound, and the percentage gaps between every pair — each only when the
    underlying number is available so partial data still renders.
    """
    if not result.get("ok"):
        return result.get("error", "compare failed")

    sense = " (maximize)" if result.get("objectiveSense") == "maximize" else ""

    def _fmt(value: object) -> str:
        if value is None:
            return "n/a"
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    def _pct(value: object) -> str:
        if value is None:
            return "n/a"
        return f"{value * 100:.2f}%"

    lines = [
        f"objective sense: {result.get('objectiveSense', 'minimize')}{sense}",
        f"LNS objective:    {_fmt(result.get('lnsObjective'))}"
        + ("  (feasible)" if result.get("lnsFeasible") else ""),
        f"solve objective:  {_fmt(result.get('exactObjective'))}"
        + f"  ({result.get('exactStatus', '?')})",
        f"solve lower bound:{_fmt(result.get('lowerBound'))}",
        "",
        "quality gaps (worse vs reference):",
        f"  LNS vs solve: {_pct(result.get('lnsVsSolvePct'))}",
        f"  LNS vs bound: {_pct(result.get('lnsVsBoundPct'))}",
        f"  solve vs bound: {_pct(result.get('solveVsBoundPct'))}",
    ]
    return "\n".join(lines)


def _parse_float(value: str) -> float | None:
    """Parse a positive float from a command argument, or ``None`` if invalid."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _resolve_description(argument: str, cwd: Path | None = None) -> tuple[str, str | None]:
    """Resolve a ``/describe`` argument to a multi-line description.

    Accepts either inline text (``/describe 8 cities, …``) or a file reference:

    - ``@path/to/description.txt`` — use the whole file,
    - ``@path/to/description.txt:Section name`` — use one ``#``-headed section.

    Windows drive letters (``C:``) are handled by rejoining colon-split path
    candidates. Returns ``(description, source_label)``; ``source_label`` is
    ``None`` for inline text and the file path otherwise (shown in the trace).
    """
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    if not argument.startswith("@"):
        return argument.strip(), None

    reference = argument[1:].strip()

    # Whole file: the entire reference is a path.
    whole = Path(reference) if Path(reference).is_absolute() else cwd / reference
    if whole.exists():
        return whole.read_text(encoding="utf-8").strip(), str(whole)

    # "path:section": find the rightmost ':' separator whose prefix is a file.
    parts = reference.split(":")
    for split_at in range(len(parts) - 1, 0, -1):
        path_text = ":".join(parts[:split_at])
        section = ":".join(parts[split_at:])
        path = Path(path_text) if Path(path_text).is_absolute() else cwd / path_text
        if path.exists():
            return _extract_section(path.read_text(encoding="utf-8"), section), str(path)

    raise FileNotFoundError(f"description file not found: {reference} (looked under {cwd})")


def _extract_section(text: str, title: str) -> str:
    """Return the body of the ``#``-headed section named *title* from *text*."""
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            if current_title is not None:
                sections.append((current_title, current))
            current_title, current = line.lstrip("#").strip(), []
        else:
            current.append(line)
    if current_title is not None:
        sections.append((current_title, current))

    wanted = title.strip().lower()
    for name, body in sections:
        if name.lower() == wanted:
            return "\n".join(body).strip()
    raise ValueError(
        f"section {title!r} not found; available sections: "
        + ", ".join(f"'{name}'" for name, _ in sections)
        or "the file has no '#'-headed sections"
    )


def _turn_trace(turn: Any, *, max_lines: int = 10) -> str | None:
    """Concise record of what the agent did during one turn.

    Shows the tool calls the model made (with a short result) followed by its
    final reply, capped to *max_lines*. Returns ``None`` when there is nothing
    worth showing, so front-ends do not paint an empty grey box.
    """
    lines: list[str] = []
    for call in turn.tool_calls[:6]:
        signature = _brief_arguments(call.get("arguments") or {})
        summary = (call.get("summary") or "").strip()
        state = "ok" if call.get("ok") is True else "failed"
        entry = f"-> {call.get('name')}({signature}) {state}"
        if summary:
            entry += f" -- {summary}"
        lines.append(entry)
    final = (turn.final_text or "").strip()
    if final:
        lines.append(final)
    if not lines:
        return None
    return "\n".join(lines[:max_lines])


def _extract_model_source(reply: str) -> str | None:
    """Pull the OptDSL source out of the model's reply for ``/describe``.

    The prompt asks for a single JSON object ``{"source": ...}``; a well-behaved
    model returns that verbatim. Tolerate fenced replies and bare source text as
    fallbacks, but refuse plain prose so a refusal is reported politely instead
    of being parsed as a broken model.
    """
    text = (reply or "").strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            source = payload.get("source")
            if isinstance(source, str) and source.strip():
                return source
    except json.JSONDecodeError:
        pass

    # Fall back: a fenced JSON object, or bare (fenced) DSL source text.
    stripped = _strip_code_fence(text)
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
            source = payload.get("source")
            if isinstance(source, str) and source.strip():
                return source
        except json.JSONDecodeError:
            return None
        return None

    if _looks_like_dsl(stripped):
        return stripped
    return None


def _looks_like_dsl(text: str) -> bool:
    """Best-effort check that text is OptDSL/Python, not explanatory prose."""
    markers = ("minimize(", "maximize(", "DSList", " : ", "def ")
    return any(marker in text for marker in markers)


def _strip_code_fence(text: str) -> str:
    """Remove a single ``` ... ``` Markdown fence, if present."""
    import re

    match = re.match(r"\s*```[a-zA-Z0-9]*\s*\n(.*?)```\s*$", text, re.DOTALL)
    if match:
        return match.group(1)
    return text


def _model_validation_errors(source: str) -> list[str]:
    """Check a freshly generated model parses, is clean, and translates.

    Mirrors the structural gate used by ``add_constraints``.
    """
    errors: list[str] = []

    from optdsl_tooling.analysis import analyze
    from optdsl_tooling.diagnostics import Severity, check
    from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator

    index = analyze(source)
    if index.syntax_error is not None:
        return [f"does not parse: {index.syntax_error}"]

    diag_errors = [
        d for d in check(index) if d.severity == Severity.ERROR
    ]
    errors.extend(f"{d.code}: {d.message}" for d in diag_errors)

    try:
        MiniZincTranslator(source, dsl_index_base=0).unroll_translation()
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        errors.append(f"does not translate to MiniZinc: {type(exc).__name__}: {exc}")

    return errors


def _brief_arguments(arguments: dict[str, Any]) -> str:
    """Flatten tool arguments into a short inline signature."""
    parts: list[str] = []
    for key, value in list(arguments.items())[:3]:
        text = value if isinstance(value, str) else repr(value)
        text = text.replace("\n", " ").strip()
        if len(text) > 22:
            text = text[:19] + "..."
        parts.append(f"{key}={text}")
    return ", ".join(parts)


def _materialise_for_tune(session: Session) -> list[Path]:
    """/tune needs a file path holding the *current* model.

    The session's file is used only while it still matches the in-memory text;
    otherwise (a /describe model, or accepted edits not yet saved) the text is
    written out, so /tune tunes the same model /lns later keys its config by.
    """
    if session.path is not None:
        try:
            if session.path.read_text(encoding="utf-8") == session.source:
                return [session.path]
        except OSError:
            pass
    session.config.ensure_directories()
    target = session.config.output_dir / f"{session.stem}.current.dsl"
    target.write_text(session.source, encoding="utf-8")
    return [target]


def _solution(session: Session) -> str:
    """Render the last solution, preferring the LNS incumbent.

    The exact solver's solution is a flat variable dict; the LNS result already
    carries a problem-specific rendering, so it is used when available.
    """
    lns = session.last_lns
    if lns and lns.get("rendered"):
        return lns["rendered"]

    exact = session.last_solve
    if exact and exact.get("solution"):
        from .printers import format_solution

        return format_solution(
            exact["solution"],
            {},
            problem_class=model_summary(session.source).problem_class,
            objective_value=exact.get("objectiveValue"),
        )

    return "no solution yet; run /solve or /lns first"


def _diff(session: Session) -> str:
    """Show how the in-memory model differs from the file on disk."""
    if session.path is None:
        return "no source file to compare against"
    try:
        original = session.path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"error: {exc}"

    if original == session.source:
        return "the model is unchanged"

    import difflib

    return "\n".join(
        difflib.unified_diff(
            original.splitlines(),
            session.source.splitlines(),
            fromfile=str(session.path),
            tofile="current",
            lineterm="",
        )
    )


def describe_session(session: Session, config: AgentConfig) -> str:
    """One-line status used by both front-ends."""
    model = config.model
    endpoint = config.base_url
    key = "key set" if config.api_key else "no key"
    return f"{model} @ {endpoint} ({key})"
