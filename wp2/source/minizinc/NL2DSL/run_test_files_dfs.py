import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import constants

def paper_20_CLASS_5_tot_flex_shapes():
    """
        Create 5 Trees of Thoughts (each with max. 16 formulations) for each of the 20 2dPackLib instances
        Creates raw data files of results: formulations in json files + correctness_results.txt in experiments/experiment_<date>
    """
    directory = constants.GENERATION_INST_DIR
    formatted = datetime.now().strftime("%Y-%m-%d_%H-%M")

    # generate 5 ToT per instances
    for i in range(5):
        for filename in os.listdir(directory):
            if not filename.endswith(".json"):
                continue

            with open("correctness_results.txt", "a", encoding="utf-8") as f:
                f.write(f"{filename}: ")
            filepath = os.path.join(directory, filename)
            print(f"""----------------------------------------------------------------------------
            Starting run for {filename}: """)
            proc = subprocess.Popen([sys.executable,
                                     "tree_search_dfs.py",
                                     "--problem_instance",
                                     filepath,
                                     "--problem_description",
                                     "problem_descriptions/2d_bin_packing_without_input.json",
                                     "-m",
                                     "flex_objects_fixed_input_values"])
            try:
                proc.wait()  # wait up to 90 minutes
            except subprocess.TimeoutExpired:
                print("Timeout — killing process")
                proc.kill()
                proc.wait()  # ensure it’s dead
            except KeyboardInterrupt:
                # do nothing
                var = 1
            finally:
                proc.terminate()
        _move_all_model_files_into_folder(f"experiments/experiment_{formatted}/20_inst_2D-BPP_CLASS_run{i}/")
        _move_file(f"experiments/experiment_{formatted}/20_inst_2D-BPP_CLASS_run{i}/",
                  "correctness_results.txt")
    return f"experiment_{formatted}"

def paper_20_CLASS_1_tot_fixed_shapes():
    """
        Create 1 Tree of Thoughts (with max. 16 formulations) and reuse each formulation for each of the remaining 19 2dPackLib instances
        Creates raw data files of results: formulations in json files in experiments/experiment_<date>
    """
    directory = constants.GENERATION_INST_DIR
    formatted = datetime.now().strftime("%Y-%m-%d_%H-%M")
    files = os.listdir(directory)
    files.sort()
    filename = files[0]
    filepath = os.path.join(directory, filename)
    print(f"""----------------------------------------------------------------------------
        Starting run for {filename}: """)

    with open("correctness_results.txt", "a", encoding="utf-8") as f:
        f.write(f"{filename}: ")
    proc = subprocess.Popen([sys.executable,
                             "tree_search_dfs.py",
                             "--problem_instance",
                             filepath,
                             "--problem_description",
                             "problem_descriptions/2d_bin_packing_without_inoutput.json",
                             "-m",
                             "fixed_objects_fixed_inoutput_values"])
    try:
        proc.wait()  # wait up to 90 minutes
    except subprocess.TimeoutExpired:
        print("Timeout — killing process")
        proc.kill()
        proc.wait()  # ensure it’s dead
    except KeyboardInterrupt:
        # do nothing
        print("UI, keyboard interrupt")
    finally:
        proc.terminate()
    os.makedirs(f"experiments/experiment_{formatted}", exist_ok=True)
    _move_all_model_files_into_folder(f"experiments/experiment_{formatted}/reusable_model")
    _move_file(f"experiments/experiment_{formatted}/reusable_model/",
              "correctness_results.txt")
    _reuse_model(f"experiments/experiment_{formatted}/reusable_model/", files, directory)

    return f"experiment_{formatted}"

def _move_all_model_files_into_folder(destination_folder: str):
    """
    Moves all json model formulation files (start with "optDSL_models_") and run_logs.log file into destination folder.
    Args:
        destination_folder: destination folder
    """
    os.makedirs(destination_folder, exist_ok=True)
    # move resulting ToT models
    for filename in os.listdir():
        if filename.startswith("optDSL_models_") and ((filename.endswith(".json")) or filename == "correctness_results.txt"):
            _move_file(destination_folder, filename)

    # move log file
    src = os.path.join(os.getcwd(), "run_logs.log")
    dst = os.path.join(os.path.join(os.getcwd(), destination_folder), "run_logs.log")
    if os.name == "nt":
        dst = dst.replace("/", "\\")
    try:
        os.rename(src, dst)
    except Exception:
        print("logs file needs to be moved, if existent.")

def _move_file(destination_folder: str, filename: str):
    """
    Moves filename to destination folder.
    Args:
        destination_folder: destination folder
        filename: filename to move
    """
    src = os.path.join(os.getcwd(), filename)
    dst = os.path.join(destination_folder, filename)
    if os.name == "nt":
        dst = dst.replace("/", "\\")
    os.rename(src, dst)


def _reuse_model(reusable_model_file_path: str, files: list[str], directory: str):
    """
    Reuse one model formulation for multiple instances.
    Args:
        reusable_model_file_path: path to reusable model formulation file
        files: list of instance files to reuse
        directory: folder where instance files are located
    """
    reusable_model_file= [file for file in os.listdir(reusable_model_file_path) if file.endswith(".json")][0]
    for filename in files:
        filepath = os.path.join(directory, filename)
        print(f"""----------------------------------------------------------------------------
Starting run for writing reused model for instance {filename}: """)
        proc = subprocess.Popen([sys.executable,
                                 "tree_search_dfs.py",
                                 "--reusable_model_file_path",
                                 os.path.join(reusable_model_file_path, reusable_model_file),
                                 "--new_instance_filename",
                                 filepath,
                                 "-m",
                                 "reuse_model_fixed_inoutput_values"])
        try:
            proc.wait()  # wait up to 90 minutes
        except subprocess.TimeoutExpired:
            print("Timeout — killing process")
            proc.kill()
            proc.wait()  # ensure it’s dead
        except KeyboardInterrupt:
            # do nothing
            m = 1
        finally:
            proc.terminate()

def update_tree_collection_correctness_results_with_objective(tree_collection_path: str,
                                                              handcrafted_objective_values: list,
                                                              execute_for_reused_formulations: bool = False):
    """
    Extend correctness results of formulations (file) with the number of formulations,
    which yielded optimal formulations (given that objective values of the handcrafted formulation are viewed as optimal).
    Args:
        tree_collection_path (str): path to where all files of ToT are located (correctness_results.txt, model_<date>.json etc.)
        handcrafted_objective_values (list): list of objective values yielded by the handcrafted formulation for various instances
        execute_for_reused_formulations (bool): indicates if the current generation process is done for reusable or non-reusable formulations.
    """
    if execute_for_reused_formulations:
        formulations = list(Path(tree_collection_path).rglob("*.json"))
        formulations.insert(0, formulations.pop())  # put original reusable formulation in folder at first position to match with handcrafted
        correctness_results_file = str(Path(tree_collection_path).joinpath("reusable_model/correctness_results.txt"))
        correctness_results = _read_correctness_results(correctness_results_file) * len(formulations)
        _update_correctness_results_optimal(correctness_results,
                                            formulations,
                                            correctness_results_file,
                                            handcrafted_objective_values)
    else:
        # Iterate over the (5) different runs within the experiments and count how many formulations
        # yield an optimal solution per run and add it to the correctness results.
        for subdir in Path(tree_collection_path).iterdir():
            if not subdir.is_dir(): continue
            correctness_results = _read_correctness_results(str(subdir.joinpath("correctness_results.txt")))
            _update_correctness_results_optimal(correctness_results,
                                                subdir.glob("*.json"),
                                                str(subdir.joinpath("correctness_results.txt")),
                                                handcrafted_objective_values)

def _update_correctness_results_optimal(correctness_results: list,
                                    formulations,
                                    correctness_results_file_path: str,
                                    handcrafted_objective_values: list):
    """
    Given the formulations' objective values, compare to optimal objective values yielded by handcrafted formulation,
    count the number of formulations reaching the optimal solution and extend the correctness_results file with that information.
    Args:
        correctness_results (list): correctness results from file as list to be extended
        formulations (list): list of formulations (incl. their objective values)
        correctness_results_file_path (str): path to correctness_results.txt file
        handcrafted_objective_values (list): list of objective values yielded by handcrafted formulation
    """
    for i, json_file in enumerate(formulations):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle different JSON structures safely
        if isinstance(data, list):
            optimals = 0
            valids = 0
            sem_invalids = 0
            for formulation in data:
                if "Successfully" in formulation["final_evaluation_result"]:
                    if int(formulation["objective_val"]) == handcrafted_objective_values[i]:
                        optimals += 1
                    else:
                        valids += 1
                    # formulation was reused, potentially one might fail the run
                    if formulation["script_generated_objects"] != "" or formulation["script_generated_objects"] is not None:
                        if "Failed" in formulation["final_evaluation_result"]: sem_invalids += 1
            correctness_results[i]["file"] = json_file.name
            correctness_results[i]["optimal"] = optimals
            correctness_results[i]["valid"] = valids
            correctness_results[i]["sem_invalid"] += sem_invalids
        else:
            print(f"Failed to update correctness results in {json_file.name}")
    _update_correctness_results_file(correctness_results_file_path, correctness_results)

def _read_correctness_results(correctness_results_file_path: str):
    """
        Read and extract correctness results from correctness_results.txt file to list of dicts.
        Args:
            correctness_results_file_path (str): path to correctness_results.txt file
    """
    extracted_data = []
    pattern = re.compile(
        r"([\w\d_\-.]+\.json):\s*"
        r"(\d+)\s+syntactically invalid,\s*"
        r"(\d+)\s+semantically invalid,\s*"
        r"(\d+)\s+valid"
    )
    with open(correctness_results_file_path, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                file = match.group(1)
                syn_invalid = int(match.group(2))
                sem_invalid = int(match.group(3))
                valid = int(match.group(4))

                extracted_data.append({
                    "file": file,
                    "syn_invalid": syn_invalid,
                    "sem_invalid": sem_invalid,
                    "valid": valid
                })
    return extracted_data

def _update_correctness_results_file(correctness_results_file_path: str,
                                     correctness_results: list):
    """
        Write correctness_results (extended by nr. of optimal formulations) to correctness_results.txt file.
        Args:
            correctness_results_file_path (str): path to correctness_results.txt file
            correctness_results (list): correctness results from file as list to be extended
    """
    with open(correctness_results_file_path, "w", encoding="utf-8") as f:
        for i, c in enumerate(correctness_results):
            f.write(f"{c["file"]} (formulations for instance {i+1}): {c["syn_invalid"]} syntactically invalid, {c["sem_invalid"]} semantically invalid, {c["valid"]} valid, {c["optimal"]} optimal" + "\n")



#if __name__ == '__main__':
    #paper_20_CLASS_5_tot_flex_shapes()
    #paper_20_CLASS_1_tot_fixed_shapes()
