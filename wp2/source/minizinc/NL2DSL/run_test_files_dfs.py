import os
import subprocess
import sys
from datetime import datetime

import constants

def move_all_model_files_into_folder(destination_folder: str):
    os.makedirs(destination_folder, exist_ok=True)
    # move resulting ToT models
    for filename in os.listdir():
        if filename.startswith("optDSL_models_") and filename.endswith(".json"):
            src = os.path.join(os.getcwd(), filename)
            dst = os.path.join(destination_folder, filename)
            os.rename(src, dst)

    # move log file
    src = os.path.join(os.getcwd(), "run_logs.log")
    dst = os.path.join(destination_folder, "run_logs.log")
    os.rename(src, dst)

def paper_20_CLASS_tot_runs():
    directory = "problem_descriptions/testset_paper_2D-BPP_CLASS/"
    formatted = datetime.now().strftime("%Y-%m-%d_%H:%M")
    #files = sorted(
    #    os.listdir(directory),
    #    key=lambda name: int(name.rsplit("_", 1)[-1].split(".")[0])
    #)
    for i in range(5):
        for filename in os.listdir(directory):
            if (not filename.endswith(".json")):
                continue
            filepath = os.path.join(directory, filename)
            print(f"""----------------------------------------------------------------------------
            Starting run for {filename}: """)
            proc = subprocess.Popen([sys.executable,
                                     "tree_search_dfs.py",
                                     "--problem_instance",
                                     filepath,
                                     "--problem_description",
                                     "problem_descriptions/2d_bin_packing_inst_1_without_input.json",
                                     "-m",
                                     "flex_objects_fixed_input_values"])
            try:
                proc.wait()  # wait up to 90 minutes
            except subprocess.TimeoutExpired:
                print("Timeout — killing process")
                proc.kill()
                proc.wait()  # ensure it’s dead
            except KeyboardInterrupt as e:
                # do nothing
                m = 1
            finally:
                proc.terminate()
        move_all_model_files_into_folder(f"experiment_{formatted}/20_inst_2D-BPP_CLASS_run{i}/")

def bot_without_semantic_feedback_20_bot_runs():
    directory = "problem_descriptions/"
    input_instance_files = ["2d_bin_packing_input_inst_1.json", "2d_bin_packing_input_inst_2.json", "2d_bin_packing_input_inst_3.json", "2d_bin_packing_input_inst_4.json"]
    constants.NR_MAX_CHILDREN = 1
    for _ in range(20):
        for filename in input_instance_files:
            if (not filename.endswith(".json")):
                continue
            filepath = os.path.join(directory, filename)
            print(f"""----------------------------------------------------------------------------
            Starting run for {filename}: """)
            proc = subprocess.Popen([sys.executable,
                                     "tree_search_dfs.py",
                                     "--problem_instance",
                                     filepath,
                                     "--problem_description",
                                     "problem_descriptions/2d_bin_packing_inst_1_without_input.json",
                                     "-m",
                                     "flex_objects_fixed_input_values"])
            try:
                proc.wait()  # wait up to 90 minutes
            except subprocess.TimeoutExpired:
                print("Timeout — killing process")
                proc.kill()
                proc.wait()  # ensure it’s dead
            except KeyboardInterrupt as e:
                # do nothing
                m = 1
            finally:
                proc.terminate()

def CLASS_tot_with_semantic_feedback():
    directory = "problem_descriptions/testset_fixed_objects_2D-BPP_CLASS/"
    formatted = datetime.now().strftime("%Y-%m-%d_%H:%M")
    files = os.listdir(directory)
    files.sort()
    # filename = files[0]
    # filepath = os.path.join(directory, filename)
    # print(f"""----------------------------------------------------------------------------
    #     Starting run for {filename}: """)
    # proc = subprocess.Popen([sys.executable,
    #                          "tree_search_dfs.py",
    #                          "--problem_instance",
    #                          filepath,
    #                          "--problem_description",
    #                          "problem_descriptions/2d_bin_packing_inst_1_without_inoutput.json",
    #                          "-m",
    #                          "fixed_objects_fixed_inoutput_values"])
    # try:
    #     proc.wait()  # wait up to 90 minutes
    # except subprocess.TimeoutExpired:
    #     print("Timeout — killing process")
    #     proc.kill()
    #     proc.wait()  # ensure it’s dead
    # except KeyboardInterrupt as e:
    #     # do nothing
    #     m = 1
    #     print("UI, keyboard interrupt")
    # finally:
    #     proc.terminate()
    # move_all_model_files_into_folder(f"experiments/experiment_{formatted}/20_inst_2D-BPP_CLASS_reusable_model/")
    #reuse_model(f"experiments/experiment_{formatted}/20_inst_2D-BPP_CLASS_reusable_model/", files, directory)
    reuse_model(f"experiments/experiment_2026-02-25_09:01/20_inst_2D-BPP_CLASS_reusable_model/", files, directory)

def reuse_model(reusable_model_file_path: str, files: list[str], directory: str):
    reusable_model_file= [file for file in os.listdir(reusable_model_file_path) if file.endswith(".json")][0]
    files = files[1:]
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
        except KeyboardInterrupt as e:
            # do nothing
            m = 1
        finally:
            proc.terminate()

if __name__ == '__main__':
    # paper_20_CLASS_tot_runs()
    # bot_without_semantic_feedback_20_bot_runs()
    CLASS_tot_with_semantic_feedback()
