import subprocess
import sys

for i in range(1, 21):
    print(f"""----------------------------------------------------------------------------
    Starting run {i}: """)
    proc = subprocess.Popen([sys.executable,
                             "tree_search_dfs.py",
                             "--problem_instance",
                             "problem_descriptions/2d_bin_packing_input_inst_3.json",
                             "--problem_description",
                             "problem_descriptions/2d_bin_packing_inst_1_without_input.json",
                             "-m",
                             "flex_objects_fixed_input_values"])
    proc.wait()
    proc.terminate()
