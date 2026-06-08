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
from .cvrp import CVRPRouteInitializer, detect_cvrp_problem, prepare_cvrp_assignment_for_evaluation
from .cvrp_operators import (
    CVRPInsertionRepair,
    CVRPOROptRepair,
    CVRPRegretInsertionRepair,
    CVRPRouteBreakDestroy,
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

__all__ = [
    "CVRPRouteInitializer",
    "CVRPRouteBreakDestroy",
    "CVRPWCUSTOMERDestroy",
    "CVRPInsertionRepair",
    "CVRPRegretInsertionRepair",
    "CVRPOROptRepair",
    "detect_cvrp_problem",
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
]
