"""LLM-synthesized feasibility initializers for problems LNS has no adapter for.

The generic greedy/random initializers cannot reach the feasible region of a
tightly-coupled model (e.g. capacitated lot-sizing), so LNS and tuning stall at
an infeasible baseline. The tuning loop can instead ask the model to write an
``Initializer`` that constructs a *feasible* assignment for the specific DSL,
verify it against the real evaluator, and persist it so later ``/lns`` runs use
it. This module owns that artifact: checking, instantiating, testing and
persisting synthesized initializers, plus a small inline static check (the
``operator-synthesis`` harness validates destroy/repair operators; initializers
are validated here so the package stays independent of it).
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Modules a generated initializer may import (same allowlist idea as the
#: operator harness).
ALLOWED_IMPORTS: frozenset[str] = frozenset(
    {
        "math",
        "random",
        "dataclasses",
        "typing",
        "collections",
        "itertools",
        "large_neighborhood_search",
        "large_neighborhood_search.components",
        "large_neighborhood_search._utils",
        "large_neighborhood_search.lns",
    }
)

FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {
        "eval", "exec", "compile", "__import__", "open", "input",
        "globals", "locals", "vars", "getattr", "setattr", "delattr",
        "breakpoint",
    }
)

_FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


@dataclass
class InitializerArtifact:
    """A feasibility initializer (builtin, or synthesized + optionally persisted)."""

    #: `"module"` when this wraps a loaded module-level class by name, or the
    #: ``source``/``class_name`` pair for synthesized code.
    source: str
    class_name: str
    #: Optional file this artifact was loaded from / written to (generated module).
    path: Path | None = None
    #: Optional instance name to construct (for module artifacts).
    module_name: str | None = None

    def instantiate(self) -> Any:
        """Build the initializer instance (execs synthesized source, or imports a module)."""
        if self.module_name is not None:
            import importlib

            module = importlib.import_module(self.module_name)
            return getattr(module, self.class_name)()
        namespace: dict[str, Any] = {"__name__": "generated_initializer"}
        exec(compile(self.source, "<generated_initializer>", "exec"), namespace)  # noqa: S102 - generated, static-checked
        return namespace[self.class_name]()


def extract_initializer_code(response: str) -> str:
    """Pull the Python class out of a model response (fence-tolerant)."""
    match = _FENCE.search(response)
    if match:
        return match.group(1).strip()
    lines = response.splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith(("import ", "from ", "class ")):
            return "\n".join(lines[index:]).strip()
    return response.strip()


def static_check_initializer(source: str) -> tuple[bool, str | None, list[str]]:
    """Vet an initializer source without executing it.

    Returns ``(ok, class_name, errors)``.
    """
    errors: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, None, [f"syntax error: {exc.msg} (line {exc.lineno})"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS:
                    errors.append(f"import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "") not in ALLOWED_IMPORTS:
                errors.append(f"import from '{node.module}' is not allowed")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            errors.append(f"use of '{node.id}' is not allowed")

    class_name: str | None = None
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
        if "Initializer" not in bases:
            continue
        class_name = node.name
        methods = {child.name for child in node.body if isinstance(child, ast.FunctionDef)}
        if "initialize" not in methods:
            errors.append(f"class '{node.name}' does not implement 'initialize'")

    if class_name is None:
        errors.append("no class subclassing Initializer found")
    elif not _imports_name(tree, "Initializer"):
        # The module is persisted and imported as-is, so it must import its
        # own base class rather than rely on a caller-provided namespace.
        errors.append(
            "'Initializer' is used but never imported; the module must be self-contained "
            "(add `from large_neighborhood_search.components import Initializer`)"
        )

    return not errors, class_name, errors


def _imports_name(tree: ast.Module, name: str) -> bool:
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any(
            (alias.asname or alias.name) == name for alias in node.names
        ):
            return True
    return False


def check_initializer(
    source: str,
    class_name: str,
    instance: str | Path,
    *,
    seed: int = 0,
    repo_root: str | Path = ".",
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Run a synthesized initializer in an isolated subprocess and judge feasibility.

    Generated code is untrusted, so it executes in a subprocess like the
    operator harness does. Returns a payload with ``ok``, ``feasible``,
    ``score`` and a ``diagnostic`` the synthesis loop can feed back to the model.
    """
    import json
    import subprocess
    import sys
    import tempfile

    payload = {
        "source": source,
        "class_name": class_name,
        "instance": str(instance),
        "repo_root": str(Path(repo_root).resolve()),
        "seed": seed,
    }

    with tempfile.TemporaryDirectory() as tmp:
        payload_path = Path(tmp) / "payload.json"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        runner_path = Path(tmp) / "runner.py"
        runner_path.write_text(_CHECK_RUNNER, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, str(runner_path), str(payload_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(repo_root).resolve()),
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"initializer check timed out after {timeout:.0f}s"}

    if completed.returncode != 0:
        return {
            "ok": False,
            "error": f"initializer runner exited {completed.returncode}\n{completed.stderr[-2000:]}",
        }

    try:
        data = json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {
            "ok": False,
            "error": f"unparseable runner output:\n{completed.stdout[-2000:]}",
        }
    return data


_CHECK_RUNNER = r'''
import json, sys, traceback
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
sys.path.insert(0, payload["repo_root"])

from large_neighborhood_search.lns import read_problem_for_lns, OptDSLEvaluator
from large_neighborhood_search.components import Initializer

source = payload["source"]
class_name = payload["class_name"]
namespace = {"__name__": "generated_initializer"}
exec(compile(source, "<generated_initializer>", "exec"), namespace)
initializer = namespace[class_name]()

try:
    problem_data, context = read_problem_for_lns(payload["instance"], random_seed=payload["seed"])
except Exception:
    print(json.dumps({"ok": False, "error": "read_problem_for_lns raised:\n" + traceback.format_exc()}))
    sys.exit(0)

evaluator = OptDSLEvaluator(problem_data)
context.extra["evaluator"] = evaluator
context.extra["penalty_base"] = evaluator.penalty_base

try:
    assignment = initializer.initialize(context)
except Exception:
    print(json.dumps({"ok": False, "error": "initialize() raised:\n" + traceback.format_exc()}))
    sys.exit(0)

if not isinstance(assignment, dict):
    print(json.dumps({"ok": False, "error": f"initialize() returned {type(assignment).__name__}, expected a dict"}))
    sys.exit(0)


def _locals_snapshot(frame):
    """Capture the integer loop/index variables of the failing frame, which
    tells the model *where* the assertion failed (e.g. period t=2, inv=3)."""
    snapshot = {}
    for k, v in (frame.f_locals or {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            snapshot[k] = v
        elif isinstance(v, bool):
            snapshot[k] = bool(v)
    return snapshot


def _failed_details(assignment_):
    """Which constraints raise on the assignment, with the failing line and
    the loop-variable values at the moment of the assertion."""
    rc = problem_data.parsed.runtime_constraints
    asts = problem_data.parsed.constraints
    details = []
    for name, fn in rc.items():
        node = asts.get(name)
        if node is None or not callable(fn):
            continue
        arg_names = [arg.arg for arg in node.args.args]
        if not all(a in assignment_ for a in arg_names):
            continue
        args = [assignment_[a] for a in arg_names]
        try:
            fn(*args)
        except AssertionError:
            tb = sys.exc_info()[2]
            frames = []
            while tb is not None:
                frames.append(tb.tb_frame)
                tb = tb.tb_next
            frame = frames[-1] if frames else None
            line_no = None
            if frame is not None:
                line_no = frame.f_lineno
            details.append({
                "constraint": name,
                "line": line_no,
                "at": _locals_snapshot(frame) if frame is not None else {},
            })
        except Exception as exc:  # noqa: BLE001 - report, not crash
            details.append({
                "constraint": name,
                "line": None,
                "error": f"{type(exc).__name__}: {exc}",
                "at": {},
            })
    return details


try:
    score = evaluator.evaluate(assignment, context)
    details = evaluator.evaluate_detailed(assignment, context)
    feasible = not details.failed_constraints
except Exception:
    print(json.dumps({"ok": False, "error": "evaluation raised:\n" + traceback.format_exc()}))
    sys.exit(0)

failed_details = [] if feasible else _failed_details(assignment)

print(json.dumps({
    "ok": True,
    "feasible": feasible,
    "score": float(score),
    "failed_constraints": int(details.failed_constraints),
    "failed_details": failed_details,
    "diagnostic": (
        f"score {score:g}, feasible={feasible}, "
        f"{int(details.failed_constraints)} constraint(s) failed"
        + (
            ": " + ", ".join(
                d["constraint"] + (f"@{d['at']}" if d.get("at") else "")
                for d in failed_details
            )
            if failed_details
            else ""
        )
    ),
}))
'''


#: Backwards-friendly alias.
_initializer = InitializerArtifact


def write_initializer(
    source: str,
    destination: str | Path,
    *,
    problem_stem: str,
) -> Path:
    """Persist a synthesized construction heuristic as a self-contained module.

    The source is written exactly as validated (it carries its own imports), so
    the file on disk is the code that was checked.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{problem_stem}_initializer.py"
    header = (
        f'"""Generated construction heuristic (initializer) for {problem_stem}.\n\n'
        f"Produced by the tuning loop and validated against the evaluator.\n"
        f'"""\n\n'
    )
    path.write_text(header + source.strip() + "\n", encoding="utf-8")
    return path


def load_initializer_file(path: str | Path, class_name: str | None = None) -> InitializerArtifact | None:
    """Load a persisted initializer module; ``None`` if missing or unusable."""
    path = Path(path)
    if not path.exists():
        return None
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    names = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(isinstance(b, ast.Name) and b.id == "Initializer" for b in node.bases)
    ]
    if class_name is None:
        class_name = names[0] if names else None
    if class_name is None or class_name not in names:
        return None
    return InitializerArtifact(source=source, class_name=class_name, path=path)


def discover_initializer(operator_dir: str | Path, problem_stem: str) -> InitializerArtifact | None:
    """Load a previously synthesized initializer for *problem_stem*, if any."""
    return load_initializer_file(Path(operator_dir) / f"{problem_stem}_initializer.py")


#: Backwards-friendly alias.
_initializer = InitializerArtifact
