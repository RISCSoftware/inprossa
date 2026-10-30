from __future__ import annotations

from _profile_common import ProblemProfile, run_profile


PROFILE = ProblemProfile(
    name="jssp",
    initializer="jssp",
    operator_profile="generic",
    default_max_iterations=4000,
    default_log_every=100,
    extra_args=[
        "--lns-init-restarts",
        "16",
        "--lns-destroy-fraction",
        "0.25",
        "--lns-repair",
        "insertion",
        "--lns-repair",
        "nondelay",
        "--lns-repair",
        "opt_active",
        "--lns-destroy",
        "critical",
        "--lns-destroy",
        "critical_block",
        "--lns-destroy",
        "bottleneck_machine",
    ],
)


if __name__ == "__main__":
    raise SystemExit(run_profile(PROFILE))
