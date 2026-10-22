from __future__ import annotations

from _comparison_common import BenchmarkConfig, extract_jssp_metadata, run_benchmark


CONFIG = BenchmarkConfig(
    title="JSSP Benchmark: MiniZinc vs LNS",
    class_name="jssp",
    default_bench_dir="problem_instances/jssp/benchmarks/ta_optdsl",
    lns_runner="studies/optdsl_bench/runners/run_jssp_lns.py",
    default_main_timeout=30.0,
    default_lns_iterations=4000,
    default_lns_seed=42,
    output_stem="benchmark_jssp_study",
    metadata_headers=["Jobs", "Machines"],
    metadata_extractor=extract_jssp_metadata,
)


if __name__ == "__main__":
    run_benchmark(CONFIG)
