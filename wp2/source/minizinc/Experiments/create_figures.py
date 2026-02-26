import matplotlib.pyplot as plt
from pathlib import Path

from Experiments.Instance import InstanceProgress
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner


def improvement_and_scatter_plots(
        code_generating_function,
        n_items,
        repeats=2,
        name: str = "unknown",
        solver_name: str = "gecode",
        timelimit: int = 10,
        print_figures: bool = False):
    runner = MiniZincRunner(solver_name=solver_name, timelimit=timelimit)

    instances = []

    for r in range(repeats):
        print("\n    Instance:", r+1)
        new_instance = InstanceProgress(f"b{name}_run{r+1}")
        codes = code_generating_function(n_items=n_items)

        if "dsl" in codes and len(codes["dsl"]) > 0:
            for n, dsl_code in enumerate(codes["dsl"]):
                translator = MiniZincTranslator(dsl_code)
                mzn_model = translator.unroll_translation()

                print(f"Model: DSL {n+1}")
                dsl_result = runner.run(mzn_model)
                new_instance.add(
                    f"dsl_formulation_{n+1}",
                    result=dsl_result
                    )
        if "minizinc" in codes and len(codes["minizinc"]) > 0:
            for n, minizinc_code in enumerate(codes["minizinc"]):
                print(f"Model: MiniZinc {n+1}")
                minizinc_result = runner.run(minizinc_code)
                new_instance.add(
                    f"minizinc_formulation_{n+1}",
                    result=minizinc_result
                    )
        
        new_instance.plot(
            outfile=f"Data/{name}/improvements_plots/compare_{r+1}_{solver_name}.png",
            print_figures=print_figures
            )
        instances.append(new_instance)

    if "dsl" in codes and "minizinc" in codes and len(codes["dsl"]) > 0 and len(codes["minizinc"]) > 0:
        formulation_1 = f"dsl_formulation_1"
        formulation_2 = f"minizinc_formulation_1"
    elif "dsl" in codes and len(codes['dsl']) >= 2:
        formulation_1 = f"dsl_formulation_1"
        formulation_2 = f"dsl_formulation_2"
    elif "minizinc" in codes and len(codes['minizinc']) >= 2:
        formulation_1 = f"minizinc_formulation_1"
        formulation_2 = f"minizinc_formulation_2"
    else:       
        print("Not enough solvers to compare for scatter plot.")
        return instances
    
    create_scatter_plot(
        instances,
        formulation_1="dsl_formulation_4",
        formulation_2="minizinc_formulation_1",
        location=f"Data/{name}/scatter_plots/dsl_formulation_4_vs_minizinc_formulation_1.png",
        print_figures=print_figures
        )
    
    create_scatter_plot(
        instances,
        formulation_1="dsl_formulation_4",
        formulation_2="minizinc_formulation_2",
        location=f"Data/{name}/scatter_plots/dsl_formulation_4_vs_minizinc_formulation_2.png",
        print_figures=print_figures
        )
    
    create_scatter_plot(
        instances,
        formulation_1=formulation_1,
        formulation_2=formulation_2,
        location=f"Data/{name}/scatter_plots/{formulation_1}_vs_{formulation_2}.png",
        print_figures=print_figures
        )
    return instances


def create_scatter_plot(
        instances,
        formulation_1: str,
        formulation_2: str,
        location="scatter_plot.png",
        print_figures: bool = False
        ):
    "Given a list of solvers and recorded instances, create a scatter plot comparing their times."
    
    times_formulation_1 = []
    times_formulation_2 = []
    for inst in instances:
        times_formulation_1.append(inst.get_timings(solver = formulation_1))
        times_formulation_2.append(inst.get_timings(solver = formulation_2))
    plt.figure()
    plt.scatter(times_formulation_1, times_formulation_2)
    plt.xlabel("DSL solve time (s)")
    plt.ylabel("MiniZinc solve time (s)")
    plt.title("Solve time comparison")

    # Optional: y=x reference line
    lo = float(min(min(times_formulation_1), min(times_formulation_2)))
    hi = float(max(max(times_formulation_1), max(times_formulation_2)))
    plt.plot([lo, hi], [lo, hi])  # default styling

    plt.tight_layout()
    location_file = Path(location)
    location_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(location, dpi=200)
    if print_figures:
        plt.show()
    plt.close()