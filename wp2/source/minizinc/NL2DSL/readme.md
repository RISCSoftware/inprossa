# Natural Language to Pythonic DSL (NL2DSL)


A tool, consisting of multiple scripts, to translate semi-natural language optimization problems to the pythonic Domain Specific Language (DSL) called **OptDSL** (developed in inprossa\wp2\source\minizinc\Translator).
The translation is done automatically using the natural-language processing capabilities of an LLM.
We use an abstract structure called a tree of thoughts, to guide the LLM translation in multiple steps.

This repo also serves to provide results and experiments of our paper "Towards Automatising the Formulation of Industrial
Optimisation Problems with LLMs: A Case Study", which was submitted to SYNASC26.

> **_Note on `src/nl2dsl/experiments/`_**: Find the (raw) result data of the experiments for Section III.C in `src/nl2dsl/experiments/experiment_2D-BPP_CLASS_flex_shapes/` and for Section IV in `src/nl2dsl/experiments/experiment_2D-BPP_CLASS_fixed_shapes/`.


# Prerequisites
Either an Amazon AWS Bedrock LLM or a locally running Vllm is required (respective clients in `NL2DSL/LLM_Client`). Please choose a LLM_Client in `NL2DSL/constants.py` (or create one yourself). In the event of using AWS Bedrock LLM models, create a file `.api_key` with your LLM API key at repo root.

A python environment in order to run the scripts.

Install MiniZinc
```bash
wget https://github.com/MiniZinc/MiniZincIDE/releases/latest/download/MiniZincIDE-latest-bundle-linux-x86_64.tgz
```
```bash
tar -xvf MiniZincIDE-<version>-bundle-linux-x86_64.tgz
```
Set path:
temporary:
```bash
export PATH="/path/to/MiniZincIDE-<version>-bundle-linux-x86_64/bin/minizinc:$PATH"
```
```bash
source ~/.bashrc
```
permanent:
```bash
echo 'export PATH="/path/to/MiniZincIDE-<version>-bundle-linux-x86_64/bin/minizinc:$PATH"' >> ~/.bashrc
```

Install sentence-transformer:
```bash
pip install -U sentence-transformers
```

**Recommended**: Restart the terminal or/and IDE.

Check if installation successful:
```bash
minizinc --version
```

# Branch and Tree of Thoughts (ToT)
The problem of translating a semi-natural language optimization problem into multiple components:
* Level 1: Objects (e.g. Person: Name, Age)
* Level 2: Constants (input variables)
* Level 3: Decision variables (output variables)
* Level 4: Objective function (calculation of the objective value which will be minimized/maximized in the end)
* Level 5: Constraints

Each component is sequentially queried to a LLM in a build-up fashion and depends on the previous components so far. This pipeline reaching from Objects to Constraints is called a **Branch of Thoughts**. In order to explore different formulations following from an LLM's non-determinism, we can build a *Tree of Thoughts*.

## Flexible shapes
One option is, to leave the choice of. which shape (type) the constants and decision variables should be used, to the LLM. Input is given as e.g. in `problem_descriptions\testset_paper_2D-BPP_CLASS`.
+ This allows more exploration, as the tree branches at each level.
- However, the resulting formulations are not reusable for different instances of constants. Due to the unknown choice of variable types, the structure of the formulation becomes unknown and hard to manipulate.
- Neither can their solution be validated automatically if all constraints are fulfilled, due to the unknown structure of the decision variables.
Find experiment results from paper in `src/nl2dsl/experiments/experiment_2D-BPP_CLASS_flex_shapes`

## Fixed shapes
To address the lacking reusability and automatic validation of the previous approach in section [Flexible shapes](#Flexible-shapes),
the user must provide the shapes to be used for all constants and decision variables. See examples for input in e.g. in `problem_descriptions\testset_paper_2D-BPP_CLASS_fixed_objects`.
As objects, constants and decision variables are fixed now, no exploration is done by the LLM in levels 1 - 3 (no branching).
Only branching/exploration is done in level 4 and level 5.
Find experiment results from paper in `src/nl2dsl/experiments/experiment_2D-BPP_CLASS_fixed_shapes`

## Usage
Use `run_paper_tot_alogrithms` to recreate the data for the plots in the paper.

### Flexible shapes
#### Reproducing the paper results from Section 6.2.2
```bash
./run_paper_tot_alogrithms.py --execution_subject tot_flexible_shapes
```
#### With custom problem description and instances
```
./run_paper_tot_alogrithms.py --execution_subject tot_flexible_shapes --problem_description <path/to/problem_description.json>  --problem_instances_dir <path/to/problem_instances_dir>
```
This script recreates the data for the bar chart (correctness_results.txt) and for the comparison of the solve times of the ToT formulations and the handcrafted formulation (solvetimes_values_n20_scatterplot.csv).
Creates 5 Trees of Thoughts (each with yielding max. 16 formulations) for each of the 20 2dPackLib-instances, 100 trees in total.
Creates raw data files of results:
* Formulations of each tree are saved to a files: `experiments/experiment_<date>/` 5 runs in `/testset_paper_2D-BPP_CLASS_runI/` each containing 20 trees in form of optDSL_models_<date>.json for 20 instances (each contains 16 formulations).
* For each run experiments/experiment_<date>/ 5 runs in /testset_paper_2D-BPP_CLASS_runI/correctness_results.txt
* scatterplot_data_handcrafted_vs_ToT/solvetimes_values_n20_scatterplot.csv with raw data for a scatterplot

Additionally, you may set features in constants.py:
`NR_MAX_CHILDREN` defines the maximum number of children per node in ToT (default = 2).
`CONSTRAINT_NODES` splits each subproblem into individual node, save formulations for all subproblems into one node (default = false).
`SAVE_NODES`, saves whole tree each node in correct nested folder structure (default = false)
`SAVE_MODEL`, saves the valid model formulations resulting from the tree (default = true)
`SOLVER`, defines the solver used by MiniZinc (default = "chuffed"). Must be a solver supported as MiniZinc backend solver.

### Fixed shapes
#### Reproducing the thesis results from Section 6.3.2
```bash
./run_paper_tot_alogrithms.py --execution_subject tot_fixed_shapes
```
#### With custom problem description and instances
```
./run_paper_tot_alogrithms.py --execution_subject tot_fixed_shapes --problem_description <path/to/problem_description.json>  --problem_instances_dir <path/to/problem_instances_dir>
```
This script recreates the data for the cactus plot for the comparison of the solve times of the ToT formulations and the handcrafted formulation (solvetimes_values_n20_cum_graph.csv).
Create 1 Tree of Thoughts (yielding max. 16 valid formulations) and reuse each formulation for each of the remaining 19 2dPackLib instances
Creates raw data files of results:
* In experiments/experiment_<date>/reusable_model/ containing optDSL_models_<date>.json for the original ToT with max. 16 reusable formulations
* In experiments/experiment_<date>/ containing 19 optDSL_models_reused_<date>.json for reused formulations for the remaining 19 instances
* For optDSL_models_<date>.json the correctness results are stored in experiments/experiment_<date>/reusable_model/correctness_results.txt
* cactus_plot_data_handcrafted_vs_ToT/solvetimes_values_n20_cum_graph.csv with raw data for a cactus plot

Additionally, you may set features in constants.py:
`NR_MAX_CHILDREN` defines the maximum number of children per node in ToT (default = 2).
`CONSTRAINT_NODES` splits each subproblem into individual node, save formulations for all subproblems into one node (default = false).
`SAVE_NODES`, saves whole tree each node in correct nested folder structure (default = false)
`SAVE_MODEL`, saves the valid model formulations resulting from the tree (default = true)
`SOLVER`, defines the solver used by MiniZinc (default = "chuffed"). Must be a solver supported as MiniZinc backend solver.

> [!Warning]
> Running each script will take at least 6 hours, it is run to create 5 trees per instance.


# AlgoPolish
Assuming the user now possesses valid OptDSL-formulations, generated from a Tree of Thoughts using fixed shapes for reusability (from \autoref{sec:tot_fixed_object_types}), it would be interesting to see, if the LLM can acquire even more efficient formulations for a specific family of instances (2d bin packing) by combining and refactoring the existing ones (polishing).
For this purpose, we take inspiration from A. Hottung's et al. algorithm, which was created to discover new heuristics by refactoring and merging existing ones to look for the best performing heuristics in the family of instances with the solver in use. Inspired by their work, we propose the framework AlgoPolish to use refactoring to discover more efficient OptDSL formulations.

We run multiple iterations, where in each iteration we extend and update a set *F* of OptDSL-formulations with new mutated formulations by:
* (biasedly) merging a well-performing formulation with a bad-performing formulation and
* refactorings on elite formulations.

To identify well-performing and bad-performing formulations (non-elites), we measure their performance with a heuristic on a separate testset of 10 random instances from 2DPackLib (see `problem_descriptions/testset_algopolish_2D-BPP_CLASS`).
This algopolish-heuristic heuristic per formulation for determining elitism is obtained by letting the formulation run for a fixed testset of 10 random samples from 2dPackLib. We take the sum of average objective values and average solvetime as a heuristic to identify elite formulations. Hence, the lower the value of this heuristic, the better more performant it is.

Starting with a set *F* of the 10 formulations with the highest algopolish-heuristic from the 16 ToT formulations, we run 5 iterations of AlgoPolish.
In each iteration we:
* merge 60% of one random elite formulation and 40% of one random non-elite formulation (5 times to receive 5 merged formulations)
* For each elite formulation:
  * refactor formulation by changing the objective function (using self-LLM-suggested approaches)
  * refactor formulation by implementing a self-LLM-suggested approach to improve performance concerning solving time, efficiency, readability etc.
  * refactor formulation by removing redundancies and cleaning up
  * refactor formulation by letting the LLM freely refactor in order to improve performance

> **_Note_**: If refactored formulation has better algopolish-heuristic than original elite formulation add to set. Otherwise, add original elite form. to set *F*.

Additionally, different constants may be set:
* NR_MERGED_MODELS, is the number of max. allowed formulations, resulting from merge, per iteration (default = 5)
* POLISHING_ITERATIONS, is the number of AlgoPlolish iterations (1 iteration = 5 formulations from merging + 3 formulations from refactoring) (default = 5)


## Usage
Use `algo_plolish` to recreate the data for the plots in the paper.

#### Reproducing the thesis results from Section 6.4
```
./algo_plolish.py
```

Custom usage:
```
./algo_plolish.py --base_formulations <path/to/file/containing/base/formulations> --problem_filepath <path/to/problem/description> --algopolish_testset_path <path/to/testset/instances> --validate_solution <path/solution-validatior/function> --objective_variable_name <name_of_decision_variable_representing_objective_value>
```
