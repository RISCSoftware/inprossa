"""Compare a reproduced size-study CSV against the reference CSV.

Compares the outcome columns (MiniZinc Quality/Bound, LNS Quality) — NOT the
wall-clock times, which are machine/runtime dependent.  Uses the LNS stop reason
as informational context.

Usage:
    python _verify_compare.py --ref output/study_results_final.csv --new output/study_results_verify.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

OUTCOME_COLS = ["MiniZinc Quality", "MiniZinc Bound", "LNS Quality"]


def load(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            key = (row.get("Class", ""), row.get("Set", ""), row.get("Instance", ""))
            rows[key] = row
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    args = parser.parse_args()

    ref = load(args.ref)
    new = load(args.new)

    ref_keys = set(ref)
    new_keys = set(new)
    only_ref = ref_keys - new_keys
    only_new = new_keys - ref_keys

    print(f"Reference rows: {len(ref_keys)}   New rows: {len(new_keys)}")
    if only_ref:
        print(f"  Missing in new run: {sorted(only_ref)}")
    if only_new:
        print(f"  Extra in new run:   {sorted(only_new)}")

    mismatches: list[tuple] = []
    for key in sorted(ref_keys & new_keys):
        r, n = ref[key], new[key]
        for col in OUTCOME_COLS:
            rv, nv = r.get(col, ""), n.get(col, "")
            if rv != nv:
                mismatches.append((key, col, rv, nv))

    print("\n=== Outcome comparison (MiniZinc Quality/Bound, LNS Quality) ===")
    if not mismatches:
        print("ALL OUTCOME COLUMNS MATCH the reference.")
    else:
        print(f"{len(mismatches)} mismatched cell(s):")
        for (key, col, rv, nv) in mismatches:
            print(f"  {key}  [{col}]: ref={rv!r}  new={nv!r}")

    print("\n=== Per-instance overview (new run) ===")
    print(f"{'Class':<8}{'Set':<8}{'Instance':<34}{'MZ Qual':<12}{'MZ Bound':<10}{'LNS':<8}{'LNS Stop'}")
    for key in sorted(ref_keys & new_keys):
        n = new[key]
        print(f"{key[0]:<8}{key[1]:<8}{key[2]:<34}{n.get('MiniZinc Quality',''):<12}{n.get('MiniZinc Bound',''):<10}"
              f"{n.get('LNS Quality',''):<8}{n.get('LNS Stop','')}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
