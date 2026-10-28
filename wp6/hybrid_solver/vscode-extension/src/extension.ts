import * as vscode from 'vscode';
import * as path from 'path';
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
} from 'vscode-languageclient/node';

import { addConstraintCommand } from './constraints';
import { selectModelCommand } from './model';
import {
  explainModelCommand,
  runLnsCommand,
  showAnalysisCommand,
  solveCommand,
  synthesizeOperatorCommand,
} from './operators';
import { configure, resolvePythonPath, resolveRepoRoot } from './python';

let client: LanguageClient | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const output = vscode.window.createOutputChannel('OptDSL');
  context.subscriptions.push(output);
  output.appendLine(`OptDSL activating (extension ${context.extension.packageJSON.version})`);

  // Anchor path resolution to the extension's own location. An Extension
  // Development Host opened with only --extensionDevelopmentPath has no
  // workspace folder, so workspaceFolders/process.cwd() are both wrong.
  configure(context.extensionPath);
  output.appendLine(`extension path: ${context.extensionPath}`);

  // Register commands FIRST. If the language client throws during
  // construction, the commands must still work — they shell out to Python
  // directly and do not need the server.
  const register = (id: string, handler: (...args: never[]) => unknown) =>
    context.subscriptions.push(vscode.commands.registerCommand(id, handler));

  register('optdsl.addConstraint', addConstraintCommand);
  register('optdsl.explainModel', explainModelCommand);
  register('optdsl.synthesizeOperator', synthesizeOperatorCommand);
  register('optdsl.showAnalysis', showAnalysisCommand);
  register('optdsl.selectModel', selectModelCommand);
  register('optdsl.solve', solveCommand);
  register('optdsl.runLns', runLnsCommand);

  try {
    client = createClient();
    context.subscriptions.push(client);

    // Do not await: a slow or failing server must not block activation.
    client.start().catch((error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      output.appendLine(`language server failed to start: ${message}`);
      void vscode.window.showErrorMessage(
        `OptDSL: the language server failed to start. ${message}`
      );
    });
  } catch (error) {
    // A throw here would abort activation and make the extension look dead.
    const message = error instanceof Error ? error.message : String(error);
    output.appendLine(`language client construction failed: ${message}`);
    void vscode.window.showErrorMessage(`OptDSL: ${message}`);
  }

  output.appendLine('OptDSL activated');
}

export async function deactivate(): Promise<void> {
  if (client) {
    await client.stop();
    client = undefined;
  }
}

function createClient(): LanguageClient {
  const config = vscode.workspace.getConfiguration('optdsl');
  // Use the same resolution as the bridge: the venv interpreter and the
  // extension-anchored repo root. Duplicating this logic here is what let the
  // server and the bridge disagree about which Python to run.
  const python = resolvePythonPath();
  const repoRoot = resolveRepoRoot();

  const serverOptions: ServerOptions = {
    command: python,
    args: ['-m', 'optdsl_lsp', ...config.get<string[]>('serverArgs', [])],
    options: {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONPATH: [
          repoRoot,
          path.join(repoRoot, 'optdsl-lsp'),
          path.join(repoRoot, 'operator-synthesis'),
          process.env.PYTHONPATH ?? '',
        ]
          .filter(Boolean)
          .join(path.delimiter),
        PYTHONIOENCODING: 'utf-8',
      },
    },
    transport: TransportKind.stdio,
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: 'file', language: 'optdsl' }],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher('**/*.dsl'),
    },
    outputChannelName: 'OptDSL',
  };

  return new LanguageClient('optdsl', 'OptDSL Language Server', serverOptions, clientOptions);
}
