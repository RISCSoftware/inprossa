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

def run_mus(code_string: str):
    # write model to temp file
    with tempfile.NamedTemporaryFile(suffix=".mzn", mode="w", delete=False) as tmp:
        tmp.write(code_string)
        mzn_path = tmp.name

    # basic: one MUS at model level
    result = subprocess.run(
        ["findMUS", mzn_path],
        capture_output=True,
        text=True,
    )

    print("STDOUT (MUS info):")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)

    if result.returncode != 0:
        print("\n findMUS failed (syntax/solver error?).")
    else:
        print("\n MUS search finished (see STDOUT above).")

    parse_mus_traces(result.stdout)

    return result

def parse_mus_traces(stdout: str):
    lines = stdout.splitlines()
    traces_line_idx = next(
        (i for i, l in enumerate(lines) if l.strip().startswith("Traces:")), None
    )
    if traces_line_idx is None:
        return []

    traces = []
    for part in lines[traces_line_idx + 1:]:
        part = part.strip()
        if not part:
            continue
        for seg in part.split(";"):
            seg = seg.strip()
            if not seg:
                continue
            fields = seg.split("|")
            if len(fields) != 7:
                continue
            file, sl, sc, el, ec, kind, info = fields
            traces.append({
                "file": file,
                "start_line": int(sl),
                "start_col": int(sc),
                "end_line": int(el),
                "end_col": int(ec),
                "kind": kind,
                "info": info,
            })
    return traces

