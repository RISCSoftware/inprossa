import json
import os
import pandas as pd

results_filepath = "objective_values_n10.csv"
results_scatterplot_filepath = "objective_values_n10_scatterplot.csv"
directory = "testset_paper_2D-BPP_10-13.2"
def extract_objective_value_scatterplot_data(dir: str, handcrafted_objective_val):
    handcrafted = []
    tot = []
    grouplabels = []

    # Extract objective values from test results and merge them with respective handcrafted obj. val.
    files = [file for file in os.listdir(dir) if file.endswith(".json")]
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
        'tot': tot
    })
    df.to_csv(results_filepath, index=False)

    # Count unique pairs
    pair_counts = {}
    for h, t in zip(handcrafted, tot):
        pair = (h, t)  # create a tuple for this pair
        if pair in pair_counts:
            pair_counts[pair] += 1
        else:
            pair_counts[pair] = 1
    df = pd.DataFrame(
        [(first, second, count) for (first, second), count in pair_counts.items()],
        columns=['handcrafted', 'tot', 'count']
    )
    df.to_csv(results_scatterplot_filepath, index=False)

if __name__ == '__main__':
    extract_objective_value_scatterplot_data(directory,
                                             [4,4])
