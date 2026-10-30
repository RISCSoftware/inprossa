# Hybrid Solver (WP6)

A self-contained extraction of the hybrid OptDSL solver from
`wp2/source/mod_gen_opt`: a MiniZinc exact backend plus a large neighborhood
search (LNS) heuristic that exchange information through `@warm_start` DSL
snapshots.

## Terminal UI (`optdsl_agent tui`)

The quickest way to drive both backends is the full-screen terminal UI of the
`optdsl_agent` harness. It shows the model digest, the conversation, and the
status line side by side, and every action is a slash command that maps 1:1 onto
the CLI, so nothing in the UI can drift from the scripts below.

### Install and start

The UI needs the optional `textual` dependency; the solver itself does not.

```powershell
uv pip install --python .venv\Scripts\python.exe "textual>=0.80"
```

The local `.venv` has no `pip`, so use `uv pip install --python …`. Installing
the package itself with the extra (`uv pip install --python
.venv\Scripts\python.exe -e ".[tui]"`) additionally puts `optdsl_agent` on the
interpreter's path, so `python -m optdsl_agent` then works from any directory.

Run it **from this directory** — without the editable install, `optdsl_agent` is
imported from the working tree rather than from the environment:

```powershell
.\.venv\Scripts\python.exe -m optdsl_agent tui problem_instances\cvrp\random_euclidean_cvrp_8.dsl
```

Omit the file to start from an empty problem and build one with `/describe` or
`/add`. Add `--dry-run` to try the UI without credentials (a stub model answers,
so `/analyze`, `/solve` and `/lns` still work for real).

Model access is configured once with `python -m optdsl_agent settings set` (or
`OPTDSL_AGENT_API_KEY` / `--base-url`); only the model-backed commands
(`/describe`, `/add`, `/explain`, `/tune`, free-form questions) need it.

### Keys

| Key | Action |
|---|---|
| `Enter` | submit the prompt |
| `/` | open the command popup (filters as you type; `Up`/`Down`, `Tab`/`Enter`, `Esc`) |
| `F1` | show the command help |
| `F4` | toggle the left pane between model digest and full source |
| `F5` | re-analyse the model |
| `Ctrl+L` | clear the conversation |
| `Ctrl+C` | quit |

The left pane is scrollable: click it (or `Tab` to it) and use the wheel, arrow
keys or `PgUp`/`PgDn`. Model calls and solver runs execute on a worker thread, so
the interface stays responsive while `/solve`, `/lns` or `/tune` are running.

### Slash commands

```
/analyze                               summarise the model
/explain                               explain the model in prose
/describe <problem> | @file[:section]  generate a whole new OptDSL model from a description
/add <request>                         add constraints described in natural language
/solve [timelimit-s]                   solve exactly with MiniZinc
/lns [iterations]                      solve heuristically with LNS
/solution                              show the last solution in problem-specific form
/compare                               compare the last LNS run with the last exact solve
/operators                             list available operators
/tune [attempts]                       run the self-tuning loop
/diff                                  show what changed since the file was loaded
/save                                  write the model (.dsl) and a session transcript
/new                                   discard the current model and start from an empty problem
/reset                                 clear the conversation, keep the model
/help                                  show this help
/quit                                  exit
```

A typical session on a prepared instance:

```
optdsl> /analyze
optdsl> /lns 500          # heuristic; stores a warm-start snapshot
optdsl> /solve 30         # exact, reusing the snapshot ("warm start applied")
optdsl> /compare          # gap between the two
optdsl> /solution         # routes / schedule / bins in problem-specific form
optdsl> /tune 3           # synthesize and validate better operators
```

### Prepared DSL problems

`problem_instances/` holds one formulation per problem class, ready to load:

| Instance | Class | Notes |
|---|---|---|
| `problem_instances\1dbp\problem_2_t_zero_based.dsl` | `1dbp` | small; exact and LNS both reach 3 |
| `problem_instances\2dbp\random_2dbp_zero_based.dsl` | `2dbp` | exact solves; the generic LNS start is infeasible |
| `problem_instances\cutting_packing\cp_0.dsl` | `woodcutting` | large; the exact backend fails on it, use `/lns` |
| `problem_instances\cvrp\random_euclidean_cvrp_8.dsl` | `cvrp` | best demo: exact 370, LNS 370 |
| `problem_instances\cvrp\random_euclidean_cvrp_15.dsl` | `cvrp` | exact needs more than 15 s; LNS ~585 |
| `problem_instances\cvrp\random_euclidean_cvrp_20.dsl` | `cvrp` | exact needs more time; LNS ~564 |
| `problem_instances\cvrp\random_euclidean_cvrp_20_gt.dsl` | `cvrp_tour` | giant-tour variant; exact 1046 |
| `problem_instances\jssp\jssp_2x2.dsl` | `jssp` | tiny; exact 6 |
| `problem_instances\jssp\jssp_5x4.dsl` | `jssp` | exact 22 |
| `problem_instances\jssp\jssp_10x5.dsl` | `jssp` | exact 38 |
| `problem_instances\woodcutting\wc_test_mini.dsl` | `woodcutting` | pipeline model; the exact backend fails on it, use `/lns` |

The class is detected automatically, which selects the problem-specific
initializer and neighborhood. Where the generic LNS start cannot reach
feasibility (`2dbp`, `cutting_packing`, `cvrp_20_gt`), `/tune` bootstraps a
construction heuristic first — that is the intended path for those instances.

### Building a model from `problem_lot_sizing.txt`

`problem_lot_sizing.txt` is a **natural-language description**, not a DSL file —
loading it as the session file only produces a parse error. Turn it into a model
with `/describe`, which asks the model for a complete OptDSL formulation,
validates it (parses, no new diagnostics, translates to MiniZinc) and adopts it:

```powershell
.\.venv\Scripts\python.exe -m optdsl_agent tui
```

```
optdsl> /describe @problem_lot_sizing.txt:Capacitated lot-sizing
generated and adopted a new OptDSL model (… lines).
wrote optdsl_agent\out\model.dsl
Run /analyze to inspect it, or /solve and /lns once you are happy.
optdsl> /analyze
optdsl> /solve 30
optdsl> /lns 500
optdsl> /save
```

`@file` uses the whole file and `@file:Section` one `#`-headed section (matched
case-insensitively); the file currently has the single section
`Capacitated lot-sizing`, so both forms work. The generated model is written to
`optdsl_agent\out\model.dsl` and can be reloaded later like any other instance:

```powershell
.\.venv\Scripts\python.exe -m optdsl_agent tui optdsl_agent\out\model.dsl
```

The description asks for `production` and `setup` as 2-D integer decisions, so
both backends can handle it. On the reference formulation of this description
(the one used by `test/test_initializer.py`) the exact solver returns the optimum
101, while the generic LNS start stays infeasible — run `/tune` to have a
construction heuristic synthesized, validated and stored for the model, after
which `/lns` reuses it automatically.

## Layout

```text
hybrid_solver/
├── src/optdsl/                  OptDSL -> MiniZinc translator + solver runner
│   ├── translator/              AST unrolling, DS types, @warm_start parsing
│   └── solver/                  DSLSolver, MiniZincRunner
├── large_neighborhood_search/   Generic LNS engine + OptDSL adapter
│   ├── registry.py              Operator registry (name -> factory)
│   ├── builtin_operators.py     Registers the 51 built-in operators
│   └── problems/                Problem-specific initializers/operators
├── optdsl_tooling/              Shared static analysis (no editor dependency)
├── optdsl-lsp/                  pygls language server
├── operator-synthesis/          LNS operator generation + validation harness
├── vscode-extension/            VS Code client (LSP + AI features)
├── hybrid/lower_bound.py        LNS -> MiniZinc bridge (estimate_lower_bound)
├── hybrid/warm_start.py         Warm-start JSON snapshots + @warm_start injection
├── optdsl_agent/                LLM harness: CLI, line REPL, TUI, tuning loop
├── run_lns.py                  LNS CLI (--emit-feasible-dsl / --export-warm-start)
├── run_minizinc.py              MiniZinc CLI (--dump-mzn translates only)
├── problem_instances/           Sample OptDSL instances per problem class
├── problem_lot_sizing.txt       Natural-language lot-sizing description (/describe input)
├── docs/tooling.md              Editor tooling and operator synthesis
└── test/                        pytest suite + PowerShell smoke tests
```

## Requirements

- Python 3.11
- MiniZinc installed and available on `PATH` (`minizinc --version`)

## Environment

A local virtual environment lives in `.venv/` (Python 3.11, `minizinc` bindings
only). Create or refresh it with:

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe "minizinc>=0.10.0,<0.11.0"
```

Then run scripts with the local interpreter:

```powershell
.\.venv\Scripts\python.exe run_minizinc.py --help
```

> This directory is a member of the repository-root uv workspace, so plain
> `uv run` resolves to the root `.venv`. Use `.\.venv\Scripts\python.exe`
> directly, or `uv run --no-project ...`, to target the local environment.

## Usage

Exact solve:

```powershell
python run_minizinc.py problem_instances\1dbp\problem_2_t_zero_based.dsl --timelimit 30 --solver cp-sat
```

Translate only (no solver invocation):

```powershell
python run_minizinc.py problem_instances\cvrp\random_euclidean_cvrp_8.dsl --dump-mzn out.mzn
```

Heuristic solve:

```powershell
python run_lns.py problem_instances\cvrp\random_euclidean_cvrp_8.dsl --initializer cvrp --max-iterations 200
```

## Hybrid workflow

The LNS heuristic and the MiniZinc backend exchange warm-start information
through a small JSON snapshot (see [`hybrid/warm_start.py`](hybrid/warm_start.py)).
A run stores the incumbent as a separate file, and the backend reuses it
together with the *original* problem DSL — the problem file is never modified.

1. Run LNS and export the incumbent as a warm-start snapshot (JSON):

   ```powershell
   python run_lns.py problem_instances\cvrp\random_euclidean_cvrp_8.dsl `
       --initializer cvrp --max-iterations 500 `
       --export-warm-start .\ws.json --emit-feasible-on incumbent
   ```

   `--export-warm-start` supports the `{iteration}`, `{event}`, and `{score}`
   placeholders (e.g. `.\ws_{iteration}.json`) and fires on the same events as
   `--emit-feasible-dsl`.

2. Feed the snapshot to the MiniZinc backend. The translator turns the hints
   into `warm_start(...)` solve annotations plus objective bound constraints:

   ```powershell
   python run_minizinc.py problem_instances\cvrp\random_euclidean_cvrp_8.dsl `
       --warm-start .\ws.json --timelimit 30 --solver cp-sat
   ```

   The snapshot only decorates the run — the original `.dsl` file stays
   untouched, so a problem can be re-run with any warm start.

3. From Python, `hybrid.estimate_lower_bound()` performs both steps and returns
   the bound, best objective, and status. It also accepts a warm-start file
   path or spec dict:

   ```python
   from hybrid import estimate_lower_bound
   result = estimate_lower_bound("problem.dsl", warm_assignment="ws.json")
   ```

Older workflows remain supported: `--emit-feasible-dsl` writes the *whole* DSL
with a `@warm_start` block appended (run `run_minizinc.py` on that file
directly), and `hybrid.estimate_lower_bound` also accepts a plain assignment
mapping.

## Notes

- `src/` and `large_neighborhood_search/` use absolute imports
  (`from src.optdsl...`, `from large_neighborhood_search...`), so the package
  root must be on `sys.path`. Run scripts from this directory.
- `large_neighborhood_search/problems/__init__.py` eagerly imports every
  problem adapter. Trim it (and `large_neighborhood_search/__init__.py`) if you
  only need a subset.
- MiniZinc `warm_start` only accepts 1-D arrays; nested (2-D) hints such as JSSP
  `completion` are skipped.

## Editor tooling

`optdsl_tooling/`, `optdsl-lsp/`, `operator-synthesis/`, and
`vscode-extension/` add:

- a language server (diagnostics, completion, hover, symbols, code actions)
- LLM-assisted constraint authoring with a vacuity check
- LNS operator synthesis with an automated quality gate

See [`docs/tooling.md`](docs/tooling.md).

```powershell
# tests
.\.venv\Scripts\python.exe -m pytest test -q

# language server
$env:PYTHONPATH = "optdsl-lsp"; .\.venv\Scripts\python.exe -m optdsl_lsp

# validate an operator
$env:PYTHONPATH = "operator-synthesis"
.\.venv\Scripts\python.exe -m operator_synthesis validate my_op.py `
    --kind destroy --instance problem_instances\cvrp\random_euclidean_cvrp_8.dsl
```
