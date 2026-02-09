import os
import subprocess
import sys

directory = "problem_descriptions/testset_paper_2D-BPP/"
result = {}
for filename in os.listdir(directory):
    if filename.endswith(".json") and "_n80.json" in filename:
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
        proc.wait()
        proc.terminate()
