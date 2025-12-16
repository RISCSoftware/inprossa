import subprocess
import sys

for i in range(1, 21):
    print(f"""----------------------------------------------------------------------------
    Starting run {i}: """)
    proc = subprocess.Popen([sys.executable, "tryout_pipeline.py"])
    proc.wait()
    proc.terminate()