import os
import re

SAMPLE_NAMES_FLEX_TESTSET = ['01_020_05.json', '02_020_07.json', '02_020_10.json', '03_020_05.json', '03_020_10.json', '04_020_08.json', '05_020_08.json', '06_020_06.json', '06_020_10.json', '07_020_05.json', '07_020_08.json', '07_020_10.json', '08_020_04.json', '08_020_08.json', '09_020_02.json', '09_020_05.json', '09_020_07.json', '10_020_02.json', '10_020_04.json', '10_020_09.json']

def collect_correctness_results(directories: list[str]):
    collected_results = {}
    for directory in directories:
        files = [
            os.path.join(root, file)
            for root, dirs, files in os.walk(directory)
            for file in files
            if file.endswith("correctness_results.txt")
        ]
        for filepath in files:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            results = []
            for i, line in enumerate(text.splitlines()):
                if ":" not in line: # Format of line: 01_020_05.json: 1 syntactically invalid, 0 semantically invalid, 0 valid, 15 optimal
                    sample_name = SAMPLE_NAMES_FLEX_TESTSET[i]
                    parts = line
                else: # Format of line: 1 syntactically invalid, 0 semantically invalid, 0 valid, 15 optimal
                    sample_name = line.split(":")[0]
                    parts = line.split(":")[1]  # after filename
                nums = [int(p) for p in re.findall(r"\d+", parts)]
                results.append(nums)
                if line.split(":")[0] in collected_results.keys():
                    collected_results[sample_name]["syn_invalid"].append(nums[0])
                    collected_results[sample_name]["sem_invalid"].append(nums[1])
                    collected_results[sample_name]["valid"].append(nums[2])
                    collected_results[sample_name]["optimal"].append(nums[3])
                else:
                    collected_results.update(
                        {sample_name: {"syn_invalid": [nums[0]],
                                       "sem_invalid":  [nums[1]],
                                       "valid": [nums[2]],
                                       "optimal": [nums[3]]}})

    for sample_name, results in collected_results.items():
        syn_invalid = sum(results["syn_invalid"])
        sem_invalid = sum(results["sem_invalid"])
        valid = sum(results["valid"])
        optimal = sum(results["optimal"])

        print(f"{sample_name}: syn_invalid: {syn_invalid}, sem_invalid: {sem_invalid}, valid: {valid}, optimal: {optimal} = {syn_invalid + sem_invalid + valid + optimal}")

    print(f"syn_invalid sum: {sum([sum(results["syn_invalid"]) for results in collected_results.values()])}")
    print(f"sem_invalid sum: {sum([sum(results["sem_invalid"]) for results in collected_results.values()])}")
    print(f"valid sum: {sum([sum(results["valid"]) for results in collected_results.values()])}")
    print(f"optimal sum: {sum([sum(results["optimal"]) for results in collected_results.values()])}")

def average(nums):
    return sum(nums) / len(nums) if nums else 0

if __name__ == '__main__':
    collect_correctness_results(["experiment_2D-BPP_CLASS_flex_shapes"])
