# InProSSA — Industrial Problem Solving using Symbolic and Subsymbolic AI

InProSSA is an FFG-funded research project (grant FO999923579) that develops a unified,
model-driven workflow for solving industrial combinatorial optimisation problems. A problem is
formulated once in **OptDSL**, a Python-based domain-specific language, and can then be dispatched
to either an exact MiniZinc backend or a heuristic Large Neighborhood Search backend, while LLMs
assist in translating natural-language problem descriptions into formulations and in generating
search operators. The approach is validated on benchmark instances from several problem classes
and on an industrial woodcutting use case.

## Setup

### Install uv

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Set up Python environment

After installing uv and cloning the repository:

```bash
cd inprossa
uv sync
```

This will create a virtual environment and install all dependencies.

## Structure

Directory tree overview:

```
├───wp1                          Project management (Data Management Plan)
├───wp2                          Problem specification & instance preparation
│   ├───documentation            Solution concept and MCTS notes (Quarto)
│   ├───formulation              Problem formulations (generic, woodcutting)
│   └───source
│       ├───minizinc             OptDSL translator to MiniZinc
│       ├───NL2DSL               Semi-NL problem description to OptDSL translation
│       │                        using LLMs, in-context learning and trees of thoughts
│       ├───llm_translator       LLM-based translation utilities
│       ├───optimiser            Optimisation pipeline
│       ├───problem-data-generator  Synthetic woodcutting instance generator
│       └───simulator            Woodcutting machine simulator
├───wp3                          DSL development and integration
│   ├───deliverables             OptDSL release and deliverable reports
│   └───examples                 DSL models and logical problem specifications
├───wp4                          Solver implementation and solution transformation
├───wp5                          Subsymbolic and hybrid solver techniques
│   ├───mcts                     AlphaZero / Gumbel MuZero self-play training (JAX + Flax)
│   └───source
│       └───unifying_framework   LNS and MiniZinc backends over shared OptDSL models
└───wp6                          Evaluation, dissemination & follow-up research
    ├───hybrid_solver            Hybrid OptDSL solver, LSP tooling and VS Code extension
    ├───dissemination            Dissemination plan and follow-up strategies
    └───final_report             Final project report
```

