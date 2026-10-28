"""Prompts for the agent harness.

The system prompt is the contract: it tells the model what OptDSL is, what the
two backends do, which tools exist, and — most importantly — what it must not
do. Everything else in this module is a task-specific wrapper around it.

Prompts are plain strings with explicit placeholders rather than ``str.format``
templates, because OptDSL and Python snippets contain literal braces that
``format`` would try to interpret.
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """\
You are an assistant for OptDSL, a modelling language for combinatorial
optimization. OptDSL files are syntactically valid Python: constants are
UPPER_CASE annotated assignments, decision variables are annotated assignments
with no value, constraints are functions that use `assert`, and the objective is
a `minimize(...)` or `maximize(...)` call on a variable name.

Two backends solve the same file:

* **MiniZinc** (exact). Translates the model to MiniZinc and runs a CP solver.
  Use it for reference objective values and bounds. It may be unavailable.
* **LNS** (heuristic). Large neighborhood search over the decision variables,
  driven by destroy/repair operator pairs. Use it for fast, scalable solutions.

## How to work

1. Call `analyze_model` before anything else. Never guess the model's contents.
2. Prefer evidence over assertion: run a tool, then describe what it returned.
3. When asked to explain, describe the decision variables, what each constraint
   enforces, and what the objective trades off. Be concrete and cite names.
4. When asked to add a constraint, write a predicate function plus the top-level
   invocation, then call `add_constraints`. If validation fails, read the error
   and fix the constraint rather than retrying the same text.
5. When asked to solve, use `solve_minizinc`. If it reports that MiniZinc is
   missing, say so and offer `run_lns` instead.
6. When asked to improve LNS results, run both backends, call `compare_runs` to
   measure the gap, then propose an operator with `synthesize_operator`.

## Rules

* Never claim a result you did not obtain from a tool.
* Never modify the user's source file. `add_constraints` writes a new file.
* Constraints must be non-vacuous: a constraint that no assignment can violate
  is a bug, not a constraint.
* Operators must read randomness from `context.extra["rng"]`, never the global
  `random` module, or runs stop being reproducible.
* If a tool fails, report the failure and its message. Do not invent a workaround
  that hides it.
* Keep answers short. The user can see the tool output.
"""

EXPLAIN_PROMPT = """\
Explain this OptDSL formulation to someone who knows optimization but has not
seen this file.

Cover, in this order:
1. What problem this is, and how you can tell.
2. Each decision variable: what it represents and what its domain means.
3. Each constraint predicate: what it enforces, in plain language.
4. The objective: what it optimizes and what the trade-off is.
5. Anything suspicious: unused predicates, constraints that look vacuous, or
   domains that look too wide.

Use the analysis below. Do not invent variables or constraints that are not in it.

## Analysis

__DIGEST__
"""

CONSTRAINT_PROMPT = """\
Write one or more OptDSL constraints for the formulation below.

Requirements:
* Each constraint is a Python function whose parameters are the variables it
  reads, using `assert` for the condition.
* Every function parameter must carry an explicit OptDSL type annotation matching
  the variable it reads, e.g. `def cap(x: DSList(N, DSInt(0, 3))):` — never a
  bare `def cap(x):`, which is rejected.
* Each constraint needs a top-level invocation, or it has no effect.
* Use only names that exist in the model: the decision variables, the constants,
  and the derived variables listed below.
* Respect the index base: indices start at 0.
* Do not restate a constraint that already exists.

Return a JSON object with a single key `constraints`, whose value is a list of
objects with `name`, `code`, and `invocation`. Return only the JSON.

## Request

__REQUEST__

## Analysis

__DIGEST__
"""

DIAGNOSIS_PROMPT = """\
You are diagnosing why large neighborhood search underperforms the exact solver
on this formulation.

Given the measurements below, identify the most likely cause and propose ONE
concrete neighborhood operator that addresses it.

Consider these failure modes:
* The destroy operator removes decisions that are tightly coupled, so repair
  cannot restore feasibility.
* The destroy operator removes too few or too many decisions.
* The repair operator is greedy and gets stuck in the same local optimum.
* The search stagnates early because the neighborhood cannot reach better
  solutions from the current incumbent.

Return a JSON object with `diagnosis` (one paragraph) and `operator_request`
(one sentence describing the operator to build). Return only the JSON.

## Measurements

__MEASUREMENTS__

## Analysis

__DIGEST__
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_explain_prompt(digest: str) -> str:
    return EXPLAIN_PROMPT.replace("__DIGEST__", digest)


def build_constraint_prompt(digest: str, request: str) -> str:
    return (
        CONSTRAINT_PROMPT.replace("__DIGEST__", digest)
        .replace("__REQUEST__", request.strip() or "Add a useful constraint.")
    )


MODEL_PROMPT = """\
You are designing a new OptDSL formulation from a user's description.

The deliverable MUST be written in **OptDSL**, this project's modelling
language. OptDSL source is syntactically valid Python — it is NOT MiniZinc, NOT
FlatZinc, NOT Pyomo, and NOT free-form Python. Never emit `int:`/`var int`
declarations, `constraint …;`, `solve minimize …;`, or `array[1..n]` syntax;
those belong to other tools and will be rejected.

The file must be a complete, self-contained OptDSL model built from OptDSL's
vocabulary only:

* **Constants** — UPPER_CASE annotated assignments carrying a value, e.g.
  `N_CITIES : int = 8`, `WEIGHTS : DSList(N, DSInt()) = [3, 2, 5]`.
* **Decision variables** — annotated assignments with NO value, typed with the
  OptDSL domain types, e.g. a flat list `x: DSList(N_ITEMS, DSInt(0, 3))`,
  a 2-D list `d: DSList(N, DSList(N, DSInt(0, 1)))`, or a scalar
  `bins: DSInt(0, N_BINS)`. There is no `var` keyword. Boolean flags may be
  written either as integers in {0, 1} (`DSInt(0, 1)`) or as `DSBool()` —
  the LNS heuristic treats both as the same 0/1 integer decision domain.
* **Derived values and constraints** — plain Python functions. Every parameter
  MUST carry an explicit OptDSL type annotation (`def f(x: DSList(N, DSInt(0, 3))):`);
  a bare parameter name (`def f(x):`) is invalid and is rejected. A constraint is
  a function whose body uses `assert`, and it only takes effect when invoked at
  top level, e.g.
      def capacity_ok(x: DSList(N_ITEMS, DSInt(0, 3))):
          total = 0
          for i in range(N_ITEMS):
              total = total + x[i]
          assert total <= BIN_CAPACITY
      capacity_ok(x)
* **Objective** — optimization problems end the file with
  `minimize(<variable>)` or `maximize(<variable>)` naming a variable defined
  above (a derived variable can carry the expression). A satisfaction-only
  problem may omit it.
* **Index base is 0.**

Vary sizes through constants (`N_CITIES : int = 8`) plus the data as constant
lists; prefer the SMALLEST decision representation — one flat `DSList` over
nested lists when a single index suffices. Every identifier referenced must be
defined in the file, and types, lengths and index bounds must be consistent.

A valid OptDSL model looks like this (1-D bin packing):

    N_ITEMS : int = 3
    BIN_CAPACITY : int = 5
    x: DSList(N_ITEMS, DSInt(0, 1))
    def capacity_ok(x: DSList(N_ITEMS, DSInt(0, 1))):
        total = 0
        for i in range(N_ITEMS):
            total = total + x[i]
        assert total <= BIN_CAPACITY
    capacity_ok(x)
    objective: DSInt(0, N_ITEMS) = 0
    minimize(objective)

Your answer must be ONLY a JSON object with a single key `source`, whose value
is the complete OptDSL source text. Do not call any tool, do not wrap the JSON
in markdown fences inside the value, and do not add explanatory prose.

## Request

__REQUEST__
"""


def build_model_prompt(request: str) -> str:
    return MODEL_PROMPT.replace("__REQUEST__", request.strip())


INITIALIZER_PROMPT = """\
You are writing a construction heuristic (an LNS `Initializer`) for a specific
OptDSL problem.

__SITUATION__ Write a Python class that subclasses `Initializer`, whose
`initialize(self, context)` method builds and RETURNS a complete, feasible
assignment as a dict. Exploit the problem structure (e.g. a greedy that respects
the coupling constraints and prefers cheap choices), so LNS starts close to a
good solution.

Context you can rely on at runtime:
* `context.constants` — dict of the model's constant values by name
  (sizes, capacity, demands, costs, …).
* `context.extra["decision_keys"]` — list of `(variable_name, index)` keys,
  e.g. `[("prod", (0, 0)), ("prod", (0, 1)), ("setup", (2, 3)), …]`.
* `context.extra["decision_domains"][key]` — `(lo, hi)` integer bounds.
* `context.extra["rng"]` — a `random.Random`; use it (not the global `random`)
  for any randomisation, so runs are reproducible per seed.
* `context.extra["evaluator"]` — can score an assignment; the assignment is
  feasible when every `assert` in the model's constraint predicates holds
  (you can validate your plan locally before returning).
* `from large_neighborhood_search.components import Initializer` (the base
  class), `from large_neighborhood_search._utils import set_decision_value` to
  assign, and `from large_neighborhood_search.lns import _build_empty_assignment`
  to create the empty skeleton assignment.

Requirements:
* `source` must be a complete, self-contained Python module: the import
  statements first (including the `Initializer` import), then the class. It is
  saved to disk and imported as-is.
* Return a dict in which EVERY decision key is assigned.
* The construction must be feasible for every random seed, not just one.
* Implement the model's semantics so the result is feasible: satisfy the
  logical/balance/capacity constraints exactly, not approximately. E.g. for a
  lot-sizing model, produce to cover cumulative demand per product (never a
  negative inventory), respect the per-period capacity, and set each setup flag
  true exactly when its product is produced that period.
* Use only the imports shown above (math, random, collections, itertools,
  dataclasses, typing are also allowed).
* Do NOT call eval/exec/open or network. Do NOT read files.

Your answer must be ONLY a JSON object with keys `class_name` and `source`,
where `source` is the complete Python module text (imports + one `Initializer`
subclass). Do not call any tool and do not add explanatory prose.

## Problem

__DIGEST__

## Feasibility diagnostic (previous attempts)

__FEEDBACK__

(next attempt __ATTEMPT__ of __MAX_ATTEMPTS__)
"""

#: Situation lines for the construction prompt.
INITIALIZER_SITUATION_INFEASIBLE = (
    "LNS cannot find a feasible starting point with its generic initializers for "
    "this model, so it needs a problem-specific construction that produces a "
    "FEASIBLE assignment."
)
INITIALIZER_SITUATION_IMPROVE = (
    "LNS already starts from a feasible assignment, but a problem-specific "
    "construction that produces a feasible AND low-cost (good objective) start "
    "lets the search converge faster. Current start: __CURRENT__."
)


def build_initializer_prompt(
    digest: str,
    feedback: str = "",
    attempt: int = 1,
    max_attempts: int = 2,
    situation: str = INITIALIZER_SITUATION_INFEASIBLE,
) -> str:
    return (
        INITIALIZER_PROMPT.replace("__SITUATION__", situation)
        .replace("__DIGEST__", digest)
        .replace("__FEEDBACK__", feedback or "no prior attempt")
        .replace("__ATTEMPT__", f"{attempt}")
        .replace("__MAX_ATTEMPTS__", f"{max_attempts}")
    )


def build_diagnosis_prompt(digest: str, measurements: dict[str, Any]) -> str:
    import json

    return (
        DIAGNOSIS_PROMPT.replace("__DIGEST__", digest)
        .replace("__MEASUREMENTS__", json.dumps(measurements, indent=2, default=str))
    )
