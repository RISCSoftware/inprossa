from __future__ import annotations

from _comparison_common import BenchmarkConfig, extract_generic_size_metadata, run_benchmark


CONFIG = BenchmarkConfig(
    title="Woodcutting Benchmark: MiniZinc vs LNS",
    class_name="woodcutting",
    default_bench_dir="problem_instances/woodcutting/benchmarks/generated_noreorder",
    lns_runner="studies/optdsl_bench/runners/run_woodcutting_lns.py",
    default_main_timeout=120.0,
    default_lns_iterations=6000,
    default_lns_seed=42,
    output_stem="benchmark_woodcutting_study",
    metadata_headers=["DSL Decls"],
    metadata_extractor=extract_generic_size_metadata,
)


if __name__ == "__main__":
    run_benchmark(CONFIG)
