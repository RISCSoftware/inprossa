"""CVRP-aware constructive initializer for the LNS framework.

Detects a CVRP-style DSL problem by structural inspection (constants and
variables) and produces a feasible initial assignment by building vehicle
routes with a randomized nearest-neighbor heuristic respecting capacity.

Falls back to a random assignment if the problem does not match the
expected CVRP structure or if no feasible route packing is found within
the allowed attempts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from ..components import Initializer
from ..lns import RandomAssignmentInitializer
from ..models import LNSContext


REQUIRED_CONSTANTS = ("DEPOT", "DEMANDS", "VEHICLE_CAPACITY", "N_CITIES", "N_VEHICLES")
REQUIRED_VARIABLES = ("arcs", "vehicle_used")


def detect_cvrp_problem(context: LNSContext) -> bool:
    constants = context.constants
    if not all(name in constants for name in REQUIRED_CONSTANTS):
        return False

    problem_data = context.extra.get("problem_data")
    if problem_data is None:
        return False
    variable_names = set(problem_data.variables.keys())
    if not all(name in variable_names for name in REQUIRED_VARIABLES):
        return False

    n_cities = int(constants["N_CITIES"])
    n_vehicles = int(constants["N_VEHICLES"])
    expected_arcs = n_vehicles * n_cities * n_cities

    arcs_value = context.extra.get("decision_domains", {})
    arc_keys = [k for k in arcs_value.keys() if isinstance(k, tuple) and len(k) == 2 and k[0] == "arcs"]
    return len(arc_keys) == expected_arcs


def prepare_cvrp_assignment_for_evaluation(assignment: dict[str, object], context: LNSContext) -> None:
    if not detect_cvrp_problem(context):
        return
    if "arcs" not in assignment:
        return

    arcs = assignment.get("arcs")
    if not isinstance(arcs, list):
        return

    constants = context.constants
    n_cities = int(constants["N_CITIES"])
    n_vehicles = int(constants["N_VEHICLES"])
    depot = int(constants["DEPOT"])
    demands_obj = constants.get("DEMANDS")
    if not isinstance(demands_obj, list):
        return

    demands = [int(v) for v in demands_obj]
    expected_arcs = n_vehicles * n_cities * n_cities
    if len(arcs) != expected_arcs or not all(isinstance(v, int) for v in arcs):
        return

    def arc_value(v: int, i: int, j: int) -> int:
        idx = v * n_cities * n_cities + i * n_cities + j
        value = arcs[idx]
        return int(value) if isinstance(value, int) else 0

    if "vehicle_used" in assignment and isinstance(assignment["vehicle_used"], list):
        vehicle_used = assignment["vehicle_used"]
        if len(vehicle_used) == n_vehicles:
            for v in range(n_vehicles):
                departures = 0
                for j in range(n_cities):
                    departures += arc_value(v, depot, j)
                vehicle_used[v] = 1 if departures > 0 else 0

    if "u" in assignment and isinstance(assignment["u"], list):
        u_values = assignment["u"]
        if len(u_values) == n_cities:
            for i in range(n_cities):
                u_values[i] = 0

            for v in range(n_vehicles):
                current = depot
                load = 0
                seen_customers: set[int] = set()
                hop_limit = n_cities + 1

                for _ in range(hop_limit):
                    successors = [j for j in range(n_cities) if arc_value(v, current, j) == 1]
                    if not successors:
                        break

                    nxt = successors[0]
                    if nxt == depot or nxt in seen_customers:
                        break

                    seen_customers.add(nxt)
                    if 0 <= nxt < len(demands):
                        load += demands[nxt]
                    u_values[nxt] = max(int(u_values[nxt]), load)
                    current = nxt

            if 0 <= depot < n_cities:
                u_values[depot] = 0


@dataclass
class CVRPRouteInitializer(Initializer):
    """Constructive CVRP initializer.

    For each restart attempt, builds vehicle routes greedily by nearest
    neighbor with randomized tie-breaking and capacity feasibility.
    Encodes the resulting routes into the binary `arcs` and `vehicle_used`
    decision variables. Returns the best feasibility-first attempt.
    """

    restarts: int = 16
    randomization: float = 0.3

    def initialize(self, context: LNSContext) -> dict[str, object]:
        if not detect_cvrp_problem(context):
            return RandomAssignmentInitializer().initialize(context)

        rng: random.Random = context.extra["rng"]
        constants = context.constants
        depot = int(constants["DEPOT"])
        n_cities = int(constants["N_CITIES"])
        n_vehicles = int(constants["N_VEHICLES"])
        capacity = int(constants["VEHICLE_CAPACITY"])
        demands = [int(d) for d in constants["DEMANDS"]]
        distance = constants.get("DISTANCE_MATRIX")
        has_u_variable = "u" in context.extra.get("keys_by_variable", {})

        best_assignment: dict[str, object] | None = None
        best_unserved = n_cities

        for _ in range(max(1, self.restarts)):
            routes, unserved = self._build_routes(
                rng=rng,
                depot=depot,
                n_cities=n_cities,
                n_vehicles=n_vehicles,
                capacity=capacity,
                demands=demands,
                distance=distance,
            )

            if unserved < best_unserved:
                best_assignment = self._encode_assignment(
                    routes,
                    n_cities,
                    n_vehicles,
                    depot,
                    demands,
                    has_u_variable,
                )
                best_unserved = unserved
                if best_unserved == 0:
                    break

        if best_assignment is None:
            return RandomAssignmentInitializer().initialize(context)
        return best_assignment

    def _build_routes(
        self,
        rng: random.Random,
        depot: int,
        n_cities: int,
        n_vehicles: int,
        capacity: int,
        demands: list[int],
        distance: Any,
    ) -> tuple[list[list[int]], int]:
        unvisited = [c for c in range(n_cities) if c != depot]
        rng.shuffle(unvisited)

        routes: list[list[int]] = [[] for _ in range(n_vehicles)]
        loads = [0] * n_vehicles
        randomization = max(0.0, min(1.0, self.randomization))

        for v in range(n_vehicles):
            current = depot
            while True:
                feasible = [c for c in unvisited if loads[v] + demands[c] <= capacity]
                if not feasible:
                    break

                if rng.random() < randomization or distance is None:
                    chosen = rng.choice(feasible)
                else:
                    chosen = min(feasible, key=lambda c, cur=current: int(distance[cur][c]))

                routes[v].append(chosen)
                loads[v] += demands[chosen]
                unvisited.remove(chosen)
                current = chosen

            if not unvisited:
                break

        return routes, len(unvisited)

    def _encode_assignment(
        self,
        routes: list[list[int]],
        n_cities: int,
        n_vehicles: int,
        depot: int,
        demands: list[int],
        include_u: bool,
    ) -> dict[str, object]:
        n_arcs = n_vehicles * n_cities * n_cities
        arcs = [0 for _ in range(n_arcs)]
        vehicle_used = [0 for _ in range(n_vehicles)]
        u = [0 for _ in range(n_cities)]

        def arc_index(v: int, i: int, j: int) -> int:
            return v * n_cities * n_cities + i * n_cities + j

        for v, route in enumerate(routes):
            if not route:
                continue
            vehicle_used[v] = 1
            previous = depot
            cumulative_load = 0
            for city in route:
                arcs[arc_index(v, previous, city)] = 1
                cumulative_load += demands[city]
                if city != depot:
                    u[city] = cumulative_load
                previous = city
            arcs[arc_index(v, previous, depot)] = 1

        assignment: dict[str, object] = {"arcs": arcs, "vehicle_used": vehicle_used}
        if include_u:
            assignment["u"] = u
        return assignment
