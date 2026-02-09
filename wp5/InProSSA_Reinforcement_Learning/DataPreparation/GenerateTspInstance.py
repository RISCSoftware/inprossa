import numpy as np
import json
import os


def generate_and_save_tsp(num_nodes, folder="instances"):
    """
    Generates a TSP instance and saves it to a JSON file in a subfolder.
    """
    # 1. Create the subfolder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Created folder: {folder}")

    # 2. Generate random coordinates (0 to 100 range)
    # Using a seed for the generation process ensures consistency if needed
    coords = np.random.rand(num_nodes, 2) * 100

    # 3. Prepare the data structure
    data = {
        "name": f"tsp_{num_nodes}_nodes",
        "num_nodes": num_nodes,
        "coords": coords.tolist()  # Convert numpy array to list for JSON
    }

    # 4. Define filename and save
    filename = os.path.join(folder, f"tsp_instance_{num_nodes}.json")

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Successfully saved {num_nodes} node instance to: {filename}")


# --- Execution ---
if __name__ == "__main__":
    # Define the sizes you want
    node_counts = [10, 50, 100]

    # Generate them
    for count in node_counts:
        generate_and_save_tsp(count)

    print("\nAll instances generated in the /instances folder.")