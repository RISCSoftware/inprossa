"""CVRP-specific LNS operators that work directly on arc variables.

Operates on the flat binary arc variables, vehicle_used, and u without
a decode/encode cycle.  Arc index: arcs[v*N^2 + i*N + j].

Destroy: zeroes arcs of selected vehicles or removes customers by
patching predecessor->successor links.

Repair: finds feasible insertion positions in the arc representation
and sets the appropriate incoming/outgoing arcs.
"""

from __future__ import annotations

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


# --------------- Arc helpers ---------------

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
    """
    d = dem[cust]
    best = float("inf")
    second = float("inf")
    best_v = best_bi = best_af = -1

    for v in range(nv):
        route = _route_of(arcs, v, n, depot, nq)
        load = sum(dem[c] for c in route)
        if load + d > cap:
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
                cost = _ins_cost(cust, bi, af, dist)
                if cost < best:
                    second = best
                    best = cost
                    best_v, best_bi, best_af = v, bi, af
                elif cost < second:
                    second = cost

    return best, second, best_v, best_bi, best_af


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

        nv, n, nq, dist, depot = p["nv"], p["n"], p["nq"], p["dist"], p["depot"]
        used = _used_vehicles(arcs, n, nv, depot, nq)
        if not used:
            return assignment

        k = min(self.route_count, len(used))
        if self.strategy == "worst":
            used.sort(key=lambda v: _rcost(arcs, v, n, depot, nq, dist), reverse=True)
            sel = used[:k]
        elif self.strategy == "largest":
            used.sort(key=lambda v: len(_route_of(arcs, v, n, depot, nq)), reverse=True)
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
        served = _all_served(arcs, n, nv, depot, nq)
        if not served:
            return assignment

        all_cust = sorted(served)
        k = self.customer_count if self.customer_count > 0 else max(1, int(len(all_cust) * self.fraction))
        k = min(k, len(all_cust))

        if self.strategy == "worst":
            savings: list[tuple[float, int]] = []
            for c in all_cust:
                for v in range(nv):
                    route = _route_of(arcs, v, n, depot, nq)
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
            route = _route_of(new_arcs, v, n, depot, nq)
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
        depot, n, nv, cap, dem, dist, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["dist"], p["nq"]

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)
        served = _all_served(new_arcs, n, nv, depot, nq)
        unserved = [c for c in range(n) if c != depot and c not in served]
        rng.shuffle(unserved)

        for c in unserved:
            best, second, bv, bi, ba = _find_best_insert(
                new_arcs, c, n, nv, depot, nq, cap, dem, dist)

            if bv >= 0 and bi >= 0:
                _insert_cust(new_arcs, bv, bi, ba, c, n, nq)
            else:
                # Fallback: append to end of existing route on first vehicle with capacity
                placed = False
                for v in range(nv):
                    if _load_of(new_arcs, v, n, depot, nq, dem) + dem[c] <= cap:
                        route = _route_of(new_arcs, v, n, depot, nq)
                        if route:
                            _insert_cust(new_arcs, v, route[-1], depot, c, n, nq)
                        else:
                            _insert_cust(new_arcs, v, depot, depot, c, n, nq)
                        placed = True
                        break
                if not placed:
                    # Force: append to vehicle 0
                    route = _route_of(new_arcs, 0, n, depot, nq)
                    if route:
                        _insert_cust(new_arcs, 0, route[-1], depot, c, n, nq)
                    else:
                        _insert_cust(new_arcs, 0, depot, depot, c, n, nq)

        partial = dict(partial)
        partial["arcs"] = new_arcs
        partial["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)
        vu = partial.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return partial


@dataclass
class CVRPRegretInsertionRepair(RepairOperator):
    """Re-insert orphaned customers using regret-2 strategy."""

    def repair(self, partial: dict[str, object], context: LNSContext) -> dict[str, object]:
        p = _cvrp(context)
        if p is None:
            return partial
        depot, n, nv, cap, dem, dist, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["dist"], p["nq"]

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)

        while True:
            served = _all_served(new_arcs, n, nv, depot, nq)
            unserved = [c for c in range(n) if c != depot and c not in served]
            if not unserved:
                break

            regrets: list[tuple[float, int, int, int, int]] = []
            for c in unserved:
                best, second, bv, bi, ba = _find_best_insert(
                    new_arcs, c, n, nv, depot, nq, cap, dem, dist)
                if best == float("inf"):
                    continue
                reg = (second - best) if second < float("inf") else best + 1e9
                regrets.append((reg, c, bv, bi, ba))

            if not regrets:
                c = unserved[0]
                for v in range(nv):
                    if _load_of(new_arcs, v, n, depot, nq, dem) + dem[c] <= cap:
                        route = _route_of(new_arcs, v, n, depot, nq)
                        if route:
                            _insert_cust(new_arcs, v, route[-1], depot, c, n, nq)
                        else:
                            _insert_cust(new_arcs, v, depot, depot, c, n, nq)
                        break
                else:
                    route = _route_of(new_arcs, 0, n, depot, nq)
                    if route:
                        _insert_cust(new_arcs, 0, route[-1], depot, c, n, nq)
                    else:
                        _insert_cust(new_arcs, 0, depot, depot, c, n, nq)
                continue

            regrets.sort(key=lambda x: x[0], reverse=True)
            _, c, bv, bi, ba = regrets[0]
            if bv >= 0 and bi >= 0:
                _insert_cust(new_arcs, bv, bi, ba, c, n, nq)
            else:
                for v in range(nv):
                    if _load_of(new_arcs, v, n, depot, nq, dem) + dem[c] <= cap:
                        route = _route_of(new_arcs, v, n, depot, nq)
                        if route:
                            _insert_cust(new_arcs, v, route[-1], depot, c, n, nq)
                        else:
                            _insert_cust(new_arcs, v, depot, depot, c, n, nq)
                        break
                else:
                    route = _route_of(new_arcs, 0, n, depot, nq)
                    if route:
                        _insert_cust(new_arcs, 0, route[-1], depot, c, n, nq)
                    else:
                        _insert_cust(new_arcs, 0, depot, depot, c, n, nq)

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
        rng: random.Random = context.extra["rng"]
        depot, n, nv, cap, dem, dist, nq = p["depot"], p["n"], p["nv"], p["cap"], p["dem"], p["dist"], p["nq"]

        arcs_data = partial.get("arcs")
        if not isinstance(arcs_data, list):
            return partial

        new_arcs = list(arcs_data)
        served = _all_served(new_arcs, n, nv, depot, nq)
        unserved = [c for c in range(n) if c != depot and c not in served]

        # Phase 1: cheapest insertion
        for c in unserved:
            best, second, bv, bi, ba = _find_best_insert(
                new_arcs, c, n, nv, depot, nq, cap, dem, dist)
            if bv >= 0 and bi >= 0:
                _insert_cust(new_arcs, bv, bi, ba, c, n, nq)
            else:
                for v in range(nv):
                    if _load_of(new_arcs, v, n, depot, nq, dem) + dem[c] <= cap:
                        route = _route_of(new_arcs, v, n, depot, nq)
                        if route:
                            _insert_cust(new_arcs, v, route[-1], depot, c, n, nq)
                        else:
                            _insert_cust(new_arcs, v, depot, depot, c, n, nq)
                        break
                else:
                    route = _route_of(new_arcs, 0, n, depot, nq)
                    if route:
                        _insert_cust(new_arcs, 0, route[-1], depot, c, n, nq)
                    else:
                        _insert_cust(new_arcs, 0, depot, depot, c, n, nq)

        # Phase 2: OR-Opt improvement
        for _ in range(self.passes):
            improved = False
            for vf in range(nv):
                brk = False
                for cl in range(1, self.or_opt_max + 1):
                    for pf in range(n):
                        if brk:
                            break
                        chain = _route_of(new_arcs, vf, n, depot, nq)
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
                            if vt == vf or _load_of(new_arcs, vt, n, depot, nq, dem) + cdem > cap:
                                continue
                            to_route = _route_of(new_arcs, vt, n, depot, nq)
                            for (tb, ta) in _insertion_pairs(to_route, depot):
                                ic = dist[tb][chain_items[0]] + dist[chain_items[-1]][ta] - dist[tb][ta]
                                if save > ic:
                                    # Remove chain from source
                                    new_arcs[vf * nq + pred * n + chain_items[0]] = 0
                                    for ci in range(len(chain_items) - 1):
                                        new_arcs[vf * nq + chain_items[ci] * n + chain_items[ci + 1]] = 0
                                    new_arcs[vf * nq + chain_items[-1] * n + nxt] = 0
                                    new_arcs[vf * nq + pred * n + nxt] = 1

                                    # Insert chain into target
                                    new_arcs[vt * nq + tb * n + ta] = 0
                                    new_arcs[vt * nq + tb * n + chain_items[0]] = 1
                                    for ci in range(len(chain_items) - 1):
                                        new_arcs[vt * nq + chain_items[ci] * n + chain_items[ci + 1]] = 1
                                    new_arcs[vt * nq + chain_items[-1] * n + ta] = 1

                                    improved = True
                                    brk = True
                                    break
                            if brk:
                                break

                if brk:
                    break
            if not improved:
                break

        partial = dict(partial)
        partial["arcs"] = new_arcs
        partial["u"] = _compute_u(new_arcs, n, nv, depot, nq, dem, cap)
        vu = partial.get("vehicle_used")
        if isinstance(vu, list):
            _update_vu(new_arcs, n, nv, depot, nq, vu)
        return partial
