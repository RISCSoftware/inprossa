
import csv
from pathlib import Path


def instances_to_csv(instances, file: str, *, filename: str = "all_timings.csv") -> Path:
    """
    Create a CSV with one row per instance and one column per solver/approach.
    Uses instance.get_all_timings().

    Parameters
    ----------
    instances : iterable of InstanceProgress
    file : str
        Either a directory path (e.g., "Data/bin_packing_with_cutting/")
        or a full CSV path (e.g., "Data/bin_packing_with_cutting/all_timings.csv")
    filename : str
        Used only if `file` is a directory path.

    Returns
    -------
    Path
        The written CSV path.
    """
    instances = list(instances)

    # Collect all solver names appearing across instances
    solver_names = sorted({
        solver
        for inst in instances
        for solver in inst.get_all_timings().keys()
    })

    # Resolve output path
    outpath = Path(file)
    if outpath.suffix.lower() != ".csv":
        outpath.mkdir(parents=True, exist_ok=True)
        outpath = outpath / filename
    else:
        outpath.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV
    fieldnames = ["instance_id"] + solver_names
    with outpath.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for inst in instances:
            timings = inst.get_all_timings()
            row = {"instance_id": inst.instance_id}
            for solver in solver_names:
                row[solver] = timings.get(solver, "")  # empty if missing
            writer.writerow(row)

    return outpath


from Projects.BinPackingWithCutting.templates import create_bin_packing_codes
from Experiments.create_figures import improvement_and_scatter_plots

if __name__ == "__main__":

    instances = improvement_and_scatter_plots(
        code_generating_function=create_bin_packing_codes,  
        n_items=6,
        repeats=20,
        name="bin_packing_with_cutting",#
        timelimit=60,
        solver_name="chuffed",
        )
    
    instances_to_csv(instances=instances, file="Data/bin_packing_with_cutting/")

