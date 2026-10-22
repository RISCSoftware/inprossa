from __future__ import annotations

from _comparison_common import BenchmarkConfig, extract_cvrp_metadata, run_benchmark


CONFIG = BenchmarkConfig(
    title="CVRPTW Benchmark: MiniZinc vs LNS",
    class_name="cvrptw",
    default_bench_dir="problem_instances/cvrptw/benchmarks/solomon_optdsl",
    lns_runner="studies/optdsl_bench/runners/run_cvrptw_lns.py",
    default_main_timeout=120.0,
    default_lns_iterations=6000,
    default_lns_seed=42,
    output_stem="benchmark_cvrptw_study",
    metadata_headers=["Cities", "Vehicles", "Capacity"],
    metadata_extractor=extract_cvrp_metadata,
)


if __name__ == "__main__":
    run_benchmark(CONFIG)
