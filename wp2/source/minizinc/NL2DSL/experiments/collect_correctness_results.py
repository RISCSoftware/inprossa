import os
import re


def collect_correctness_results(directories: list[str]):
    collected_results = {}
    for directory in directories:
        for filename in os.listdir(directory):
            if (filename != "correctness_results.txt"):
                continue
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            results = []
            for line in text.splitlines():
                sample_name = line.split(":")[0]
                parts = line.split(":")[1]  # after filename
                nums = [int(p) for p in re.findall(r"\d+", parts)]
                results.append(nums)
                if line.split(":")[0] in collected_results.keys():
                    collected_results.update({sample_name: {"valid": collected_results[sample_name]["valid"].append(nums[0]),
                                                            "syn_invalid": collected_results[sample_name]["syn_invalid"].append(nums[1]),
                                                            "sem_invalid": collected_results[sample_name]["sem_invalid"].append(nums[2])}})
                else:
                    collected_results.update(
                        {sample_name: {"valid": [nums[0]],
                                       "syn_invalid": [nums[1]],
                                       "sem_invalid":  [nums[2]]}})

    for sample_name, results in collected_results.items():
        print(f"{sample_name}: valid: {average(results["valid"])}, syn_invalid: {average(results["syn_invalid"])}, sem_invalid: {average(results["sem_invalid"])}")

def average(nums):
    return sum(nums) / len(nums) if nums else 0

if __name__ == '__main__':
    collect_correctness_results(["testset_paper_2D-BPP_CLASS_16.2"]) #, "experiments/testset_paper_2D-BPP_CLASS_17.2"
