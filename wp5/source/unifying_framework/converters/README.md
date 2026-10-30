# Instance Conversion Scripts

Reusable converters for transforming standard benchmark formats into OptDSL format (.dsl) for use with the mod_gen_opt framework.

## Scripts

### CVRP: `convert_cvrp.py`

Converts Capacitated Vehicle Routing Problem instances from:
- CVRP Library format (.vrp, EUC_2D)
- Christofides/Eilon format (.vrp, including EXPLICIT/LOWER_ROW)

**Usage:**

```bash
# Batch conversion: all .vrp files in input_dir → output_dir
python convert_cvrp.py --input-dir problem_instances/cvrp/benchmarks/golden \
  --output-dir problem_instances/cvrp/benchmarks/golden_optdsl

# Single file
python convert_cvrp.py --input-file instance.vrp --output-file instance.dsl

# Christofides/Eilon (extract vehicle count from E-n*-k* filename)
python convert_cvrp.py --input-file problem_instances/cvrp/benchmarks/christofides_e/E-n22-k4.vrp \
  --output-file problem_instances/cvrp/benchmarks/christofides_e_optdsl/E-n22-k4.dsl \
  --vehicles filename --edge-weight-type auto

# Override parameters
python convert_cvrp.py --input-file instance.vrp --output-file instance.dsl \
  --vehicles 10 --capacity 5000
```

**Input Format (.vrp):**
Standard CVRP Library format with sections:
- NAME, TYPE, EDGE_WEIGHT_TYPE
- DIMENSION (number of cities)
- VEHICLES, CAPACITY
- NODE_COORD_SECTION (x, y coordinates)
- DEMAND_SECTION (customer demands)

Christofides/Eilon EXPLICIT instances additionally use:
- EDGE_WEIGHT_FORMAT: LOWER_ROW
- EDGE_WEIGHT_SECTION (lower-triangular distance data)
- no VEHICLES header (use `--vehicles filename` or `--vehicles auto`)

**Output:**
OptDSL model with arc-based formulation, MTZ subtour elimination, and capacity constraints. Minimizes total travel distance.

---

### 2D Bin Packing: `Tools/convert_2dbp_to_optdsl.py`

2D bin packing is **not** handled by a script in this directory. Use
`Tools/convert_2dbp_to_optdsl.py`, which reads the `*.ins2D.json` benchmark
format and emits the model consumed by the study:

```bash
python Tools/convert_2dbp_to_optdsl.py \
  problem_instances/2dbp/benchmarks/testset_paper_2D-BPP_CLASS \
  -o problem_instances/2dbp/benchmarks/testset_paper_optdsl
```

> The former `convert_2dbp.py` was removed: it could not parse either bundled
> benchmark family (Hopper writes `n` then `W H`; Wang writes `n W` then
> `w h quantity`) and its `bool + bool` overlap test is not translatable to
> MiniZinc. Hopper/Wang `.txt` instances are therefore not convertible; the
> study uses the JSON test set.

---

### Job Shop Scheduling: `convert_jssp.py`

Converts Job Shop Scheduling instances from standard format (.txt).

**Usage:**

```bash
# Batch conversion
python convert_jssp.py --input-dir problem_instances/jssp/benchmarks/taillard \
  --output-dir problem_instances/jssp/benchmarks/taillard_optdsl --format txt

# Single file
python convert_jssp.py --input-file instance.txt --output-file instance.dsl --format txt
```

**Input Format (.txt):**
```
n_jobs n_machines
job_1_machine_1 job_1_time_1 job_1_machine_2 job_1_time_2 ...
job_2_machine_1 job_2_time_1 job_2_machine_2 job_2_time_2 ...
...
```

Each job must have exactly n_machines operations, with machine ID and processing time for each.

**Output:**
OptDSL model with precedence constraints (job operation order) and machine capacity constraints (no overlap). Minimizes makespan.

**Indexing convention:** `PROCESSING_TIMES[job][machine]` is indexed by **machine
id**, while `MACHINE_SEQUENCE[job][op]` is indexed by **operation position**. The
processing time of operation `op` of job `j` is therefore
`PROCESSING_TIMES[j][MACHINE_SEQUENCE[j][op]]`. This matches the hand-written
instances (`jssp_2x2.dsl`, `jssp_5x4.dsl`, `jssp_10x5.dsl`) and the LNS operators
in `large_neighborhood_search/problems/jssp.py` / `jssp_optdsl.py`.

Because the encoding stores one processing time per (job, machine) pair, each
job's machine sequence must be a permutation of `0..n_machines-1`. Instances
that visit a machine twice are rejected with an error.

---

### CVRPTW: `convert_cvrptw.py`

Converts Capacitated Vehicle Routing with Time Windows instances from the
Solomon format (.txt).

**Usage:**

```bash
# Batch conversion
python convert_cvrptw.py --input-dir problem_instances/cvrptw/benchmarks/Solomon \
  --output-dir problem_instances/cvrptw/benchmarks/solomon_optdsl

# Single file
python convert_cvrptw.py --input-file C101.txt --output-file C101.dsl
```

**Input Format (.txt):**
```
INSTANCE_NAME

VEHICLE
NUMBER     CAPACITY
   25         200

CUSTOMER
CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME  DUE DATE   SERVICE TIME

    0      40         50          0          0       1236          0
    1      45         68         10        912        967         90
    ...
```

The depot is customer 0. Distances are Euclidean, rounded to the nearest integer.

**Output:**
OptDSL model with an arc-based formulation and explicit time propagation.
Minimizes total travel distance.

**Indexing convention:** the model uses three flat arrays, all indexed by
vehicle `k`:

- `arc[i * NUM_NODES * N_VEHICLES + j * N_VEHICLES + k]` — vehicle `k` travels `i -> j`
- `arrival_time[(c - 1) * N_VEHICLES + k]`, `departure_time[...]`, `load[...]` —
  customer-indexed slots (customer `c` is 1-based, so the depot has no slot)
- `route_start[k]` / `route_end[k]` — depot departure / return time per vehicle

Every constraint is emitted as a top-level `def` function
(`all_customers_visited`, `flow_conservation`, `no_self_loops`,
`depot_balance`, `capacity_constraints`, `time_windows`). This is required by
the LNS backend: `OptDSLImporter` only collects `ast.FunctionDef` nodes as
constraints, so a model written as bare top-level `for`/`assert` statements is
invisible to the evaluator and every candidate is scored as infeasible.

---

## Workflow

### Step 1: Download Benchmarks

- **CVRP**: [CVRP Library](https://cvrplib.gurobi.com) — download .vrp files
  - Example: Solomon instances (100 cities), Gehring-Homberger (200-1000 cities)
  
- **2D Bin Packing**: Hopper & Turton, Berkey & Wang, or similar sources
  - JSON `*.ins2D.json` format (see `Tools/convert_2dbp_to_optdsl.py`)
  
- **JSSP**: Fisher-Thompson, Taillard, or Applegate & Cook benchmarks
  - Standard .txt format (machine_id time pairs per job)

### Step 2: Organize Locally

```
problem_instances/
  cvrp/
    benchmarks/
      golden/          # Downloaded .vrp files
      solomon/         # Downloaded .vrp files
  2dbp/
    benchmarks/
      testset_paper_2D-BPP_CLASS/   # Downloaded *.ins2D.json files
  jssp/
    benchmarks/
      taillard/        # Downloaded .txt files
```

### Step 3: Convert

```bash
# CVRP
python converters/convert_cvrp.py --input-dir problem_instances/cvrp/benchmarks/golden \
  --output-dir problem_instances/cvrp/benchmarks/golden_optdsl

# CVRP (Christofides/Eilon)
python converters/convert_cvrp.py --input-dir problem_instances/cvrp/benchmarks/christofides_e \
  --output-dir problem_instances/cvrp/benchmarks/christofides_e_optdsl \
  --vehicles filename --edge-weight-type auto

# 2DBP (JSON test set)
python Tools/convert_2dbp_to_optdsl.py \
  problem_instances/2dbp/benchmarks/testset_paper_2D-BPP_CLASS \
  -o problem_instances/2dbp/benchmarks/testset_paper_optdsl

# CVRPTW (Solomon)
python converters/convert_cvrptw.py --input-dir problem_instances/cvrptw/benchmarks/Solomon \
  --output-dir problem_instances/cvrptw/benchmarks/solomon_optdsl

# JSSP
python converters/convert_jssp.py --input-dir problem_instances/jssp/benchmarks/taillard \
  --output-dir problem_instances/jssp/benchmarks/taillard_optdsl --format txt
```

### Step 4: Verify

Run the converter test suite. It converts a representative instance of every
class, re-parses the result with the LNS reader, and checks the emitted
constants against the source benchmark:

```bash
pytest tests/test_converters.py -v
```

### Step 5: Use in Benchmarks

The converted .dsl files are now ready for the benchmark suite:

```bash
python studies/optdsl_bench/benchmarks/benchmark_cvrp.py \
  --output results.csv \
  --lns-timeout-seconds 3600
```

---

## Notes

- All converters support **batch mode** (entire directories) and **single-file mode** (one instance).
- Conversion is idempotent: re-running is safe and will overwrite existing .dsl files.
- Most errors are logged to stdout; check the output for skipped files.
- Large instances (200+ cities, 1000+ items) may generate large .dsl files (10-100 MB).
  - Benchmarking such files requires sufficient memory for the OptDSL parser and solver.

---

## Troubleshooting

**"No files matching pattern found"**
- Check that input files exist and have correct extension (.vrp, .txt)

**"Expected N values, got M"**
- File format mismatch; verify input file matches expected format (see examples above)

**"EOFError" or "ValueError during parsing"**
- Malformed input file; check for extra whitespace, missing sections, or non-numeric values
- Try validating the input file with the original benchmark source's parser

---

## Performance Considerations

- **CVRP instances** (100-1000 cities): ~100-1000 lines per .dsl file
- **2DBP instances** (20-1000 items): ~50-500 lines per .dsl file
- **JSSP instances** (5-100 jobs): ~100-500 lines per .dsl file

Conversion time is typically < 1 second per instance on modern hardware.
