"""Tests for the extension's Python interpreter and repo-root resolution.

These mirror the logic in ``vscode-extension/src/python.ts``. The bug they guard
against: an Extension Development Host launched with only
``--extensionDevelopmentPath`` has no workspace folder, so ``workspaceFolders``
is undefined and ``process.cwd()`` points at the VS Code installation
directory. Falling back to either produced a ``ModuleNotFoundError`` for
``optdsl_tooling``.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_venv_interpreter_exists() -> None:
    """The repo venv must exist; the extension prefers it over PATH."""
    if sys.platform == "win32":
        candidate = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = REPO_ROOT / ".venv" / "bin" / "python"
    assert candidate.exists(), f"expected a virtualenv at {candidate}"


def test_venv_has_tooling_dependencies() -> None:
    """The venv must have the packages the bridge and server import."""
    import importlib.util

    for module in ("pygls", "lsprotocol", "minizinc"):
        assert importlib.util.find_spec(module) is not None, f"{module} is not installed"


def test_repo_root_contains_tooling() -> None:
    """The extension derives the repo root as the parent of its own directory."""
    extension_dir = REPO_ROOT / "vscode-extension"
    assert extension_dir.is_dir()

    derived_root = extension_dir.parent
    assert (derived_root / "optdsl_tooling").is_dir()
    assert (derived_root / "optdsl-lsp").is_dir()
    assert (derived_root / "operator-synthesis").is_dir()


def test_subfolder_is_not_mistaken_for_repo_root() -> None:
    """A workspace folder without the tooling must not be used as the repo root.

    The extension validates a candidate root by checking for `optdsl_tooling`.
    Opening `problem_instances` as the workspace must not make it look like the
    repo root, or every bridge call fails with ModuleNotFoundError.
    """
    for subfolder in ("problem_instances", "vscode-extension", "test"):
        candidate = REPO_ROOT / subfolder
        assert candidate.is_dir(), candidate
        assert not (candidate / "optdsl_tooling").is_dir(), (
            f"{subfolder} must not look like the repo root"
        )


def test_launch_config_opens_a_folder() -> None:
    """The dev host must be given a folder, or it opens an empty window."""
    import json
    import re

    text = (REPO_ROOT / ".vscode" / "launch.json").read_text(encoding="utf-8")
    launch = json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE))

    for configuration in launch["configurations"]:
        args = configuration.get("args", [])
        assert any("--extensionDevelopmentPath" in arg for arg in args), configuration["name"]
        # Every config must pass a folder argument in addition to the extension path.
        folders = [arg for arg in args if not arg.startswith("--")]
        assert folders, f"{configuration['name']} passes no folder argument"


def test_bridge_importable_from_repo_root() -> None:
    """`python -m optdsl_tooling.bridge` must resolve with the repo root on the path."""
    import subprocess

    completed = subprocess.run(
        [sys.executable, "-c", "import optdsl_tooling.bridge; print('ok')"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONIOENCODING": "utf-8",
        },
    )
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout


def test_extension_manifest_points_at_compiled_entry() -> None:
    """`main` must exist, or activation fails with no useful message."""
    import json

    manifest = json.loads((REPO_ROOT / "vscode-extension" / "package.json").read_text(encoding="utf-8"))
    main = manifest["main"].lstrip("./")
    assert (REPO_ROOT / "vscode-extension" / main).exists(), f"{main} is missing; run npm run compile"


def test_grammar_does_not_self_reference() -> None:
    """A grammar that includes its own scope makes the tokenizer recurse forever."""
    import json

    grammar = json.loads(
        (REPO_ROOT / "vscode-extension" / "syntaxes" / "optdsl.tmLanguage.json").read_text(
            encoding="utf-8"
        )
    )
    scope = grammar["scopeName"]
    includes = [pattern["include"] for pattern in grammar["patterns"] if "include" in pattern]
    assert scope not in includes, f"grammar {scope} includes itself"


def test_launch_task_label_resolves() -> None:
    """`preLaunchTask` must match a task label, or the launch stalls."""
    import json
    import re

    def load_jsonc(path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
        return json.loads(text)

    launch = load_jsonc(REPO_ROOT / ".vscode" / "launch.json")
    tasks = load_jsonc(REPO_ROOT / ".vscode" / "tasks.json")
    labels = {task["label"] for task in tasks["tasks"]}

    for configuration in launch["configurations"]:
        pre_launch = configuration.get("preLaunchTask")
        if pre_launch is not None:
            assert pre_launch in labels, f"{pre_launch!r} is not a task label"
