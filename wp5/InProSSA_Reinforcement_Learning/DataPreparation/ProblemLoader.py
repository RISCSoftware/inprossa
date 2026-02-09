import os
import json
import numpy as np

def load_problem(filename, base_path="instances"):
    full_path = os.path.join(base_path, filename)

    # Check if the path exists
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Could not find the file: {full_path}")

    # Load the json instance
    with open(full_path, "r") as f:
        data = json.load(f)

    coords = np.array(data["coords"])

    num_cities = len(coords)
    dist_matrix = np.zeros((num_cities, num_cities))
    for i in range(num_cities):
        for j in range(num_cities):
            dist_matrix[i][j] = np.linalg.norm(coords[i] - coords[j])

    return dist_matrix, coords