"""Cutting & packing (1D cutting stock + layer bin-packing) LNS operators.

Targets the unified cutting/packing OptDSL model (see
``problem_instances/cutting_packing/benchmarks/generated_cp/*.dsl``), which has
two decision variables:

* ``cut_positions``  — ``DSList(N_CUTS, DSInt(0, MAX_SEGMENT_LENGTH))``
* ``piece_assignments`` — ``DSList(N_PIECES, DSInt(0, N_LAYERS))`` (``N_LAYERS``
  is the "waste" sentinel)

The hard constraint is an *exact-sum* layer fill: every layer must sum to
exactly ``LAYER_LENGTH`` (or be empty).  Generic random destroy/repair cannot
reach this, so these operators exploit the structure directly:

* ``CuttingPackingInitializer`` — constructive: cut each segment into
  full-layer pieces plus a remainder, then assign pieces to layers with an
  exact subset-sum fill.
* ``CuttingPackingLayerDestroy`` / ``CuttingPackingPieceDestroy`` — clear whole
  layers or a random fraction of pieces.
* ``CuttingPackingRepackRepair`` — re-assign *all* pieces given the current
  cuts (full repack).
* ``CuttingPackingInsertionRepair`` — re-assign only the destroyed pieces,
  keeping the rest fixed (local move).
* ``CuttingPackingRecutRepair`` — re-cut segments (randomized) and re-assign
  (a "shake" that explores the cut space).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..components import DestroyOperator, Initializer, RepairOperator
from ..lns import RandomAssignmentInitializer
from ..models import LNSContext


REQUIRED_CONSTANTS = (
    "LAYER_LENGTH",
    "N_LAYERS",
    "N_SEGMENTS",
    "N_CUTS_PER_SEGMENT",
    "N_PIECES_PER_SEGMENT",
    "N_CUTS",
    "N_PIECES",
    "SEGMENT_LENGTHS",
)
REQUIRED_VARIABLES = ("cut_positions", "piece_assignments")


def detect_cutting_packing_problem(context: LNSContext) -> bool:
    """Detect a cutting/packing problem by structural inspection."""
    constants = context.constants
    if not all(name in constants for name in REQUIRED_CONSTANTS):
        return False

    problem_data = context.extra.get("problem_data")
    if problem_data is None:
        return False
    variable_names = set(problem_data.variables.keys())
    return all(name in variable_names for name in REQUIRED_VARIABLES)


def _get_cutting_packing_constants(context: LNSContext):
    """Return the required constants as a dict, or None if not a C&P problem."""
    if not detect_cutting_packing_problem(context):
        return None
    c = context.constants
    return {
        "layer_length": int(c["LAYER_LENGTH"]),
        "n_layers": int(c["N_LAYERS"]),
        "n_segments": int(c["N_SEGMENTS"]),
        "n_cuts_per_seg": int(c["N_CUTS_PER_SEGMENT"]),
        "n_pieces_per_seg": int(c["N_PIECES_PER_SEGMENT"]),
        "n_cuts": int(c["N_CUTS"]),
        "n_pieces": int(c["N_PIECES"]),
        "segment_lengths": [int(v) for v in c["SEGMENT_LENGTHS"]],
        "min_piece_length": int(c.get("MIN_PIECE_LENGTH", 0)),
        "waste_weight": int(c.get("WASTE_WEIGHT", 1)),
        "cut_weight": int(c.get("CUT_WEIGHT", 1)),
    }


def _compute_piece_lengths(cut_positions: list, info: dict) -> list[int]:
    """Derive the flat piece-length vector from the cut positions.

    For segment ``s`` with cuts ``c[0..k-1]`` (k = N_CUTS_PER_SEGMENT) and
    length ``L``, the pieces are ``c[0]``, ``c[1]-c[0]``, ..., ``L-c[k-1]``.
    """
    n_segments = info["n_segments"]
    n_cuts_per_seg = info["n_cuts_per_seg"]
    n_pieces_per_seg = info["n_pieces_per_seg"]
    segment_lengths = info["segment_lengths"]

    piece_lengths = [0] * info["n_pieces"]
    for s in range(n_segments):
        length = segment_lengths[s]
        prev = 0
        for j in range(n_cuts_per_seg):
            cut = cut_positions[s * n_cuts_per_seg + j]
            piece_lengths[s * n_pieces_per_seg + j] = cut - prev
            prev = cut
        piece_lengths[s * n_pieces_per_seg + n_cuts_per_seg] = length - prev
    return piece_lengths


def _compute_cost(
    cut_positions: list,
    piece_assignments: list,
    piece_lengths: list[int],
    info: dict,
) -> int:
    """Replicate the DSL ``total_cost``: waste_weight * waste + cut_weight * n_cuts."""
    n_pieces = info["n_pieces"]
    n_layers = info["n_layers"]
    n_segments = info["n_segments"]
    n_cuts_per_seg = info["n_cuts_per_seg"]

    waste = 0
    for p in range(n_pieces):
        if piece_assignments[p] == n_layers:
            waste += piece_lengths[p]

    n_cuts = 0
    for s in range(n_segments):
        prev = 0
        for j in range(n_cuts_per_seg):
            if cut_positions[s * n_cuts_per_seg + j] > prev:
                n_cuts += 1
            prev = cut_positions[s * n_cuts_per_seg + j]

    return info["waste_weight"] * waste + info["cut_weight"] * n_cuts


def _generate_cuts(info: dict, rng: random.Random, randomized: bool = False):
    """Generate cut positions and the resulting piece lengths.

    Non-randomized mode cuts each segment into full ``LAYER_LENGTH`` pieces
    plus one remainder (minimizes the number of cuts).  Randomized mode picks
    random sorted cut positions to explore the cut space.
    """
    n_segments = info["n_segments"]
    n_cuts_per_seg = info["n_cuts_per_seg"]
    n_pieces_per_seg = info["n_pieces_per_seg"]
    n_cuts = info["n_cuts"]
    n_pieces = info["n_pieces"]
    layer_length = info["layer_length"]
    segment_lengths = info["segment_lengths"]

    cut_positions = [0] * n_cuts
    piece_lengths = [0] * n_pieces

    for s in range(n_segments):
        length = segment_lengths[s]
        if randomized and rng.random() < 0.6:
            positions = sorted(rng.randint(0, length) for _ in range(n_cuts_per_seg))
        else:
            positions = []
            prev_cut = 0
            remaining = length
            for _ in range(n_cuts_per_seg):
                if remaining >= layer_length:
                    prev_cut += layer_length
                    remaining -= layer_length
                positions.append(prev_cut)

        for j in range(n_cuts_per_seg):
            cut_positions[s * n_cuts_per_seg + j] = positions[j]

        prev = 0
        for j in range(n_cuts_per_seg):
            piece_lengths[s * n_pieces_per_seg + j] = positions[j] - prev
            prev = positions[j]
        piece_lengths[s * n_pieces_per_seg + n_cuts_per_seg] = length - prev

    return cut_positions, piece_lengths


def _find_exact_subset(
    pieces: list[int],
    piece_lengths: list[int],
    target: int,
    budget: int = 5000,
) -> list[int] | None:
    """Return a subset of *pieces* summing exactly to *target*, or None.

    Uses greedy first-fit followed by a bounded depth-first search.
    """
    # Greedy pass (pieces are expected to be sorted descending).
    chosen: list[int] = []
    total = 0
    for p in pieces:
        if total + piece_lengths[p] <= target:
            chosen.append(p)
            total += piece_lengths[p]
            if total == target:
                return chosen

    # Bounded DFS for an exact match.
    return _dfs_subset(pieces, piece_lengths, target, 0, [], 0, [budget])


def _dfs_subset(
    pieces: list[int],
    piece_lengths: list[int],
    target: int,
    idx: int,
    chosen: list[int],
    total: int,
    budget: list[int],
) -> list[int] | None:
    if total == target:
        return list(chosen)
    if total > target or idx >= len(pieces) or budget[0] <= 0:
        return None
    budget[0] -= 1

    p = pieces[idx]
    if total + piece_lengths[p] <= target:
        chosen.append(p)
        result = _dfs_subset(pieces, piece_lengths, target, idx + 1, chosen, total + piece_lengths[p], budget)
        if result is not None:
            return result
        chosen.pop()
    return _dfs_subset(pieces, piece_lengths, target, idx + 1, chosen, total, budget)


def _assign_pieces_exact(piece_lengths: list[int], info: dict) -> list[int]:
    """Assign pieces to layers so each layer sums exactly to LAYER_LENGTH.

    Pieces shorter than ``min_piece_length`` (or zero length) cannot be placed
    in a layer and are left as waste.  Layers are filled one at a time with an
    exact subset-sum; anything left over becomes waste.
    """
    n_pieces = info["n_pieces"]
    n_layers = info["n_layers"]
    layer_length = info["layer_length"]
    min_piece_length = info["min_piece_length"]

    piece_assignments = [n_layers] * n_pieces

    layerable = [
        p for p in range(n_pieces)
        if piece_lengths[p] > 0 and piece_lengths[p] >= min_piece_length
    ]
    layerable.sort(key=lambda p: -piece_lengths[p])

    remaining = list(layerable)
    for layer in range(n_layers):
        subset = _find_exact_subset(remaining, piece_lengths, layer_length)
        if subset is None:
            break
        for p in subset:
            piece_assignments[p] = layer
            remaining.remove(p)

    return piece_assignments


def _fix_partial_layers(
    piece_assignments: list,
    piece_lengths: list[int],
    layer_sum: list[int],
    info: dict,
) -> None:
    """Ensure every layer is exactly full or exactly empty.

    A partially-filled layer (0 < sum < LAYER_LENGTH) is infeasible.  Try to
    complete it from waste pieces; otherwise empty it (send its pieces to
    waste).
    """
    n_layers = info["n_layers"]
    layer_length = info["layer_length"]
    n_pieces = info["n_pieces"]
    min_piece_length = info["min_piece_length"]

    for layer in range(n_layers):
        total = layer_sum[layer]
        if total == 0 or total == layer_length:
            continue

        waste = [
            p for p in range(n_pieces)
            if piece_assignments[p] == n_layers
            and piece_lengths[p] > 0
            and piece_lengths[p] >= min_piece_length
        ]
        subset = _find_exact_subset(waste, piece_lengths, layer_length - total)
        if subset is not None:
            for p in subset:
                piece_assignments[p] = layer
            layer_sum[layer] = layer_length
        else:
            for p in range(n_pieces):
                if piece_assignments[p] == layer:
                    piece_assignments[p] = n_layers
            layer_sum[layer] = 0


def _construct(info: dict, rng: random.Random, randomized: bool = False):
    """Build a full assignment (cut + assign) and return (assignment, cost)."""
    cut_positions, piece_lengths = _generate_cuts(info, rng, randomized)
    piece_assignments = _assign_pieces_exact(piece_lengths, info)
    cost = _compute_cost(cut_positions, piece_assignments, piece_lengths, info)
    return {"cut_positions": cut_positions, "piece_assignments": piece_assignments}, cost


@dataclass
class CuttingPackingInitializer(Initializer):
    """Constructive cutting/packing initializer.

    Cuts each segment into full-layer pieces plus a remainder, then assigns
    pieces to layers with an exact subset-sum fill.  Returns the best of
    ``restarts`` independent attempts (feasibility/cost first).
    """

    restarts: int = 16

    def initialize(self, context: LNSContext) -> dict[str, object]:
        info = _get_cutting_packing_constants(context)
        if info is None:
            return RandomAssignmentInitializer().initialize(context)

        rng: random.Random = context.extra["rng"]
        best_assignment = None
        best_cost = float("inf")

        for _ in range(max(1, self.restarts)):
            assignment, cost = _construct(info, rng, randomized=False)
            if cost < best_cost:
                best_assignment = assignment
                best_cost = cost

        if best_assignment is None:
            return RandomAssignmentInitializer().initialize(context)
        return best_assignment


@dataclass
class CuttingPackingLayerDestroy(DestroyOperator):
    """Clear all pieces from selected layers (unassign them).

    Parameters
    ----------
    layer_count : int
        How many layers to clear per iteration.
    strategy : str
        'random' — pick layers uniformly; 'fullest' — pick the layers with the
        most pieces (frees the most material for re-packing).
    """

    layer_count: int = 1
    strategy: str = "random"

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_cutting_packing_constants(context)
        if info is None:
            return assignment

        rng: random.Random = context.extra["rng"]
        n_layers = info["n_layers"]
        n_pieces = info["n_pieces"]

        piece_assignments = assignment.get("piece_assignments")
        if not isinstance(piece_assignments, list) or len(piece_assignments) != n_pieces:
            return assignment

        layer_pieces: dict[int, list[int]] = {l: [] for l in range(n_layers)}
        for p in range(n_pieces):
            a = piece_assignments[p]
            if isinstance(a, int) and 0 <= a < n_layers:
                layer_pieces[a].append(p)

        non_empty = [l for l in range(n_layers) if layer_pieces[l]]
        if not non_empty:
            return assignment

        k = min(self.layer_count, len(non_empty))
        if self.strategy == "fullest" and len(non_empty) > 1:
            non_empty.sort(key=lambda l: -len(layer_pieces[l]))
            selected = non_empty[:k]
        else:
            selected = rng.sample(non_empty, k)

        for layer in selected:
            for p in layer_pieces[layer]:
                piece_assignments[p] = None

        return assignment


@dataclass
class CuttingPackingPieceDestroy(DestroyOperator):
    """Unassign a random fraction of pieces.

    Parameters
    ----------
    fraction : float
        Fraction of assigned pieces to unassign (0.0 – 1.0).
    min_pieces : int
        Minimum number of pieces to destroy even if fraction yields fewer.
    """

    fraction: float = 0.3
    min_pieces: int = 1

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_cutting_packing_constants(context)
        if info is None:
            return assignment

        rng: random.Random = context.extra["rng"]
        n_pieces = info["n_pieces"]

        piece_assignments = assignment.get("piece_assignments")
        if not isinstance(piece_assignments, list) or len(piece_assignments) != n_pieces:
            return assignment

        assigned = [p for p in range(n_pieces) if piece_assignments[p] is not None]
        if not assigned:
            return assignment

        n_destroy = max(self.min_pieces, int(round(n_pieces * max(0.0, min(1.0, self.fraction)))))
        to_destroy = rng.sample(assigned, min(n_destroy, len(assigned)))

        for p in to_destroy:
            piece_assignments[p] = None

        return assignment


@dataclass
class CuttingPackingRepackRepair(RepairOperator):
    """Re-assign *all* pieces given the current cut positions (full repack).

    Ignores which pieces were destroyed and rebuilds the layer assignment from
    scratch with an exact subset-sum fill.  Returns the best of ``restarts``
    attempts.
    """

    restarts: int = 8

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_cutting_packing_constants(context)
        if info is None:
            return partial_assignment

        cut_positions = partial_assignment.get("cut_positions")
        if not isinstance(cut_positions, list) or len(cut_positions) != info["n_cuts"]:
            return partial_assignment

        piece_lengths = _compute_piece_lengths(cut_positions, info)

        best_assignments = None
        best_cost = float("inf")
        for _ in range(max(1, self.restarts)):
            piece_assignments = _assign_pieces_exact(piece_lengths, info)
            cost = _compute_cost(cut_positions, piece_assignments, piece_lengths, info)
            if cost < best_cost:
                best_assignments = piece_assignments
                best_cost = cost

        if best_assignments is not None:
            out = dict(partial_assignment)
            out["piece_assignments"] = best_assignments
            return out
        return partial_assignment


@dataclass
class CuttingPackingInsertionRepair(RepairOperator):
    """Re-assign only the destroyed (unassigned) pieces, keeping the rest fixed.

    A local move: computes current layer sums from the fixed pieces, then
    greedily inserts the unassigned pieces (largest first) and repairs any
    partially-filled layers to satisfy the exact-sum constraint.
    """

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_cutting_packing_constants(context)
        if info is None:
            return partial_assignment

        piece_assignments = partial_assignment.get("piece_assignments")
        cut_positions = partial_assignment.get("cut_positions")
        if not isinstance(piece_assignments, list) or not isinstance(cut_positions, list):
            return partial_assignment

        piece_lengths = _compute_piece_lengths(cut_positions, info)
        n_pieces = info["n_pieces"]
        n_layers = info["n_layers"]
        layer_length = info["layer_length"]
        min_piece_length = info["min_piece_length"]

        layer_sum = [0] * n_layers
        unassigned: list[int] = []
        for p in range(n_pieces):
            a = piece_assignments[p]
            if a is None:
                unassigned.append(p)
            elif isinstance(a, int) and 0 <= a < n_layers:
                layer_sum[a] += piece_lengths[p]

        unassigned.sort(key=lambda p: -piece_lengths[p])
        for p in unassigned:
            if piece_lengths[p] <= 0 or piece_lengths[p] < min_piece_length:
                piece_assignments[p] = n_layers
                continue
            placed = False
            for layer in range(n_layers):
                if layer_sum[layer] + piece_lengths[p] <= layer_length:
                    piece_assignments[p] = layer
                    layer_sum[layer] += piece_lengths[p]
                    placed = True
                    break
            if not placed:
                piece_assignments[p] = n_layers

        _fix_partial_layers(piece_assignments, piece_lengths, layer_sum, info)
        return partial_assignment


@dataclass
class CuttingPackingRecutRepair(RepairOperator):
    """Re-cut segments (randomized) and re-assign — a full "shake".

    Explores the cut space (which the assignment-only repairs leave fixed) so
    LNS can escape local optima in the number of cuts / waste trade-off.
    Returns the best of ``restarts`` randomized reconstructions.
    """

    restarts: int = 8

    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        info = _get_cutting_packing_constants(context)
        if info is None:
            return partial_assignment

        rng: random.Random = context.extra["rng"]
        best_assignment = None
        best_cost = float("inf")

        for _ in range(max(1, self.restarts)):
            assignment, cost = _construct(info, rng, randomized=True)
            if cost < best_cost:
                best_assignment = assignment
                best_cost = cost

        if best_assignment is not None:
            return best_assignment
        return partial_assignment
