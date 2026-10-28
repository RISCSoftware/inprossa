# OptDSL tooling

Editor support, LLM-assisted constraint authoring, and LNS operator synthesis for
OptDSL formulations.

## Why this is not a parser project

OptDSL files are syntactically valid Python and are parsed with `ast.parse` in
two places: the MiniZinc translator (`src/optdsl/translator/Objects/MiniZincTranslator.py`)
and the LNS importer (`large_neighborhood_search/importer.py`). There is no
grammar, no lexer, and no parser generator.

That means the language server is a *semantic* layer over Python's AST, not a
language implementation. The work is in the symbol table, the diagnostics, and
the validation harness — not in parsing.

## Layout

```text
optdsl_tooling/          shared analysis core (no editor dependency)
  analysis.py            ModuleIndex: symbol table + decision indices
  diagnostics.py         rule engine
  fingerprint.py         problem-class detection
  positions.py           ast byte offsets -> LSP UTF-16 positions
  constraint_validation.py  vacuity / over-constraint checks
  bridge.py              JSON-in/JSON-out entry point for the extension

optdsl-lsp/              pygls language server (thin protocol adapter)
  optdsl_lsp/server.py

operator-synthesis/      operator generation + validation harness
  operator_synthesis/harness.py     the quality gate
  operator_synthesis/prompts.py     prompt construction
  operator_synthesis/synthesize.py  propose/validate/retry loop
  operator_synthesis/cli.py

optdsl_agent/            LLM harness over both backends
  config.py              AgentConfig, Budget, precedence resolution
  settings.py            stored profiles (model, endpoint, key)
  llm.py                 OpenAI-compatible client, tool calling, stub
  digest.py              shared prompt context
  session.py             model text, artifacts, budget counters
  lns_runner.py          run_lns + trajectory capture
  operator_loader.py     generated-operator loading
  tools.py               the tool registry
  agent.py               the agent loop
  commands.py            slash commands shared by REPL and TUI
  printers.py            problem-specific solution rendering
  tuning.py              gap measurement + bounded self-tuning
  tui.py                 optional full-screen UI (textual)
  cli.py                 subcommands and REPL

vscode-extension/        VS Code client
  src/extension.ts       LSP client + command registration
  src/model.ts           vscode.lm model selection
  src/constraints.ts     LLM constraint authoring
  src/operators.ts       operator synthesis
  src/python.ts          bridge to the Python tooling
```

## Setup

```powershell
uv pip install --python .venv\Scripts\python.exe "pygls>=2.1" "lsprotocol>=2023.0.1" pytest
```

Run the language server directly:

```powershell
$env:PYTHONPATH = "optdsl-lsp"
.\.venv\Scripts\python.exe -m optdsl_lsp
```

Build the extension:

```powershell
cd vscode-extension
npm install
npm run compile
```

Then press F5 in VS Code to launch an Extension Development Host.

### Debugging the extension

`.vscode/launch.json` and `.vscode/tasks.json` are both required.

**The launch args must include a folder.** `--extensionDevelopmentPath` alone
opens an empty window: no workspace folder, so `File > Open Folder` is the only
way in and the extension has nothing to resolve paths against.

```json
"args": [
  "--extensionDevelopmentPath=${workspaceFolder}/vscode-extension",
  "${workspaceFolder}"
]
```

The `preLaunchTask` label must match a task in `tasks.json` exactly — VS Code
only auto-detects npm scripts for *workspace folders*, and `vscode-extension` is
a subfolder, so the task has to be declared explicitly. If the label does not
resolve, the launch stalls on a task-picker prompt.

Path resolution order for the repo root:

1. `optdsl.repoRoot` setting, if set.
2. The parent of the extension directory — reliable regardless of which folder
   is open.
3. The workspace folder, **only if it contains `optdsl_tooling`**.

Step 3 is validated because opening `problem_instances` as the workspace must
not make that directory look like the repo root.

Interpreter resolution order:

1. `optdsl.pythonPath` setting, if set.
2. `<repo>/.venv/Scripts/python.exe` (or `.venv/bin/python`).
3. The Python extension's `defaultInterpreterPath`.
4. `python` on `PATH`.

Step 2 matters: the project needs Python 3.11 with `pygls`, `lsprotocol`, and
`minizinc`, and `python` on `PATH` is often an unrelated version.

If the Extension Development Host window closes immediately or hangs:

1. **Output panel → "OptDSL"** — activation log, including whether the language
   client was constructed and whether the server started.
2. **Output panel → "Extension Host"** — activation errors.
3. **Help → Toggle Developer Tools → Console** — grammar and renderer errors.
4. **Run → "Developer: Show Running Extensions"** — whether `optdsl` activated.

A TextMate grammar must not include its own scope. `optdsl.tmLanguage.json`
declares `source.optdsl` and includes `source.python`; if it declared
`source.python` *and* included it, the tokenizer would recurse until the window
hangs.

## Language server

| Capability | Notes |
|---|---|
| Diagnostics | 15 rules; see `optdsl_tooling/diagnostics.py` |
| Completion | DS types, constants, variables, predicates, record types |
| Hover | Resolved domain, decision-index count, constant value |
| Document/workspace symbols | Constants, types, variables, predicates, objective |
| Definition / references / rename | Name-based, whole document |
| Semantic tokens | Distinguishes decision from derived variables |
| Inlay hints | Decision count per variable |
| Code lens | Decision count, problem class |
| Code actions | Add missing predicate invocation, add objective |
| Signature help | Predicate parameters |
| Folding | Functions and control flow |

The server never executes the buffer. `analyze()` calls the importer with
`compile_runtime=False`, which skips the `exec()` that the runtime path uses.

### Diagnostics worth knowing about

Two rules exist because OptDSL fails *silently* in ways that produce a running
solver with a wrong answer:

- `predicate-parameter-unbound` — in isolated (non-pipeline) mode the evaluator
  only calls a predicate when every parameter name matches a variable name. A
  typo in a parameter name disables the constraint with no error.
- `decision-not-enumerated` — an annotation the importer does not recognise
  turns a decision variable into a constant.

Boolean decisions (`DSBool()`, `DSList(N, bool)`) are *not* an error: the
problem reader normalises them to the binary integer domain `{0, 1}`, so they
are enumerated and searchable exactly like `DSInt(0, 1)`.

## LLM constraint authoring

Flow: describe the constraint → model proposes JSON → Python validates → diff
preview → user accepts.

The model never writes to the file.

Validation has three gates:

1. **Parses and stays clean** — the combined module produces no new error
   diagnostics.
2. **Not vacuous** — the constraint must be violated by at least one of 200
   random assignments. A constraint that is never violated constrains nothing.
3. **Not over-constrained** — the constraint must be satisfiable by at least one
   random assignment. Always-violated usually means a misread constant or index
   base.

Gates 2 and 3 are heuristics, not proofs. They cannot detect a constraint that
is satisfiable but semantically wrong; that still needs a human.

## Operator synthesis

`OptDSL: Synthesize LNS Operator` asks for one description and generates **both**
halves of the neighborhood — a destroy operator and a repair operator. You are
not asked to pick a kind: a neighborhood needs both, and a good destroy paired
with a broken repair is still a broken neighborhood.

Each half is validated independently, so a failure in one does not discard the
other. The result dialog reports which halves were accepted and which were not.

The harness is the only thing between a model proposal and the registry. Four
gates:

1. **Static** — parses, imports only from an allowlist, subclasses the right
   ABC, implements the required method.
2. **Contract** — returns a dict, survives a fully-empty and a fully-assigned
   input.
3. **Robustness** — never raises across many seeds and iterations.
4. **Quality** — measured differently per kind:
   - *destroy*: clears a sensible fraction of decisions (5–60%) and improves on
     the baseline initializer.
   - *repair*: restores at least 50% of what a destroy removed, produces
     feasible candidates at a useful rate, and improves on the baseline.

Gate 4 is what makes this useful. A no-op destroy operator passes gates 1–3
trivially, so the harness measures effect.

All candidate code runs in a subprocess with a timeout.

### CLI

Validate a hand-written operator:

```powershell
$env:PYTHONPATH = "operator-synthesis"
.\.venv\Scripts\python.exe -m operator_synthesis validate my_op.py `
    --kind destroy --instance problem_instances\cvrp\random_euclidean_cvrp_8.dsl
```

Synthesize with an external model:

```powershell
$env:OPENAI_API_KEY = "..."
.\.venv\Scripts\python.exe -m operator_synthesis generate `
    --kind destroy --instance problem_instances\cvrp\random_euclidean_cvrp_8.dsl `
    --model gpt-4o --attempts 3
```

## Operator registry

`large_neighborhood_search/registry.py` maps names to factories. Importing
`large_neighborhood_search.builtin_operators` populates it with the 51 built-in
operators.

`example_lns.py` falls back to the registry for any name not handled by its
explicit `if/elif` chains, so a generated operator is reachable from the CLI
without editing that file:

```powershell
.\.venv\Scripts\python.exe example_lns.py instance.dsl --lns-destroy MyGeneratedDestroy
```

Generated operators live in `large_neighborhood_search/problems/generated/`.
Nothing imports that directory automatically — importing every generated file at
package import time would make the language server pay for code most runs never
use, and one broken file would break the package. Load them explicitly:

```python
from large_neighborhood_search.registry import load_generated_directory
load_generated_directory()          # returns the names that became available
```

A module that fails to import is skipped rather than aborting the load.

Each generated operator file is a complete, self-contained module: its own
imports, one operator class, and a registration footer written when the
operator was accepted (`register_destroy("Name", problem=..., generated=True)(Name)`).
`/tune` additionally writes `<problem_key>.lns.json` next to the operators — the
tuned LNS config (construction heuristic + operator pool) that `/lns` applies
automatically; see `optdsl_agent/README.md`.

## Agent harness

`optdsl_agent/` composes the pieces above into one LLM-driven harness. It is the
only place that compares the two backends.

```powershell
python -m optdsl_agent analyze  problem_instances\cvrp\random_euclidean_cvrp_8.dsl
python -m optdsl_agent solve    problem_instances\jssp\jssp_2x2.dsl --timelimit 10
python -m optdsl_agent lns      problem_instances\cvrp\random_euclidean_cvrp_8.dsl --iterations 500
python -m optdsl_agent operators problem_instances\cvrp\random_euclidean_cvrp_8.dsl
python -m optdsl_agent tune     problem_instances\cvrp\*.dsl --attempts 4
python -m optdsl_agent chat     problem_instances\cvrp\random_euclidean_cvrp_8.dsl
python -m optdsl_agent tui      problem_instances\cvrp\random_euclidean_cvrp_8.dsl
```

`analyze`, `solve`, `lns` and `operators` need no model. `explain`,
`add-constraint`, `tune`, `chat` and `tui` do; they read a stored profile, then
`OPTDSL_AGENT_API_KEY` / `OPTDSL_AGENT_BASE_URL`, and `--dry-run` substitutes a
stub.

`tui` needs the optional `textual` dependency (`pip install -e .[tui]`). The line
REPL works without it, and both front-ends share the same slash commands in
`optdsl_agent/commands.py`, so they cannot drift apart. Typing `/` in the TUI
opens a filtered completion popup; in the REPL it prints the command list.

Store the model, endpoint and key once instead of repeating three flags:

```powershell
python -m optdsl_agent settings set risc --model "..." --base-url "..." --api-key "..."
python -m optdsl_agent settings use risc
python -m optdsl_agent settings show      # key is masked
```

Precedence is CLI flag, then environment, then stored profile, then default. The
settings file is plaintext with owner-only permissions; see
`optdsl_agent/README.md` for the caveat.

The harness adds three things the existing tooling did not have:

* **A trajectory.** The engine reports aggregate counters only, which is enough
  to report a score but not enough to diagnose a stall. `RecordingLogger`
  captures per-iteration current/incumbent scores, bounded by halving the
  resolution rather than growing without limit.
* **A gap measurement.** `compare_runs` reports the objective gap and relative
  gap between LNS and the exact solver, with the sign convention flipped for
  maximization so a positive gap always means "LNS is worse".
* **A holdout test.** The tuning loop keeps a synthesized operator only if it
  improves on seeds that were never used during synthesis. An operator that
  improves one instance on one seed has not been shown to be useful.

See `optdsl_agent/README.md` for the tool surface and design rationale.

## Model selection

The extension does **not** filter on `vendor: 'copilot'`. `vscode.lm.selectChatModels({})`
returns every model the user has made available, including BYOK providers
(OpenAI, Anthropic, Azure, Gemini, Ollama, OpenRouter). Hardcoding a vendor
would silently exclude those users.

Run `OptDSL: Select Language Model` to pick one; the choice is stored in
`optdsl.languageModel`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest test -q
```

`test/test_tooling.py` covers the analysis core, diagnostics, fingerprinting,
position mapping, the registry, and the synthesis harness.
`test/test_bridge.py` covers the JSON bridge the extension uses.
`test/test_lsp_protocol.py` drives a real LSP session over stdio — it asserts the
server answers `initialize` and publishes diagnostics, which is the failure mode
that makes the editor window hang.

Two tests are load-bearing:

- `test_decision_indices_match_runtime_reader` asserts the editor's decision set
  equals the LNS runtime's, so the two AST consumers cannot drift.
- `test_analysis_never_executes_source` asserts analysis does not run the buffer.

## Known limitations

- `maximize` is now collected by the importer, but no shipped instance uses it.
- The vacuity check samples uniformly from declared domains. A constraint that
  only fires on rare combinations may be misclassified as vacuous; raise
  `samples` if that happens.
- Operator synthesis validates quality on a single instance. A candidate that
  overfits that instance will pass. Use several instances for a real evaluation.
- The extension's `solve` and `runLns` commands open a terminal rather than
  streaming results, so a long solve does not block the language server.
