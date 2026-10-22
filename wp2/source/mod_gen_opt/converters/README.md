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

### 2D Bin Packing: `convert_2dbp.py`

Converts 2D bin packing instances from standard format (.txt).

**Usage:**

```bash
# Batch conversion
python convert_2dbp.py --input-dir problem_instances/2dbp/benchmarks/hopper \
  --output-dir problem_instances/2dbp/benchmarks/hopper_optdsl

# Single file
python convert_2dbp.py --input-file instance.txt --output-file instance.dsl
```

**Input Format (.txt):**
```
n_boxes box_width box_height
item_1_width item_1_height
item_2_width item_2_height
...
```

**Output:**
OptDSL model with 2D placement constraints (bounds, no-overlap). Minimizes number of boxes used.

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

---

## Workflow

### Step 1: Download Benchmarks

- **CVRP**: [CVRP Library](https://cvrplib.gurobi.com) — download .vrp files
  - Example: Solomon instances (100 cities), Gehring-Homberger (200-1000 cities)
  
- **2D Bin Packing**: Hopper & Turton, Berkey & Wang, or similar sources
  - Standard .txt format (width height per line)
  
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
      hopper/          # Downloaded .txt files
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

# 2DBP
python converters/convert_2dbp.py --input-dir problem_instances/2dbp/benchmarks/hopper \
  --output-dir problem_instances/2dbp/benchmarks/hopper_optdsl

# JSSP
python converters/convert_jssp.py --input-dir problem_instances/jssp/benchmarks/taillard \
  --output-dir problem_instances/jssp/benchmarks/taillard_optdsl --format txt
```

### Step 4: Verify

Check a few converted files to ensure they parse correctly:

```bash
cd problem_instances/cvrp/benchmarks/golden_optdsl
# Inspect a few .dsl files to verify structure
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
