from __future__ import annotations

from _profile_common import ProblemProfile, run_profile


PROFILE = ProblemProfile(
    name="2dbp",
    initializer="2dbp",
    operator_profile="generic",
    default_max_iterations=5000,
    default_log_every=50,
    extra_args=[
        "--lns-destroy",
        "DBPClearBoxesDestroy",
        "--lns-destroy",
        "DBPClearItemsDestroy",
        "--lns-repair",
        "DBPGreedyPlacementRepair",
        "--lns-repair",
        "DBPFullRepackRepair",
        "--lns-init-restarts",
        "16",
        "--repair-samples",
        "16",
    ],
)


if __name__ == "__main__":
    raise SystemExit(run_profile(PROFILE))
