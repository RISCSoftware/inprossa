from __future__ import annotations

from _comparison_common import BenchmarkConfig, extract_cvrp_metadata, run_benchmark


CONFIG = BenchmarkConfig(
    title="CVRP Benchmark: MiniZinc vs LNS",
    class_name="cvrp",
    default_bench_dir="problem_instances/cvrp/benchmarks/golden_optdsl",
    lns_runner="studies/optdsl_bench/runners/run_cvrp_lns.py",
    default_main_timeout=120.0,
    default_lns_iterations=5000,
    default_lns_seed=42,
    output_stem="benchmark_cvrp_study",
    metadata_headers=["Cities", "Vehicles", "Capacity"],
    metadata_extractor=extract_cvrp_metadata,
)


if __name__ == "__main__":
    run_benchmark(CONFIG)
