# Hybrid Solver (WP6)

A self-contained extraction of the hybrid OptDSL solver from
`wp2/source/mod_gen_opt`: a MiniZinc exact backend plus a large neighborhood
search (LNS) heuristic that exchange information through `@warm_start` DSL
snapshots.

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
├── run_lns.py                  LNS CLI (--emit-feasible-dsl / --export-warm-start)
├── run_minizinc.py              MiniZinc CLI (--dump-mzn translates only)
├── problem_instances/           Sample OptDSL instances per problem class
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
