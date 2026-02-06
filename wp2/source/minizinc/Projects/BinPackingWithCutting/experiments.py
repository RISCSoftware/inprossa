
from Projects.BinPackingWithCutting.templates import create_bin_packing_codes
from Experiments.create_figures import improvement_and_scatter_plots

if __name__ == "__main__":

    instances = improvement_and_scatter_plots(
        code_generating_function=create_bin_packing_codes,
        repeats=20,
        name="bin_packing_with_cutting",
        solver_name="chuffed"
        )
