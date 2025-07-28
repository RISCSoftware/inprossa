

from IncrementalPipeline.experiments.create_list_boards import (
    run_problem_data_generator
)
from IncrementalPipeline.experiments.time_solution import (
    time_solution,
    time_solution_after_warm_start
)


if __name__ == "__main__":
    for i in range(1, 6):
        # Create input of that size
        input_list = run_problem_data_generator(n_boards=i)
        # Time the solution
        print(f"Testing input size: {i}", "type of input:", type(input_list))
        _, total_time = time_solution(input_list)
        time_taken = time_solution_after_warm_start(input_list)
        print(f"Input size: {i}, Time taken: {total_time:.2f} seconds")
        print(f"Time taken after warm start: {time_taken:.2f} seconds")
