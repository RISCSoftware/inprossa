# LNS Feasible-Start Commands

This project contains multiple OptDSL problem families. The commands below are validated entry points to get an initial feasible solution reliably.

## Prerequisites

Run from project root:

```powershell
poetry install
```

## 1D Bin Packing (1DBP)

Good baseline command:

```powershell
poetry run python example_lns.py .\problem_instances\1dbp\problem_2_t_zero_based.dsl --max-iterations 500 --log-every 100
```

Expected behavior:
- Finds feasible solutions quickly
- Typical best objective on this instance: `3`

## 2D Bin Packing (2DBP)

Use this command (includes feasible snapshot export):

```powershell
poetry run python example_lns.py .\problem_instances\2dbp\random_2dbp_zero_based.dsl --emit-feasible-dsl '.\problem_instances\2dbp\lns_snapshot_{event}_{iteration}.dsl' --emit-feasible-on incumbent --emit-feasible-every 1 --max-iterations=500 --log-every 10
```

Expected behavior:
- Produces incumbent snapshots once feasible incumbents appear
- On current code, this run finds feasible incumbents and reaches objective `3` on the provided random instance

## CVRP

Use the CVRP-specific initializer:

```powershell
poetry run python example_lns.py .\problem_instances\cvrp\random_euclidean_cvrp_8.dsl --initializer cvrp --max-iterations 200 --log-every 50
```

Expected behavior:
- Starts from feasible route structures
- On the provided instance, reaches objective `370`

## Job Shop Scheduling (JSSP)

JSSP-specific operators target the two defining constraint families of job shop scheduling:
job precedence (each job's operations must run in order) and machine no-overlap
(no two operations can use the same machine at the same time).

### JSSP Operators

**Initialization — `JSSPScheduleInitializer`**
Constructs a feasible initial schedule using a Shortest Processing Time (SPT) dispatch rule.
Repeatedly picks the ready operation with the smallest processing time.
Multiple restarts (`--lns-init-restarts`) keep the best makespan found.

**Destroy Operators**

| Operator | Strategy |
|---|---|
| `JSSPJobLevelDestroy` | Zero out all operations of a fraction of jobs |
| `JSSPMachineLevelDestroy` | Zero out all operations on a fraction of machines |
| `JSSPShuffleDestroy` | Shuffle a random segment of operations within each selected job |
| `JSSPSwapDestroy` | Swap random operation blocks between two selected jobs |
| `JSSPShiftTimesDestroy` | Add a random time offset to all operations of selected jobs |

**Repair Operators**

| Repair | Behavior |
|---|---|
| `JSSPGanttRepair` | Full SPT re-schedule from scratch; ignores any existing completion times |
| `JSSPConstraintAwareRepair` | Anchors non-destroyed operations and only extends the schedule forward |

### Activation

The `--initializer jssp` flag selects JSSP mode.

```powershell
# Small instance (2 jobs x 2 machines)
poetry run python example_lns.py .\problem_instances\jssp\jssp_2x2.dsl --initializer jssp --max-iterations 1000

# Medium instance (5 jobs x 4 machines)
poetry run python example_lns.py .\problem_instances\jssp\jssp_5x4.dsl --initializer jssp --lns-destroy-fraction 0.25 --max-iterations 2000

# Large instance (10 jobs x 5 machines)
poetry run python example_lns.py .\problem_instances\jssp\jssp_10x5.dsl --initializer jssp --lns-init-restarts 16 --max-iterations 3000
```

### JSSP-specific options

| Flag | Effect | Default |
|---|---|---|
| `--initializer jssp` | Activate JSSP mode (initializer + operators) | — |
| `--lns-init-restarts` | Restart attempts for constructive initializer | 16 |
| `--lns-destroy-fraction` | Fraction of elements destroyed per LNS iteration | 0.25 |
| `--lns-repair` | Repair strategy: `gantt` (full rebuild) or `constraint_aware` (anchor & propagate) | `constraint_aware` |

**Objective:** minimize makespan (completion time of the last operation in the schedule).

## Operator Profiles (Command-Line Controlled)

`example_lns.py` supports explicit operator selection via:

```powershell
--operator-profile generic|permutation
```

Use `generic` for formulations like:
- 2D bin packing
- CVRP arc encoding (`arcs`, `vehicle_used`, `u`)

Use `permutation` for giant-tour formulations where a route is encoded as a city permutation (for example `city_tour`).

### Generic profile example

```powershell
poetry run python example_lns.py .\problem_instances\cvrp\random_euclidean_cvrp_8.dsl --operator-profile generic --initializer cvrp --max-iterations 200 --log-every 50
```

### Permutation profile example (giant tour)

```powershell
poetry run python example_lns.py .\problem_instances\cvrp\random_euclidean_cvrp_20_gt.dsl --operator-profile permutation --initializer greedy --max-iterations 200 --log-every 50
```

In permutation mode, the run uses:
- permutation-preserving initializer
- permutation-segment destroy
- repair that fills missing permutation values without duplicates

## Optional: Print Best Assignment

Append this flag to any command:

```powershell
--print-assignment
```

## Optional: Stronger Feasibility Bias

For packing-style instances or when initialization stays infeasible, explicitly set:

```powershell
--init-scoring feasibility-first --init-restarts 32
```

This controls the greedy initializer's behavior:
- `--init-scoring`: `objective` (default) or `feasibility-first`
- `--init-restarts`: Number of restart attempts (default: 1)

### Initialization Strategies

```powershell
# Default greedy (randomized)
--initializer greedy --init-restarts 1 --init-scoring objective

# Feasibility-focused greedy (recommended for 2DBP)
--initializer greedy --init-restarts 32 --init-scoring feasibility-first

# CVRP-specific constructive initializer
--initializer cvrp --cvrp-init-restarts 16 --cvrp-init-randomization 0.3

# JSSP-specific constructive initializer (schedule building via SPT dispatch)
--initializer jssp --lns-init-restarts 16 --lns-destroy-fraction 0.25

# Random assignment
--initializer random
```

## Visualizing Solutions

### CVRP Visualization

Use `Tools/visualize_cvrp_solution.py` to generate HTML route maps:

```powershell
# Arc-based encoding (default)
poetry run python .\Tools\visualize_cvrp_solution.py --dsl-file .\problem_instances\cvrp\random_euclidean_cvrp_8.dsl --result-file <solver_output.txt> --output cvrp_viz.html

# Giant-tour encoding (city_tour permutation)
poetry run python .\Tools\visualize_cvrp_solution.py --dsl-file .\problem_instances\cvrp\random_euclidean_cvrp_20_gt.dsl --encoding giant-tour --output cvrp_gt_viz.html
```

The `--encoding` flag (`arcs` or `giant-tour`) determines how the solution is decoded:
- `arcs` (default): Expects `arcs` and `vehicle_used` arrays
- `giant-tour`: Expects `city_tour` permutation, splits into routes by capacity

### JSSP Visualization

Use `Tools/visualize_jssp_solution.py` to generate HTML Gantt charts:

```powershell
# Visualize JSSP solution from LNS snapshot
poetry run python .\Tools\visualize_jssp_solution.py --dsl-file .\problem_instances\jssp\lns_jssp_snapshot.dsl --output jssp_viz.html
```

The visualizer expects a DSL file with `@warm_start` decorator containing:
- `completion[job][operation]` — completion time for each job-operation pair
