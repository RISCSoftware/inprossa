"""End-to-end LSP handshake test.

Starts the real server over stdio and drives a minimal session: initialize,
didOpen, then assert diagnostics come back. This catches the failure mode where
the extension host hangs because the server never answers `initialize`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _frame(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _read_message(stream) -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        decoded = line.decode("ascii").strip()
        if not decoded:
            break
        key, _, value = decoded.partition(":")
        headers[key.strip().lower()] = value.strip()

    length = int(headers.get("content-length", "0"))
    if length == 0:
        return None
    return json.loads(stream.read(length))


def test_server_accepts_stdio_flag() -> None:
    """`vscode-languageclient` appends `--stdio` unconditionally.

    If the server rejects it, the client crash-loops with
    "unrecognized arguments: --stdio" and never connects.
    """
    completed = subprocess.run(
        [sys.executable, "-m", "optdsl_lsp", "--stdio", "--version"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            **__import__("os").environ,
            "PYTHONPATH": f"{REPO_ROOT}{__import__('os').pathsep}{REPO_ROOT / 'optdsl-lsp'}",
            "PYTHONIOENCODING": "utf-8",
        },
    )
    assert completed.returncode == 0, completed.stderr
    assert "optdsl-lsp" in completed.stdout


def test_server_accepts_node_ipc_flag() -> None:
    """The client may pass `--node-ipc`; it must not be a hard error."""
    completed = subprocess.run(
        [sys.executable, "-m", "optdsl_lsp", "--node-ipc", "--version"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={
            **__import__("os").environ,
            "PYTHONPATH": f"{REPO_ROOT}{__import__('os').pathsep}{REPO_ROOT / 'optdsl-lsp'}",
            "PYTHONIOENCODING": "utf-8",
        },
    )
    assert completed.returncode == 0, completed.stderr


def test_server_completes_initialize_handshake() -> None:
    """The server must answer `initialize`; otherwise the editor hangs."""
    process = subprocess.Popen(
        [sys.executable, "-m", "optdsl_lsp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        env={
            **__import__("os").environ,
            "PYTHONPATH": f"{REPO_ROOT}{__import__('os').pathsep}{REPO_ROOT / 'optdsl-lsp'}",
            "PYTHONIOENCODING": "utf-8",
        },
    )

    try:
        assert process.stdin is not None and process.stdout is not None

        process.stdin.write(
            _frame(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "processId": None,
                        "rootUri": REPO_ROOT.as_uri(),
                        "capabilities": {},
                    },
                }
            )
        )
        process.stdin.flush()

        response = _read_message(process.stdout)
        assert response is not None, "server closed the stream instead of replying"
        assert response.get("id") == 1
        assert "result" in response, response

        capabilities = response["result"]["capabilities"]
        assert capabilities["hoverProvider"] is True
        assert capabilities["completionProvider"] is not None
        assert capabilities["textDocumentSync"] is not None

        # Shut down cleanly so the test does not leak a process.
        process.stdin.write(
            _frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None})
        )
        process.stdin.write(_frame({"jsonrpc": "2.0", "method": "exit", "params": None}))
        process.stdin.flush()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()


def test_server_publishes_diagnostics_on_open() -> None:
    """Opening a document must produce diagnostics, not silence."""
    process = subprocess.Popen(
        [sys.executable, "-m", "optdsl_lsp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        env={
            **__import__("os").environ,
            "PYTHONPATH": f"{REPO_ROOT}{__import__('os').pathsep}{REPO_ROOT / 'optdsl-lsp'}",
            "PYTHONIOENCODING": "utf-8",
        },
    )

    try:
        assert process.stdin is not None and process.stdout is not None

        process.stdin.write(
            _frame(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"processId": None, "rootUri": REPO_ROOT.as_uri(), "capabilities": {}},
                }
            )
        )
        process.stdin.flush()
        assert _read_message(process.stdout) is not None

        process.stdin.write(
            _frame({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        )

        uri = "file:///broken.dsl"
        process.stdin.write(
            _frame(
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": uri,
                            "languageId": "optdsl",
                            "version": 1,
                            "text": "x: DSInt()\nminimize(x)\n",
                        }
                    },
                }
            )
        )
        process.stdin.flush()

        # Expect a publishDiagnostics notification mentioning the unbounded domain.
        for _ in range(10):
            message = _read_message(process.stdout)
            if message is None:
                break
            if message.get("method") == "textDocument/publishDiagnostics":
                diagnostics = message["params"]["diagnostics"]
                codes = {d.get("code") for d in diagnostics}
                assert "unbounded-domain" in codes, codes
                break
        else:
            raise AssertionError("no publishDiagnostics notification received")

        process.stdin.write(
            _frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None})
        )
        process.stdin.write(_frame({"jsonrpc": "2.0", "method": "exit", "params": None}))
        process.stdin.flush()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
