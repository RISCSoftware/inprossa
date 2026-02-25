import json
import os

import pandas as pd
from handcrafted_2d_bin_packing import apply_handcrafted

objective_val_results_filepath = "objective_values_n20.csv"
objective_val_results_scatterplot_filepath = "objective_values_n20_scatterplot.csv"
solve_time_results_filepath = "solvetimes_values_n20.csv"
solve_time_results_scatterplot_filepath = "solvetimes_values_n20_scatterplot.csv"
directory = "testset_paper_2D-BPP_CLASS_run1"
def extract_objective_value_scatterplot_data(directories: list[str], handcrafted_objective_val, include_label: bool = False):
    handcrafted = []
    tot = []
    grouplabels = []

    for dir in directories:
        # Extract objective values from test results and merge them with respective handcrafted obj. val.
        files = []
        for root, dirs, files in os.walk(dir):
            for file in files:
                if file.endswith(".json"):
                    files.append(os.path.join(root, file))
        if len(handcrafted_objective_val) != len(files): raise ValueError("handcrafted_objective_val must have same length as files")
        for i, filepath in enumerate(files):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for model in data:
                handcrafted.append(handcrafted_objective_val[i])
                tot.append(model["objective_val"])
                grouplabels.append(i)
    df = pd.DataFrame({
        'handcrafted': handcrafted,
        'tot': tot,
        'grouplabels': grouplabels
    })
    df.to_csv(objective_val_results_filepath, index=False)

    # Count unique pairs
    pair_counts = {}
    if include_label:
        for h, t, l in zip(handcrafted, tot, grouplabels):
            pair = (h, t, l)
            if pair in pair_counts:
                pair_counts[pair] += 1
            else:
                pair_counts[pair] = 1
        df = pd.DataFrame(
            [(first, second, third, count) for (first, second, third), count in pair_counts.items()],
            columns=['handcrafted', 'tot', 'grouplabels', 'count']
        )
    else:
        for h, t in zip(handcrafted, tot):
            pair = (h, t)
            if pair in pair_counts:
                pair_counts[pair] += 1
            else:
                pair_counts[pair] = 1
        df = pd.DataFrame(
            [(first, second, count) for (first, second), count in pair_counts.items()],
            columns=['handcrafted', 'tot', 'count']
        )
    df.to_csv(objective_val_results_scatterplot_filepath, index=False)

def extract_solve_time_scatterplot_data(directories: list[str], handcrafted_solvetime, include_label: bool = False):
    handcrafted = []
    tot = []
    grouplabels = []

    better_than_handcrafted = 0
    for dir in directories:
        # Extract solve times from test results and merge them with respective handcrafted obj. val.
        files = [file for file in os.listdir(dir) if file.endswith(".json")]
        if len(handcrafted_solvetime) != len(files): raise ValueError("handcrafted_solve_times must have same length as files")
        for i, filename in enumerate(files):
            if filename.endswith(".json"):
                filepath = os.path.join(dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for model in data:
                    handcrafted.append(handcrafted_solvetime[i])
                    tot.append(model["solve_time"],8)
                    grouplabels.append(i)
                    better_than_handcrafted += 1
    print(f"better_than_handcrafted:{better_than_handcrafted}")
    df = pd.DataFrame({
        'handcrafted': handcrafted,
        'tot': tot,
        'grouplabels': grouplabels
    })
    df.to_csv(solve_time_results_filepath, index=False)

    # Count unique pairs
    pair_counts = {}
    if include_label:
        for h, t, l in zip(handcrafted, tot, grouplabels):
            pair = (h, t, l)
            if pair in pair_counts:
                pair_counts[pair] += 1
            else:
                pair_counts[pair] = 1
        df = pd.DataFrame(
            [(first, second, third, count) for (first, second, third), count in pair_counts.items()],
            columns=['handcrafted', 'tot', 'grouplabels', 'count']
        )
    else:
        for h, t in zip(handcrafted, tot):
            pair = (h, t)
            if pair in pair_counts:
                pair_counts[pair] += 1
            else:
                pair_counts[pair] = 1
        df = pd.DataFrame(
            [(first, second, count) for (first, second), count in pair_counts.items()],
            columns=['handcrafted', 'tot', 'count']
        )
    df.to_csv(solve_time_results_scatterplot_filepath, index=False)

if __name__ == '__main__':
    directories = ["testset_paper_2D-BPP_CLASS_run1", "testset_paper_2D-BPP_CLASS_run2", "testset_paper_2D-BPP_CLASS_run3", "testset_paper_2D-BPP_CLASS_run4", "testset_paper_2D-BPP_CLASS_run5"]
    # handcrafted_objective_values, handcrafted_solve_times = apply_handcrafted("../problem_descriptions/testset_paper_2D-BPP_CLASS/", object_types_are_fixed=False)
    # handcrafted_objective_values, handcrafted_solve_times = apply_handcrafted("../problem_descriptions/testset_fixed_objects_2D-BPP_CLASS/", object_types_are_fixed=True)

    # extract_objective_value_scatterplot_data(directories,[6,1,1,4,7,1,5,1,1,6,7,4,7,5,13,16,9,3,5,5], True)
    extract_objective_value_scatterplot_data(directories, [6, 1, 1, 2, 6, 1, 3, 1, 1, 5, 5, 3, 7, 5, 13, 2, 5, 2, 4, 4], True)
    # extract_solve_time_scatterplot_data(directories, [0.074, 0.028, 0.04, 0.079, 0.041, 0.029, 0.051, 0.05, 0.045, 1.419, 14.992, 0.086, 0.798, 0.082, 16.78, 149.817, 0.129, 0.045, 0.08, 0.262])
    # extract_solve_time_scatterplot_data(directories,
    #                                    [0.064, 0.018, 0.016, 0.031, 0.023, 0.017, 0.026, 0.025, 0.032, 1.162, 11.495, 0.047, 0.272, 0.077, 8.645, 149.883, 0.087, 0.019, 0.039, 0.09])
