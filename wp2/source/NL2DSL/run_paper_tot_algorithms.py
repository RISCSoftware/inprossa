import argparse

import constants
from constants import GENERATION_INST_DIR
from experiments.extract_objective_value_scatterplot_data import extract_solve_time_scatterplot_data, \
    extract_solve_times_cum_graph
from experiments.handcrafted_2d_bin_packing import apply_handcrafted
from run_test_files_dfs import paper_20_CLASS_5_tot_flex_shapes, update_tree_collection_correctness_results_with_objective, \
    paper_20_CLASS_1_tot_fixed_shapes


def tots_with_flexible_shapes():
    """
        Create 5 Trees of Thoughts (each with max. 16 formulations) for each of the 20 2dPackLib instances
        Creates raw data files of results:
            > correctness_results.txt
            > scatterplot_data_handcrafted_vs_ToT/solvetimes_values_n20_scatterplot.csv
    """
    # Take problem description of folder problem_descriptions/
    tree_collection_path = paper_20_CLASS_5_tot_flex_shapes()
    # tree_collection_path = "experiments/experiment_2026-04-30_09-08"

    # Get results for those 20 instances for the handcrafted formulation
    handcrafted_objective_values, handcrafted_solve_times = apply_handcrafted(
        GENERATION_INST_DIR, object_types_are_fixed=False)

    # Save correctness results as txt to use for a potential barplot
    if constants.DEBUG_MODE_ON: print("correctness.txt updated for optimal results.")
    update_tree_collection_correctness_results_with_objective(tree_collection_path, handcrafted_objective_values, execute_for_reused_formulations=False)

    # Create csv file for scatterplot
    extract_solve_time_scatterplot_data(tree_collection_path,
                                        handcrafted_solve_times,
                                        handcrafted_objective_values)

def tots_with_fixed_shapes():
    """
        Create 1 Tree of Thoughts (with max. 16 formulations) and reuse each formulation for each of the 20 2dPackLib instances
        Creates raw data files of results:
            > correctness_results.txt
            > cactus_plot_data_handcrafted_vs_ToT/solvetimes_values_n20_cum_graph.csv
    """
    # No exploration in object-type-node and variable-node -> set max allowed children to 4 to receive 16 formulations
    constants.NR_MAX_CHILDREN = 4
    constants.GENERATION_INST_DIR = "problem_descriptions/testset_paper_2D-BPP_CLASS_fixed_objects/"

    # Take problem description of folder /problem_descriptions and set of instances from constants.GENERATION_INST_DIR
    tree_collection_path = paper_20_CLASS_1_tot_fixed_shapes()
    # tree_collection_path = "experiments/experiment_2026-05-06_10-56"

    # Get results for those 20 instances for the handcrafted formulation
    handcrafted_objective_values, handcrafted_solve_times = apply_handcrafted(
        GENERATION_INST_DIR, object_types_are_fixed=False)
    with open(f"{tree_collection_path}/reusable_model/handcrafted_results.txt", "w", encoding="utf-8") as f:
        f.write(f"{handcrafted_objective_values}\n{handcrafted_solve_times}")

    # Save correctness results as txt to use for a potential barplot
    if constants.DEBUG_MODE_ON: print("correctness.txt updated for optimal results.")
    update_tree_collection_correctness_results_with_objective(tree_collection_path, handcrafted_objective_values, execute_for_reused_formulations=True)

    # Create csv file for cactus plot
    extract_solve_times_cum_graph(tree_collection_path,
                                  handcrafted_solve_times,
                                  handcrafted_objective_values)
    constants.NR_MAX_CHILDREN = 2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tree of Thoughts generation script with DFS algorithm from paper")
    parser.add_argument("--execution_subject",
                        "-e",
                        choices=["tot_flexible_shapes",
                                 "tot_fixed_shapes"],
                        help="execution_subject: defines what algorithm to run.")

    args = parser.parse_args()
    if args.execution_subject == "tot_flexible_shapes":
        tots_with_flexible_shapes()
    elif args.execution_subject == "tot_fixed_shapes":
        tots_with_fixed_shapes()
    else:
        raise ValueError("Invalid execution_subject")
