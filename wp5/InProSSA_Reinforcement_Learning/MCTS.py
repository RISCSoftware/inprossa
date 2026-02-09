from mcts.searcher.mcts import MCTS
from DataPreparation.ProblemLoader import load_problem
from Visualization.TspVisualizer import show_tour

# Load one of the generated TSP instances
VISUALIZE_RESULTS = True
ITERATIONS_AFTER_EACH_NODE = 100
DIST_MATRIX, CITY_COORDS = load_problem("tsp_instance_50.json")
NUM_CITIES = len(CITY_COORDS)

class TSPState:
    def __init__(self, visited_cities, current_city):
        self.visited_cities = visited_cities
        self.current_city = current_city

    # Change getPossibleActions -> get_possible_actions
    def get_possible_actions(self):
        all_cities = set(range(NUM_CITIES))
        visited = set(self.visited_cities)
        return list(all_cities - visited)

    # Change takeAction -> take_action
    def take_action(self, city_index):
        new_visited = self.visited_cities + [city_index]
        return TSPState(new_visited, city_index)

    # Change isTerminal -> is_terminal
    def is_terminal(self):
        return len(self.visited_cities) == NUM_CITIES

    # Change getReward -> get_reward
    def get_reward(self):
        total_dist = 0
        for i in range(len(self.visited_cities) - 1):
            u, v = self.visited_cities[i], self.visited_cities[i+1]
            total_dist += DIST_MATRIX[u][v]
        total_dist += DIST_MATRIX[self.visited_cities[-1]][self.visited_cities[0]]
        return 1000 / total_dist

    def get_current_player(self):
        return 1


initial_state = TSPState(visited_cities=[0], current_city=0)
searcher = MCTS(iterationLimit=ITERATIONS_AFTER_EACH_NODE) # Ensure MCTS is capitalized if using the searcher module

current_state = initial_state
while not current_state.is_terminal():  # Updated name
    action = searcher.search(initial_state=current_state)
    current_state = current_state.take_action(action)  # Updated name
    print(f"Visited City: {action}")


final_path = current_state.visited_cities
print(f"\nFinal Tour: {final_path}")

# Calculate final distance
final_dist = 1000 / current_state.get_reward()
print(f"Total Distance: {final_dist:.2f}")

if VISUALIZE_RESULTS:
    # Create a list of (x, y) tuples based on the city IDs in final_path
    coords_to_plot = [CITY_COORDS[city_id] for city_id in final_path]
    show_tour(coords_to_plot)