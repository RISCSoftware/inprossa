from __future__ import annotations

from _comparison_common import BenchmarkConfig, extract_2dbp_metadata, run_benchmark


CONFIG = BenchmarkConfig(
    title="2D-BPP Benchmark: MiniZinc vs LNS",
    class_name="2dbp",
    default_bench_dir="problem_instances/2dbp/benchmarks/testset_paper_optdsl",
    lns_runner="studies/optdsl_bench/runners/run_2dbp_lns.py",
    default_main_timeout=30.0,
    default_lns_iterations=5000,
    default_lns_seed=42,
    output_stem="benchmark_2dbp_study",
    metadata_headers=["Box", "Items"],
    metadata_extractor=extract_2dbp_metadata,
)


if __name__ == "__main__":
    run_benchmark(CONFIG)
