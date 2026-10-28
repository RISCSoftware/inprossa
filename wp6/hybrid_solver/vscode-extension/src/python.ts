import * as vscode from 'vscode';
import { execFile } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Bridge to the Python tooling.
 *
 * Every semantic operation (analysis, validation, solving, synthesis) lives in
 * Python. The extension shells out rather than reimplementing any of it, so
 * there is exactly one implementation of "what does this formulation mean".
 *
 * All calls go through `optdsl_tooling.bridge`, a small JSON-in/JSON-out entry
 * point, which keeps the argument passing trivial and avoids quoting bugs.
 */

export interface BridgeRequest {
  command: string;
  [key: string]: unknown;
}

/**
 * Absolute path of the extension directory, set during activation.
 *
 * This is the reliable anchor for locating the repository. `workspaceFolders`
 * is NOT reliable: an Extension Development Host launched with only
 * `--extensionDevelopmentPath` opens an empty window with no folder, so
 * `workspaceFolders` is undefined and `process.cwd()` points at the VS Code
 * installation directory.
 */
let extensionRoot: string | undefined;

export function configure(extensionPath: string): void {
  extensionRoot = extensionPath;
}

function repoRoot(): string {
  const configured = vscode.workspace.getConfiguration().get<string>('optdsl.repoRoot', '').trim();
  if (configured) {
    return configured;
  }

  // The extension lives at <repo>/vscode-extension, so its parent is the repo.
  // This is the most reliable anchor: it does not depend on which folder the
  // user happened to open.
  const anchored = extensionRoot ? path.dirname(extensionRoot) : undefined;
  if (anchored && looksLikeRepo(anchored)) {
    return anchored;
  }

  // Fall back to the workspace folder, but only if it actually contains the
  // tooling. Opening `problem_instances` as the workspace must not make that
  // directory look like the repo root.
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (folder && looksLikeRepo(folder.uri.fsPath)) {
    return folder.uri.fsPath;
  }

  return anchored ?? folder?.uri.fsPath ?? process.cwd();
}

function looksLikeRepo(candidate: string): boolean {
  return fs.existsSync(path.join(candidate, 'optdsl_tooling'));
}

/** Public accessor so the language client uses the same resolution rules. */
export function resolveRepoRoot(): string {
  return repoRoot();
}

/** Public accessor so the language client uses the same resolution rules. */
export function resolvePythonPath(): string {
  return pythonPath();
}

function pythonPath(): string {
  const configured = vscode.workspace.getConfiguration().get<string>('optdsl.pythonPath', '').trim();
  if (configured) {
    return configured;
  }

  // Prefer the repository's own virtualenv. The project requires Python 3.11
  // and the venv is where minizinc/pygls are installed; falling back to
  // whatever `python` happens to be on PATH picks up an unrelated interpreter.
  const venv = venvPython(repoRoot());
  if (venv) {
    return venv;
  }

  const interpreter = vscode.workspace
    .getConfiguration('python')
    .get<string>('defaultInterpreterPath', '');
  if (interpreter) {
    return interpreter;
  }

  return process.platform === 'win32' ? 'python' : 'python3';
}

function venvPython(root: string): string | undefined {
  const candidate =
    process.platform === 'win32'
      ? path.join(root, '.venv', 'Scripts', 'python.exe')
      : path.join(root, '.venv', 'bin', 'python');

  return fs.existsSync(candidate) ? candidate : undefined;
}

function bridgeEnv(): NodeJS.ProcessEnv {
  const root = repoRoot();
  const extraPaths = [
    root,
    path.join(root, 'optdsl-lsp'),
    path.join(root, 'operator-synthesis'),
  ].join(path.delimiter);

  const existing = process.env.PYTHONPATH;
  return {
    ...process.env,
    PYTHONPATH: existing ? `${extraPaths}${path.delimiter}${existing}` : extraPaths,
    PYTHONIOENCODING: 'utf-8',
  };
}

/**
 * Run a bridge command and parse its JSON output.
 *
 * Returns `undefined` (after showing an error) rather than throwing, so command
 * handlers stay linear.
 */
export async function runPythonJson<T>(
  command: string,
  payload: Record<string, unknown>,
  options: { timeoutMs?: number; silent?: boolean } = {}
): Promise<T | undefined> {
  const request: BridgeRequest = { command, ...payload };
  const root = repoRoot();

  return new Promise<T | undefined>((resolve) => {
    execFile(
      pythonPath(),
      ['-m', 'optdsl_tooling.bridge'],
      {
        cwd: root,
        env: bridgeEnv(),
        timeout: options.timeoutMs ?? 120_000,
        maxBuffer: 32 * 1024 * 1024,
      },
      (error, stdout, stderr) => {
        if (error) {
          if (!options.silent) {
            const detail = (stderr || error.message).trim().split('\n').slice(-8).join('\n');
            void vscode.window.showErrorMessage(
              `OptDSL: ${command} failed.\n${detail}\n\n${_diagnostics()}`
            );
          }
          resolve(undefined);
          return;
        }

        try {
          resolve(JSON.parse(stdout) as T);
        } catch {
          if (!options.silent) {
            void vscode.window.showErrorMessage(
              `OptDSL: ${command} returned unparseable output.\n${stdout.slice(0, 500)}`
            );
          }
          resolve(undefined);
        }
      }
    ).stdin?.end(JSON.stringify(request));
  });
}

/**
 * Run a repository script in a terminal, for long-running work the user should
 * see. PYTHONPATH is passed through the terminal's environment rather than a
 * shell-specific `$env:` prefix, so this works in PowerShell, cmd, and bash.
 */
export function runScript(script: string, args: string[], name: string): void {
  const root = repoRoot();
  const terminal = vscode.window.createTerminal({
    name,
    cwd: root,
    env: bridgeEnv(),
  });

  terminal.show();
  terminal.sendText([pythonPath(), script, ...args].map(quote).join(' '));
}

function quote(value: string): string {
  return /[\s"]/.test(value) ? `"${value.replace(/"/g, '\\"')}"` : value;
}

/**
 * Describe the interpreter and paths in use, so a failure is diagnosable
 * without opening a terminal.
 */
function _diagnostics(): string {
  const root = repoRoot();
  const python = pythonPath();
  const tooling = path.join(root, 'optdsl_tooling');
  const lines = [
    `interpreter: ${python}`,
    `repo root:   ${root}`,
    `tooling:     ${tooling} ${fs.existsSync(tooling) ? '(found)' : '(MISSING)'}`,
  ];
  if (!fs.existsSync(tooling)) {
    lines.push(
      'Set "optdsl.repoRoot" to the hybrid_solver directory, or open that folder as the workspace.'
    );
  }
  return lines.join('\n');
}
