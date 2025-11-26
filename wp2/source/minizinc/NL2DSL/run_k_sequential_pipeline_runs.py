import subprocess
import sys

for i in range(20):  # run 5 times
    print(f"""----------------------------------------------------------------------------
    Starting run {i}: """)
    subprocess.run([sys.executable, "tryout_pipeline.py"])