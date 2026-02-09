import matplotlib.pyplot as plt

def show_tour(coords):
    # Create a copy so we don't modify the original list
    plot_coords = list(coords)
    plot_coords.append(coords[0])  # Add the start city to the end to close the loop

    x, y = zip(*plot_coords)

    plt.figure("Tour Visualization")
    plt.plot(x, y, marker='o', linestyle='-', color='b')
    plt.title("Final Tour Path")

    # This command triggers the popup window
    plt.show()