# OptDSL Benchmark Runners

Thin per-class runners for LNS experiments, backed by the shared `run_lns.py` implementation.

## Available Scripts

- `run_2dbp_lns.py`
- `run_jssp_lns.py`
- `run_cvrp_lns.py`
- `run_cvrptw_lns.py`
- `run_woodcutting_lns.py`
- `run_exact_bound.py`

## Quick Start

Run a class-specific profile:

```powershell
python studies/optdsl_bench/runners/run_2dbp_lns.py problem_instances/2dbp/random_2dbp_zero_based.dsl
```

Inspect resolved command without execution:

```powershell
python studies/optdsl_bench/runners/run_cvrp_lns.py problem_instances/cvrp/random_euclidean_cvrp_8.dsl --dry-run
```

Pass through additional options to `run_lns.py`:

```powershell
python studies/optdsl_bench/runners/run_jssp_lns.py problem_instances/jssp/jssp_5x4.dsl --extra-arg "--lns-run-restarts 5"
```

Extract MiniZinc bound metadata:

```powershell
python studies/optdsl_bench/runners/run_exact_bound.py problem_instances/cvrp/random_euclidean_cvrp_8.dsl --timelimit 120 --output-json output/cvrp_bound.json
```

## Notes

- CVRPTW currently reuses CVRP baseline operators as a first implementation wave.
- The runner scripts are intentionally thin wrappers; solver logic remains centralized in `run_lns.py` and `large_neighborhood_search`.
