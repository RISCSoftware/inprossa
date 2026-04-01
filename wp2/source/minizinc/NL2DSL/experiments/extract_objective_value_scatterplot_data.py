import json
import os

import pandas as pd
from handcrafted_2d_bin_packing import apply_handcrafted

scatterplot_folder_path = "scatterplot_data_handcrafted_vs_ToT"
cum_graph_folder_path = "cum_graph_data_handcrafted_vs_ToT"
#objective_val_results_filepath = "objective_values_n20.csv"
objective_val_results_scatterplot_filepath = "objective_values_n20_scatterplot.csv"
#solve_time_results_filepath = "solvetimes_values_n20.csv"
solve_time_results_scatterplot_filepath = "solvetimes_values_n20_scatterplot.csv"
objective_val_results_cum_graph_filepath = "objective_values_n20_cum_graph.csv"
solve_time_results_cum_graph_filepath = "solvetimes_values_n20_cum_graph.csv"


def extract_objective_value_scatterplot_data(directory: str, handcrafted_objective_val, include_label: bool = False):
    handcrafted = []
    tot = []
    grouplabels = []

    os.makedirs(scatterplot_folder_path, exist_ok=True)

    directories = [os.path.join(directory, f) for f in os.listdir(directory) if
                   os.path.isdir(os.path.join(directory, f))]
    for dir in directories:
        # Extract objective values from test results and merge them with respective handcrafted obj. val.
        files = [os.path.join(directory, file) for file in os.listdir(dir) if file.endswith(".json")]
        if len(handcrafted_objective_val) != len(files): raise ValueError(
            "handcrafted_objective_val must have same length as files")
        for i, filepath in enumerate(files):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for model in data:
                handcrafted.append(handcrafted_objective_val[i])
                tot.append(model["objective_val"])
                grouplabels.append(i)
    #df = pd.DataFrame({
    #    'handcrafted': handcrafted,
    #    'tot': tot,
    #    'grouplabels': grouplabels
    #})
    #df.to_csv(scatterplot_folder_path + "/" + objective_val_results_filepath, index=False)

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
    df.to_csv(scatterplot_folder_path + "/" + objective_val_results_scatterplot_filepath, index=False)


def extract_solve_time_scatterplot_data(directory: str, handcrafted_solvetime: list, handcrafted_objective_val: list,
                                        include_label: bool = False):
    handcrafted = []
    tot = []
    grouplabels = []

    better_than_handcrafted_solvetime_percentage = 0
    better_than_handcrafted_solvetime = 0
    directories = [os.path.join(directory, f) for f in os.listdir(directory) if
                   os.path.isdir(os.path.join(directory, f))]

    os.makedirs(scatterplot_folder_path, exist_ok=True)

    for dir in directories:
        # Extract solve times from test results and merge them with respective handcrafted obj. val.
        files = [file for file in os.listdir(dir) if file.endswith(".json")]
        if len(handcrafted_solvetime) != len(files): raise ValueError(
            "handcrafted_solve_times must have same length as files")
        for i, filename in enumerate(files):
            filepath = os.path.join(dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for model in data:
                if model["solve_time"] is None or model["solve_time"] >= 151:
                    continue
                if model["solve_time"] < 149.2 and model["objective_val"] > handcrafted_objective_val[i]:
                    continue
                handcrafted.append(handcrafted_solvetime[i])
                tot.append(model["solve_time"])
                grouplabels.append(i)
                if model["solve_time"] < handcrafted_solvetime[i] and better_than_handcrafted_solvetime < (
                    handcrafted_solvetime[i] - model["solve_time"]):
                    better_than_handcrafted_solvetime = handcrafted_solvetime[i] - model["solve_time"]
                    better_than_handcrafted_solvetime_percentage = (
                            (handcrafted_solvetime[i] - model["solve_time"]) / handcrafted_solvetime[i])
    print(f"average solvetime decrease: {better_than_handcrafted_solvetime_percentage}")
    #df = pd.DataFrame({
    #    'handcrafted': handcrafted,
    #    'tot': tot,
    #    'grouplabels': grouplabels
    #})
    #df.to_csv(scatterplot_folder_path + "/" + solve_time_results_filepath, index=False)

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
    df.to_csv(scatterplot_folder_path + "/" + solve_time_results_scatterplot_filepath, index=False)


def extract_solve_times_cum_graph(directory: str, handcrafted_solvetime: list, handcrafted_objective_val: list):
    collected_results = {"y": [i for i in range(1,len(handcrafted_solvetime)+1)]}
    files = [
        os.path.join(root, file)
        for root, dirs, files in os.walk(directory)
        for file in files
        if file.endswith(".json")
    ]
    for e, filepath in enumerate(files):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for i, model in enumerate(data):
            existing_solvetimes = collected_results[
                f"formulation_{i}"] if f"formulation_{i}" in collected_results else []
            if not (model["solve_time"] - handcrafted_solvetime[i] < -0.5 and model["objective_val"] > \
                handcrafted_objective_val[i]):
                existing_solvetimes.append(model["solve_time"])
            collected_results.update({f"formulation_{i}": existing_solvetimes})

    for i in range(len(collected_results.keys())-1):
        collected_results[f"formulation_{i}"].sort()

    handcrafted_solvetime.sort()
    collected_results.update({"handcrafted": handcrafted_solvetime})

    df = pd.DataFrame(dict([(k, pd.Series(v)) if k == "y" else (k, pd.Series(v).cumsum()) for k, v in collected_results.items()]))

    os.makedirs(cum_graph_folder_path, exist_ok=True)
    df.to_csv(cum_graph_folder_path + "/" + solve_time_results_cum_graph_filepath, index=False)


if __name__ == '__main__':
    directory = "experiment_2D-BPP_CLASS_flex_shapes"
    # handcrafted_objective_values, handcrafted_solve_times = apply_handcrafted("../problem_descriptions/experiment_2D-BPP_CLASS_flex_shapes/", object_types_are_fixed=False)
    # handcrafted_objective_values, handcrafted_solve_times = apply_handcrafted("../problem_descriptions/testset_fixed_objects_2D-BPP_CLASS/", object_types_are_fixed=True)

    # paper testset and result extraction
    # extract_objective_value_scatterplot_data(directories,[6,1,1,4,7,1,5,1,1,6,7,4,7,5,13,16,9,3,5,5], True)
    #extract_solve_time_scatterplot_data(directories,
    #                                    [0.064, 0.018, 0.016, 0.031, 0.023, 0.017, 0.026, 0.025, 0.032, 1.162, 11.495, 0.047, 0.272, 0.077, 8.645, 149.883, 0.087, 0.019, 0.039, 0.09],
    #                                    [6,1,1,4,7,1,5,1,1,6,7,4,7,5,13,16,9,3,5,5])

    # random seed 0
    # extract_solve_time_scatterplot_data(directory,
    #                                     [0.238, 0.105, 0.11299999999999999, 0.155, 0.111, 0.124, 0.136, 0.14200000000000002, 0.163, 1.98, 16.258999999999997, 0.192, 0.446, 0.163, 12.372, 149.821, 0.21300000000000002, 0.13, 0.194, 0.313],
    #                                     [6, 1, 1, 4, 7, 1, 5, 1, 1, 6, 7, 4, 7, 5, 13, 16, 9, 3, 5, 5])

    #extract_solve_time_scatterplot_data(directories,
    #                                    [0.253, 0.2, 5.317, 0.20400000000000001, 0.249, 0.167, 0.274, 0.285, 0.97, 1.3290000000000002, 23.299999999999997, 0.269, 1.082, 0.581, 11.807, 150.05299999999997, 0.325, 0.20400000000000001, 0.22499999999999998, 0.919],
    #                                    [6, 1, 1, 4, 7, 1, 5, 1, 1, 6, 7, 4, 7, 5, 13, 16, 9, 3, 5, 5])

    # fixed-shapes testset and result extraction
    extract_solve_times_cum_graph("experiment_2D-BPP_CLASS_fixed_shapes",
                                  [0.265, 0.2, 5.398999999999999, 0.21799999999999997, 0.253, 0.14700000000000002, 0.265, 0.348, 0.944, 1.1889999999999998, 34.32, 0.262, 0.573, 0.539, 9.159, 149.922, 0.29000000000000004, 0.155, 0.20500000000000002, 0.6910000000000001],
                                  [6, 1, 1, 4, 7, 1, 5, 1, 1, 6, 7, 4, 7, 5, 13, 16, 9, 3, 5, 5])
