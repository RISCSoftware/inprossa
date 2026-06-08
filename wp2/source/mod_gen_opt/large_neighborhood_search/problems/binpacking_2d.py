"""2D-bin-packing-specific LNS operators for optdsl formulations.

Destroy operator clears items from selected boxes; repair repacks using
greedy first-fit with bottom-left placement heuristic.  Together they
exploit the geometric structure of the problem and consistently reach
solutions close to the theoretical lower bound on box count.
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass
from itertools import product

from ..components import DestroyOperator, RepairOperator
from ..models import LNSContext


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def detect_2dbp_problem(context: LNSContext) -> bool:
    """Detect a 2D bin-packing problem by inspecting DSL constants."""
    return _get_2dbp_constants(context) is not None


def _get_2dbp_constants(context: LNSContext):
    """Return required 2DBP constants or None if not a 2DBP problem."""
    constants = context.constants
    required = ("NBOXES", "NITEMS", "ITEM_WIDTHS", "ITEM_HEIGHTS",
                 "BOX_WIDTH_CAPACITIES", "BOX_HEIGHT_CAPACITIES")
    if not all(k in constants for k in required):
        return None
    return {
        "nboxes": int(constants["NBOXES"]),
        "nitems": int(constants["NITEMS"]),
        "item_w": [int(v) for v in constants["ITEM_WIDTHS"]],
        "item_h": [int(v) for v in constants["ITEM_HEIGHTS"]],
        "box_w": [int(v) for v in constants["BOX_WIDTH_CAPACITIES"]],
        "box_h": [int(v) for v in constants["BOX_HEIGHT_CAPACITIES"]],
    }


def _items_overlap(x1: int, y1: int, w1: int, h1: int,
                   x2: int, y2: int, w2: int, h2: int) -> bool:
    """Return True if two axis-aligned rectangles overlap (share interior)."""
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or
                y1 + h1 <= y2 or y2 + h2 <= y1)


def _find_position(
    item_idx: int,
    box_items: list[int],
    box_x: list[int],
    box_y: list[int],
    item_w: list[int],
    item_h: list[int],
    box_width: int,
    box_height: int,
) -> tuple[int, int] | None:
    """Find the bottom-left non-overlapping position for *item_idx*.

    Generates candidate (x, y) from box boundaries and existing-item edges,
    then returns the first candidate sorted by (y, x) that fits without
    overlap.

    box_x / box_y are parallel to box_items (indexed by slot in box,
    NOT by global item index).
    """
    wi, hi = item_w[item_idx], item_h[item_idx]

    x_candidates = {0}
    y_candidates = {0}
    for si in range(len(box_items)):
        j = box_items[si]
        x_base = box_x[si] + item_w[j]
        if x_base <= box_width - wi:
            x_candidates.add(x_base)
        y_base = box_y[si] + item_h[j]
        if y_base <= box_height - hi:
            y_candidates.add(y_base)

    # Sort by y then x for classic bottom-left
    positions = sorted(
        (x, y) for x, y in product(x_candidates, y_candidates)
        if x + wi <= box_width and y + hi <= box_height
    )
    # Bottom-left: prefer lowest y, then lowest x
    positions.sort(key=lambda p: (p[1], p[0]))

    for px, py in positions:
        overlap = any(
            _items_overlap(px, py, wi, hi,
                           box_x[si], box_y[si], item_w[box_items[si]], item_h[box_items[si]])
            for si in range(len(box_items))
        )
        if not overlap:
            return (px, py)

    return None


# ------------------------------------------------------------------
# Destroy operators
# ------------------------------------------------------------------

@dataclass
class DBPClearBoxesDestroy(DestroyOperator):
    """Destroy all items from randomly selected boxes.

    Clears `assignments`, `x_positions`, `y_positions` for every item
    currently in the selected boxes.  Cleared items get assignment ``-1``
    (a sentinel) so the repair operator knows what to repack.

    Parameters
    ----------
    box_count : int
        How many boxes to clear per iteration.
    strategy : str
        'random' – pick boxes uniformly.
        'largest_load' – pick boxes with the most items.
    """

    box_count: int = 1
    strategy: str = "random"

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_2dbp_constants(context)
        if info is None:
            return assignment

        rng: random.Random = context.extra["rng"]
        nboxes = info["nboxes"]
        nitems = info["nitems"]

        assignments = assignment.get("assignments")
        if not isinstance(assignments, list) or len(assignments) != nitems:
            return assignment

        # Build box -> item mapping
        box_items: dict[int, list[int]] = {b: [] for b in range(nboxes)}
        for i in range(nitems):
            b = assignments[i]
            if isinstance(b, int) and 0 <= b < nboxes:
                box_items[b].append(i)

        # Select boxes to clear
        loaded = [b for b in range(nboxes) if box_items[b]]
        if not loaded:
            return assignment

        k = min(self.box_count, len(loaded))

        if self.strategy == "largest_load" and len(loaded) > 1:
            loaded.sort(key=lambda b: len(box_items[b]), reverse=True)
            selected = loaded[:k]
        else:
            selected = rng.sample(loaded, k)

        # Clear items
        x_pos = assignment.get("x_positions", [])
        y_pos = assignment.get("y_positions", [])

        for b in selected:
            for i in box_items[b]:
                assignments[i] = -1
                if isinstance(x_pos, list) and i < len(x_pos):
                    x_pos[i] = -1
                if isinstance(y_pos, list) and i < len(y_pos):
                    y_pos[i] = -1

        return assignment


@dataclass
class DBPClearItemsDestroy(DestroyOperator):
    """Destroy a random fraction of items by unassigning them.

    Parameters
    ----------
    fraction : float
        Fraction of items to unassign (0.0 – 1.0).
    min_items : int
        Minimum items to destroy even if fraction yields fewer.
    """

    fraction: float = 0.3
    min_items: int = 1

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_2dbp_constants(context)
        if info is None:
            return assignment

        rng: random.Random = context.extra["rng"]
        nitems = info["nitems"]

        assignments = assignment.get("assignments")
        if not isinstance(assignments, list) or len(assignments) != nitems:
            return assignment

        assigned = [i for i in range(nitems) if assignments[i] != -1]
        if not assigned:
            return assignment

        n_destroy = max(self.min_items, int(math.ceil(nitems * max(0.0, min(1.0, self.fraction)))))
        to_destroy = rng.sample(assigned, min(n_destroy, len(assigned)))

        x_pos = assignment.get("x_positions", [])
        y_pos = assignment.get("y_positions", [])

        for i in to_destroy:
            assignments[i] = -1
            if isinstance(x_pos, list) and i < len(x_pos):
                x_pos[i] = -1
            if isinstance(y_pos, list) and i < len(y_pos):
                y_pos[i] = -1

        return assignment


# ------------------------------------------------------------------
# Repair operators
# ------------------------------------------------------------------

@dataclass
class DBPGreedyPlacementRepair(RepairOperator):
    """Repack items into boxes using greedy first-fit placement heuristics.

    Multiple constructive strategies are tried (sorted by area descending,
    sorted by max dimension descending, random shuffle), each with
    bottom-left placement.  The best feasible solution (fewest boxes used)
    is returned.

    Parameters
    ----------
    restarts : int
        Number of independent constructive attempts.
    """

    restarts: int = 8

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_2dbp_constants(context)
        if info is None:
            return partial_assignment

        rng: random.Random = context.extra["rng"]
        nitems = info["nitems"]
        nboxes = info["nboxes"]

        assignments = partial_assignment.get("assignments")
        if not isinstance(assignments, list) or len(assignments) != nitems:
            return partial_assignment

        x_positions = partial_assignment.get("x_positions", [0] * nitems)
        y_positions = partial_assignment.get("y_positions", [0] * nitems)
        if not isinstance(x_positions, list):
            x_positions = [0] * nitems
        if not isinstance(y_positions, list):
            y_positions = [0] * nitems

        # Determine which items need placement
        unassigned = [i for i in range(nitems) if assignments[i] == -1]
        if not unassigned:
            return partial_assignment

        # Separate fixed items (kept from partial assignment) from unassigned
        fixed_assignments = list(assignments)
        fixed_x = list(x_positions)
        fixed_y = list(y_positions)

        best_result = None
        best_box_count = nboxes + 1

        # Build sort-key strategies
        strategies = [
            lambda idxs: sorted(idxs, key=lambda i: info["item_w"][i] * info["item_h"][i], reverse=True),
            lambda idxs: sorted(idxs, key=lambda i: max(info["item_w"][i], info["item_h"][i]), reverse=True),
            lambda idxs: sorted(idxs, key=lambda i: info["item_w"][i], reverse=True),
            lambda idxs: sorted(idxs, key=lambda i: info["item_h"][i], reverse=True),
        ]

        for attempt in range(max(1, self.restarts)):
            # Pick strategy
            strat = strategies[attempt % len(strategies)]
            order = strat(unassigned)

            # Start from fixed items
            asgn = list(fixed_assignments)
            x_pos = list(fixed_x)
            y_pos = list(fixed_y)

            # Build per-box state from fixed items
            box_state: list[dict] = []
            for b in range(nboxes):
                items = [i for i in range(nitems) if asgn[i] == b]
                bx = [x_pos[i] for i in items]
                by = [y_pos[i] for i in items]
                box_state.append({"items": items, "x": bx, "y": by})

            placed = True
            for i in order:
                # Try boxes in order (prefer lower-indexed boxes to pack tight)
                placed_in_box = False
                for b in range(nboxes):
                    pos = _find_position(i, box_state[b]["items"],
                                         box_state[b]["x"], box_state[b]["y"],
                                         info["item_w"], info["item_h"],
                                         info["box_w"][b], info["box_h"][b])
                    if pos is not None:
                        asgn[i] = b
                        x_pos[i] = pos[0]
                        y_pos[i] = pos[1]
                        box_state[b]["items"].append(i)
                        box_state[b]["x"].append(pos[0])
                        box_state[b]["y"].append(pos[1])
                        placed_in_box = True
                        break

                if not placed_in_box:
                    placed = False
                    break

            if placed:
                # Count boxes used
                used = len([b for b in range(nboxes) if box_state[b]["items"]])
                if used < best_box_count:
                    best_box_count = used
                    best_result = (asgn, x_pos, y_pos)

            # If already optimal (1 box), stop
            if best_box_count == 1:
                break

        if best_result is not None:
            assignment_out = dict(partial_assignment)
            assignment_out["assignments"] = best_result[0]
            assignment_out["x_positions"] = best_result[1]
            assignment_out["y_positions"] = best_result[2]
            return assignment_out

        # Fallback: try random-first box ordering (instead of 0,1,2,...)
        for attempt in range(max(4, self.restarts)):
            strat_idx = rng.randint(0, len(strategies) - 1)
            order = strategies[strat_idx](unassigned)

            asgn = list(fixed_assignments)
            x_pos = list(fixed_x)
            y_pos = list(fixed_y)

            box_state: list[dict] = []
            for b in range(nboxes):
                items = [i for i in range(nitems) if asgn[i] == b]
                bx = [x_pos[i] for i in items]
                by = [y_pos[i] for i in items]
                box_state.append({"items": items, "x": bx, "y": by})

            # Random box order per attempt
            box_order = list(range(nboxes))
            rng.shuffle(box_order)

            placed = True
            for i in order:
                placed_in_box = False
                for b in box_order:
                    pos = _find_position(i, box_state[b]["items"],
                                         box_state[b]["x"], box_state[b]["y"],
                                         info["item_w"], info["item_h"],
                                         info["box_w"][b], info["box_h"][b])
                    if pos is not None:
                        asgn[i] = b
                        x_pos[i] = pos[0]
                        y_pos[i] = pos[1]
                        box_state[b]["items"].append(i)
                        box_state[b]["x"].append(pos[0])
                        box_state[b]["y"].append(pos[1])
                        placed_in_box = True
                        break

                if not placed_in_box:
                    placed = False
                    break

            if placed:
                used = len([b for b in range(nboxes) if box_state[b]["items"]])
                if used < best_box_count:
                    best_box_count = used
                    best_result = (asgn, x_pos, y_pos)

        if best_result is not None:
            assignment_out = dict(partial_assignment)
            assignment_out["assignments"] = best_result[0]
            assignment_out["x_positions"] = best_result[1]
            assignment_out["y_positions"] = best_result[2]
            return assignment_out

        # If nothing worked, return original (evaluator will penalize)
        return partial_assignment


@dataclass
class DBPFullRepackRepair(RepairOperator):
    """Aggressively repack ALL items (not just destroyed) into boxes.

    Ignores the current assignment and repacks every item from scratch
    using greedy placement.  Useful when the incumbent solution has
    poor packing quality and needs a full reconstruction.

    Parameters
    ----------
    restarts : int
        Number of independent constructive attempts.
    """

    restarts: int = 16

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_2dbp_constants(context)
        if info is None:
            return partial_assignment

        rng: random.Random = context.extra["rng"]
        nitems = info["nitems"]
        nboxes = info["nboxes"]

        # Initialize fresh assignment
        asgn = [-1] * nitems
        x_pos = [0] * nitems
        y_pos = [0] * nitems

        best_result = None
        best_box_count = nboxes + 1

        strategies = [
            lambda: sorted(range(nitems), key=lambda i: info["item_w"][i] * info["item_h"][i], reverse=True),
            lambda: sorted(range(nitems), key=lambda i: max(info["item_w"][i], info["item_h"][i]), reverse=True),
            lambda: sorted(range(nitems), key=lambda i: info["item_w"][i], reverse=True),
            lambda: sorted(range(nitems), key=lambda i: info["item_h"][i], reverse=True),
        ]

        for attempt in range(max(1, self.restarts)):
            strat = strategies[attempt % len(strategies)]
            order = strat()

            box_state: list[dict] = [{"items": [], "x": [], "y": []} for _ in range(nboxes)]

            # Try different box orderings
            box_order = list(range(nboxes))
            if attempt >= len(strategies):
                rng.shuffle(box_order)

            placed = True
            for i in order:
                placed_in_box = False
                for b in box_order:
                    pos = _find_position(i, box_state[b]["items"],
                                         box_state[b]["x"], box_state[b]["y"],
                                         info["item_w"], info["item_h"],
                                         info["box_w"][b], info["box_h"][b])
                    if pos is not None:
                        asgn[i] = b
                        x_pos[i] = pos[0]
                        y_pos[i] = pos[1]
                        box_state[b]["items"].append(i)
                        box_state[b]["x"].append(pos[0])
                        box_state[b]["y"].append(pos[1])
                        placed_in_box = True
                        break

                if not placed_in_box:
                    placed = False
                    break

            if placed:
                used = len([b for b in range(nboxes) if box_state[b]["items"]])
                if used < best_box_count:
                    best_box_count = used
                    best_result = (list(asgn), list(x_pos), list(y_pos))

        if best_result is None:
            # Fallback with shuffled strategies
            for _ in range(8):
                order = list(range(nitems))
                rng.shuffle(order)
                big_first = sorted(order, key=lambda i: info["item_w"][i] * info["item_h"][i], reverse=True)

                box_state: list[dict] = [{"items": [], "x": [], "y": []} for _ in range(nboxes)]
                box_order = list(range(nboxes))
                rng.shuffle(box_order)

                placed = True
                for i in big_first:
                    p = False
                    for b in box_order:
                        pos = _find_position(i, box_state[b]["items"],
                                             box_state[b]["x"], box_state[b]["y"],
                                             info["item_w"], info["item_h"],
                                             info["box_w"][b], info["box_h"][b])
                        if pos is not None:
                            asgn[i] = b
                            x_pos[i] = pos[0]
                            y_pos[i] = pos[1]
                            box_state[b]["items"].append(i)
                            box_state[b]["x"].append(pos[0])
                            box_state[b]["y"].append(pos[1])
                            p = True
                            break
                    if not p:
                        placed = False
                        break

                if placed:
                    used = len([b for b in range(nboxes) if box_state[b]["items"]])
                    if used < best_box_count:
                        best_box_count = used
                        best_result = (list(asgn), list(x_pos), list(y_pos))

        if best_result is not None:
            partial_assignment["assignments"] = best_result[0]
            partial_assignment["x_positions"] = best_result[1]
            partial_assignment["y_positions"] = best_result[2]

        return partial_assignment
