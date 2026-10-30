import * as vscode from 'vscode';
import { complete, describeModelError, resolveModel } from './model';
import { runPythonJson, runScript } from './python';

/**
 * Operator synthesis from the editor.
 *
 * The model proposes classes; the Python harness decides whether they are any
 * good. The extension never accepts an operator on the model's word alone.
 *
 * A neighborhood needs both halves, so this generates a destroy *and* a repair
 * from one description rather than asking the user to pick. Each half is
 * validated independently: a good destroy with a broken repair is still a
 * broken neighborhood, and the user needs to know which half failed.
 */

const DESTROY_PROMPT = `You write DESTROY operators for a large neighborhood search (LNS) engine.

A destroy operator removes part of a solution to create a neighborhood.

Rules:
1. Output ONE Python class and nothing else. No prose, no markdown fences.
2. Subclass DestroyOperator and implement destroy(self, assignment, context).
3. Decorate with @dataclass; every hyperparameter is a field with a default.
4. Import only from: math, random, dataclasses, typing, collections, itertools,
   heapq, large_neighborhood_search.components, large_neighborhood_search.models,
   large_neighborhood_search._utils.
5. Never call eval, exec, open, __import__, or touch dunder attributes.
6. Read randomness from context.extra["rng"]; never use the global random module.
7. Read decision metadata from context.extra: decision_keys, decision_domains,
   keys_by_variable, problem_data.
8. Use set_decision_value(assignment, key, None) to unassign a decision.
9. If the required constants or variables are missing, return the assignment unchanged.
10. Be fast: roughly 1 ms per call for instances with a few thousand decisions.
11. Clear between 5% and 60% of decisions. Clearing everything is a restart, not
    a neighborhood; clearing almost nothing explores nothing.`;

const REPAIR_PROMPT = `You write REPAIR operators for a large neighborhood search (LNS) engine.

A repair operator rebuilds a partial solution after a destroy operator has
unassigned some decisions.

Rules:
1. Output ONE Python class and nothing else. No prose, no markdown fences.
2. Subclass RepairOperator and implement repair(self, partial_assignment, context).
3. Decorate with @dataclass; every hyperparameter is a field with a default.
4. Import only from: math, random, dataclasses, typing, collections, itertools,
   heapq, large_neighborhood_search.components, large_neighborhood_search.models,
   large_neighborhood_search._utils.
5. Never call eval, exec, open, __import__, or touch dunder attributes.
6. Read randomness from context.extra["rng"]; never use the global random module.
7. Read decision metadata from context.extra: decision_keys, decision_domains,
   keys_by_variable, problem_data.
8. Use get_decision_value(assignment, key) to read a decision and
   set_decision_value(assignment, key, value) to assign one.
9. Only fill decisions that are None; never overwrite an assigned decision.
10. If the required constants or variables are missing, return the assignment unchanged.
11. Be fast: roughly 1 ms per call for instances with a few thousand decisions.
12. Aim for feasible completions. A repair that produces infeasible solutions
    more than half the time is rejected.`;

interface SynthesisVerdict {
  accepted: boolean;
  reasons: string[];
  static?: { ok: boolean; errors: string[]; class_name?: string };
  metrics?: {
    ok: boolean;
    error?: string;
    feasible_rate: number;
    mean_cleared_fraction: number;
    mean_completion_fraction: number;
    improvement: number;
    baseline_score: number | null;
    best_score: number | null;
    iterations: number;
    elapsed_seconds: number;
  };
}

interface HalfResult {
  kind: 'destroy' | 'repair';
  code: string;
  verdict: SynthesisVerdict;
}

export async function synthesizeOperatorCommand(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'optdsl') {
    void vscode.window.showWarningMessage('Open an OptDSL (.dsl) file first.');
    return;
  }

  const description = await vscode.window.showInputBox({
    title: 'Synthesize LNS neighborhood',
    prompt: 'Describe the neighborhood. A destroy and a repair operator will both be generated.',
    placeHolder: 'e.g. remove a geographic cluster of nearby customers',
    ignoreFocusOut: true,
  });
  if (!description) {
    return;
  }

  const model = await resolveModel();
  if (!model) {
    void vscode.window.showWarningMessage('No language model available.');
    return;
  }

  const document = editor.document;
  const source = document.getText();
  const config = vscode.workspace.getConfiguration('optdsl.synthesis');

  const analysis = await runPythonJson<Record<string, unknown>>('analyze', { source });
  const contextBlock = [
    '## Formulation',
    '```python',
    source,
    '```',
    analysis ? `\n## Static analysis\n\`\`\`json\n${JSON.stringify(analysis, null, 2)}\n\`\`\`` : '',
    `\n## Requested neighborhood\n\n${description}`,
  ]
    .filter(Boolean)
    .join('\n');

  const maxAttempts = config.get<number>('maxAttempts', 3);
  const iterations = config.get<number>('iterations', 200);
  const requireImprovement = config.get<boolean>('requireImprovement', true);

  // Generate both halves. They are independent, so a failure in one does not
  // discard the other.
  const destroy = await synthesizeHalf(
    'destroy',
    DESTROY_PROMPT,
    contextBlock,
    model,
    document.uri.fsPath,
    { maxAttempts, iterations, requireImprovement }
  );

  const repair = await synthesizeHalf(
    'repair',
    REPAIR_PROMPT,
    contextBlock,
    model,
    document.uri.fsPath,
    { maxAttempts, iterations, requireImprovement }
  );

  await reportNeighborhood(destroy, repair);
}

async function synthesizeHalf(
  kind: 'destroy' | 'repair',
  systemPrompt: string,
  contextBlock: string,
  model: vscode.LanguageModelChat,
  instancePath: string,
  options: { maxAttempts: number; iterations: number; requireImprovement: boolean }
): Promise<HalfResult | undefined> {
  const messages: vscode.LanguageModelChatMessage[] = [
    vscode.LanguageModelChatMessage.User(systemPrompt),
    vscode.LanguageModelChatMessage.User(contextBlock),
  ];

  for (let attempt = 1; attempt <= options.maxAttempts; attempt += 1) {
    const result = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `OptDSL: ${kind} operator (attempt ${attempt}/${options.maxAttempts})…`,
        cancellable: true,
      },
      async (progress, token) => {
        let code: string;
        try {
          code = extractCode(await complete(model, messages, token));
        } catch (error) {
          void vscode.window.showErrorMessage(`OptDSL: ${describeModelError(error)}`);
          return undefined;
        }

        progress.report({ message: 'validating…' });

        const verdict = await runPythonJson<SynthesisVerdict>('synthesizeOperator', {
          source: code,
          kind,
          instance: instancePath,
          iterations: options.iterations,
          requireImprovement: options.requireImprovement,
        });

        return verdict ? { kind, code, verdict } : undefined;
      }
    );

    if (!result) {
      return undefined;
    }

    if (result.verdict.accepted) {
      return result;
    }

    messages.push(vscode.LanguageModelChatMessage.Assistant(result.code));
    messages.push(vscode.LanguageModelChatMessage.User(feedback(result.verdict)));
  }

  return undefined;
}

async function reportNeighborhood(
  destroy: HalfResult | undefined,
  repair: HalfResult | undefined
): Promise<void> {
  const accepted = [destroy, repair].filter(
    (half): half is HalfResult => half !== undefined && half.verdict.accepted
  );

  if (accepted.length === 0) {
    void vscode.window.showWarningMessage(
      'OptDSL: neither the destroy nor the repair operator passed validation. See the OptDSL output channel.'
    );
    return;
  }

  const summary = accepted
    .map((half) => `${half.kind}: ${describeMetrics(half.verdict)}`)
    .join('\n');

  const missing = (['destroy', 'repair'] as const).filter(
    (kind) => !accepted.some((half) => half.kind === kind)
  );

  const choice = await vscode.window.showInformationMessage(
    `Neighborhood accepted.\n${summary}` +
      (missing.length ? `\n\nNot accepted: ${missing.join(', ')}` : ''),
    { modal: true },
    'Open in Editor',
    'Save to problems/generated'
  );

  if (choice === 'Open in Editor') {
    const content = accepted.map((half) => half.code).join('\n\n\n');
    const document = await vscode.workspace.openTextDocument({ language: 'python', content });
    await vscode.window.showTextDocument(document, { preview: true });
  } else if (choice === 'Save to problems/generated') {
    await saveOperators(accepted);
  }
}

function describeMetrics(verdict: SynthesisVerdict): string {
  const metrics = verdict.metrics;
  if (!metrics) {
    return 'validated';
  }
  const parts = [
    `feasible ${(metrics.feasible_rate * 100).toFixed(0)}%`,
    `improvement ${metrics.improvement.toFixed(3)}`,
    `${metrics.elapsed_seconds.toFixed(2)}s`,
  ];
  if (metrics.mean_cleared_fraction > 0) {
    parts.splice(1, 0, `clears ${(metrics.mean_cleared_fraction * 100).toFixed(0)}%`);
  }
  if (metrics.mean_completion_fraction > 0) {
    parts.splice(1, 0, `restores ${(metrics.mean_completion_fraction * 100).toFixed(0)}%`);
  }
  return parts.join(', ');
}

async function saveOperators(halves: HalfResult[]): Promise<void> {
  const root =
    vscode.workspace.getConfiguration().get<string>('optdsl.repoRoot', '') ||
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!root) {
    void vscode.window.showErrorMessage('OptDSL: no workspace folder to save into.');
    return;
  }

  const directory = vscode.Uri.file(`${root}/large_neighborhood_search/problems/generated`);
  await vscode.workspace.fs.createDirectory(directory);

  const saved: string[] = [];
  for (const half of halves) {
    const name = snakeCase(half.verdict.static?.class_name ?? `generated_${half.kind}`);
    const target = vscode.Uri.joinPath(directory, `${name}.py`);
    await vscode.workspace.fs.writeFile(target, Buffer.from(half.code, 'utf8'));
    saved.push(target.fsPath);
  }

  void vscode.window.showInformationMessage(`Saved ${saved.length} operator(s):\n${saved.join('\n')}`);
}

function extractCode(response: string): string {
  const fenced = /```(?:python)?\s*([\s\S]*?)```/.exec(response);
  if (fenced) {
    return fenced[1].trim();
  }
  const lines = response.split('\n');
  const start = lines.findIndex((line) => /^\s*(import |from |@|class )/.test(line));
  return (start >= 0 ? lines.slice(start) : lines).join('\n').trim();
}

function feedback(verdict: SynthesisVerdict): string {
  const lines = ['That candidate was rejected. Fix these problems and try again:', ''];
  for (const reason of verdict.reasons) {
    lines.push(`- ${reason}`);
  }
  if (verdict.metrics?.ok) {
    const m = verdict.metrics;
    lines.push(
      '',
      'Measured behaviour:',
      `- feasible candidate rate: ${(m.feasible_rate * 100).toFixed(0)}%`,
      `- mean fraction of decisions cleared: ${(m.mean_cleared_fraction * 100).toFixed(1)}%`,
      `- mean fraction of destroyed decisions restored: ${(m.mean_completion_fraction * 100).toFixed(1)}%`,
      `- baseline score: ${m.baseline_score}`,
      `- best score reached: ${m.best_score}`,
      `- iterations: ${m.iterations}`,
      `- wall clock: ${m.elapsed_seconds.toFixed(2)}s`
    );
  }
  lines.push('', 'Return only the corrected Python class.');
  return lines.join('\n');
}

function snakeCase(name: string): string {
  return name.replace(/(?<!^)(?=[A-Z])/g, '_').toLowerCase();
}

// ---------------------------------------------------------------------------
// other commands
// ---------------------------------------------------------------------------

export async function explainModelCommand(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'optdsl') {
    return;
  }

  const model = await resolveModel();
  if (!model) {
    void vscode.window.showWarningMessage('No language model available.');
    return;
  }

  const source = editor.document.getText();
  const analysis = await runPythonJson<Record<string, unknown>>('analyze', { source });

  const text = await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: 'OptDSL: explaining…', cancellable: true },
    async (_progress, token) => {
      try {
        return await complete(
          model,
          [
            vscode.LanguageModelChatMessage.User(
              'Explain this OptDSL optimization formulation to an operations researcher. ' +
                'Cover: what is being decided, what the constraints enforce, what the objective ' +
                'minimises, and any modelling risks you notice. Be concise and concrete.'
            ),
            vscode.LanguageModelChatMessage.User(
              `\`\`\`python\n${source}\n\`\`\`\n\nStatic analysis:\n\`\`\`json\n${JSON.stringify(analysis, null, 2)}\n\`\`\``
            ),
          ],
          token
        );
      } catch (error) {
        void vscode.window.showErrorMessage(`OptDSL: ${describeModelError(error)}`);
        return undefined;
      }
    }
  );

  if (text) {
    const document = await vscode.workspace.openTextDocument({ language: 'markdown', content: text });
    await vscode.window.showTextDocument(document, { preview: true, viewColumn: vscode.ViewColumn.Beside });
  }
}

export async function showAnalysisCommand(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'optdsl') {
    return;
  }

  const analysis = await runPythonJson<Record<string, unknown>>('analyze', {
    source: editor.document.getText(),
  });
  if (!analysis) {
    return;
  }

  const document = await vscode.workspace.openTextDocument({
    language: 'json',
    content: JSON.stringify(analysis, null, 2),
  });
  await vscode.window.showTextDocument(document, { preview: true, viewColumn: vscode.ViewColumn.Beside });
}

export function solveCommand(): void {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'optdsl') {
    void vscode.window.showWarningMessage('Open an OptDSL (.dsl) file first.');
    return;
  }
  // run_minizinc.py is the supported entry point. `python -m
  // src.optdsl.solver.DSL_solver` does not work: that module has no __main__.
  runScript('run_minizinc.py', [editor.document.uri.fsPath, '--timelimit', '30'], 'OptDSL Solve');
}

export function runLnsCommand(): void {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'optdsl') {
    void vscode.window.showWarningMessage('Open an OptDSL (.dsl) file first.');
    return;
  }
  runScript('run_lns.py', [editor.document.uri.fsPath, '--max-iterations', '500'], 'OptDSL LNS');
}
