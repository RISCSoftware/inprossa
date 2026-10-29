---
project: InProSSA – Industrial Problem Solving using Symbolic and Subsymbolic AI
funding: FFG, FO999923579
work package: WP1 – Project Management
document: Data Management Plan
version: 1.2
date: 2026-10-29
data steward: Michael Bögl
---

# Data Management Plan (DMP)

| | |
|---|---|
| **Project** | InProSSA — Industrial Problem Solving using Symbolic and Subsymbolic AI |
| **Funding** | FFG, FO999923579 |
| **Work package** | WP1 (Project Management) |
| **Repository** | <https://github.com/RISCSoftware/inprossa> |
| **Version** | 1.2 |
| **Date** | 2026-10-29 |
| **Data Steward** | Michael Bögl (michael.boegl@risc-software.at) |


## Version History

| Date | Version | Change |
|---|---|---|
| 01.07.2025 | 0.1 | First version of Data Management Plan is available |
| 31.01.2026 | 1.0 | Benchmark generator added, synthetic benchmarks added |
| 31.08.2026 | 1.1 | Benchmark data from literature added |
| 29.10.2026 | 1.2 | roles and archiving consolidated; dataset inventory revised and renumbered (D1–D5, G1–G6); 2DPackLib dataset (D5) and experimental-branch data documented in §3.5 |


## 1. Purpose and Scope

This DMP describes how data generated and used in the InProSSA project is collected,
documented, stored, shared, and preserved. It covers all work packages (WP1–WP6) and the
shared repository at [RISCSoftware/inprossa](https://github.com/RISCSoftware/inprossa).

The project produces **no personal data**. All data is either

- **third-party benchmark data** (publicly available, re-used under its original terms),
- **synthetic/generated problem instances** (machine-generated, no personal reference), or
- **derived research data** (solver results, LLM interaction logs).

Scope exclusions: source code is versioned in Git and is not treated as research data here,
although its releases are archived together with the data (see §7).

## 2. Roles and Responsibilities

| Role | Person | Responsibility |
|---|---|---|
| Data Steward | **Michael Bögl** | Owns this DMP; maintains the data inventory; enforces naming, storage and archiving rules; approves data releases; single point of contact for data requests |
| Project lead / authors | Michael Bögl | Ensure data underlying each publication is deposited and referenced |
| WP owners | All contributors | Follow the conventions in §5, document provenance of new datasets, keep secrets out of the repository |

The Data Steward reviews and updates this plan periodically.

## 3. Data Inventory

All paths are relative to the repository root. All data listed below is held in the public GitHub
repository [RISCSoftware/inprossa](https://github.com/RISCSoftware/inprossa) and is publicly
available. The same applies to all algorithms and research results of the project: they are
developed and published in that repository and are publicly accessible there.

### 3.1 Input data (used)

These datasets are third-party benchmark data, publicly available and used according to their
respective licence. Repository paths for each dataset are listed in Annex A.

+-----+----------------------------------------------------+----------------------------------------------+
| ID  | Dataset                                            | Origin / licence                             |
+=====+====================================================+==============================================+
| D1  | **CVRP benchmarks** (Golden,\                      | [CVRPLIB][cvrplib] — sets E and Golden;\     |
|     | Christofides–Eilon)\                               | public                                       |
|     | 33 instances (66 files), `.vrp` / `.sol`           |                                              |
+-----+----------------------------------------------------+----------------------------------------------+
| D2  | **CVRPTW benchmarks** (Solomon)\                   | [Solomon benchmark, SINTEF TOP][solomon]\    |
|     | 112 files, `.txt` / `.sol`;\                       | (Solomon 1987); public                       |
|     | classes C1/C2/R1/R2/RC1/RC2                        |                                              |
+-----+----------------------------------------------------+----------------------------------------------+
| D3  | **2D bin-packing benchmarks**\                     | [ESICUP Cutting & Packing datasets][esicup]\ |
|     | (Hopper & Turton, Wang, 2D-BPP CLASS)\             | (`2d_rectangular`); public                   |
|     | 20 JSON + 75 instance files,\                      |                                              |
|     | `.json` / `.ins2D.json` / `.dsl`                   |                                              |
+-----+----------------------------------------------------+----------------------------------------------+
| D4  | **JSSP benchmarks**\                               | [JSPLIB][jsplib], [Taillard][taillard],\     |
|     | (Taillard, Lawrence, Adams/Balasz/Zawack,\         | [jobshop.jjvh.nl][jjvh]; public              |
|     | Applegate/Cook, Storer/Wu/Vaccari)\                |                                              |
|     | 155 files, `.txt`                                  |                                              |
+-----+----------------------------------------------------+----------------------------------------------+
| D5  | **2DPackLib 2D packing instances**\                | [2DPackLib][2dpacklib] (Univ. Bologna);\     |
|     | 510 files, `.ins2D`; CLASS (500, 10 classes ×\     | public, re-obtainable from §3.4;\            |
|     | n = 20/40/60/80/100) and BENG (10);\               | experimental branch only, see §3.5           |
|     | `origin/mctx` only                                 |                                              |
+-----+----------------------------------------------------+----------------------------------------------+

### 3.2 Generated and derived data

Data produced by project tooling or derived from the input data. Retention decisions are given per
dataset, and the rationale for the "do not preserve" entry is in §7.

+-----+----------------------------------------------------+----------------------------------------------+
| ID  | Dataset                                            | Retention                                    |
+=====+====================================================+==============================================+
| G1  | **OptDSL instances (hand-written)**\               | Preserve                                     |
|     | 15 files, `.dsl`; 1DBP, 2DBP, cutting/\            |                                              |
|     | packing, CVRP, JSSP, woodcutting                   |                                              |
+-----+----------------------------------------------------+----------------------------------------------+
| G2  | **OptDSL instances (converted)**\                  | Regenerable from D1–D4 +\                    |
|     | 299 files, ~25 MB, `.dsl`                          | converters                                   |
+-----+----------------------------------------------------+----------------------------------------------+
| G3  | **Synthetic 2DBP instances**\                      | Regenerable via\                             |
|     | 6 files, `.dsl`; n = 30/40/50                      | `Tools/generate_2dbp_instances.py`           |
+-----+----------------------------------------------------+----------------------------------------------+
| G4  | **Synthetic woodcutting instances**\               | Regenerable via the problem data\            |
|     | 19 files, `.json` / `.dsl` / `.mzn` / `.ozn`       | generator, §3.3                              |
+-----+----------------------------------------------------+----------------------------------------------+
| G5  | **Benchmark study results**\                       | **Preserve — primary evidence for\           |
|     | 7 files, `.csv` / `.md`; MiniZinc vs. LNS\         | publications**                               |
|     | quality, bound, runtime, gap                       |                                              |
+-----+----------------------------------------------------+----------------------------------------------+
| G6  | **NL2DSL experiment results**\                     | Do not preserve long-term —\                 |
|     | 309 files, `.json` / `.txt` / `.csv`               | experimental branch, see §3.5                |
+-----+----------------------------------------------------+----------------------------------------------+

**Total research data volume:** ≈ 29 MB tracked on `integration`, including duplicate copies of
instances across work packages. The experimental branches in §3.5 hold a further ≈ 108 MB, which is
not part of long-term preservation.

### 3.3 Synthetic data generation

Synthetic instances are **not** stored as an exhaustive collection. They are produced on demand by
documented generators, and only the instances actually used in studies are kept in the repository.
This keeps the data volume small while making every instance reproducible.

| Generator | Produces | Location | Key parameters |
|---|---|---|---|
| **Woodcutting problem data generator** | Woodcutting instances (beams, boards, layers, faults) as JSON | `wp2/source/problem-data-generator/problem_data_generator/main.py` | `--beams`, `--beamlength`, `--layers`, `--boards`, `--boardlength`, `--beamskipstart/end`, `--minlengthofboardinlayer`, `--gap`, `--maxshiftcurvedcut`, `--f` (forbidden zones), `--randomseed`, `--defect_rate`, `--ratio_bad_curved`, `--bad-min/max-length`, `--curved-min/max-length`, `--compact` |
| Woodcutting DSL variant generator | OptDSL/MiniZinc variants of generated woodcutting instances | `wp5/source/unifying_framework/Tools/generate_woodcutting_dsl_variants.py`, `convert_woodcutting_benchmarks_noreorder.py` | source JSON, indexing base, reordering on/off |
| 2DBP instance generator | Size-scaled 2D bin-packing instances | `wp5/source/unifying_framework/Tools/generate_2dbp_instances.py` | item count, box size, seed |

**Woodcutting synthetic data.** The woodcutting use case is the project's industrial scenario. The
**problem data generator** in `wp2/source/problem-data-generator/` creates arbitrary numbers of
instances with controlled difficulty: number of beams and boards, beam length, number of layers,
minimum board length, gap and shift constraints, static forbidden zones, and the density and length
distribution of bad and curved faults. Because the generator takes an explicit `--randomseed`, every
instance is exactly reproducible from its parameter set.

**Documentation requirement.** Whenever a synthetic instance is used in a study or publication, the
full generator invocation (all parameters, including the seed) must be recorded next to the result
file or in the study README, so the instance can be regenerated without storing it.

### 3.4 Publicly available datasets used in this study

All third-party benchmark data used in the study is publicly available. The table lists the
canonical download locations, so every instance in §3.1 can be re-obtained independently of this
repository.

| Problem class | Dataset / collection | Link | Used for |
|---|---|---|---|
| CVRP | CVRPLIB (PUC-Rio / UFF / UFPB) | <https://galgos.inf.puc-rio.br/cvrplib/index.php/en/> | Set E (Christofides–Eilon) and set Golden |
| CVRPTW | SINTEF TOP — Solomon benchmark | <https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/> | C1/C2/R1/R2/RC1/RC2 instances and best-known solutions |
| CVRPTW (extension) | SINTEF TOP — Gehring & Homberger benchmark | <https://www.sintef.no/projectweb/top/vrptw/homberger-benchmark/> | Larger VRPTW instances (optional extension) |
| 2D bin packing / cutting & packing | ESICUP datasets (GitHub, CC0-1.0) | <https://github.com/ESICUP/datasets> | Hopper & Turton, Wang, 2D-BPP CLASS testset (`2d_rectangular`) |
| 2D bin packing (NL2DSL) | 2DPackLib (University of Bologna) | <http://or.dei.unibo.it/library/2dpacklib> | CLASS and BENG instance sets used in the NL2DSL study (D5) |
| JSSP | JSPLIB (GitHub) | <https://github.com/tamy0612/JSPLIB> | ta, la, abz, orb, swv instances and `instances.json` metadata |
| JSSP | Taillard benchmark page (HEIG-VD) | <https://mistic.heig-vd.ch/taillard/problemes.dir/ordonnancement.dir/ordonnancement.html> | Original Taillard instances |
| JSSP | jobshop.jjvh.nl | <http://jobshop.jjvh.nl/> | Best-known solutions and instance metadata |

**Availability note.** The ESICUP data sets were migrated from `euro-online.org` to GitHub. Links were last verified on 2026-10-28.

### 3.5 Data on experimental branches

This data is documented here for completeness and provenance, but it is not part of the long-term preservation scope (§7). The one exception is the third-party 2DPackLib dataset (D5), which is a public benchmark and remains re-obtainable from its original source.

| Branch | Unique data | Volume | Status |
|---|---|---|---|
| `origin/mctx` | 2DPackLib instances (D5), NL2DSL results (G6) | 970 unique files, 91 MB | Experimental; not merged |
| `Implementing_translation` | Earlier NL2DSL experiments and prompts; `FirstProject/*.mzn` | 481 unique files, 17 MB | Experimental; superseded by `origin/mctx` |
| `origin/msteindl2`, `origin/aborted/lightzero` | AlphaZero/MuZero training logs | 17 files, 0.9 MB | Aborted experiment |
| `main`, `problem-generator` | none | — | Contained in `integration` |
| `0-based_DSL`, `origin/msteindl` | one commit each (translator indexing, dependencies) | small | Not merged; no research data |

Paths:

- `origin/mctx` — `wp2/source/NL2DSL/`
- `Implementing_translation` — `wp2/source/minizinc/NL2DSL/` (including `stable_7.1.2026`,
  `examples_z3py`, `examples_optDSL`, `late_2025`) and `wp2/source/minizinc/FirstProject/`
- `origin/msteindl2`, `origin/aborted/lightzero` — `data_az/` and `data_mz_ptree/` at repository root

**2DPackLib (D5).** The 510 two-dimensional packing instances (500 CLASS + 10 BENG) in
`wp2/source/NL2DSL/problem_descriptions/2DPackLib/` are third-party benchmark data from the
University of Bologna's 2DPackLib collection (§3.4). They are used as input for the NL2DSL
experiments and are **not** project output. Because they are publicly available, they do not need to
be preserved with the project: they can be re-obtained from the original source at any time. The
repository copy is a convenience for reproducing the NL2DSL runs.

**NL2DSL experiment results (G6).** The `experiments/` and `prompts/` directories on `origin/mctx`
hold LLM-generated OptDSL models, correctness results, solve-time/objective CSVs and prompt
templates from the NL2DSL study. They are retained on the experimental branch for traceability but
are not part of the long-term archive.

**Handling.** Experimental branches may be archived as tagged snapshots or deleted once their
content is no longer needed. If any NL2DSL result is later used in a publication, the specific
result files must be moved to `integration` and added to the preservation scope in §7 before the
branch is removed.

## 4. FAIR Principles

### 4.1 Findable

- **Structured repository:** one directory per work package (`wp1`–`wp6`), with data separated
  from source code (`problem_instances/`, `output/`).
- **Descriptive file names:** problem class, instance family, size and variant are encoded in the
  file name (e.g. `2d_bpp_inst_cl_06_020_06.ins2D.dsl`, `jssp_10x5.dsl`, `Golden_1.vrp`).
- **Embedded metadata:** generated `.dsl` files carry a header comment naming the source instance or
  generator and the key parameters; `instance_sets.json` documents the purpose, measurement
  environment and per-instance measured costs of the study sets.
- **README per dataset family:** `problem_instances/README.md` (one per problem class),
  `studies/optdsl_bench/benchmarks/README.md`, `wp2/source/problem-data-generator/README.md`,
  `wp6/hybrid_solver/README.md`.
- **Persistent identifiers:** each public release is tagged in Git (`v<major>.<minor>`) and archived
  in the institutional backup.

### 4.2 Accessible

- **Public access:** the repository is public, so all data, algorithms and results are publicly
  available (see §3). Third-party benchmarks are **not** re-published as a separate dataset; the
  conversion scripts and source URLs are provided so they can be re-obtained from the original
  providers, and the third-party files in the repository remain under their original licences.
- **Open, non-proprietary formats:** plain text, JSON, CSV, Markdown, LaTeX — no vendor lock-in.
- **Third-party data stays retrievable:** every external dataset is referenced by its canonical
  public download link (§3.4), so access does not depend on this repository remaining online.
- **Authentication:** public data requires no authentication. Secrets (LLM API keys) are never part
  of the data and are excluded from the repository (`.gitignore`: `.env-secrets`).

### 4.3 Interoperable

- **OptDSL** is syntactically valid Python and is the single shared problem representation across
  all backends (MiniZinc, LNS, RL), which makes instances exchangeable between paradigms.
- **Standard community formats** are used for input data (TSPLIB/CVRPLIB `.vrp`/`.sol`, Solomon `.txt`,
  JSPLIB `.txt`, JSON for 2DBP), so instances remain usable with third-party tools.

### 4.4 Reusable

- **Provenance:** every converted instance is traceable to its source file and conversion script
  (`Tools/convert_*.py`, `converters/convert_*.py`); generated instances record their generator and
  seed in the file name and header (`Tools/generate_2dbp_instances.py`,
  `problem-data-generator --randomseed`).
- **Regenerable synthetic data:** synthetic woodcutting instances are reproducible from the
  documented generator invocation (see §3.3), so re-users can create additional instances of the
  same distribution instead of being limited to the stored sample.
- **Reproducibility:** pinned environments (`uv.lock`, `Dockerfile`, `.devcontainer`; the
  `problem-data-generator` sub-project additionally pins `poetry.lock`), documented solver versions
  (cp-sat 9.15, MiniZinc 2.10.1, Python 3.11), explicit seeds and time budgets, and documented run
  commands in the study READMEs.
- **Documented semantics:** `wp5/source/unifying_framework/README.md` (Part II) describes the LNS
  engine, operator contracts and data model; `wp6/hybrid_solver/docs/tooling.md` describes the
  analysis and synthesis tooling.
- **Licensing:** project code and derived data are released under an open licence; third-party data
  keeps its original licence and is referenced, not relicensed (see §8).
- **Quality assurance:** automated tests (`wp5/source/unifying_framework/test/`,
  `wp6/hybrid_solver/test/`) validate converters against published solutions, so re-users can verify
  that a converted instance preserves the original problem.

## 5. Storage, Naming and Versioning

**Storage locations**

| Purpose | Location |
|---|---|
| Working copy / version control | Git repository [RISCSoftware/inprossa](https://github.com/RISCSoftware/inprossa) |
| Large binaries (archives) | Git LFS or project file share, referenced from the repository |
| Long-term archive | Institutional backup |

**Naming conventions**

- Instances: `<family>_<size>[_<variant>].<ext>` — e.g. `jssp_10x5.dsl`, `Golden_1.vrp`,
  `gen_bpp_n030_box100_s01.dsl`. Third-party instances keep their original names (`E-n13-k4.vrp`,
  `abz5.txt`, `C101.txt`) so they stay traceable to the source collection.
- Converted instances: original stem + `.dsl`, stored in a sibling `<family>_optdsl/` directory
  (e.g. `jssp/benchmarks/abz_optdsl/abz5.dsl`).
- Results: `<study>_<variant>.{csv,md}` — e.g. `study_results_final.csv`,
  `study_results_verify2.md`.

**Versioning**

- All data under version control is versioned with Git; releases are tagged (`v<major>.<minor>`).
  No release tag has been created yet.
- Result files carry the generating command and solver/budget settings in their header or in the
  accompanying README, so a result set can be tied to a code revision.
- Superseded result sets are kept, not overwritten, and marked as superseded in the README.

**Backup**

- Repository: remote Git hosting with institutional backup.
- Non-versioned large artifacts: daily backup of the project file share.
- The Data Steward verifies restorability once per project year.

## 6. Security and Sensitive Data

- **No personal data** is collected or processed. No ethics approval or GDPR data-protection
  impact assessment is required.
- **Secrets:** LLM API keys and endpoints are supplied via environment variables
  (`OPTDSL_AGENT_API_KEY`) or a per-user settings file outside the repository. Keys are masked in
  logs and session files (`api_key: "***"`). `.env-secrets` is git-ignored.
- **LLM logs:** prompts and responses are stored for traceability. Before any release they are
  reviewed and redacted for keys, internal hostnames and partner-identifying content.

## 7. Archiving, Publication and Preservation

| Aspect | Decision |
|---|---|
| What is published | OptDSL instances (G1–G4), study results (G5) — already public via the repository |
| What is not published | Third-party benchmarks (D1–D5, referenced only), experimental-branch data (G6) |
| Where | Public Git repository (continuous) |
| When | Continuously via the repository |
| Metadata | `README.md` per dataset, `CITATION.cff`, `datasets.json` manifest listing every dataset with ID, description, format, size, licence and checksum |
| Retention period | Project duration |
| Formats for preservation | Non-proprietary: `.dsl`, `.json`, `.csv`, `.md`, `.txt`, `.pdf/A` where feasible; `.zip` only for the OptDSL release bundle |
| Checksums | SHA-256 recorded in the release manifest |

## 8. Legal and Ethical Aspects

- **Third-party benchmark data** (CVRPLIB, Solomon, JSPLIB, Hopper/Wang, 2D-BPP CLASS, 2DPackLib) is
  used for scientific comparison under its original terms. It is not relicensed or presented as
  project output; source references and conversion scripts are published so results can be
  reproduced, and canonical download links are listed in §3.4. Where third-party files are present
  in the published repository, their original licence and attribution are recorded in the
  per-dataset READMEs.
- **Project code and derived data** are released under an open-source licence (to be confirmed by
  the project lead; `liccheck` is configured in `pyproject.toml` to verify dependency licences).
  **Action item:** no `LICENSE` file exists in the repository yet, although the repository is
  already public. The project lead must choose the licence and add `LICENSE` plus a `license` field
  in `pyproject.toml`; until then the default "all rights reserved" applies to the project's own
  code and data.
- **No ethical concerns** arise from the data itself. LLM-generated content (operators, constraints)
  is always validated by automated tests and human review before being used in reported results.

## 9. Responsibilities and Review

| Task | Responsible | Frequency |
|---|---|---|
| Maintain data inventory (§3) | Data Steward | Each milestone |
| Verify FAIR compliance (§4) | Data Steward | Each release |
| Review secrets/redaction before release (§6) | Data Steward | Each release |
| Archive release in institutional backup | Data Steward | Each publication / project end |
| Verify backup restorability | Data Steward | Yearly |
| Confirm `LICENSE` and `CITATION.cff` exist (§8) | Data Steward | Each release |
| Update this DMP | Data Steward | periodically |

## Annex A — Dataset locations

Repository paths for every dataset in §3.1 and §3.2. All paths are relative to the repository root.

| ID | Path |
|:-----|:----------------------------------------------------------------------------------------------------|
| D1 | `wp5/source/unifying_framework/problem_instances/cvrp/benchmarks/` |
| D2 | `wp5/source/unifying_framework/problem_instances/cvrptw/benchmarks/Solomon/` |
| D3 | `wp5/source/unifying_framework/problem_instances/2dbp/benchmarks/` |
| D4 | `wp5/source/unifying_framework/problem_instances/jssp/{ta,la,abz,orb,swv}/` |
| D5 | `wp2/source/NL2DSL/problem_descriptions/2DPackLib/` (branch `origin/mctx` only) |
| G1 | `wp5/source/unifying_framework/problem_instances/{1dbp,2dbp,cutting_packing,cvrp,jssp,woodcutting}/`, `wp6/hybrid_solver/problem_instances/` |
| G2 | `wp5/source/unifying_framework/problem_instances/*/benchmarks/*_optdsl/` |
| G3 | `wp5/source/unifying_framework/problem_instances/2dbp/benchmarks/generated_optdsl/` |
| G4 | `wp5/source/unifying_framework/problem_instances/woodcutting/`, `wp2/source/problem-data-generator/problem_data_generator/example_output/` |
| G5 | `wp5/source/unifying_framework/publication/technical_report/results_initial/` |
| G6 | `wp2/source/NL2DSL/experiments/`, `wp2/source/NL2DSL/prompts/` (branch `origin/mctx` only) |

<!-- Link targets used by the inventory tables in §3.1 -->

[cvrplib]: https://galgos.inf.puc-rio.br/cvrplib/index.php/en/
[solomon]: https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/
[esicup]: https://github.com/ESICUP/datasets
[jsplib]: https://github.com/tamy0612/JSPLIB
[taillard]: https://mistic.heig-vd.ch/taillard/problemes.dir/ordonnancement.dir/ordonnancement.html
[jjvh]: http://jobshop.jjvh.nl/
[2dpacklib]: http://or.dei.unibo.it/library/2dpacklib
