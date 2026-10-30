"""Problem-specific initializers and helpers for the LNS framework.

These components are opt-in: the generic LNS engine remains agnostic. Use a
problem-specific initializer when the structure of the DSL allows much
stronger feasibility-aware construction than generic randomized search.
"""

from .binpacking_2d import (
    DBPClearBoxesDestroy,
    DBPClearItemsDestroy,
    DBPFullRepackRepair,
    DBPGreedyPlacementRepair,
    detect_2dbp_problem,
)
from .cutting_packing import (
    CuttingPackingInitializer,
    CuttingPackingLayerDestroy,
    CuttingPackingPieceDestroy,
    CuttingPackingRepackRepair,
    CuttingPackingInsertionRepair,
    CuttingPackingRecutRepair,
    detect_cutting_packing_problem,
)
from .cvrp import CVRPRouteInitializer, detect_cvrp_problem, prepare_cvrp_assignment_for_evaluation
from .cvrp_giant_tour import (
    GiantTourCutRepair,
    GiantTourInitializer,
    detect_giant_tour_problem,
)
from .cvrp_operators import (
    CVRPClusterDestroy,
    CVRPInsertionRepair,
    CVRPInterRouteRepair,
    CVRPOROptRepair,
    CVRPRegretInsertionRepair,
    CVRPRouteBreakDestroy,
    CVRPSegmentDestroy,
    CVRPShawDestroy,
    CVRPTwoOptRepair,
    CVRPWCUSTOMERDestroy,
)
from .jssp import (
    JSSPConstraintAwareRepair,
    JSSPCriticalPathDestroy,
    JSSPInsertionRepair,
    JSSPNonDelayRepair,
    JSSPGanttRepair,
    JSSPJobLevelDestroy,
    JSSPMachineLevelDestroy,
    JSSPScheduleInitializer,
    JSSPShiftTimesDestroy,
    JSSPShuffleDestroy,
    JSSPSwapDestroy,
    detect_jssp_problem,
)
from .jssp_optdsl import (
    JSSPCriticalBlockDestroy,
    JSSPBottleneckMachineDestroy,
    JSSPCriticalBlockReinsertRepair,
    JSSPGapDestroy,
    JSSPMachineBalanceRepair,
    JSSPOptActiveScheduleRepair,
    JSSPRemainingWorkRepair,
    JSSPTimeWindowDestroy,
)
from .woodcutting_pipeline import (
    WoodcuttingCarryThreadDestroy,
    WoodcuttingCarryThreadRepair,
    WoodcuttingCutDestroy,
    WoodcuttingCutRepair,
    WoodcuttingKeepDestroy,
    WoodcuttingKeepRepair,
    WoodcuttingPipelineInitializer,
    WoodcuttingSwapDestroy,
    WoodcuttingSwapRepair,
    detect_woodcutting_pipeline_problem,
)

__all__ = [
    "CVRPRouteInitializer",
    "CVRPRouteBreakDestroy",
    "CVRPWCUSTOMERDestroy",
    "CVRPShawDestroy",
    "CVRPClusterDestroy",
    "CVRPSegmentDestroy",
    "CVRPInsertionRepair",
    "CVRPRegretInsertionRepair",
    "CVRPOROptRepair",
    "CVRPTwoOptRepair",
    "CVRPInterRouteRepair",
    "GiantTourInitializer",
    "GiantTourCutRepair",
    "detect_cvrp_problem",
    "detect_giant_tour_problem",
    "prepare_cvrp_assignment_for_evaluation",
    "JSSPScheduleInitializer",
    "JSSPJobLevelDestroy",
    "JSSPMachineLevelDestroy",
    "JSSPGanttRepair",
    "JSSPConstraintAwareRepair",
    "JSSPCriticalPathDestroy",
    "JSSPInsertionRepair",
    "JSSPNonDelayRepair",
    "JSSPSwapDestroy",
    "JSSPShuffleDestroy",
    "JSSPShiftTimesDestroy",
    "JSSPCriticalBlockDestroy",
    "JSSPCriticalBlockReinsertRepair",
    "JSSPTimeWindowDestroy",
    "JSSPBottleneckMachineDestroy",
    "JSSPGapDestroy",
    "JSSPOptActiveScheduleRepair",
    "JSSPRemainingWorkRepair",
    "JSSPMachineBalanceRepair",
    "detect_jssp_problem",
    # 2D bin-packing
    "DBPClearBoxesDestroy",
    "DBPClearItemsDestroy",
    "DBPGreedyPlacementRepair",
    "DBPFullRepackRepair",
    "detect_2dbp_problem",
    # Cutting & packing (1D cutting stock + layer bin-packing)
    "CuttingPackingInitializer",
    "CuttingPackingLayerDestroy",
    "CuttingPackingPieceDestroy",
    "CuttingPackingRepackRepair",
    "CuttingPackingInsertionRepair",
    "CuttingPackingRecutRepair",
    "detect_cutting_packing_problem",
    # Woodcutting rich pipeline model (Board/Interval/Piece/CutList DSRecords)
    "WoodcuttingPipelineInitializer",
    "WoodcuttingCarryThreadDestroy",
    "WoodcuttingCarryThreadRepair",
    "WoodcuttingCutDestroy",
    "WoodcuttingCutRepair",
    "WoodcuttingKeepDestroy",
    "WoodcuttingKeepRepair",
    "WoodcuttingSwapDestroy",
    "WoodcuttingSwapRepair",
    "detect_woodcutting_pipeline_problem",
]
