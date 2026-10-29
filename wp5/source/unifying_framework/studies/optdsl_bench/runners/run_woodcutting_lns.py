from __future__ import annotations

from _profile_common import ProblemProfile, run_profile


PROFILE = ProblemProfile(
    name="woodcutting",
    initializer="woodcutting_pipeline",
    operator_profile="generic",
    default_max_iterations=6000,
    default_log_every=100,
    extra_args=[
        "--lns-init-restarts",
        "8",
        "--destroy-rate",
        "0.25",
        "--repair-samples",
        "20",
    ],
)


if __name__ == "__main__":
    raise SystemExit(run_profile(PROFILE))
