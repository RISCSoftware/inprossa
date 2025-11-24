import subprocess, tempfile, os

def run_mzn_and_detect_inconsistency(code_string: str):
    # save model to temp file
    with tempfile.NamedTemporaryFile(suffix=".mzn", mode="w", delete=False) as tmp:
        tmp.write(code_string)
        mzn_path = tmp.name

    print("=== Checking flattening ===")

    # Ask MiniZinc to only FLATTEN (not solve):
    # --fzn writes FlatZinc
    # --solver chuffed/none ensures no solving
    result = subprocess.run(
        ["minizinc", "--solver", "chuffed", "--fzn", mzn_path + ".fzn", mzn_path],
        capture_output=True,
        text=True
    )

    print("\nSTDOUT:")
    print(result.stdout)

    print("\nSTDERR:")
    print(result.stderr)

    if "inconsistency" in result.stderr.lower():
        print("\n❌ Model is inconsistent!")
    elif result.returncode != 0:
        print("\n❌ MiniZinc failed (syntax or flattening error).")
    else:
        print("\n✅ Model is consistent (flattened successfully).")

    return result
