"""Giant-tour CVRP initializer and cut-aware repair for the LNS framework.

Two giant-tour encodings are supported:

* ``tour`` + ``cut_after`` -- a permutation of the customer ids plus a binary
  array marking route breaks (``golden_optdsl_giant_tour``).
* ``city_tour`` -- a permutation only; route breaks are derived from the
  capacity constraint inside the DSL (``random_euclidean_cvrp_20_gt``).

The generic permutation initializer fills ``cut_after`` uniformly at random,
which violates the route-count constraint on any instance with more than a
handful of customers.  ``GiantTourInitializer`` builds a capacity-feasible
tour instead, and ``GiantTourCutRepair`` re-derives the cuts after every
destroy step so the search stays in the feasible region.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .._utils import _list_get, _list_set
from ..components import Initializer, RepairOperator
from ..lns import RandomAssignmentInitializer
from ..models import LNSContext


REQUIRED_CONSTANTS = ("DEPOT", "DEMANDS", "VEHICLE_CAPACITY", "N_CITIES")
TOUR_VARIABLES = ("tour", "city_tour")
CUT_VARIABLE = "cut_after"


def _distance_matrix(constants: dict[str, Any]) -> list[list[int]] | None:
    matrix = constants.get("DISTANCE_MATRIX")
    if matrix is None:
        return None
    size = len(matrix)
    return [[int(matrix[i][j]) for j in range(size)] for i in range(size)]


def _giant_tour_spec(
    context: LNSContext,
) -> tuple[str, str | None, list[int], int, int, list[int], list[list[int]] | None, int] | None:
    """Return the giant-tour structure of the model, or ``None`` if absent.

    Tuple layout: ``(tour_var, cut_var, customers, depot, capacity, demands,
    distance, n_vehicles)``.  ``cut_var`` is ``None`` for permutation-only
    encodings where the DSL derives route breaks from the capacity constraint.
    """
    constants = context.constants
    if not all(name in constants for name in REQUIRED_CONSTANTS):
        return None

    problem_data = context.extra.get("problem_data")
    if problem_data is None:
        return None
    variables = set(problem_data.variables.keys())

    tour_var = next((name for name in TOUR_VARIABLES if name in variables), None)
    if tour_var is None:
        return None
    cut_var = CUT_VARIABLE if CUT_VARIABLE in variables else None

    keys_by_variable = context.extra.get("keys_by_variable", {})
    domains = context.extra.get("decision_domains", {})
    keys = [key for key in keys_by_variable.get(tour_var, []) if isinstance(key[1], int)]
    if not keys:
        return None
    keys.sort(key=lambda key: key[1])
    if [key[1] for key in keys] != list(range(len(keys))):
        return None

    lower, upper = domains[keys[0]]
    if upper - lower + 1 != len(keys):
        return None

    demands = [int(value) for value in constants["DEMANDS"]]
    customers = list(range(lower, upper + 1))
    if customers and max(customers) >= len(demands):
        return None

    depot = int(constants["DEPOT"])
    capacity = int(constants["VEHICLE_CAPACITY"])
    n_vehicles = int(constants.get("N_VEHICLES", len(customers)))
    return (
        tour_var,
        cut_var,
        customers,
        depot,
        capacity,
        demands,
        _distance_matrix(constants),
        n_vehicles,
    )


def detect_giant_tour_problem(context: LNSContext) -> bool:
    """True when the model uses a giant-tour (permutation) CVRP encoding."""
    return _giant_tour_spec(context) is not None


def _place_cuts(tour: list[int], capacity: int, demands: list[int]) -> list[int]:
    """Greedy longest-prefix segmentation; optimal route count for a fixed tour.

    Cheap (single pass) and used inside the 2-opt loop, where the cut plan is
    only needed to check the route-count constraint.
    """
    cuts = [0] * len(tour)
    load = 0
    for pos, city in enumerate(tour):
        demand = demands[city]
        if load + demand > capacity and pos > 0:
            cuts[pos - 1] = 1
            load = 0
        load += demand
    return cuts


def _optimal_cuts(
    tour: list[int],
    capacity: int,
    demands: list[int],
    depot: int,
    distance: list[list[int]] | None,
    n_vehicles: int,
) -> list[int]:
    """Minimum-cost cut placement for a fixed tour (shortest-path DP).

    Greedy longest-prefix segmentation minimises the route *count* but not the
    distance, because a cut costs ``d(prev, depot) + d(depot, next)`` instead of
    ``d(prev, next)``.  After a repair the difference is several hundred units,
    so the repair uses this instead.  Falls back to greedy when no distance
    matrix is available or the DP would exceed ``n_vehicles`` routes.
    """
    greedy = _place_cuts(tour, capacity, demands)
    if distance is None or not tour:
        return greedy

    size = len(tour)
    infinity = float("inf")
    best = [infinity] * (size + 1)
    previous = [-1] * (size + 1)
    best[0] = 0.0

    for start in range(size):
        if best[start] == infinity:
            continue
        load = 0
        segment = 0
        for end in range(start, size):
            load += demands[tour[end]]
            if load > capacity:
                break
            if end == start:
                segment = distance[depot][tour[end]]
            else:
                segment += distance[tour[end - 1]][tour[end]]
            total = best[start] + segment + distance[tour[end]][depot]
            if total < best[end + 1]:
                best[end + 1] = total
                previous[end + 1] = start

    if previous[size] < 0:
        return greedy

    cuts = [0] * size
    position = size
    while position > 0:
        start = previous[position]
        if start < 0:
            return greedy
        if position - 1 < size - 1:
            cuts[position - 1] = 1
        position = start

    if sum(cuts) + 1 > n_vehicles:
        return greedy
    return cuts


def _or_opt_improve(
    tour: list[int],
    depot: int,
    capacity: int,
    demands: list[int],
    distance: list[list[int]] | None,
    n_vehicles: int,
    steps: int,
) -> list[int]:
    """First-improvement Or-opt (relocate segments of 1-3 customers).

    2-opt alone cannot move a customer between two distant parts of the giant
    tour, which is exactly the move a destroy/repair step needs to be able to
    exploit.  ``steps`` bounds the number of candidate relocations examined.
    """
    if distance is None or steps <= 0 or len(tour) < 3:
        return tour

    best = list(tour)
    size = len(best)
    best_cuts = _place_cuts(best, capacity, demands)
    best_cost = _tour_cost(best, best_cuts, depot, distance)
    examined = 0

    improved = True
    while improved and examined < steps:
        improved = False
        for length in (1, 2, 3):
            if improved or examined >= steps:
                break
            for start in range(size - length + 1):
                if examined >= steps:
                    break
                segment = best[start : start + length]
                remainder = best[:start] + best[start + length :]
                for pos in range(len(remainder) + 1):
                    if pos == start:
                        continue
                    examined += 1
                    if examined > steps:
                        break
                    candidate = remainder[:pos] + segment + remainder[pos:]
                    cuts = _place_cuts(candidate, capacity, demands)
                    if sum(cuts) + 1 > n_vehicles:
                        continue
                    cost = _tour_cost(candidate, cuts, depot, distance)
                    if cost < best_cost:
                        best, best_cuts, best_cost = candidate, cuts, cost
                        improved = True
                        break
                if improved:
                    break

    return best


def _local_search(
    tour: list[int],
    depot: int,
    capacity: int,
    demands: list[int],
    distance: list[list[int]] | None,
    n_vehicles: int,
    steps: int,
) -> list[int]:
    """Alternate 2-opt and Or-opt until neither improves or the budget is spent."""
    if steps <= 0:
        return tour
    remaining = steps
    while remaining > 0:
        before = _tour_cost(tour, _place_cuts(tour, capacity, demands), depot, distance)
        tour = _two_opt_improve(
            tour, random.Random(0), depot, capacity, demands, distance, n_vehicles, remaining
        )
        tour = _or_opt_improve(
            tour, depot, capacity, demands, distance, n_vehicles, remaining
        )
        after = _tour_cost(tour, _place_cuts(tour, capacity, demands), depot, distance)
        if after >= before:
            break
        remaining //= 2
    return tour


def _tour_cost(
    tour: list[int],
    cuts: list[int],
    depot: int,
    distance: list[list[int]] | None,
) -> int:
    if not tour or distance is None:
        return 0
    total = distance[depot][tour[0]]
    for pos in range(len(tour) - 1):
        if cuts[pos]:
            total += distance[tour[pos]][depot] + distance[depot][tour[pos + 1]]
        else:
            total += distance[tour[pos]][tour[pos + 1]]
    total += distance[tour[-1]][depot]
    return total


def _build_tour(
    rng: random.Random,
    customers: list[int],
    depot: int,
    capacity: int,
    demands: list[int],
    distance: list[list[int]] | None,
    randomization: float,
) -> list[int]:
    """Randomized nearest-neighbour tour that never overfills a route.

    ``randomization`` sizes a restricted candidate list (GRASP style): the next
    customer is drawn from the ``1 + 4 * randomization`` nearest feasible ones.
    Picking uniformly among *all* feasible customers instead would destroy the
    tour quality on instances of this size.
    """
    unvisited = list(customers)
    rng.shuffle(unvisited)
    tour: list[int] = []
    load = 0
    current = depot
    rcl_size = max(1, int(round(1 + 4 * max(0.0, min(1.0, randomization)))))

    while unvisited:
        feasible = [city for city in unvisited if load + demands[city] <= capacity]
        if not feasible:
            load = 0
            current = depot
            continue
        if distance is None:
            chosen = rng.choice(feasible)
        else:
            feasible.sort(key=lambda city: distance[current][city])
            chosen = rng.choice(feasible[:rcl_size])
        tour.append(chosen)
        unvisited.remove(chosen)
        load += demands[chosen]
        current = chosen

    return tour


def _insertion_delta(
    tour: list[int],
    pos: int,
    city: int,
    depot: int,
    distance: list[list[int]] | None,
) -> int:
    """Distance delta of inserting ``city`` at ``pos`` in the giant tour.

    Computed on the pure tour order (no depot detours), because the repair
    re-derives the cut plan after every insertion.
    """
    if not tour or distance is None:
        return 0
    if pos == 0:
        return distance[depot][city] + distance[city][tour[0]] - distance[depot][tour[0]]
    if pos == len(tour):
        return distance[tour[-1]][city] + distance[city][depot] - distance[tour[-1]][depot]

    left, right = tour[pos - 1], tour[pos]
    return distance[left][city] + distance[city][right] - distance[left][right]


def _insert_customers(
    tour: list[int],
    missing: list[int],
    depot: int,
    capacity: int,
    demands: list[int],
    distance: list[list[int]] | None,
    n_vehicles: int,
    rng: random.Random | None = None,
    rcl_size: int = 1,
) -> list[int]:
    """Insert ``missing`` customers, re-deriving the cut plan afterwards.

    Positions are ranked by pure distance delta and the cut plan is recomputed
    from the resulting tour, so an insertion may rebalance two neighbouring
    routes instead of being forced into the one route that still has slack.
    Ranking by segment feasibility first would pin every customer to the tail
    of the tour once the routes are packed to capacity.
    """
    for city in missing:
        options: list[tuple[int, int]] = []
        for pos in range(len(tour) + 1):
            delta = _insertion_delta(tour, pos, city, depot, distance)
            options.append((delta, pos))
        options.sort()

        chosen_pos: int | None = None
        for _, pos in options:
            candidate = tour[:pos] + [city] + tour[pos:]
            if sum(_place_cuts(candidate, capacity, demands)) + 1 <= n_vehicles:
                chosen_pos = pos
                break

        if chosen_pos is None:
            chosen_pos = options[0][1] if options else len(tour)

        if rng is not None and rcl_size > 1:
            window = [pos for _, pos in options[: min(rcl_size, len(options))]]
            feasible_window = [
                pos
                for pos in window
                if sum(_place_cuts(tour[:pos] + [city] + tour[pos:], capacity, demands)) + 1
                <= n_vehicles
            ]
            if feasible_window:
                chosen_pos = rng.choice(feasible_window)

        tour.insert(chosen_pos, city)

    return tour


def _fill_remaining(
    assignment: dict[str, object],
    context: LNSContext,
    handled: set[str],
) -> None:
    """Randomly complete any decision variable not owned by this repair."""
    from ..defaults import _decision_keys, _sample_value

    rng: random.Random = context.extra["rng"]
    for key in _decision_keys(context):
        var_name, idx = key
        if var_name in handled:
            continue
        if idx is None:
            if assignment.get(var_name) is None:
                assignment[var_name] = _sample_value(rng, key, context)
            continue
        value = assignment.get(var_name)
        if isinstance(value, list) and _list_get(value, idx) is None:
            _list_set(value, idx, _sample_value(rng, key, context))


def _two_opt_improve(
    tour: list[int],
    rng: random.Random,
    depot: int,
    capacity: int,
    demands: list[int],
    distance: list[list[int]] | None,
    n_vehicles: int,
    steps: int,
) -> list[int]:
    """First-improvement 2-opt on the giant tour, keeping the route count feasible.

    ``steps`` bounds the number of candidate reversals examined, so the work
    stays predictable on large instances.  A reversal is accepted only if the
    re-derived cut plan still fits into ``n_vehicles`` routes and the tour cost
    decreases.
    """
    if distance is None or steps <= 0 or len(tour) < 4:
        return tour

    best = list(tour)
    size = len(best)
    best_cuts = _place_cuts(best, capacity, demands)
    best_cost = _tour_cost(best, best_cuts, depot, distance)
    examined = 0

    improved = True
    while improved and examined < steps:
        improved = False
        for i in range(size - 1):
            if examined >= steps:
                break
            left = depot if i == 0 else best[i - 1]
            for j in range(i + 1, size):
                examined += 1
                if examined > steps:
                    break
                right = depot if j == size - 1 else best[j + 1]
                delta = (
                    distance[left][best[j]]
                    + distance[best[i]][right]
                    - distance[left][best[i]]
                    - distance[best[j]][right]
                )
                if delta >= 0:
                    continue
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                cuts = _place_cuts(candidate, capacity, demands)
                if sum(cuts) + 1 > n_vehicles:
                    continue
                cost = _tour_cost(candidate, cuts, depot, distance)
                if cost < best_cost:
                    best, best_cuts, best_cost = candidate, cuts, cost
                    improved = True
                    break
            if improved:
                break

    return best


@dataclass
class GiantTourInitializer(Initializer):
    """Constructive giant-tour initializer with capacity-feasible cut placement.

    Builds a randomized nearest-neighbour tour that never overfills a route,
    derives ``cut_after`` by greedy longest-prefix segmentation, and polishes
    the best restart with bounded 2-opt.  Restarts are ranked by
    (route-count excess, tour cost).
    """

    restarts: int = 8
    randomization: float = 0.1
    improve_steps: int = 20000
    or_opt_steps: int = 20000

    def initialize(self, context: LNSContext) -> dict[str, object]:
        spec = _giant_tour_spec(context)
        if spec is None:
            return RandomAssignmentInitializer().initialize(context)

        tour_var, cut_var, customers, depot, capacity, demands, distance, n_vehicles = spec
        rng: random.Random = context.extra["rng"]

        best_tour: list[int] | None = None
        best_key: tuple[int, int] | None = None

        for _ in range(max(1, self.restarts)):
            tour = _build_tour(
                rng, customers, depot, capacity, demands, distance, self.randomization
            )
            cuts = _place_cuts(tour, capacity, demands)
            routes = sum(cuts) + 1 if tour else 0
            key = (max(0, routes - n_vehicles), _tour_cost(tour, cuts, depot, distance))
            if best_key is None or key < best_key:
                best_key = key
                best_tour = tour

        # Nearest neighbour can need more vehicles than available; a
        # demand-descending order minimises the route count for a fixed tour.
        if best_key is not None and best_key[0] > 0:
            fallback = sorted(customers, key=lambda city: -demands[city])
            if sum(_place_cuts(fallback, capacity, demands)) + 1 <= n_vehicles:
                best_tour = fallback

        if best_tour is not None:
            best_tour = _two_opt_improve(
                best_tour,
                rng,
                depot,
                capacity,
                demands,
                distance,
                n_vehicles,
                self.improve_steps,
            )
            best_tour = _or_opt_improve(
                best_tour,
                depot,
                capacity,
                demands,
                distance,
                n_vehicles,
                self.or_opt_steps,
            )

        assignment = RandomAssignmentInitializer().initialize(context)
        if best_tour is not None:
            assignment[tour_var] = best_tour
            if cut_var is not None:
                assignment[cut_var] = _optimal_cuts(
                    best_tour, capacity, demands, depot, distance, n_vehicles
                )
        return assignment


@dataclass
class GiantTourCutRepair(RepairOperator):
    """Restore a giant-tour assignment and re-derive ``cut_after``.

    Holes left by a permutation destroy are re-inserted at the cheapest
    position that keeps the route count within ``N_VEHICLES``, the tour is
    polished with bounded 2-opt, and the cut array is recomputed by
    shortest-path DP.  Without this step the generic permutation repair
    re-randomizes ``cut_after`` and the candidate is infeasible on every
    iteration.
    """

    insertion_candidates: int = 3
    improve_steps: int = 2000

    def repair(
        self,
        partial_assignment: dict[str, object],
        context: LNSContext,
    ) -> dict[str, object]:
        spec = _giant_tour_spec(context)
        if spec is None:
            from ..defaults import FillMissingPermutationRepair

            return FillMissingPermutationRepair().repair(partial_assignment, context)

        tour_var, cut_var, customers, depot, capacity, demands, distance, n_vehicles = spec
        rng: random.Random = context.extra["rng"]

        current = partial_assignment.get(tour_var)
        if not isinstance(current, list):
            current = []

        allowed = set(customers)
        seen: set[int] = set()
        tour: list[int] = []
        for value in current:
            if isinstance(value, int) and value in allowed and value not in seen:
                seen.add(value)
                tour.append(value)

        missing = [city for city in customers if city not in seen]
        rng.shuffle(missing)
        tour = _insert_customers(
            tour,
            missing,
            depot,
            capacity,
            demands,
            distance,
            n_vehicles,
            rng=rng,
            rcl_size=max(1, self.insertion_candidates),
        )
        tour = _two_opt_improve(
            tour,
            rng,
            depot,
            capacity,
            demands,
            distance,
            n_vehicles,
            self.improve_steps,
        )

        partial_assignment[tour_var] = tour
        if cut_var is not None:
            partial_assignment[cut_var] = _optimal_cuts(
                tour, capacity, demands, depot, distance, n_vehicles
            )

        handled = {tour_var} if cut_var is None else {tour_var, cut_var}
        _fill_remaining(partial_assignment, context, handled)
        return partial_assignment
