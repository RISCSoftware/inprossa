# OptDSL agent harness

An LLM harness over OptDSL and its two backends. It can analyse a formulation,
explain it, add constraints, solve it exactly with MiniZinc, solve it
heuristically with LNS, synthesize neighborhood operators, and tune those
operators by measuring the gap between the two backends.

## Why this exists

The repository already had every piece:

| Piece | Where |
|---|---|
| Static analysis, never executing the buffer | `optdsl_tooling/analysis.py` |
| Constraint validation (vacuity, over-constraint) | `optdsl_tooling/constraint_validation.py` |
| Operator quality gate (static + subprocess + policy) | `operator-synthesis/operator_synthesis/harness.py` |
| Propose/validate/feedback loop | `operator-synthesis/operator_synthesis/synthesize.py` |
| LNS engine, registry, problem adapters | `large_neighborhood_search/` |
| Exact backend | `src/optdsl/solver/` |

What was missing was a single thing that composes them, plus the measurement
that makes tuning possible: the engine reports an aggregate score but no
trajectory, and nothing compared LNS against MiniZinc. This package adds the
composition, the trajectory, and the comparison.

## Install

No new dependencies. The package uses `urllib.request` for model access, so it
works with any OpenAI-compatible endpoint: OpenAI, Azure OpenAI, Ollama, vLLM,
LM Studio.

```powershell
# Optional: MiniZinc for the exact backend
# https://www.minizinc.org/software.html
```

## Usage

### One-shot subcommands

```powershell
# Structure only; no model needed
python -m optdsl_agent analyze problem_instances/cvrp/random_euclidean_cvrp_8.dsl

# Exact solve
python -m optdsl_agent solve problem_instances/jssp/jssp_2x2.dsl --timelimit 10

# Heuristic solve
python -m optdsl_agent lns problem_instances/cvrp/random_euclidean_cvrp_8.dsl --iterations 500

# Which operators apply to this model?
python -m optdsl_agent operators problem_instances/cvrp/random_euclidean_cvrp_8.dsl

# Needs a model
python -m optdsl_agent explain problem_instances/cvrp/random_euclidean_cvrp_8.dsl
python -m optdsl_agent add-constraint problem_instances/cvrp/random_euclidean_cvrp_8.dsl \
    "no vehicle may visit more than three customers"

# Self-tuning
python -m optdsl_agent tune problem_instances/cvrp/*.dsl --attempts 4 --iterations 500
```

### Interactive session

Two front-ends, one implementation. Both delegate to the same slash commands, so
they cannot drift apart.

You can start from an existing formulation **or from an empty problem** — omit
the file argument and the session starts blank, labelled `new empty problem`,
ready to be built up with `/add` or free-form requests:

```powershell
python -m optdsl_agent chat                       # empty problem
python -m optdsl_agent tui                        # empty problem
python -m optdsl_agent chat problem.dsl           # load a formulation
```

**Creating a problem.** Starting empty, describe the model to the agent and add
constraints with `/add`. Each `/save` writes the current model to `out/<stem>.dsl`
(so a newly built problem becomes a reusable formulation) plus a session
transcript `out/<stem>.session.json`. `/new` discards the current model and
restarts from a blank problem without relaunching the session.

To generate a whole model from a description in one step, use `/describe`:

```
optdsl> /describe 8 cities, 4 vehicles of capacity 10, minimize total route length
generated and adopted a new OptDSL model (32 lines).
wrote out\model.dsl
Run /analyze to inspect it, or /solve and /lns once you are happy.
```

Multi-line descriptions come from a file: `/describe @file` uses the whole
file, and `/describe @file:Section` uses one `#`-headed section (sections are
matched case-insensitively), e.g.
`/describe @problem_examples.txt:Capacitated lot-sizing`.

`/describe` asks the model for a complete OptDSL formulation, validates it
(parses, introduces no new diagnostics, and translates to MiniZinc), and adopts
it as the session's model — no file needed beforehand.

**Line REPL** — works everywhere, no extra dependency:

```powershell
python -m optdsl_agent chat problem_instances/cvrp/random_euclidean_cvrp_8.dsl
```

**Full-screen TUI** — three panes (model digest, conversation, status), scrollback,
and keybindings. Needs the optional `textual` dependency:

```powershell
pip install -e .[tui]        # or: pip install textual
python -m optdsl_agent tui problem_instances/cvrp/random_euclidean_cvrp_8.dsl
```

| Key | Action |
|---|---|
| `Enter` | submit the prompt |
| `F1` | show help |
| `F4` | toggle the left pane between model digest and full source |
| `F5` | re-analyse the model |
| `Ctrl+L` | clear the conversation |
| `Ctrl+C` | quit |

Model calls run on a worker thread, so the interface stays responsive while a
request is in flight. Slash commands do too: `/solve`, `/lns` and `/tune` block
for as long as the solver runs, and running them on the event loop would freeze
the interface.

The left pane is a scrollable, focusable view: use the mouse wheel, arrow keys
or `PgUp`/`PgDn` to move through either the digest or the full source (click the
pane first, or `Tab` to it, to scroll with the keyboard).

**Agent turns stay visible.** Model-backed commands (`/add`, `/explain`, and
plain questions) are multi-step: the model may validate and invoke tools before
replying, and a terse final reply alone leaves the "did anything happen?"
question open. After each such turn a light-grey window appears in the
conversation pane with the tool calls the model made and their outcome, roughly
5-10 lines, capped so it never floods the view.

**Command completion.** Typing `/` opens a popup listing every command with its
argument hint and a one-line description. The list filters as you keep typing.

| Key | Action |
|---|---|
| `Up` / `Down` | move through the matches |
| `Tab` or `Enter` | insert the highlighted command |
| `Esc` | dismiss the popup, keep what you typed |

The popup closes as soon as you type a space, because from then on you are
writing an argument rather than a command name.

In the line REPL there is no popup — Windows Python has no `readline` — so a bare
`/` prints the same list instead.

```
optdsl> /analyze
optdsl> /solve 30
optdsl> /lns 500
optdsl> /compare
optdsl> /tune 3
optdsl> why is the LNS result worse than the exact one?
```

`/solve` takes an optional time limit in seconds (`/solve 30`); without an
argument it uses the configured default (`solve_timelimit`).

Slash commands are deterministic and never call the model; free-form text goes
to the agent loop, which can call any tool.

### Configuration

Precedence, highest first:

1. CLI flag
2. Environment variable
3. Stored profile
4. Built-in default

Environment beating the stored profile is deliberate: a CI job or a one-off shell
can override a saved profile without editing it.

| Setting | Environment variable | CLI flag | Default |
|---|---|---|---|
| API key | `OPTDSL_AGENT_API_KEY`, then `OPENAI_API_KEY` | `--api-key` | none |
| Model name | `OPTDSL_AGENT_MODEL` | `--model` | `gpt-4o` |
| Endpoint | `OPTDSL_AGENT_BASE_URL` | `--base-url` | `https://api.openai.com/v1` |
| Profile | `OPTDSL_AGENT_PROFILE` | `--profile` | `default` |
| Output directory | `OPTDSL_AGENT_OUT` | `--out` | `optdsl_agent/out` |

`OPTDSL_AGENT_API_KEY` is preferred over `OPENAI_API_KEY` because it is not tied
to one vendor; the OpenAI-named variable is still read as a fallback so the
existing `operator_synthesis` CLI keeps working.

A non-default base URL counts as configured, so a local endpoint needs no key.

### Stored profiles

Store the model, endpoint and key once instead of repeating three flags on every
invocation:

```powershell
# Save a profile
python -m optdsl_agent settings set risc `
    --model "risc/deepseek-ai/deepseek-v4-flash-0731" `
    --base-url http://litellm.risc.local:4000/v1 `
    --api-key "..."

# Make it the default
python -m optdsl_agent settings use risc

# Inspect (the key is masked)
python -m optdsl_agent settings show

# Use a different profile for one run
python -m optdsl_agent explain model.dsl --profile fireworks

# Remove one
python -m optdsl_agent settings unset risc
```

Profiles live in a per-user config file:

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\optdsl_agent\settings.json` |
| Linux / macOS | `$XDG_CONFIG_HOME/optdsl_agent/settings.json` (or `~/.config/...`) |

`python -m optdsl_agent settings path` prints the exact location.

**The file is plaintext.** It is written with owner-only permissions (`chmod 600`
on POSIX, a restricted ACL on Windows), and `settings show` masks the key. It is
not a secret store: if you need one, keep the key in `OPTDSL_AGENT_API_KEY` and
store only the model and endpoint here.

```powershell
# Key from the environment (preferred: not in shell history)
$env:OPTDSL_AGENT_API_KEY = "..."
python -m optdsl_agent explain model.dsl

# Key as a flag, for a one-off against another provider
python -m optdsl_agent explain model.dsl `
    --base-url https://api.deepseek.com/v1 --model deepseek-chat --api-key "..."

# Local endpoint, no key
python -m optdsl_agent chat model.dsl `
    --base-url http://localhost:11434/v1 --model qwen2.5-coder:14b
```

`--api-key` is visible in shell history and in the process list. Prefer a stored
profile or the environment variable on a shared machine.

## Architecture

```
optdsl_agent/
  _paths.py          makes the sibling packages importable
  config.py          AgentConfig, Budget, precedence resolution
  settings.py        stored profiles (model, endpoint, key)
  llm.py             LLMClient (urllib), tool-calling with JSON fallback, StubClient
  digest.py          model_summary / model_digest: the shared prompt context
  session.py         Session: model text, artifacts, budget counters
  lns_runner.py      LNSRunConfig, run_lns, RecordingLogger (trajectory)
  lns_config.py      tuned LNS configs (<problem_key>.lns.json): load, save, apply
  initializer.py     synthesized construction heuristics: check, persist, load
  operator_loader.py generated-operator loading and listing
  tools.py           the tool registry the model can call
  prompts.py         system, explain, constraint and diagnosis prompts
  agent.py           AgentLoop: history, budget, dispatch
  commands.py        slash commands + completion, shared by the REPL and the TUI
  printers.py        problem-specific solution rendering
  tuning.py          multi-instance evaluation, diagnosis, bounded tuning loop
  report.py          JSON and Markdown reports
  tui.py             optional full-screen UI (textual)
  cli.py             subcommands and the line REPL
```

### The tool surface

| Tool | Purpose |
|---|---|
| `analyze_model` | Problem class, decisions, domains, constants, predicates, diagnostics |
| `translate_model` | OptDSL to MiniZinc text |
| `solve_minizinc` | Exact solve: objective, status, bound, solution |
| `estimate_bound` | Bound for gap analysis |
| `propose_constraints` | Validate without writing |
| `add_constraints` | Validate, append, write `<stem>.constrained.dsl` |
| `list_operators` | Registered operators, filtered by problem class |
| `run_lns` | Heuristic solve with statistics and optional trajectory |
| `evaluate_operator` | The operator quality gate |
| `synthesize_operator` | Propose, validate, retry, save |
| `compare_runs` | LNS vs exact: gap and relative gap |
| `write_file` | Write inside the output directory only |

Every tool returns `{"ok": bool, ...}` and never raises. A failure is data the
model can read and react to, not an exception that ends the conversation.

## Self-tuning
`tune` runs a bounded, autonomous loop:

1. **Exact baseline** — solve with MiniZinc. If MiniZinc is missing, the loop
   continues with LNS-only comparison.
2. **LNS baseline** — run this model's tuned LNS config if one exists (see
   below), otherwise the problem-specific default neighborhood.
3. **Construction heuristic** — ask the model for a problem-specific
   `Initializer` (see below).
4. **Diagnose** — measure the gap, the failed-constraint count, and where the
   search stopped improving. With a model, ask it to explain the gap; without
   one, use a deterministic summary.
5. **Synthesize** — ask the model for one operator that addresses the diagnosis.
   The prompt contains the full model source and the runtime decision-key
   layout, and the candidate is gated together with its partner operator (the
   last accepted generated operator of the opposite kind, or the built-in
   partner of a known problem class).
6. **Train** — measure it on the training seeds.
7. **Hold out** — measure it on seeds never used during synthesis.
8. **Keep or discard** — keep only if it improves on the held-out seeds.
9. **Write the tuned LNS config** and verify it with one LNS run.

Step 7 is the point. An operator that improves one instance on one seed has not
been shown to be useful; it may have memorized that instance. The holdout test
is what separates a real improvement from noise.

The loop stops when the attempt budget or the wall-clock budget runs out, or
immediately when LNS already matches the exact solver — there is nothing to fix
in that case, and any accepted operator would be noise.

Tuning is **verbose by design**: in the TUI and REPL, `/tune N` streams live
progress into the pane — the baseline objectives, the diagnosis, and each
attempt's synthesize / train / holdout stage with its measured improvement — so
the long phases never look hung. Before the first step it prints the plan and
the wall-clock cap, so you can Ctrl-C if the budget is too generous. The CLI
prints the same lines when invoked as `python -m optdsl_agent tune ...`.

**Generated code is plain, self-contained Python.** Operators and construction
heuristics must be complete modules — imports first, then one class — and the
static check rejects a class whose base or decorator is never imported. An
accepted operator is written to the generated operator directory with a
registration footer (`register_destroy(...)` / `register_repair(...)`), so
importing the file is all it takes to make it available by name. A class name
that would shadow a built-in or a different generated operator is renamed
(`Name2`, ...).

**Tuned LNS config.** Everything a run accepts is recorded in
`<operator_dir>/<problem_key>.lns.json`: the construction heuristic (class and
file), the destroy and repair operators (generated ones first, the previous
ones kept in the pool), and adaptive selection when there is more than one
neighborhood. `problem_key` identifies the *formulation* — a known class name
such as `cvrp`, or for any other model its decision variable names plus a hash
of its structure (e.g. `production_setup_40a80726`) — so every instance of the
model shares the config while data changes do not. A later `/tune` continues
from it. `/lns` (and `optdsl-agent lns`, unless `--no-tuned` or explicit
`--destroy`/`--repair` are given) applies the config automatically and logs it:

```text
LNS config: tuned (production_setup_40a80726.lns.json) — construction LotForLotShiftBack;
neighborhoods ProductWindowDestroy+CoverDemandRepair, ...
```

The same record is stored as `lnsConfig` in the run result and the session
transcript, and every run reports the `initializer` and `neighborhoods` it used.

**Construction heuristic.** `/tune` asks the model for an `Initializer` that
constructs a feasible assignment for the specific DSL, and verifies it against
the real evaluator on every instance and every train and holdout seed (with
corrective feedback naming the failing constraint and loop values). When the
generic start is infeasible (no problem-specific adapter, e.g. a
/describe-generated formulation) a feasible construction is adopted and the LNS
baseline is re-measured from it. When the start is already feasible, a candidate
is only adopted if LNS reaches a strictly better objective from it. The adopted
construction is written as `<problem_key>_initializer.py` and referenced by the
tuned config.

**Progress mode (no feasible initializer).** Synthesizing an initializer that
hits the feasible region exactly is itself hard — the model must get the values
and the matching non-`ID` index bookkeeping right. When every initializer
attempt fails, `/tune` gives up on a feasible start and switches to *progress
mode*: candidates are no longer judged by their feasible-candidate rate (which
is zero) but by how much they reduce the infeasibility penalty (the number of
failed constraints) on held-out seeds. Any operator that cuts the penalty on
a fresh seed is accepted, exactly the behavior a human tuning an infeasible
start would use. The tuning report marks an infeasible baseline explicitly
(`baselineFeasible: false` / an "_infeasible start_" banner in the Markdown) so
a "kept" operator from such a run is not mistaken for a solution-quality win.
Because the penalty is measured in failed-constraint units, the incumbent
objective is *not* projected forward in this mode.

**A note on generated models and LNS.** The LNS heuristic indexes *integer*
decision domains. `DSBool()` — a boolean domain — is transparently normalised
to the binary integer domain `DSInt(0, 1)` by the problem reader, so setup
flags and other "true/false" decisions written as `DSBool()` (or `DSList(N,
bool)`) are searchable just like `DSInt(0, 1)`. This used to be a silent trap:
the importer had no `DSBool` branch, so such a variable never became a decision
and no LNS run over it was ever feasible. That is fixed; the exact and
heuristic backends now agree on the model either way. (In MiniZinc the same
flags can stay booleans — it accepts both forms.)

Reports are written to the output directory as `<stem>.json` and `<stem>.md`.

## Solution printers

A raw assignment is a dict of flat lists: 256 zeros and ones for CVRP, a
completion matrix for JSSP. Neither tells you anything at a glance. Each problem
class has a printer that reconstructs the structure the solver already had:

```
Solution (minimize objective = 370)

  4/4 vehicles, 7 customers served, total distance 370

  vehicle 0: 0 -> 4 -> 3 -> 0
      2 customers, load 6/10, distance 105
  vehicle 1: 0 -> 6 -> 0
      1 customers, load 9/10, distance 52
```

```
Solution (minimize objective = 53)

  makespan 53

  machine 0: J0.0[42-45]  J1.1[51-53]
  machine 1: J0.1[45-47]  J1.0[47-51]
```

| Class | Rendering |
|---|---|
| `cvrp`, `cvrp_tour` | one line per vehicle: route, load, distance |
| `jssp` | per-machine schedule with start/end times, plus makespan |
| `1dbp` | one line per bin: contents and load |
| `2dbp` | one line per box: item placements and fill ratio |
| `cutting_packing` | one line per segment: cuts and derived pieces |
| `woodcutting` | one line per board: cuts and derived pieces |

Anything else falls back to a truncated variable dump.

Printers are **defensive by design**: one that cannot find the constants it needs
returns `None` and the caller falls back to the generic dump, rather than raising
in the middle of a report. An infeasible solution is labelled explicitly — a
degenerate assignment (every item at the origin) renders as a plausible-looking
table, and without the label you would take it at face value.

```powershell
python -m optdsl_agent lns model.dsl --solution   # print the rendering
```

In the REPL and TUI, `/lns` shows it automatically and `/solution` re-prints the
last one.

## Warm-start hand-off (LNS → exact)

A feasible `/lns` run stores the incumbent as a transient warm-start snapshot
(`<stem>.warmstart.json` in the output directory) and hands it to the next
`/solve` — the exact backend then starts from those hints plus the incumbent's
objective bound, and reports `warm start applied`. The problem file is never
modified; hints live entirely in the snapshot and are merged into the translated
MiniZinc model at solve time. Run `/lns` again to refresh the snapshot, or
start a fresh session to drop it.

```
optdsl> /lns 200
objective 370.0, feasible True, ...
warm start saved to out\random_euclidean_cvrp_8.warmstart.json — the next /solve will reuse it
optdsl> /solve
status OPTIMAL_SOLUTION, objective 370, bound 370, warm start applied
```

`/compare` then shows both solution qualities, the exact solver's lower bound,
and the percentage gaps between every pair (worse-vs-reference, so a positive
number always means the first value is worse):

```
optdsl> /compare
objective sense: minimize
LNS objective:    372  (feasible)
solve objective:  370  (OPTIMAL_SOLUTION)
solve lower bound:368

quality gaps (worse vs reference):
  LNS vs solve: 0.54%
  LNS vs bound: 1.09%
  solve vs bound: 0.54%
```

## Design decisions

**No SDK.** The project's only runtime dependency is `minizinc`. One POST does
not justify adding `openai`, and `urllib.request` reaches every compatible
endpoint.

**Tool calling with a fallback.** Native `tools` is the better protocol, but not
every compatible endpoint implements it. When the endpoint rejects the request,
the client degrades to a JSON-action protocol in the message body, so the agent
loop is identical either way.

**The source file is never modified.** `add_constraints` writes
`<stem>.constrained.dsl`; operators go to
`large_neighborhood_search/problems/generated/`. The user diffs and adopts
deliberately.

**Reuse over reimplementation.** `synthesize()` and `evaluate_candidate()` are
called as-is, so the CLI, the VS Code extension and this harness share one
quality gate. A second implementation would drift.

**Budgets are enforced, not advisory.** `max_llm_calls`, `max_tool_calls` and
`max_wall_seconds` are checked before every call, and the loop also caps tool
steps per turn so a model that never concludes cannot spin.

**Blocking work never runs on the UI thread.** Model calls and slash commands
both run on worker threads. This is not only about responsiveness: the MiniZinc
runner starts its own event loop, so calling it from inside the TUI's loop failed
outright with "asyncio.run() cannot be called from a running event loop".

## Known limitations

* **Azure OpenAI is not supported.** It needs an `api-key:` header and an
  `?api-version=` query parameter; the client always sends
  `Authorization: Bearer` and appends only `/chat/completions`. Every other
  OpenAI-compatible endpoint works.
* **`MiniZincRunner` requires MiniZinc at construction time.** The tools report
  this as a normal failure, but the exact backend is simply unavailable without
  it.
* **Generated operators are not sandboxed.** The harness runs them in a
  subprocess with a timeout and an AST allowlist, which is a guardrail, not a
  security boundary. Do not run untrusted operator code on a machine you care
  about.
* **The digest is a summary.** For very large models the constant previews are
  truncated; the model sees structure, not every value.
* **Tuning is single-objective.** Multi-objective formulations are not handled
  specially.
