"""Registration of the built-in LNS operators.

Importing this module populates the registry. It is imported lazily by
``run_lns.py`` and by the synthesis harness, so the language server (which
never needs operators) does not pay for it.

Every factory accepts ``**kwargs`` and forwards them to the operator's
dataclass, which lets the CLI pass a uniform hyperparameter dict regardless of
which operator was selected.
"""

from __future__ import annotations

from typing import Any

from . import defaults
from .problems import (
    binpacking_2d,
    cutting_packing,
    cvrp_operators,
    jssp,
    jssp_optdsl,
    woodcutting_pipeline,
)
from .registry import register_destroy, register_repair


def _factory(cls: type) -> Any:
    def make(**kwargs: Any) -> Any:
        return cls(**kwargs)

    make.__name__ = f"make_{cls.__name__}"
    make.__doc__ = cls.__doc__
    return make


# ---------------------------------------------------------------------------
# generic
# ---------------------------------------------------------------------------

register_destroy(
    "RandomFractionDestroy",
    description="Clear a random fraction of all decision variables.",
    parameters={"fraction": 0.2},
)(_factory(defaults.RandomFractionDestroy))

register_destroy(
    "VariableBlockDestroy",
    description="Clear one whole decision variable at a time.",
)(_factory(defaults.VariableBlockDestroy))

register_destroy(
    "PermutationSegmentDestroy",
    description="Clear a contiguous segment of a permutation decision.",
    parameters={"fraction": 0.2, "min_segment": 2},
)(_factory(defaults.PermutationSegmentDestroy))

register_repair(
    "RandomRepair",
    description="Fill every unassigned decision with a uniformly random value.",
)(_factory(defaults.RandomRepair))

register_repair(
    "SampledRepair",
    description="Sample several random completions and keep the best-scoring one.",
    parameters={"samples": 4},
)(_factory(defaults.SampledRepair))

register_repair(
    "FillMissingPermutationRepair",
    description="Complete a permutation by filling the missing values.",
)(_factory(defaults.FillMissingPermutationRepair))


# ---------------------------------------------------------------------------
# 2D bin packing
# ---------------------------------------------------------------------------

register_destroy(
    "DBPClearBoxesDestroy",
    problem="2dbp",
    description="Empty one or more boxes and unassign their items.",
    parameters={"box_count": 1, "strategy": "random"},
)(_factory(binpacking_2d.DBPClearBoxesDestroy))

register_destroy(
    "DBPClearItemsDestroy",
    problem="2dbp",
    description="Unassign a random fraction of items.",
    parameters={"fraction": 0.3, "min_items": 1},
)(_factory(binpacking_2d.DBPClearItemsDestroy))

register_repair(
    "DBPGreedyPlacementRepair",
    problem="2dbp",
    description="Bottom-left placement of unassigned items, keeping fixed ones.",
    parameters={"restarts": 8},
)(_factory(binpacking_2d.DBPGreedyPlacementRepair))

register_repair(
    "DBPFullRepackRepair",
    problem="2dbp",
    description="Repack every item from scratch.",
    parameters={"restarts": 16},
)(_factory(binpacking_2d.DBPFullRepackRepair))


# ---------------------------------------------------------------------------
# cutting / packing
# ---------------------------------------------------------------------------

register_destroy(
    "CuttingPackingLayerDestroy",
    problem="cutting_packing",
    description="Clear one or more layers.",
    parameters={"layer_count": 1, "strategy": "random"},
)(_factory(cutting_packing.CuttingPackingLayerDestroy))

register_destroy(
    "CuttingPackingPieceDestroy",
    problem="cutting_packing",
    description="Unassign a random fraction of pieces.",
    parameters={"fraction": 0.3, "min_pieces": 1},
)(_factory(cutting_packing.CuttingPackingPieceDestroy))

register_repair(
    "CuttingPackingRepackRepair",
    problem="cutting_packing",
    description="Repack all layers from scratch.",
    parameters={"restarts": 8},
)(_factory(cutting_packing.CuttingPackingRepackRepair))

register_repair(
    "CuttingPackingInsertionRepair",
    problem="cutting_packing",
    description="Insert unassigned pieces into existing layers.",
)(_factory(cutting_packing.CuttingPackingInsertionRepair))

register_repair(
    "CuttingPackingRecutRepair",
    problem="cutting_packing",
    description="Randomized re-cut followed by re-assignment.",
    parameters={"restarts": 8},
)(_factory(cutting_packing.CuttingPackingRecutRepair))


# ---------------------------------------------------------------------------
# CVRP
# ---------------------------------------------------------------------------

register_destroy(
    "CVRPRouteBreakDestroy",
    problem="cvrp",
    description="Remove one or more whole routes.",
    parameters={"route_count": 1, "strategy": "random"},
)(_factory(cvrp_operators.CVRPRouteBreakDestroy))

register_destroy(
    "CVRPWCUSTOMERDestroy",
    problem="cvrp",
    description="Remove a set of customers chosen by a worst/random strategy.",
    parameters={"customer_count": 0, "fraction": 0.2, "strategy": "worst"},
)(_factory(cvrp_operators.CVRPWCUSTOMERDestroy))

register_destroy(
    "CVRPShawDestroy",
    problem="cvrp",
    description="Shaw relatedness removal (distance, demand, time).",
    parameters={"customer_count": 0, "fraction": 0.2, "seed_strategy": "random"},
)(_factory(cvrp_operators.CVRPShawDestroy))

register_destroy(
    "CVRPClusterDestroy",
    problem="cvrp",
    description="Remove a geographic cluster of customers by sweep angle.",
    parameters={"fraction": 0.2, "angle_span": 1.2},
)(_factory(cvrp_operators.CVRPClusterDestroy))

register_destroy(
    "CVRPSegmentDestroy",
    problem="cvrp",
    description="Remove a contiguous segment of a route.",
    parameters={"segment_len": 5, "fraction": 0.0},
)(_factory(cvrp_operators.CVRPSegmentDestroy))

register_repair(
    "CVRPInsertionRepair",
    problem="cvrp",
    description="Cheapest-insertion repair.",
    parameters={"strategy": "cheapest"},
)(_factory(cvrp_operators.CVRPInsertionRepair))

register_repair(
    "CVRPRegretInsertionRepair",
    problem="cvrp",
    description="Regret-k insertion repair.",
    parameters={"regret_k": 3},
)(_factory(cvrp_operators.CVRPRegretInsertionRepair))

register_repair(
    "CVRPOROptRepair",
    problem="cvrp",
    description="Or-opt local search.",
    parameters={"or_opt_max": 2, "passes": 5},
)(_factory(cvrp_operators.CVRPOROptRepair))

register_repair(
    "CVRPTwoOptRepair",
    problem="cvrp",
    description="2-opt intra-route improvement.",
    parameters={"passes": 3, "only_dirty": False},
)(_factory(cvrp_operators.CVRPTwoOptRepair))

register_repair(
    "CVRPInterRouteRepair",
    problem="cvrp",
    description="Inter-route relocation/exchange improvement.",
    parameters={"passes": 3},
)(_factory(cvrp_operators.CVRPInterRouteRepair))


# ---------------------------------------------------------------------------
# JSSP
# ---------------------------------------------------------------------------

register_destroy(
    "JSSPJobLevelDestroy",
    problem="jssp",
    description="Clear a fraction of jobs across all machines.",
    parameters={"fraction": 0.25},
)(_factory(jssp.JSSPJobLevelDestroy))

register_destroy(
    "JSSPMachineLevelDestroy",
    problem="jssp",
    description="Clear a fraction of machines across all jobs.",
    parameters={"fraction": 0.25},
)(_factory(jssp.JSSPMachineLevelDestroy))

register_destroy(
    "JSSPShuffleDestroy",
    problem="jssp",
    description="Shuffle a fraction of completion times.",
    parameters={"fraction": 0.3},
)(_factory(jssp.JSSPShuffleDestroy))

register_destroy(
    "JSSPSwapDestroy",
    problem="jssp",
    description="Swap a fraction of completion times.",
    parameters={"fraction": 0.3},
)(_factory(jssp.JSSPSwapDestroy))

register_destroy(
    "JSSPShiftTimesDestroy",
    problem="jssp",
    description="Shift completion times by a bounded random amount.",
    parameters={"fraction": 0.25, "max_shift": 10},
)(_factory(jssp.JSSPShiftTimesDestroy))

register_destroy(
    "JSSPCriticalPathDestroy",
    problem="jssp",
    description="Clear operations on or near the critical path.",
    parameters={"fraction": 0.3, "strategy": "critical", "min_destroy": 0},
)(_factory(jssp.JSSPCriticalPathDestroy))

register_repair(
    "JSSPGanttRepair",
    problem="jssp",
    description="Rebuild a Gantt schedule from the surviving completion times.",
)(_factory(jssp.JSSPGanttRepair))

register_repair(
    "JSSPConstraintAwareRepair",
    problem="jssp",
    description="Anchor fixed operations and dispatch ready ones.",
)(_factory(jssp.JSSPConstraintAwareRepair))

register_repair(
    "JSSPInsertionRepair",
    problem="jssp",
    description="Insertion-based schedule repair.",
    parameters={"order": "priority", "improve": True},
)(_factory(jssp.JSSPInsertionRepair))

register_repair(
    "JSSPNonDelayRepair",
    problem="jssp",
    description="Non-delay schedule construction.",
    parameters={"selection": "spt", "passes": 2},
)(_factory(jssp.JSSPNonDelayRepair))

register_destroy(
    "JSSPGapDestroy",
    problem="jssp",
    description="Clear operations in the tightest machine gaps.",
    parameters={"gap_fraction": 0.35, "min_destroy": 2},
)(_factory(jssp_optdsl.JSSPGapDestroy))

register_destroy(
    "JSSPTimeWindowDestroy",
    problem="jssp",
    description="Clear operations inside a time window.",
    parameters={"window_fraction": 0.25, "destroy_fraction": 0.25, "min_destroy": 2},
)(_factory(jssp_optdsl.JSSPTimeWindowDestroy))

register_destroy(
    "JSSPBottleneckMachineDestroy",
    problem="jssp",
    description="Clear operations on the bottleneck machines.",
    parameters={"machine_fraction": 0.4, "destroy_fraction": 0.25, "min_destroy": 2},
)(_factory(jssp_optdsl.JSSPBottleneckMachineDestroy))

register_destroy(
    "JSSPCriticalBlockDestroy",
    problem="jssp",
    description="Clear a critical block of consecutive operations.",
    parameters={"block_size": 3, "min_destroy": 2},
)(_factory(jssp_optdsl.JSSPCriticalBlockDestroy))

register_repair(
    "JSSPOptActiveScheduleRepair",
    problem="jssp",
    description="Active-schedule construction with back-shifting.",
    parameters={"look_ahead": 1, "passes": 3},
)(_factory(jssp_optdsl.JSSPOptActiveScheduleRepair))

register_repair(
    "JSSPRemainingWorkRepair",
    problem="jssp",
    description="Prioritise operations with the most remaining work.",
    parameters={"random_pick_prob": 0.2},
)(_factory(jssp_optdsl.JSSPRemainingWorkRepair))

register_repair(
    "JSSPMachineBalanceRepair",
    problem="jssp",
    description="Balance machine load during dispatch.",
    parameters={"random_pick_prob": 0.2},
)(_factory(jssp_optdsl.JSSPMachineBalanceRepair))

register_repair(
    "JSSPCriticalBlockReinsertRepair",
    problem="jssp",
    description="Reinsert critical blocks with look-ahead.",
    parameters={"block_size": 4, "base_passes": 2, "base_look_ahead": 1},
)(_factory(jssp_optdsl.JSSPCriticalBlockReinsertRepair))


# ---------------------------------------------------------------------------
# woodcutting pipeline
# ---------------------------------------------------------------------------

register_destroy(
    "WoodcuttingCutDestroy",
    problem="woodcutting",
    description="Clear the cut lists of one or more boards.",
    parameters={"board_count": 1},
)(_factory(woodcutting_pipeline.WoodcuttingCutDestroy))

register_destroy(
    "WoodcuttingKeepDestroy",
    problem="woodcutting",
    description="Clear a fraction of keep decisions.",
    parameters={"fraction": 0.3},
)(_factory(woodcutting_pipeline.WoodcuttingKeepDestroy))

register_destroy(
    "WoodcuttingSwapDestroy",
    problem="woodcutting",
    description="Clear a fraction of reordering decisions.",
    parameters={"fraction": 0.3, "include_board_swaps": False},
)(_factory(woodcutting_pipeline.WoodcuttingSwapDestroy))

register_destroy(
    "WoodcuttingCarryThreadDestroy",
    problem="woodcutting",
    description="Clear every decision (full restart).",
)(_factory(woodcutting_pipeline.WoodcuttingCarryThreadDestroy))

register_repair(
    "WoodcuttingCutRepair",
    problem="woodcutting",
    description="Recompute cut lists.",
    parameters={"randomized": False},
)(_factory(woodcutting_pipeline.WoodcuttingCutRepair))

register_repair(
    "WoodcuttingKeepRepair",
    problem="woodcutting",
    description="Recompute keep decisions by simulation.",
)(_factory(woodcutting_pipeline.WoodcuttingKeepRepair))

register_repair(
    "WoodcuttingSwapRepair",
    problem="woodcutting",
    description="Sample reordering completions and keep the best.",
    parameters={"samples": 12},
)(_factory(woodcutting_pipeline.WoodcuttingSwapRepair))

register_repair(
    "WoodcuttingCarryThreadRepair",
    problem="woodcutting",
    description="Full rebuild of the carry-thread assignment.",
)(_factory(woodcutting_pipeline.WoodcuttingCarryThreadRepair))
