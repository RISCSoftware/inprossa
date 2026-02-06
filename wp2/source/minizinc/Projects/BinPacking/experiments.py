import random 
import csv


def make_bin_packing_code(n_boxes: int, n_items: int, box_capacity: int = 10) -> str:
    # super-simple capacities and weights; tweak as needed
    box_capacities = [box_capacity] * n_boxes
    item_weights = [random.randint(1, box_capacity) for _ in range(n_items)]

    return f"""
BOX_CAPACITIES : DSList({n_boxes}, DSInt()) = {box_capacities}
ITEM_WEIGHTS : DSList({n_items}, DSInt()) = {item_weights}

NBOXES : int = {n_boxes}
NITEMS : int = {n_items}
 
assignments: DSList(NITEMS, DSInt(1, NBOXES))

def not_exceed(assignments: DSList(NITEMS, DSInt(1, NBOXES))):
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_WEIGHTS)))
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + ITEM_WEIGHTS[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            objective = objective + 1

not_exceed(assignments)
"""


import time
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner

def measure_solve_time(n_items_list, repeats=10):
    runner = MiniZincRunner()
    results = []


    # save to CSV
    csv_path = "binpacking_times.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["NBOXES", "NITEMS", "AVG_TIME_SECONDS"])

        for n_items in n_items_list:
            times = []
            print(f"\n=== NBOXES={n_items}, NITEMS={n_items} ===")
            for r in range(repeats):
                code = make_bin_packing_code(n_items, n_items)
                translator = MiniZincTranslator(code)
                mzn_model = translator.unroll_translation()

                t0 = time.perf_counter()
                result = runner.run(mzn_model)
                t1 = time.perf_counter()
                elapsed = t1 - t0
                times.append(elapsed)
                print(f"  run {r+1}: {elapsed:.4f}s, status={getattr(result, 'status', None)}")
                outcome = getattr(result, 'status', 'unknown')
                writer.writerow([n_items, n_items, elapsed, outcome])

            avg_time = sum(times) / len(times)
            results.append((n_items, n_items, avg_time))
            print(f"→ avg time: {avg_time:.4f}s")
    
    print(f"\nSaved results to {csv_path}")


    return results


if __name__ == "__main__":
    n_items_list = list(range(2, 7, 1))

    results = measure_solve_time(n_items_list)


    for nb, ni, t in results:
        print(f"NBOXES={nb:2d}, NITEMS={ni:2d} → {t:.4f}s")
