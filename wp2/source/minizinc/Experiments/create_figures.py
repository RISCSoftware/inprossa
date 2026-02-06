import matplotlib.pyplot as plt
from pathlib import Path

from Experiments.Instance import InstanceProgress
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner


def improvement_and_scatter_plots(
        code_generating_function,
        repeats=2,
        name: str = "unknown",
        solver_name: str = "chuffed",
        print_figures: bool = False):
    runner = MiniZincRunner(solver_name=solver_name)

    instances = []

    for r in range(repeats):
        print("\n    Instance:", r+1)
        new_instance = InstanceProgress(f"b{name}_run{r+1}")
        codes = code_generating_function()

        for n, dsl_code in enumerate(codes["dsl"]):
            translator = MiniZincTranslator(dsl_code)
            mzn_model = translator.unroll_translation()

            print(f"Model: DSL {n+1}")
            dsl_result = runner.run(mzn_model)
            new_instance.add(
                f"dsl_solver_{n+1}",
                result=dsl_result
                )

        for n, minizinc_code in enumerate(codes["minizinc"]):
            print(f"Model: MiniZinc {n+1}")
            minizinc_result = runner.run(minizinc_code)
            new_instance.add(
                f"minizinc_solver_{n+1}",
                result=minizinc_result
                )
        
        new_instance.plot(
            outfile=f"Data/{name}/improvements_plots/compare_{r+1}_{solver_name}.png",
            print_figures=print_figures
            )
        instances.append(new_instance)

    if len(codes["dsl"]) > 0 and len(codes["minizinc"]) > 0:
        solver_1 = f"dsl_solver_1"
        solver_2 = f"minizinc_solver_1"
    elif len(codes['dsl']) >= 2:
        solver_1 = f"dsl_solver_1"
        solver_2 = f"dsl_solver_2"
    elif len(codes['minizinc']) >= 2:
        solver_1 = f"minizinc_solver_1"
        solver_2 = f"minizinc_solver_2"
    else:       
        print("Not enough solvers to compare for scatter plot.")
        return instances
    
    create_scatter_plot(
        instances,
        solver_1=solver_1,
        solver_2=solver_2,
        location=f"Data/{name}/scatter_plots/{solver_1}_vs_{solver_2}.png",
        print_figures=print_figures
        )
    return instances


def create_scatter_plot(
        instances,
        solver_1: str,
        solver_2: str,
        location="scatter_plot.png",
        print_figures: bool = False
        ):
    "Given a list of solvers and recorded instances, create a scatter plot comparing their times."
    
    times_solver_1 = []
    times_solver_2 = []
    for inst in instances:
        times_solver_1.append(inst.get_timings(solver = solver_1))
        times_solver_2.append(inst.get_timings(solver = solver_2))
    plt.figure()
    plt.scatter(times_solver_1, times_solver_2)
    plt.xlabel("DSL solve time (s)")
    plt.ylabel("MiniZinc solve time (s)")
    plt.title("Solve time comparison")

    # Optional: y=x reference line
    lo = float(min(min(times_solver_1), min(times_solver_2)))
    hi = float(max(max(times_solver_1), max(times_solver_2)))
    plt.plot([lo, hi], [lo, hi])  # default styling

    plt.tight_layout()
    location_file = Path(location)
    location_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(location, dpi=200)
    if print_figures:
        plt.show()
    plt.close()