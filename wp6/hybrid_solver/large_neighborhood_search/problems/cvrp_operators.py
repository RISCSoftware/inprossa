"""CVRP-specific LNS operators that work directly on arc variables.

Operates on the flat binary arc variables, vehicle_used, and u without
a decode/encode cycle.  Arc index: arcs[v*N^2 + i*N + j].

Destroy: zeroes arcs of selected vehicles or removes customers by
patching predecessor->successor links.

Repair: finds feasible insertion positions in the arc representation
and sets the appropriate incoming/outgoing arcs.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ..components import DestroyOperator, RepairOperator
from ..models import LNSContext

_REQUIRED = ("DEPOT", "DEMANDS", "VEHICLE_CAPACITY", "N_CITIES", "N_VEHICLES", "DISTANCE_MATRIX")


def _cvrp(ctx: LNSContext) -> dict | None:
    c = ctx.constants
    if not all(k in c for k in _REQUIRED):
        return None
    depot = int(c["DEPOT"])
    n = int(c["N_CITIES"])
    nv = int(c["N_VEHICLES"])
    cap = int(c["VEHICLE_CAPACITY"])
    dem = [int(v) for v in c["DEMANDS"]]
    dm = c["DISTANCE_MATRIX"]
    dist = [[int(dm[i][j]) for j in range(n)] for i in range(n)]
    q = n * n
    return {"depot": depot, "n": n, "nv": nv, "cap": cap, "dem": dem, "dist": dist, "nq": q}


# --------------- Route-list cache ---------------
# A transient per-operator view built from the flat `arcs` list in a single
# O(N*V) pass.  Replaces the repeated _route_of / _load_of / _all_served
# scans that dominated per-iteration cost on Golden_1 (240 customers, 9
# vehicles -> 638,891 arc variables).  The cache is NOT persisted: operators
# mutate the route lists and call apply() to write back to arcs + recompute
# u / vehicle_used.

class _RouteCache:
    """Cached route-list view of a flat `arcs` assignment.

    Attributes:
        n, nv, depot, nq, cap, dem, dist: problem constants (from _cvrp()).
        routes: list[list[int]] -- customer list per vehicle (excluding depot).
        loads: list[int] -- cumulative demand per vehicle.
        costs: list[int] -- route distance (depot->...->depot) per vehicle.
        served: set[int] -- customers appearing on any route.
        used: list[int] -- indices of vehicles with a non-empty route.
        dirty: set[int] -- vehicles whose route changed since the last apply().
            Operators mark vehicles dirty so local-search repairs can limit
            2-opt/inter-route work to touched routes only.
    """

    __slots__ = ("n", "nv", "depot", "nq", "cap", "dem", "dist",
                 "routes", "loads", "costs", "served", "used", "dirty")

    def __init__(self, p: dict) -> None:
        self.n = p["n"]
        self.nv = p["nv"]
        self.depot = p["depot"]
        self.nq = p["nq"]
        self.cap = p["cap"]
        self.dem = p["dem"]
        self.dist = p["dist"]
        self.routes: list[list[int]] = [[] for _ in range(self.nv)]
        self.loads = [0] * self.nv
        self.costs = [0] * self.nv
        self.served: set[int] = set()
        self.used: list[int] = []
        self.dirty: set[int] = set()

    @classmethod
    def from_arcs(cls, arcs: list[int], p: dict) -> "_RouteCache":
        cache = cls(p)
        cache._build_from_arcs(arcs)
        return cache

    def _build_from_arcs(self, arcs: list[int]) -> None:
        """Populate routes/loads/costs/served/used from arcs in one pass."""
        n, nv, depot, nq, dem, dist = self.n, self.nv, self.depot, self.nq, self.dem, self.dist
        self.routes = [[] for _ in range(nv)]
        self.loads = [0] * nv
        self.costs = [0] * nv
        self.served = set()
        self.used = []
        for v in range(nv):
            offset = v * nq
            cur = depot
            load = 0
            cost = 0
            visited: set[int] = set()
            route: list[int] = []
            for _ in range(n):
                nxt = -1
                base = offset + cur * n
                for j in range(n):
                    if arcs[base + j]:
                        nxt = j
                        break
                if nxt < 0 or nxt == depot or nxt in visited:
                    break
                visited.add(nxt)
                route.append(nxt)
                load += dem[nxt]
                cost += dist[cur][nxt]
                cur = nxt
            if route:
                cost += dist[cur][depot]
                self.used.append(v)
                self.served.update(route)
            self.routes[v] = route
            self.loads[v] = load
            self.costs[v] = cost
        self.dirty = set()

    def route_cost(self, route: list[int]) -> int:
        """Distance of depot->route[0]->...->route[-1]->depot."""
        depot, dist = self.depot, self.dist
        cost = 0
        cur = depot
        for c in route:
            cost += dist[cur][c]
            cur = c
        cost += dist[cur][depot]
        return cost

    def mark_dirty(self, v: int) -> None:
        self.dirty.add(v)

    def apply(self, arcs: list[int]) -> None:
        """Write cached routes back to `arcs` for dirty vehicles and recompute
        loads/costs.  Non-dirty vehicles are left untouched.  Clears dirty.
        """
        n, nq, depot = self.n, self.nq, self.depot
        for v in self.dirty:
            offset = v * nq
            # Zero all arcs for this vehicle.
            for idx in range(offset, offset + nq):
                arcs[idx] = 0
            route = self.routes[v]
            if not route:
                self.loads[v] = 0
                self.costs[v] = 0
                continue
            prev = depot
            for c in route:
                arcs[offset + prev * n + c] = 1
                prev = c
            arcs[offset + prev * n + depot] = 1
            self.loads[v] = sum(self.dem[c] for c in route)
            self.costs[v] = self.route_cost(route)
        # Rebuild served/used from scratch (cheap: O(nv + sum|route|)).
        served: set[int] = set()
        used: list[int] = []
        for v in range(self.nv):
            if self.routes[v]:
                served.update(self.routes[v])
                used.append(v)
        self.served = served
        self.used = used
        self.dirty = set()

    def apply_all(self, arcs: list[int]) -> None:
        """Force-write every vehicle (used after bulk mutation)."""
        self.dirty = set(range(self.nv))
        self.apply(arcs)

    def unserved(self) -> list[int]:
        """Customers not on any route (excluding depot)."""
        depot, n = self.depot, self.n
        return [c for c in range(n) if c != depot and c not in self.served]

    def total_cost(self) -> int:
        return sum(self.costs)


# --------------- Arc helpers (legacy, kept for backward compatibility) ---------------

def _route_of(arcs: list[int], v: int, n: int, depot: int, nq: int) -> list[int]:
    """Trace vehicle v route from depot, returning customer list."""
    route: list[int] = []
    cur = depot
    vis: set[int] = set()
    for _ in range(n):
        nxt = -1
        offset = v * nq
        for j in range(n):
            if arcs[offset + cur * n + j]:
                nxt = j
                break
        if nxt < 0 or nxt == depot or nxt in vis:
            break
        vis.add(nxt)
        route.append(nxt)
        cur = nxt
    return route


def _load_of(arcs: list[int], v: int, n: int, depot: int, nq: int,
             dem: list[int]) -> int:
    return sum(dem[c] for c in _route_of(arcs, v, n, depot, nq))


def _ins_cost(cust: int, before: int, after: int, dist: list[list[int]]) -> int:
    return dist[before][cust] + dist[cust][after] - dist[before][after]


def _all_served(arcs: list[int], n: int, nv: int, depot: int, nq: int) -> set[int]:
    """Customers with ANY incoming arc from non-depot node."""
    served: set[int] = set()
    for v in range(nv):
        offset = v * nq
        for i in range(n):
            for j in range(n):
                if arcs[offset + i * n + j] and i != depot and j != depot:
                    served.add(j)
        # Also mark customers directly reached from depot
        for j in range(n):
            if arcs[offset + depot * n + j] and j != depot:
                served.add(j)
    return served


def _used_vehicles(arcs: list[int], n: int, nv: int, depot: int, nq: int) -> list[int]:
    result: list[int] = []
    for v in range(nv):
        for j in range(n):
            if arcs[v * nq + depot * n + j] and j != depot:
                result.append(v)
                break
    return result


def _compute_u(arcs: list[int], n: int, nv: int, depot: int, nq: int,
               dem: list[int], cap: int) -> list[int]:
    """Compute MTZ u[] that satisfies u[j] >= u[i] + dem[j] for each arc i->j.

    Strategy: for each customer, take the max position across all vehicles.
    u[c] = max over routes containing c of (cumulative_demand_sum_up_to_c - dem[c]).
    This ensures u[j] >= u[i] + dem[j] when arc(i,j) exists.

    Actually simpler: u[depot]=0, and for route c1,c2,...,ck:
    u[c1]=dem[c1], u[c2]=dem[c1]+dem[c2], ..., u[ck]=dem[c1]+...+dem[ck]
    Then u[ci] - u[cj] = -(dem[ci+1]+...+dem[cj]) when i<j
    So u[ci] - u[cj] + cap*arc_ij = -(dem[ci+1]+...+dem[cj]) + cap
    This is <= cap - dem[cj] because -(dem[ci+1]+...+dem[cj]) <= -dem[cj].
    ✓ Satisfies the MTZ constraint.

    If a customer appears on multiple vehicles, take the max u.
    """
    u = [0] * n
    for v in range(nv):
        offset = v * nq
        cur = depot
        cumulative = 0
        for _ in range(n):
            nxt = -1
            for j in range(n):
                if arcs[offset + cur * n + j]:
                    nxt = j
                    break
            if nxt < 0 or nxt == depot:
                break
            cumulative += dem[nxt]
            u[nxt] = max(u[nxt], cumulative)
            cur = nxt
    return u


def _update_vu(arcs: list[int], n: int, nv: int, depot: int, nq: int, vu: list[int]) -> None:
    for v in range(nv):
        vu[v] = 1 if any(arcs[v * nq + depot * n + j] for j in range(n) if j != depot) else 0


def _insert_cust(arcs: list[int], v: int, before: int, after: int, cust: int, n: int, nq: int) -> None:
    """Insert cust between before and after on vehicle v.

    When before == after (empty vehicle), creates depot->cust and cust->depot.
    Otherwise, clears arcs[v,before,after] and sets arcs[v,before,cust], arcs[v,cust,after].
    """
    if before == after:
        arcs[v * nq + before * n + cust] = 1
        arcs[v * nq + cust * n + after] = 1
    else:
        arcs[v * nq + before * n + after] = 0
        arcs[v * nq + before * n + cust] = 1
        arcs[v * nq + cust * n + after] = 1


def _insertion_pairs(route: list[int], depot: int) -> list[tuple[int, int]]:
    """(before, after) pairs for inserting along a route."""
    if not route:
        return []
    pairs: list[tuple[int, int]] = [(depot, route[0])]
    for i in range(len(route) - 1):
        pairs.append((route[i], route[i + 1]))
    pairs.append((route[-1], depot))
    return pairs


def _find_best_insert(arcs: list[int], cust: int, n: int, nv: int, depot: int,
                      nq: int, cap: int, dem: list[int],
                      dist: list[list[int]]) -> tuple[float, float, int, int, int]:
    """Find cheapest and 2nd-cheapest arc insertion for cust.

    Returns (best_cost, second_cost, vehicle, before, after).
    For empty vehicles, considers cost = dist[depot][cust] + dist[cust][depot].

    Legacy signature retained for backward compatibility; delegates to the
    cache-based implementation.
    """
    p = {"depot": depot, "n": n, "nv": nv, "nq": nq, "cap": cap, "dem": dem, "dist": dist}
    cache = _RouteCache.from_arcs(arcs, p)
    return _find_best_insert_cache(cache, cust)


def _find_best_insert_cache(
    cache: _RouteCache, cust: int,
) -> tuple[float, float, int, int, int]:
    """Cheapest + 2nd-cheapest insertion for cust using a _RouteCache.

    Returns (best_cost, second_cost, vehicle, before, after).  When fewer than
    2 feasible insertions exist, the missing slots are +inf with vehicle -1.
    """
    depot, nv, cap, dem, dist = cache.depot, cache.nv, cache.cap, cache.dem, cache.dist
    d = dem[cust]
    best = second = float("inf")
    best_v = best_bi = best_af = -1
    for v in range(nv):
        route = cache.routes[v]
        if cache.loads[v] + d > cap:
            continue
        if not route:
            cost = dist[depot][cust] + dist[cust][depot]
            if cost < best:
                second = best
                best = cost
                best_v, best_bi, best_af = v, depot, depot
            elif cost < second:
                second = cost
        else:
            for (bi, af) in _insertion_pairs(route, depot):
                cost = dist[bi][cust] + dist[cust][af] - dist[bi][af]
                if cost < best:
                    second = best
                    best = cost
                    best_v, best_bi, best_af = v, bi, af
                elif cost < second:
                    second = cost
    return best, second, best_v, best_bi, best_af


def _find_k_best_insert(
    cache: _RouteCache, cust: int, k: int,
) -> list[tuple[float, int, int, int]]:
    """Return the k cheapest feasible insertions for cust as
    [(cost, vehicle, before, after), ...] sorted ascending.  Fewer than k if
    not enough feasible positions exist.  Used by regret-k repair.
    """
    depot, nv, cap, dem, dist = cache.depot, cache.nv, cache.cap, cache.dem, cache.dist
    d = dem[cust]
    candidates: list[tuple[float, int, int, int]] = []
    for v in range(nv):
        route = cache.routes[v]
        if cache.loads[v] + d > cap:
            continue
        if not route:
            candidates.append((dist[depot][cust] + dist[cust][depot], v, depot, depot))
        else:
            for (bi, af) in _insertion_pairs(route, depot):
                candidates.append((dist[bi][cust] + dist[cust][af] - dist[bi][af], v, bi, af))
    candidates.sort(key=lambda x: x[0])
    return candidates[:k]


def _force_insert_fallback(cache: _RouteCache, cust: int) -> bool:
    """Capacity-aware last-resort insertion.

    Tries the least-loaded vehicle with room for `cust`; only falls back to
    forcing onto vehicle 0 (ignoring capacity) if NO vehicle has room.  Marks
    the chosen vehicle dirty.  Returns True if inserted (always True).
    """
    d = cache.dem[cust]
    # Prefer the least-loaded vehicle that still has capacity.
    candidates = [v for v in range(cache.nv) if cache.loads[v] + d <= cache.cap]
    if candidates:
        v = min(candidates, key=lambda x: cache.loads[x])
    else:
        # Truly no room anywhere -- force onto the least-loaded vehicle to
        # minimise the capacity violation (better than always vehicle 0).
        v = min(range(cache.nv), key=lambda x: cache.loads[x])
    route = cache.routes[v]
    if route:
        _insert_cust_cache(cache, v, route[-1], cache.depot, cust)
    else:
        _insert_cust_cache(cache, v, cache.depot, cache.depot, cust)
    return True


def _insert_cust_cache(
    cache: _RouteCache, v: int, before: int, after: int, cust: int,
) -> None:
    """Insert cust between before and after on vehicle v, updating the cache.

    When before == after (empty vehicle), creates depot->cust->depot.
    Mutates cache.routes[v], cache.loads[v], cache.costs[v] and marks v dirty.
    """
    route = cache.routes[v]
    d = cache.dem[cust]
    if not route:
        # Empty route: depot -> cust -> depot.
        cache.routes[v] = [cust]
    else:
        bi_idx = route.index(before) if before != cache.depot else -1
        if before == cache.depot:
            # Insert at head: cust becomes new first customer.
            cache.routes[v] = [cust] + route
        elif after == cache.depot:
            # Insert at tail.
            cache.routes[v] = route + [cust]
        else:
            # Insert between before and after.
            bi_idx = route.index(before)
            cache.routes[v] = route[:bi_idx + 1] + [cust] + route[bi_idx + 1:]
    cache.loads[v] += d
    cache.costs[v] = cache.route_cost(cache.routes[v])
    cache.served.add(cust)
    if v not in cache.used:
        cache.used.append(v)
    cache.mark_dirty(v)


def _remove_cust_cache(cache: _RouteCache, v: int, cust: int) -> None:
    """Remove cust from vehicle v's route, patching the link, updating cache."""
    route = cache.routes[v]
    if cust not in route:
        return
    idx = route.index(cust)
    cache.routes[v] = route[:idx] + route[idx + 1:]
    cache.loads[v] -= cache.dem[cust]
    cache.costs[v] = cache.route_cost(cache.routes[v])
    cache.mark_dirty(v)
    # served set is rebuilt on apply(); leave stale entries here, they are
    # only read via cache.served which apply() refreshes.


def _rcost(arcs: list[int], v: int, n: int, depot: int, nq: int,
           dist: list[list[int]]) -> int:
    route = _route_of(arcs, v, n, depot, nq)
    cost = 0
    cur = depot
    for c in route:
        cost += dist[cur][c]
        cur = c
    return cost


# ------------------------------------------------------------------
# Destroy operators
# ------------------------------------------------------------------

@dataclass
class CVRPRouteBreakDestroy(DestroyOperator):
    """Remove vehicle routes by zeroing all their arcs."""
    route_count: int = 1
    strategy: str = "random"

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        arcs = assignment.get("arcs")
        if not isinstance(arcs, list):
            return assignment

        nq = p["nq"]
        cache = _RouteCache.from_arcs(arcs, p)
        used = cache.used
        if not used:
            return assignment

        k = min(self.route_count, len(used))
        if self.strategy == "worst":
            used.sort(key=lambda v: cache.costs[v], reverse=True)
            sel = used[:k]
        elif self.strategy == "largest":
            used.sort(key=lambda v: len(cache.routes[v]), reverse=True)
            sel = used[:k]
        else:
            sel = rng.sample(used, k)

        new_arcs = list(arcs)
        for v in sel:
            offset = v * nq
            for idx in range(nq):
                new_arcs[offset + idx] = 0

        assignment = dict(assignment)
        assignment["arcs"] = new_arcs
        vu = assignment.get("vehicle_used")
        if isinstance(vu, list):
            for v in sel:
                vu[v] = 0
        return assignment


@dataclass
class CVRPWCUSTOMERDestroy(DestroyOperator):
    """Remove customers by patching pred->succ arcs (reverse-order processing)."""
    customer_count: int = 0
    fraction: float = 0.2
    strategy: str = "worst"

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        arcs = assignment.get("arcs")
        if not isinstance(arcs, list):
            return assignment

        nv, n, depot, nq, dist = p["nv"], p["n"], p["depot"], p["nq"], p["dist"]
        cache = _RouteCache.from_arcs(arcs, p)
        served = set(cache.served)
        if not served:
            return assignment

        all_cust = sorted(served)
        k = self.customer_count if self.customer_count > 0 else max(1, int(len(all_cust) * self.fraction))
        k = min(k, len(all_cust))

        if self.strategy == "worst":
            savings: list[tuple[float, int]] = []
            for c in all_cust:
                for v in range(nv):
                    route = cache.routes[v]
                    for ii in range(len(route)):
                        if route[ii] == c:
                            pred = route[ii - 1] if ii > 0 else depot
                            nxt = route[ii + 1] if ii < len(route) - 1 else depot
                            ic = _ins_cost(c, pred, nxt, dist)
                            savings.append((-ic, c))
                            break
                    if savings and savings[-1][1] == c:
                        break
            savings.sort(key=lambda x: x[0], reverse=True)
            chosen = set(c for _, c in savings[:k])
        else:
            chosen = set(rng.sample(all_cust, k))

        new_arcs = list(arcs)
        for v in range(nv):
            route = cache.routes[v]
            chosen_in_route = [(i, c) for i, c in enumerate(route) if c in chosen]
            for i, c in reversed(chosen_in_route):
                pred = route[i - 1] if i > 0 else depot
                nxt = route[i + 1] if i < len(route) - 1 else depot
                new_arcs[v * nq + pred * n + c] = 0
                new_arcs[v * nq + c * n + nxt] = 0
                if pred != nxt:
                    new_arcs[v * nq + pred * n + nxt] = 1

        assignment = dict(assignment)
        assignment["arcs"] = new_arcs
        vu = assignment.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return assignment


@dataclass
class CVRPShawDestroy(DestroyOperator):
    """Shaw / related-removal destroy (Ropke & Pisinger 2006).

    Picks a seed customer, then iteratively removes the customer most *related*
    to one already in the removal set.  Relatedness metric:

        R(i, j) = d[i,j] / max_d  +  λ · |dem[i] - dem[j]| / max_dem

    Lower R = more related = more likely to be removed together.  This groups
    geographically close and demand-similar customers, making the repair
    problem harder (and thus the search more diverse) than random removal.
    """
    customer_count: int = 0
    fraction: float = 0.2
    seed_strategy: str = "random"       # "random" or "worst"
    lambda_demand: float = 0.5
    phi: float = 0.5                    # randomisation exponent (1=greedy, <1=noisy)

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        arcs = assignment.get("arcs")
        if not isinstance(arcs, list):
            return assignment

        n, nv, depot, nq, dist, dem = p["n"], p["nv"], p["depot"], p["nq"], p["dist"], p["dem"]
        cache = _RouteCache.from_arcs(arcs, p)
        served = sorted(cache.served)
        if not served:
            return assignment

        k = self.customer_count if self.customer_count > 0 else max(1, int(len(served) * self.fraction))
        k = min(k, len(served))

        # Precompute normalisation constants.
        max_d = max(max(row) for row in dist)
        max_dem = max(dem)
        if max_d == 0:
            max_d = 1
        if max_dem == 0:
            max_dem = 1

        # Choose seed.
        if self.seed_strategy == "worst":
            worst_cost = -1.0
            seed = served[0]
            for c in served:
                for v in range(nv):
                    route = cache.routes[v]
                    if c in route:
                        idx = route.index(c)
                        pred = route[idx - 1] if idx > 0 else depot
                        nxt = route[idx + 1] if idx + 1 < len(route) else depot
                        ic = _ins_cost(c, pred, nxt, dist)
                        if ic > worst_cost:
                            worst_cost = ic
                            seed = c
                        break
        else:
            seed = rng.choice(served)

        removed: set[int] = {seed}
        # Map customer -> vehicle for quick lookup.
        cust_vehicle: dict[int, int] = {}
        for v in range(nv):
            for c in cache.routes[v]:
                cust_vehicle[c] = v

        while len(removed) < k:
            # Pick a reference from the removed set (random).
            ref = rng.choice(list(removed))
            # Score all remaining served customers by relatedness to ref.
            candidates: list[tuple[float, int]] = []
            for c in served:
                if c in removed:
                    continue
                relatedness = (
                    dist[ref][c] / max_d
                    + self.lambda_demand * abs(dem[ref] - dem[c]) / max_dem
                )
                # Add noise: divide by U(0,1)^phi so low relatedness (high score)
                # can still be picked with some probability.
                noise = rng.random() ** self.phi
                if noise <= 0:
                    noise = 1e-9
                candidates.append((relatedness / noise, c))
            if not candidates:
                break
            candidates.sort(key=lambda x: x[0])
            removed.add(candidates[0][1])

        # Patch arcs: remove chosen customers.
        new_arcs = list(arcs)
        for v in range(nv):
            route = cache.routes[v]
            chosen_in_route = [(i, c) for i, c in enumerate(route) if c in removed]
            for i, c in reversed(chosen_in_route):
                pred = route[i - 1] if i > 0 else depot
                nxt = route[i + 1] if i + 1 < len(route) else depot
                new_arcs[v * nq + pred * n + c] = 0
                new_arcs[v * nq + c * n + nxt] = 0
                if pred != nxt:
                    new_arcs[v * nq + pred * n + nxt] = 1

        assignment = dict(assignment)
        assignment["arcs"] = new_arcs
        vu = assignment.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return assignment


@dataclass
class CVRPClusterDestroy(DestroyOperator):
    """Sweep / angle-based cluster removal.

    Computes a pseudo-angle for each customer from the distance matrix (using
    the first non-depot customer as a reference axis), then removes all
    customers whose angle falls within a random window of width ``angle_span``.
    Falls back to Shaw removal if angles cannot be derived (fewer than 2
    customers).
    """
    customer_count: int = 0
    fraction: float = 0.2
    angle_span: float = 1.2          # radians (~69°)

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        arcs = assignment.get("arcs")
        if not isinstance(arcs, list):
            return assignment

        n, nv, depot, nq, dist = p["n"], p["nv"], p["depot"], p["nq"], p["dist"]
        cache = _RouteCache.from_arcs(arcs, p)
        served = sorted(cache.served)
        if len(served) < 2:
            return assignment

        # Derive pseudo-angles from the distance matrix using the law of
        # cosines with depot as the vertex and the first served customer as
        # the reference direction.
        ref = served[0]
        d_depot_ref = dist[depot][ref]
        angles: dict[int, float] = {}
        for c in served:
            d_depot_c = dist[depot][c]
            d_ref_c = dist[ref][c]
            if d_depot_ref == 0 or d_depot_c == 0:
                angles[c] = 0.0
                continue
            cos_a = (d_depot_ref ** 2 + d_depot_c ** 2 - d_ref_c ** 2) / (2 * d_depot_ref * d_depot_c)
            cos_a = max(-1.0, min(1.0, cos_a))
            angle = math.acos(cos_a)
            # Use a cross-product sign to get full [0, 2π) range.
            # Without coordinates we approximate the sign from a third point.
            angles[c] = angle  # [0, π] is enough for sweep clustering

        # Pick a random centre angle and remove customers within ±span/2.
        centre = rng.uniform(0, math.pi)
        half = self.angle_span / 2
        chosen = {c for c, a in angles.items() if abs(a - centre) <= half or abs(a - centre + math.pi) <= half}

        # Ensure at least one removal; if window is empty, take nearest to centre.
        if not chosen:
            nearest = min(served, key=lambda c: abs(angles[c] - centre))
            chosen = {nearest}

        # Respect customer_count / fraction cap.
        k = self.customer_count if self.customer_count > 0 else max(1, int(len(served) * self.fraction))
        if len(chosen) > k:
            chosen = set(rng.sample(list(chosen), k))

        # Patch arcs.
        new_arcs = list(arcs)
        for v in range(nv):
            route = cache.routes[v]
            chosen_in_route = [(i, c) for i, c in enumerate(route) if c in chosen]
            for i, c in reversed(chosen_in_route):
                pred = route[i - 1] if i > 0 else depot
                nxt = route[i + 1] if i + 1 < len(route) else depot
                new_arcs[v * nq + pred * n + c] = 0
                new_arcs[v * nq + c * n + nxt] = 0
                if pred != nxt:
                    new_arcs[v * nq + pred * n + nxt] = 1

        assignment = dict(assignment)
        assignment["arcs"] = new_arcs
        vu = assignment.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return assignment


@dataclass
class CVRPSegmentDestroy(DestroyOperator):
    """Remove a contiguous chain of customers from a single route.

    Picks a used vehicle at random, chooses a random start position, and
    removes ``segment_len`` consecutive customers.  This creates an OR-Opt-
    style relocation opportunity for the repair operator.
    """
    segment_len: int = 5
    fraction: float = 0.0       # if >0, segment_len = max(1, int(fraction * route_len))

    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return assignment
        rng: random.Random = context.extra["rng"]
        arcs = assignment.get("arcs")
        if not isinstance(arcs, list):
            return assignment

        n, nv, depot, nq = p["n"], p["nv"], p["depot"], p["nq"]
        cache = _RouteCache.from_arcs(arcs, p)
        used = cache.used
        if not used:
            return assignment

        v = rng.choice(used)
        route = cache.routes[v]
        if not route:
            return assignment

        seg_len = self.segment_len
        if self.fraction > 0:
            seg_len = max(1, int(self.fraction * len(route)))
        seg_len = min(seg_len, len(route))

        start = rng.randint(0, len(route) - seg_len)
        chosen = set(route[start:start + seg_len])

        # Patch arcs for this vehicle only.
        new_arcs = list(arcs)
        chosen_in_route = [(i, c) for i, c in enumerate(route) if c in chosen]
        for i, c in reversed(chosen_in_route):
            pred = route[i - 1] if i > 0 else depot
            nxt = route[i + 1] if i + 1 < len(route) else depot
            new_arcs[v * nq + pred * n + c] = 0
            new_arcs[v * nq + c * n + nxt] = 0
            if pred != nxt:
                new_arcs[v * nq + pred * n + nxt] = 1

        assignment = dict(assignment)
        assignment["arcs"] = new_arcs
        vu = assignment.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return assignment


# ------------------------------------------------------------------
# Repair operators
# ------------------------------------------------------------------

@dataclass
class CVRPInsertionRepair(RepairOperator):
    """Re-insert orphaned customers at cheapest arc position."""
    strategy: str = "cheapest"

    def repair(self, partial: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return partial
        rng: random.Random = context.extra["rng"]
        depot, n, nv, cap, dem, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["nq"]

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)
        cache = _RouteCache.from_arcs(new_arcs, p)
        unserved = cache.unserved()
        rng.shuffle(unserved)

        for c in unserved:
            _, _, bv, bi, ba = _find_best_insert_cache(cache, c)
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)

        cache.apply(new_arcs)
        partial = dict(partial)
        partial["arcs"] = new_arcs
        partial["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)
        vu = partial.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return partial


@dataclass
class CVRPRegretInsertionRepair(RepairOperator):
    """Re-insert orphaned customers using regret-k strategy.

    regret_k controls how many best insertions are compared.  regret-2 (the
    classic Ropke & Pisinger formulation) is the default; regret-3 considers
    the 3rd-best position as well, which tends to produce better assignments
    on tight-capacity instances.
    """
    regret_k: int = 3

    def repair(self, partial: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return partial
        depot, n, nv, cap, dem, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["nq"]
        k = max(2, self.regret_k)

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)
        cache = _RouteCache.from_arcs(new_arcs, p)

        while True:
            unserved = cache.unserved()
            if not unserved:
                break

            regrets: list[tuple[float, int, int, int, int]] = []
            for c in unserved:
                kbest = _find_k_best_insert(cache, c, k)
                if not kbest:
                    continue
                best_cost = kbest[0][0]
                # Regret = sum of (cost_i - best) for i=2..k, with missing
                # positions penalised by a large constant.
                reg = 0.0
                for idx in range(1, k):
                    if idx < len(kbest):
                        reg += kbest[idx][0] - best_cost
                    else:
                        reg += best_cost + 1e9
                bv, bi, ba = kbest[0][1], kbest[0][2], kbest[0][3]
                regrets.append((reg, c, bv, bi, ba))

            if not regrets:
                # No feasible insertion for any remaining customer -- force.
                for c in unserved:
                    _force_insert_fallback(cache, c)
                break

            regrets.sort(key=lambda x: x[0], reverse=True)
            _, c, bv, bi, ba = regrets[0]
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)

        cache.apply(new_arcs)
        partial = dict(partial)
        partial["arcs"] = new_arcs
        partial["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)
        vu = partial.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return partial


@dataclass
class CVRPOROptRepair(RepairOperator):
    """Cheapest insertion + OR-Opt chain moves on arcs."""
    or_opt_max: int = 2
    passes: int = 5

    def repair(self, partial: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return partial
        depot, n, nv, cap, dem, dist, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["dist"], p["nq"]

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)
        cache = _RouteCache.from_arcs(new_arcs, p)

        # Phase 1: cheapest insertion of unserved customers
        unserved = cache.unserved()
        for c in unserved:
            _, _, bv, bi, ba = _find_best_insert_cache(cache, c)
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)

        # Phase 2: OR-Opt improvement (chain relocation between routes)
        for _ in range(self.passes):
            improved = False
            for vf in range(nv):
                brk = False
                for cl in range(1, self.or_opt_max + 1):
                    for pf in range(n):
                        if brk:
                            break
                        chain = cache.routes[vf]
                        if pf + cl > len(chain):
                            break
                        chain_items = chain[pf:pf + cl]
                        cdem = sum(dem[x] for x in chain_items)

                        pred = depot if pf == 0 else chain[pf - 1]
                        nxt = depot if pf + cl == len(chain) else chain[pf + cl]

                        save = dist[pred][chain_items[0]] + dist[chain_items[-1]][nxt] - dist[pred][nxt]
                        if save <= 0:
                            continue

                        for vt in range(nv):
                            if vt == vf or cache.loads[vt] + cdem > cap:
                                continue
                            to_route = cache.routes[vt]
                            for (tb, ta) in _insertion_pairs(to_route, depot):
                                ic = dist[tb][chain_items[0]] + dist[chain_items[-1]][ta] - dist[tb][ta]
                                if save > ic:
                                    # Remove chain from source route
                                    src = cache.routes[vf]
                                    cache.routes[vf] = src[:pf] + src[pf + cl:]
                                    cache.loads[vf] -= cdem
                                    cache.costs[vf] = cache.route_cost(cache.routes[vf])
                                    cache.mark_dirty(vf)

                                    # Insert chain into target route
                                    tgt = cache.routes[vt]
                                    if tb == depot:
                                        cache.routes[vt] = chain_items + tgt
                                    elif ta == depot:
                                        cache.routes[vt] = tgt + chain_items
                                    else:
                                        ti = tgt.index(tb)
                                        cache.routes[vt] = tgt[:ti + 1] + chain_items + tgt[ti + 1:]
                                    cache.loads[vt] += cdem
                                    cache.costs[vt] = cache.route_cost(cache.routes[vt])
                                    cache.mark_dirty(vt)

                                    improved = True
                                    brk = True
                                    break
                            if brk:
                                break

                if brk:
                    break
            if not improved:
                break

        cache.apply(new_arcs)
        partial = dict(partial)
        partial["arcs"] = new_arcs
        partial["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)
        vu = partial.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return partial


def _intra_route_2opt(cache: _RouteCache, v: int) -> bool:
    """Intra-route 2-opt on vehicle v's route.  Returns True if improved.

    Reverses segments [i+1..j] when doing so reduces the route distance.
    Operates on the cache route list directly and marks v dirty.
    """
    depot, dist = cache.depot, cache.dist
    route = cache.routes[v]
    n = len(route)
    if n < 2:
        return False
    improved = False
    changed = True
    while changed:
        changed = False
        for i in range(n - 1):
            for j in range(i + 1, n):
                # Edges before reversal: (prev_i -> route[i]) and (route[j] -> next_j)
                prev_i = route[i - 1] if i > 0 else depot
                next_j = route[j + 1] if j + 1 < n else depot
                before = dist[prev_i][route[i]] + dist[route[j]][next_j]
                after = dist[prev_i][route[j]] + dist[route[i]][next_j]
                if after < before:
                    route[i:j + 1] = route[i:j + 1][::-1]
                    changed = True
                    improved = True
                    break
            if changed:
                break
    if improved:
        cache.costs[v] = cache.route_cost(route)
        cache.mark_dirty(v)
    return improved


def _inter_route_2opt_star(cache: _RouteCache) -> bool:
    """Inter-route 2-opt*: swap the tails of two routes.

    For routes v1=[...a] and v2=[...b], try reconnecting as
    v1=[...a] + tail(b...) and v2=[...b] + tail(a...) when capacity allows
    and the total distance decreases.  Returns True if any improvement made.
    """
    depot, dist, dem, cap, nv = cache.depot, cache.dist, cache.dem, cache.cap, cache.nv
    improved = False
    changed = True
    while changed:
        changed = False
        for v1 in range(nv):
            r1 = cache.routes[v1]
            if not r1:
                continue
            for v2 in range(v1 + 1, nv):
                r2 = cache.routes[v2]
                if not r2:
                    continue
                # Try every split point: r1[:i+1] + r2[j+1:] and r2[:j+1] + r1[i+1:]
                for i in range(len(r1)):
                    for j in range(len(r2)):
                        # New loads.
                        new_load1 = sum(dem[c] for c in r1[:i + 1]) + sum(dem[c] for c in r2[j + 1:])
                        new_load2 = sum(dem[c] for c in r2[:j + 1]) + sum(dem[c] for c in r1[i + 1:])
                        if new_load1 > cap or new_load2 > cap:
                            continue
                        # Cost delta.
                        a = r1[i]
                        b = r2[j]
                        next_a = r1[i + 1] if i + 1 < len(r1) else depot
                        next_b = r2[j + 1] if j + 1 < len(r2) else depot
                        before = dist[a][next_a] + dist[b][next_b]
                        after = dist[a][next_b] + dist[b][next_a]
                        if after >= before:
                            continue
                        # Apply swap.
                        tail1 = r1[i + 1:]
                        tail2 = r2[j + 1:]
                        cache.routes[v1] = r1[:i + 1] + tail2
                        cache.routes[v2] = r2[:j + 1] + tail1
                        cache.loads[v1] = sum(dem[c] for c in cache.routes[v1])
                        cache.loads[v2] = sum(dem[c] for c in cache.routes[v2])
                        cache.costs[v1] = cache.route_cost(cache.routes[v1])
                        cache.costs[v2] = cache.route_cost(cache.routes[v2])
                        cache.mark_dirty(v1)
                        cache.mark_dirty(v2)
                        improved = True
                        changed = True
                        break
                    if changed:
                        break
                if changed:
                    break
            if changed:
                break
    return improved


def _inter_route_swap(cache: _RouteCache) -> bool:
    """Swap one customer between each pair of routes when it reduces total
    distance and respects capacity.  Returns True if any improvement made.
    """
    depot, dist, dem, cap, nv = cache.depot, cache.dist, cache.dem, cache.cap, cache.nv
    improved = False
    changed = True
    while changed:
        changed = False
        for v1 in range(nv):
            r1 = cache.routes[v1]
            if not r1:
                continue
            for v2 in range(v1 + 1, nv):
                r2 = cache.routes[v2]
                if not r2:
                    continue
                for i in range(len(r1)):
                    c1 = r1[i]
                    for j in range(len(r2)):
                        c2 = r2[j]
                        # Capacity check after swap.
                        new_load1 = cache.loads[v1] - dem[c1] + dem[c2]
                        new_load2 = cache.loads[v2] - dem[c2] + dem[c1]
                        if new_load1 > cap or new_load2 > cap:
                            continue
                        # Cost delta for route 1.
                        pred1 = r1[i - 1] if i > 0 else depot
                        next1 = r1[i + 1] if i + 1 < len(r1) else depot
                        before1 = dist[pred1][c1] + dist[c1][next1]
                        after1 = dist[pred1][c2] + dist[c2][next1]
                        # Cost delta for route 2.
                        pred2 = r2[j - 1] if j > 0 else depot
                        next2 = r2[j + 1] if j + 1 < len(r2) else depot
                        before2 = dist[pred2][c2] + dist[c2][next2]
                        after2 = dist[pred2][c1] + dist[c1][next2]
                        if after1 + after2 >= before1 + before2:
                            continue
                        # Apply swap.
                        cache.routes[v1][i] = c2
                        cache.routes[v2][j] = c1
                        cache.loads[v1] = new_load1
                        cache.loads[v2] = new_load2
                        cache.costs[v1] = cache.route_cost(cache.routes[v1])
                        cache.costs[v2] = cache.route_cost(cache.routes[v2])
                        cache.mark_dirty(v1)
                        cache.mark_dirty(v2)
                        improved = True
                        changed = True
                        break
                    if changed:
                        break
                if changed:
                    break
            if changed:
                break
    return improved


@dataclass
class CVRPTwoOptRepair(RepairOperator):
    """Cheapest-insertion repair followed by intra-route 2-opt local search.

    Re-inserts all unserved customers at their cheapest feasible position
    (reusing the Phase-A cache helpers), then runs 2-opt on every route until
    no improving reversal exists.  Only routes in the cache's dirty set (those
    touched by insertion) are local-searched when ``only_dirty=True``.
    """
    passes: int = 3
    only_dirty: bool = False

    def repair(self, partial: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return partial
        rng: random.Random = context.extra["rng"]
        depot, n, nv, cap, dem, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["nq"]

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)
        cache = _RouteCache.from_arcs(new_arcs, p)

        # Phase 1: cheapest insertion of unserved customers.
        unserved = cache.unserved()
        rng.shuffle(unserved)
        for c in unserved:
            _, _, bv, bi, ba = _find_best_insert_cache(cache, c)
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)

        # Phase 2: intra-route 2-opt.
        targets = cache.dirty if self.only_dirty else range(nv)
        for _ in range(self.passes):
            any_improved = False
            for v in targets:
                if _intra_route_2opt(cache, v):
                    any_improved = True
            if not any_improved:
                break

        cache.apply(new_arcs)
        partial = dict(partial)
        partial["arcs"] = new_arcs
        partial["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)
        vu = partial.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return partial


@dataclass
class CVRPInterRouteRepair(RepairOperator):
    """Cheapest-insertion repair + inter-route 2-opt* and swap local search.

    The most powerful repair: after re-inserting unserved customers, it
    rebalances routes via inter-route 2-opt* (tail swaps) and single-customer
    swaps until no improving move exists.  All moves are capacity-checked.
    """
    passes: int = 3

    def repair(self, partial: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return partial
        rng: random.Random = context.extra["rng"]
        depot, n, nv, cap, dem, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["nq"]

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)
        cache = _RouteCache.from_arcs(new_arcs, p)

        # Phase 1: cheapest insertion of unserved customers.
        unserved = cache.unserved()
        rng.shuffle(unserved)
        for c in unserved:
            _, _, bv, bi, ba = _find_best_insert_cache(cache, c)
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)

        # Phase 2: intra-route 2-opt on all routes (cheap, do first).
        for v in range(nv):
            _intra_route_2opt(cache, v)

        # Phase 3: inter-route 2-opt* + swap, alternating until stable.
        for _ in range(self.passes):
            improved = _inter_route_2opt_star(cache)
            improved = _inter_route_swap(cache) or improved
            if not improved:
                break

        cache.apply(new_arcs)
        partial = dict(partial)
        partial["arcs"] = new_arcs
        partial["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)
        vu = partial.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return partial


# ------------------------------------------------------------------
# Generic mutation: destroy some customers + repair (re-insert)
# Used as a proposal operator for MCMC / MGA initialisation.
# ------------------------------------------------------------------

def _cvrp_arc_mutation(
    assignment: dict[str, object],
    context: LNSContext,
    rng: random.Random,
    customer_count: int = 3,
    *,
    remove_strategy: str = "random",
    insert_strategy: str = "cheapest",
) -> dict[str, object]:
    """Remove *customer_count* customers from routes then re-insert them.

    This is a route-structure-preserving move: destroy (remove customers by
    patching predecessor→successor links) + repair (cheapest or regret
    re-insertion).  Returns a new assignment dict; the original is untouched.
    """
    p = _cvrp(context)
    if p is None:
        return dict(assignment)

    depot, n, nv, cap, dem, dist, nq = (
        p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["dist"], p["nq"],
    )

    arcs_data = assignment.get("arcs")
    if not isinstance(arcs_data, list):
        return dict(assignment)

    new_arcs = list(arcs_data)
    cache = _RouteCache.from_arcs(new_arcs, p)

    # --- Destroy phase: remove customers ---
    served = set(cache.served)
    if not served:
        # No customers served; need to insert random ones
        all_cust = [c for c in range(n) if c != depot]
        chosen = rng.sample(all_cust, min(customer_count, len(all_cust)))
        for c in chosen:
            _, _, bv, bi, ba = _find_best_insert_cache(cache, c)
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)
    else:
        all_cust = sorted(served)
        k = min(customer_count, len(all_cust))

        if remove_strategy == "worst":
            savings: list[tuple[float, int]] = []
            for c in all_cust:
                for v in range(nv):
                    route = cache.routes[v]
                    for ii in range(len(route)):
                        if route[ii] == c:
                            pred = route[ii - 1] if ii > 0 else depot
                            nxt = route[ii + 1] if ii < len(route) - 1 else depot
                            ic = _ins_cost(c, pred, nxt, dist)
                            savings.append((-ic, c))
                            break
                    if savings and savings[-1][1] == c:
                        break
            savings.sort(key=lambda x: x[0], reverse=True)
            chosen = set(c for _, c in savings[:k])
        else:
            chosen = set(rng.sample(all_cust, k))

        # Remove chosen customers via cache
        for v in range(nv):
            for c in list(chosen):
                if c in cache.routes[v]:
                    _remove_cust_cache(cache, v, c)

    # --- Repair phase: re-insert removed + any still-unserved ---
    unserved = cache.unserved()
    rng.shuffle(unserved)

    if insert_strategy == "regret":
        # Regret-k insertion
        while unserved:
            regrets: list[tuple[float, int, int, int, int]] = []
            for c in unserved:
                kbest = _find_k_best_insert(cache, c, 3)
                if not kbest:
                    continue
                best_cost = kbest[0][0]
                reg = 0.0
                for idx in range(1, 3):
                    if idx < len(kbest):
                        reg += kbest[idx][0] - best_cost
                    else:
                        reg += best_cost + 1e9
                bv, bi, ba = kbest[0][1], kbest[0][2], kbest[0][3]
                regrets.append((reg, c, bv, bi, ba))
            if not regrets:
                for c in unserved:
                    _force_insert_fallback(cache, c)
                break

            regrets.sort(key=lambda x: x[0], reverse=True)
            _, c, bv, bi, ba = regrets[0]
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)
            unserved = [x for x in unserved if x != c]
    else:
        # Cheapest insertion
        for c in unserved:
            _, _, bv, bi, ba = _find_best_insert_cache(cache, c)
            if bv >= 0 and bi >= 0:
                _insert_cust_cache(cache, bv, bi, ba, c)
            else:
                _force_insert_fallback(cache, c)

    # Build result
    cache.apply(new_arcs)
    result = dict(assignment)
    result["arcs"] = new_arcs
    result["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)

    vu = result.get("vehicle_used")
    if isinstance(vu, list):
        _update_vu(new_arcs, n, nv, depot, nq, vu)

    return result

