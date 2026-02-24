import os
import subprocess
import sys

import constants


def paper_20_CLASS_tot_runs():
    directory = "problem_descriptions/testset_paper_2D-BPP_CLASS/"
    result = {}
    #files = sorted(
    #    os.listdir(directory),
    #    key=lambda name: int(name.rsplit("_", 1)[-1].split(".")[0])
    #)
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

def paper_20_bot_runs():
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

if __name__ == '__main__':
    # paper_20_CLASS_tot_runs()
    paper_20_bot_runs()
