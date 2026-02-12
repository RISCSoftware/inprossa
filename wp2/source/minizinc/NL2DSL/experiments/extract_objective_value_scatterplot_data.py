import json
import os
import statistics

import pandas as pd

objective_val_results_filepath = "objective_values_n10.csv"
objective_val_results_scatterplot_filepath = "objective_values_n10_scatterplot.csv"
solve_time_results_filepath = "solvetimes_values_n10.csv"
solve_time_results_scatterplot_filepath = "solvetimes_values_n10_scatterplot.csv"
directory = "testset_paper_2D-BPP_10-13.2"
def extract_objective_value_scatterplot_data(dir: str, handcrafted_objective_val):
    handcrafted = []
    tot = []
    grouplabels = []

    # Extract objective values from test results and merge them with respective handcrafted obj. val.
    files = [file for file in os.listdir(dir) if file.endswith(".json") and "_n10_" in file]
    if len(handcrafted_objective_val) != len(files): raise ValueError("handcrafted_objective_val must have same length as files")
    #files = sorted(
    #    files,
    #    key=lambda name: int(name.rsplit("_", 1)[-1].split(".")[0])
    #)
    for i, filename in enumerate(files):
        if filename.endswith(".json"):
            filepath = os.path.join(dir, filename)
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
    for h, t, l in zip(handcrafted, tot, grouplabels):
        pair = (h, t, l)  # create a tuple for this pair
        if pair in pair_counts:
            pair_counts[pair] += 1
        else:
            pair_counts[pair] = 1
    df = pd.DataFrame(
        [(first, second, third, count) for (first, second, third), count in pair_counts.items()],
        columns=['handcrafted', 'tot', 'grouplabels', 'count']
    )
    df.to_csv(objective_val_results_scatterplot_filepath, index=False)

def extract_solve_time_scatterplot_data(dir: str, handcrafted_solvetime):
    handcrafted = []
    tot = []
    grouplabels = []

    # Extract objective values from test results and merge them with respective handcrafted obj. val.
    files = [file for file in os.listdir(dir) if file.endswith(".json") and "_n10_" in file]
    if len(handcrafted_solvetime) != len(files): raise ValueError("handcrafted_solve_times must have same length as files")
    #files = sorted(
    #    files,
    #    key=lambda name: int(name.rsplit("_", 1)[-1].split(".")[0])
    #)
    for i, filename in enumerate(files):
        if filename.endswith(".json"):
            filepath = os.path.join(dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for model in data:
                handcrafted.append(handcrafted_solvetime[i])
                tot.append(model["solve_time"])
                grouplabels.append(i)
    df = pd.DataFrame({
        'handcrafted': handcrafted,
        'tot': tot,
        'grouplabels': grouplabels
    })
    df.to_csv(solve_time_results_filepath, index=False)
    print(f"mean: {statistics.median(tot)}")
    print(f"xmin: {min(handcrafted)}")
    print(f"xmax: {max(handcrafted)}")

    # Count unique pairs
    pair_counts = {}
    for h, t, l in zip(handcrafted, tot, grouplabels):
        pair = (h, t, l)  # create a tuple for this pair
        if pair in pair_counts:
            pair_counts[pair] += 1
        else:
            pair_counts[pair] = 1
    df = pd.DataFrame(
        [(first, second, third, count) for (first, second, third), count in pair_counts.items()],
        columns=['handcrafted', 'tot', 'grouplabels', 'count']
    )
    df.to_csv(solve_time_results_scatterplot_filepath, index=False)

if __name__ == '__main__':
    #extract_objective_value_scatterplot_data(directory,[4,2,4,4,3,4,3,4,4,5,6,5,4,4,5,4,2,4,6,4])
    extract_solve_time_scatterplot_data(directory, [0.023657, 0.893122, 0.12878, 0.168585, 0.889075, 3.96961, 2.08088, 2.08715, 31.1767, 0.336059, 19.3796, 5.26092, 11.0878, 1.23004, 0.97022, 1.8003, 0.009028, 0.483556, 17.8248, 0.569987])
