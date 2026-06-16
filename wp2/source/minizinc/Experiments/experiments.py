from Projects.BinPackingWithCutting.templates import create_bin_packing_codes
from create_figures import improvement_and_scatter_plots
from create_csv import instances_to_csv

function_mapping = {
    "bin_packing_with_cutting": create_bin_packing_codes
}

if __name__ == "__main__":

    name = "bin_packing_with_cutting"

    instances = improvement_and_scatter_plots(
        code_generating_function=function_mapping[name],
        n_items=6,
        repeats=20,
        name=name,
        timelimit=60,
        solver_name="chuffed",
        )
    
    instances_to_csv(instances=instances, file=f"Data/{name}/")

