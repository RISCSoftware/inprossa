import * as vscode from 'vscode';
import { complete, describeModelError, resolveModel } from './model';
import { runPythonJson } from './python';

/**
 * LLM-assisted constraint authoring.
 *
 * The model never writes to the file. The flow is:
 *
 *   prompt -> JSON proposal -> static validation -> diff preview -> user accepts
 *
 * Validation happens in Python (`optdsl_tooling`), not here, so the same gate
 * protects the CLI and CI. The extension only orchestrates.
 */

interface ConstraintProposal {
  rationale: string;
  constraints: Array<{
    name: string;
    code: string;
    invocation: string;
  }>;
  assumptions?: string[];
  risks?: string[];
}

interface ValidationResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
  /** Fraction of random assignments that violate the constraint. */
  violationRate?: number;
  vacuous?: boolean;
  overConstrained?: boolean;
}

const SYSTEM_PROMPT = `You write constraints for OptDSL, a Python-syntax optimization modelling language.

OptDSL facts you must respect:
- A constraint is a top-level \`def\` whose body contains \`assert\` statements.
- Loops are unrolled at translation time, so \`for i in range(N)\` is fine.
- Decision variables are declared as bare annotations, e.g. \`x: DSList(N, DSInt(0, 5))\`.
- Constants are UPPER_CASE module-level values.
- Available builtins: sum, min, max, abs, len, any, all, range, enumerate, zip.
- Comparisons and boolean operators are Python's: ==, !=, <, <=, >, >=, and, or, not.
- There is no \`if\` expression inside an assert; use boolean operators instead.
- A constraint function must be invoked at top level to take effect.

Return ONLY a JSON object with this shape:
{
  "rationale": "one paragraph explaining the constraint",
  "constraints": [
    { "name": "snake_case_name", "code": "def name(...):\\n    ...", "invocation": "name(args)" }
  ],
  "assumptions": ["..."],
  "risks": ["..."]
}

Do not wrap the JSON in markdown fences.`;

export async function addConstraintCommand(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'optdsl') {
    void vscode.window.showWarningMessage('Open an OptDSL (.dsl) file first.');
    return;
  }

  const request = await vscode.window.showInputBox({
    title: 'Add a constraint',
    prompt: 'Describe the constraint in natural language',
    placeHolder: 'e.g. every item must be assigned to exactly one box',
    ignoreFocusOut: true,
  });

  if (!request) {
    return;
  }

  const model = await resolveModel();
  if (!model) {
    void vscode.window.showWarningMessage(
      'No language model available. Sign in to Copilot or configure a provider, then run "OptDSL: Select Language Model".'
    );
    return;
  }

  const document = editor.document;
  const source = document.getText();
  const selection = editor.selection.isEmpty ? undefined : document.getText(editor.selection);

  const analysis = await runPythonJson<Record<string, unknown>>('analyze', {
    source,
  });

  const userPrompt = [
    '## Current formulation',
    '```python',
    source,
    '```',
    selection ? `\n## Selected text\n\`\`\`python\n${selection}\n\`\`\`` : '',
    analysis ? `\n## Static analysis\n\`\`\`json\n${JSON.stringify(analysis, null, 2)}\n\`\`\`` : '',
    `\n## Requested constraint\n\n${request}`,
  ]
    .filter(Boolean)
    .join('\n');

  const proposal = await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: 'OptDSL: proposing a constraint…', cancellable: true },
    async (_progress, token) => {
      try {
        const text = await complete(
          model,
          [
            vscode.LanguageModelChatMessage.User(SYSTEM_PROMPT),
            vscode.LanguageModelChatMessage.User(userPrompt),
          ],
          token
        );
        return parseProposal(text);
      } catch (error) {
        void vscode.window.showErrorMessage(`OptDSL: ${describeModelError(error)}`);
        return undefined;
      }
    }
  );

  if (!proposal || proposal.constraints.length === 0) {
    return;
  }

  const validation = await runPythonJson<ValidationResult>('validateConstraint', {
    source,
    constraints: proposal.constraints,
  });

  if (!validation) {
    void vscode.window.showErrorMessage('OptDSL: constraint validation failed to run.');
    return;
  }

  // Check the specific failure modes before the generic one, so the user gets
  // an explanation rather than a bare "invalid".
  if (validation.vacuous) {
    void vscode.window.showWarningMessage(
      'OptDSL: the proposed constraint is never violated by random assignments, so it does not constrain anything. Not applied.'
    );
    return;
  }

  if (validation.overConstrained) {
    void vscode.window.showWarningMessage(
      'OptDSL: the proposed constraint is violated by every random assignment, which usually means a misread constant or index base. Not applied.'
    );
    return;
  }

  if (!validation.ok) {
    const detail = validation.errors.join('\n');
    void vscode.window.showErrorMessage(`OptDSL: the proposed constraint is invalid.\n${detail}`);
    return;
  }

  const accepted = await showProposalPreview(proposal, validation);
  if (!accepted) {
    return;
  }

  await applyProposal(editor, proposal);
}

function parseProposal(text: string): ConstraintProposal | undefined {
  const cleaned = text
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/```\s*$/, '')
    .trim();

  try {
    const parsed = JSON.parse(cleaned) as ConstraintProposal;
    if (!Array.isArray(parsed.constraints)) {
      throw new Error('missing "constraints" array');
    }
    return parsed;
  } catch (error) {
    void vscode.window.showErrorMessage(
      `OptDSL: could not parse the model response as JSON (${(error as Error).message}).`
    );
    return undefined;
  }
}

async function showProposalPreview(
  proposal: ConstraintProposal,
  validation: ValidationResult
): Promise<boolean> {
  const lines: string[] = [];
  lines.push(`# ${proposal.rationale}`, '');

  for (const constraint of proposal.constraints) {
    lines.push(constraint.code, '', constraint.invocation, '');
  }

  if (proposal.assumptions?.length) {
    lines.push('# Assumptions:');
    for (const assumption of proposal.assumptions) {
      lines.push(`#   - ${assumption}`);
    }
    lines.push('');
  }

  if (proposal.risks?.length) {
    lines.push('# Risks:');
    for (const risk of proposal.risks) {
      lines.push(`#   - ${risk}`);
    }
    lines.push('');
  }

  if (validation.warnings.length) {
    lines.push('# Warnings:');
    for (const warning of validation.warnings) {
      lines.push(`#   - ${warning}`);
    }
    lines.push('');
  }

  if (validation.violationRate !== undefined) {
    lines.push(
      `# Violated by ${(validation.violationRate * 100).toFixed(1)}% of random assignments.`,
      ''
    );
  }

  const preview = await vscode.workspace.openTextDocument({
    language: 'optdsl',
    content: lines.join('\n'),
  });

  await vscode.window.showTextDocument(preview, { preview: true, viewColumn: vscode.ViewColumn.Beside });

  const choice = await vscode.window.showInformationMessage(
    'Apply this constraint to the formulation?',
    { modal: true },
    'Apply',
    'Discard'
  );

  await vscode.commands.executeCommand('workbench.action.closeActiveEditor');

  return choice === 'Apply';
}

async function applyProposal(
  editor: vscode.TextEditor,
  proposal: ConstraintProposal
): Promise<void> {
  const document = editor.document;
  const insertAt = findInsertionPoint(document);

  const block = [
    '',
    ...proposal.constraints.flatMap((constraint) => [
      constraint.code,
      '',
      constraint.invocation,
      '',
    ]),
  ].join('\n');

  const edit = new vscode.WorkspaceEdit();
  edit.insert(document.uri, insertAt, block);
  await vscode.workspace.applyEdit(edit);
  await document.save();
}

/**
 * Insert new predicates after the last existing predicate, so the objective
 * and its `minimize(...)` call stay at the bottom of the file.
 */
function findInsertionPoint(document: vscode.TextDocument): vscode.Position {
  let lastPredicateEnd = -1;

  for (let line = 0; line < document.lineCount; line += 1) {
    const text = document.lineAt(line).text;
    if (/^\s*def\s+\w+\s*\(/.test(text)) {
      lastPredicateEnd = line;
    }
  }

  if (lastPredicateEnd < 0) {
    return new vscode.Position(document.lineCount, 0);
  }

  // Walk forward past the predicate body.
  let line = lastPredicateEnd + 1;
  while (line < document.lineCount) {
    const text = document.lineAt(line).text;
    if (text.trim() !== '' && !/^\s/.test(text)) {
      break;
    }
    line += 1;
  }

  return new vscode.Position(line, 0);
}
