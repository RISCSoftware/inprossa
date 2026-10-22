from __future__ import annotations

from _profile_common import ProblemProfile, run_profile


PROFILE = ProblemProfile(
    name="cvrptw",
    initializer="cvrp",
    operator_profile="generic",
    default_max_iterations=6000,
    default_log_every=100,
    extra_args=[
        # Current implementation wave uses CVRP baseline operators.
        # TW-specific destroys/repairs will be plugged in as they are implemented.
        "--cvrp-init-restarts",
        "24",
        "--lns-destroy",
        "CVRPRouteBreakDestroy",
        "--lns-destroy",
        "CVRPWCUSTOMERDestroy",
        "--lns-repair",
        "CVRPRegretInsertionRepair",
        "--lns-repair",
        "CVRPOROptRepair",
    ],
)


if __name__ == "__main__":
    raise SystemExit(run_profile(PROFILE))
