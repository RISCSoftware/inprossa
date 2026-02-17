import os
import subprocess
import sys

directory = "problem_descriptions/testset_paper_2D-BPP_CLASS/"
result = {}
#files = sorted(
#    os.listdir(directory),
#    key=lambda name: int(name.rsplit("_", 1)[-1].split(".")[0])
#)
for filename in os.listdir(directory):
    if (not filename.endswith(".json")): #or
        #( "01_020_05" in filename or
        #"02_020_07" in filename or
        #"02_020_10" in filename or
        #"03_020_05" in filename or
        #"03_020_10" in filename or
        #"04_020_08" in filename or
        #"05_020_08" in filename
        #"09_020_02" in filename or
        #"09_020_05" in filename or
        #"09_020_07" in filename or
        #"10_020_02" in filename or
        #"10_020_04" in filename or
        #"10_020_09" in filename
        #)):
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
