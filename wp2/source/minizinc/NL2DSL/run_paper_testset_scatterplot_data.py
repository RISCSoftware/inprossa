from experiments.extract_objective_value_scatterplot_data import extract_solve_time_scatterplot_data
from experiments.handcrafted_2d_bin_packing import apply_handcrafted
from run_test_files_dfs import paper_20_CLASS_tot_runs

if __name__ == '__main__':
    # Create 5 Trees of Thoughts (each with max. 16 formulations) for each of the 20 2dPackLib instances
    # Take problem description of folder problem_descriptions/
    tree_collection_path = paper_20_CLASS_tot_runs()

    # Get results for those 20 instances for the handcrafted formulation
    handcrafted_objective_values, handcrafted_solve_times = apply_handcrafted(
        "../problem_descriptions/experiment_2D-BPP_CLASS_flex_shapes/", object_types_are_fixed=False)

    # Create csv file for scatterplot
    extract_solve_time_scatterplot_data(tree_collection_path,
                                        handcrafted_solve_times,
                                        handcrafted_objective_values)
