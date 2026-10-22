from __future__ import annotations

from _profile_common import ProblemProfile, run_profile


PROFILE = ProblemProfile(
    name="cvrp",
    initializer="cvrp",
    operator_profile="generic",
    default_max_iterations=5000,
    default_log_every=10,
    extra_args=[
        "--cvrp-init-restarts",
        "16",
        "--cvrp-init-randomization",
        "0.3",
        "--lns-destroy",
        "CVRPRouteBreakDestroy",
        "--lns-destroy",
        "CVRPWCUSTOMERDestroy",
        "--lns-destroy",
        "CVRPShawDestroy",
        "--lns-destroy",
        "CVRPClusterDestroy",
        "--lns-destroy",
        "CVRPSegmentDestroy",
        "--lns-repair",
        "CVRPInsertionRepair",
        "--lns-repair",
        "CVRPRegretInsertionRepair",
        "--lns-repair",
        "CVRPOROptRepair",
        "--lns-repair",
        "CVRPTwoOptRepair",
        "--lns-repair",
        "CVRPInterRouteRepair",
        "--lns-adaptive-selection",
        "--lns-adaptive-destroy-intensity",
    ],
)


if __name__ == "__main__":
    raise SystemExit(run_profile(PROFILE))
