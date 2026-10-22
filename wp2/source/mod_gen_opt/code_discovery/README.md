# Code Discovery Module

A Python module implementing an automated optimization discovery pipeline that combines large neighborhood search (LNS), lower-bound estimation via MiniZinc, and LLM-based operator generation.

## Overview

The `CodeDiscoveryPipeline` implements a 5-phase workflow designed to autonomously improve solution quality for combinatorial optimization problems:

### 5-Phase Pipeline

1. **Initial LNS Phase** (Default Operators)
   - Solve the optimization problem using standard LNS with random destroy and sampled repair operators
   - Produces incumbent solution and objective value

2. **Lower Bound Estimation** (MiniZinc with Warm-Start)
   - Use MiniZinc/CP-SAT solver with the Phase 1 incumbent as a warm-start hint
   - Produces lower bound for the problem (useful for solution quality assessment)

3. **LLM Operator Generation** (Optional)
   - Generate custom destroy and repair operators by prompting an LLM
   - LLM generates Python classes inheriting from `DestroyOperator` and `RepairOperator`
   - Falls back gracefully to default operators if generation fails

4. **Generated LNS Phase**
   - Run LNS again using the generated operators (if available) or defaults
   - Compare solution quality vs. Phase 1

5. **Re-estimation** (MiniZinc with New Warm-Start)
   - Use MiniZinc/CP-SAT with Phase 4 incumbent as warm-start
   - Assess if the new LNS approach improved the lower bound or solver performance

## Usage

### Basic Usage (No LLM)

```bash
python example_code_discovery.py problem_instances/cvrp/random_euclidean_cvrp_8.dsl \
    --lns-iterations 100 \
    --solver-timelimit 20
```

### With LLM Operator Generation

```bash
python example_code_discovery.py problem_instances/cvrp/random_euclidean_cvrp_8.dsl \
    --llm-url http://your-llm-api:8002/v1/chat/completions \
    --llm-model your-model-name \
    --lns-iterations 100 \
    --solver-timelimit 20
```

### CLI Arguments

- `dsl_file`: Path to .dsl problem file (required)
- `--lns-iterations`: Number of LNS iterations per phase (default: 150)
- `--solver-timelimit`: MiniZinc solver time limit in seconds (default: 20.0)
- `--solver`: MiniZinc backend name (default: "cp-sat")
- `--seed`: Random seed for reproducibility (default: 42)
- `--llm-url`: LLM API endpoint (optional; omit to skip operator generation)
- `--llm-model`: LLM model name (default: "nvidia/MiniMax-M2.7-NVFP4")
- `--quiet`: Suppress per-iteration LNS output
- `--save-result`: Save JSON results to file

## Core Components

### `CodeDiscoveryPipeline`

Main orchestrator class that runs the 5-phase pipeline.

**Constructor:**
```python
CodeDiscoveryPipeline(
    dsl_path: Path | str,
    llm_client: LLMClient | None = None,
    lns_iterations: int = 200,
    solver_timelimit: float = 30.0,
    solver_name: str = "cp-sat",
    random_seed: int = 42,
    verbose: bool = True,
)
```

**Main Method:**
```python
def run() -> DiscoveryResult:
    """Execute the 5-phase pipeline."""
```

### `estimate_lower_bound()`

Lower-bound estimation using MiniZinc with optional warm-start.

```python
def estimate_lower_bound(
    dsl_path: str | Path,
    warm_assignment: dict[str, Any] | None = None,
    timelimit: float = 30.0,
    solver_name: str = "cp-sat",
    dsl_index_base: int = 0,
) -> dict[str, Any]:
    """Estimate lower bound for the problem.
    
    Args:
        dsl_path: Path to .dsl file
        warm_assignment: Optional dict of variable assignments to prime the solver
        timelimit: Solver time limit in seconds
        solver_name: MiniZinc backend (e.g., "cp-sat", "chuffed")
        dsl_index_base: Whether DSL uses 0-based (0) or 1-based (1) indexing
    
    Returns:
        {
            "lower_bound": float,
            "best_objective": float,
            "status": str,  # "OPTIMAL_SOLUTION", "SATISFIED", etc.
            "solver_result": dict  # Full solver output
        }
    """
```

### `generate_operators_with_llm()`

Generate custom LNS operators by prompting an LLM.

```python
def generate_operators_with_llm(
    problem_dsl_text: str,
    lns_result_summary: str,
    llm_client: LLMClient,
    max_tokens: int = 2048,
) -> tuple[DestroyOperator, RepairOperator]:
    """Generate destroy and repair operator classes via LLM.
    
    Args:
        problem_dsl_text: DSL problem description
        lns_result_summary: Summary of initial LNS performance
        llm_client: LLMClient instance with API endpoint
        max_tokens: Max tokens for LLM response
    
    Returns:
        (destroy_operator_instance, repair_operator_instance)
    
    Raises:
        RuntimeError: If code extraction, compilation, or execution fails
    """
```

## LLM Compatibility

### Supported Models

- **Recommended**: Models that output code directly to the `content` field without preamble
- **Tested**: Code generation models that follow instruction constraints well

### Known Limitations

**MiniMax-M2.7-NVFP4 with Reasoning:**
- Extended thinking models output reasoning to a separate field
- Reasoning text can contain pseudo-code or explanations that look like code but aren't executable
- Result: Syntax errors in extracted code
- **Mitigation**: Graceful fallback to default operators (pipeline continues normally)

### Best Practices for LLM Selection

1. **Prefer direct code output**: Models that don't separate reasoning from code
2. **Test extraction**: Run with `--quiet` and check Phase 3 output
3. **Fallback design**: Pipeline is designed to work WITHOUT operator generation
   - If LLM fails or produces invalid code, all 5 phases run with default operators
   - This is by design—not a failure condition

## Output Format

### Console Output

Each phase produces a summary line:
```
[Phase 1] Initial LNS  › best score: 1000000003.0  (100 iterations, 1.7s)
[Phase 2] Lower bound  › solver best: 370.0  bound: 370.0  status: OPTIMAL_SOLUTION
[Phase 3] LLM operatorsù destroy: GeneratedDestroyOperator  repair: GeneratedRepairOperator
[Phase 4] Generated LNSù best score: 999990000.0  (100 iterations, 1.2s)
[Phase 5] Re-estimated › solver best: 350.0  bound: 350.0  status: OPTIMAL_SOLUTION
```

### JSON Output (with --save-result)

```json
{
  "dsl_file": "problem_instances/cvrp/random_euclidean_cvrp_8.dsl",
  "initial_lns_score": 1000000003.0,
  "initial_lower_bound": 370.0,
  "initial_solver_best": 370.0,
  "generated_destroy": "GeneratedDestroyOperator",
  "generated_repair": "GeneratedRepairOperator",
  "generated_lns_score": 999990000.0,
  "generated_lower_bound": 350.0,
  "generated_solver_best": 350.0
}
```

## Architecture

```
code_discovery/
├── __init__.py              # Public API exports
├── pipeline.py              # CodeDiscoveryPipeline orchestrator (5 phases)
├── lower_bound.py           # MiniZinc integration with warm-start
├── operator_gen.py          # LLM-based operator generation
└── README.md               # This file
```

### Dependencies

- `large_neighborhood_search` (workspace LNS framework)
- `src.optdsl.solver.DSLSolver` (DSL problem solver)
- `src.optdsl.solver.Minizinc_solver` (MiniZinc runner)
- `llm.llmclient` (LLM API client)
- Standard library: `random`, `pathlib`, `json`, `types`, `textwrap`, `typing`

## Error Handling

The pipeline includes comprehensive error handling:

1. **Missing DSL File**: Validates path exists before starting
2. **LNS Failures**: Catches and logs solver exceptions; continues if possible
3. **Warm-Start Errors**: Logs and tries without warm-start
4. **LLM Failures**:
   - Connection errors: Gracefully skip Phase 3
   - Invalid code: Validate extraction, reject broken syntax
   - Falls back to default operators for Phase 4
5. **MiniZinc Errors**: Catches and logs solver timeouts/errors

## Examples

### Example 1: Simple Run on CVRP

```bash
poetry run python example_code_discovery.py problem_instances/cvrp/random_euclidean_cvrp_8.dsl --quiet
```

Output:
```
No LLM URL provided — operator generation phase will use default operators.

[CodeDiscovery] Phase 1: Running initial LNS
  Best score: 1000000003.0
[CodeDiscovery] Phase 2: Estimating lower bound via MiniZinc
  Lower bound: 370.0  best: 370.0  status: OPTIMAL_SOLUTION
...
```

### Example 2: Run with LLM and Save Results

```bash
poetry run python example_code_discovery.py problem_instances/2dbp/random_2dbp_zero_based.dsl \
    --llm-url http://ada01.risc.local:8002/v1/chat/completions \
    --lns-iterations 100 \
    --solver-timelimit 15 \
    --save-result results.json
```

This saves a JSON file with all metrics for post-processing.

### Example 3: Reproducible Run

```bash
poetry run python example_code_discovery.py problem_instances/cvrp/random_euclidean_cvrp_20.dsl \
    --seed 99 \
    --lns-iterations 150 \
    --quiet
```

Setting `--seed` ensures reproducible results across runs.

## Troubleshooting

### LLM Operator Generation Fails

**Symptom**: Phase 3 shows `[WARNING] Operator generation failed`

**Causes**:
1. LLM returns code with syntax errors
2. LLM outputs reasoning mixed with code (model-specific)
3. Network/API connection issue

**Solution**: Pipeline falls back to default operators automatically. This is expected behavior.

### MiniZinc Solver Hangs or Times Out

**Symptom**: Phase 2 or 5 takes very long or exits with timeout

**Causes**:
1. Problem is very hard (typical for large optimization problems)
2. `--solver-timelimit` is too short

**Solution**: Increase `--solver-timelimit` or reduce problem size

### DSL File Not Found

**Symptom**: Error message about missing DSL file

**Solution**: Verify file path and use absolute path if relative path fails

## Future Enhancements

1. **Multiple LLM Models**: Support model selection and fallback chains
2. **Operator Validation**: Verify generated operators semantic correctness before use
3. **Metric Tracking**: Per-phase performance dashboards
4. **Caching**: Cache MiniZinc results for identical warm-starts
5. **Parallelization**: Run phases in parallel where possible (phases 1 & 3 are independent)
