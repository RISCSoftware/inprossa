import subprocess
import json
from pathlib import Path
from IncrementalPipeline.Translator.config2boards import (
    convert_inputboards_to_boards
    )


def run_problem_data_generator(n_boards: int,
                               d: float = 0.5,
                               b: float = 0.5,
                               random_seed: int = 0):
    """
    Run the problem data generator script and return the generated data.
    """
    # Path to the current file
    current_dir = Path(__file__).resolve().parent

    # Go up to wp2/source/
    source_dir = current_dir.parent.parent.parent

    # Path to main.py in problem-data-generator
    script_path = (
        source_dir
        / "problem-data-generator"
        / "problem_data_generator"
        / "main.py"
    )

    # Path to venv python
    venv_python = source_dir.parent.parent / "venv" / "Scripts" / "python.exe"

    cmd = [
        str(venv_python),
        str(script_path),
        "--boards", str(n_boards),
        "-d", str(d),
        "-b", str(b),
        "-random-seed", str(random_seed)
    ]
    # Run the script and capture its output
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Error running script:")
        print(result.stderr)
    else:
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Could not parse JSON output:")
            print(result.stdout)

    list_of_boards = convert_inputboards_to_boards(data["InputBoards"])

    return list_of_boards  # Return the processed list of boards


if __name__ == "__main__":
    # Example usage
    n_boards = 5  # Specify the number of boards you want to generate
    random_seed = 42  # Specify a random seed for reproducibility
    first_run_output = run_problem_data_generator(n_boards,
                                                  random_seed=random_seed)
    print([elem.__dict__ for elem in first_run_output])

    # Check if run two times same output
    random_seed = 41
    second_run_output = run_problem_data_generator(n_boards,
                                                   random_seed=random_seed)
    print([elem.__dict__ for elem in second_run_output])
    if first_run_output == second_run_output:
        print("Both runs produced the same output.")
    else:
        print("The outputs differ between runs.")
