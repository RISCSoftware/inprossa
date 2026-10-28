"""Structural problem-class detection.

The LNS package currently carries seven near-identical ``detect_*_problem``
helpers, each hardcoding a list of required constant and variable names. That
works for the operators but is useless for tooling: it cannot answer "what
problem class is this?" for an arbitrary formulation, and it cannot tell you
*which* requirement is missing.

This module replaces them with one fingerprint: a set of required constants and
variables per class, plus a similarity score. The score is what the operator
synthesis harness uses to decide which operator library is relevant, and what
the language server uses to offer problem-specific completions.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .analysis import ModuleIndex

#: Minimum fraction of a class's required markers a model must contain before
#: it is reported as (a partial match of) that class. Below this the model is
#: treated as an unknown formulation rather than labelled with whichever class
#: happened to sort first — a lot-sizing model has nothing in common with bin
#: packing and must not be presented to operator synthesis as "1dbp".
MIN_MATCH_SCORE = 0.5


@dataclass(frozen=True)
class ProblemClass:
    """A known problem family and the structural markers that identify it."""

    name: str
    required_constants: tuple[str, ...]
    required_variables: tuple[str, ...]
    optional_constants: tuple[str, ...] = ()
    optional_variables: tuple[str, ...] = ()
    description: str = ""


#: Registry of known problem families, mirroring the ``problems/`` adapters.
PROBLEM_CLASSES: tuple[ProblemClass, ...] = (
    ProblemClass(
        name="1dbp",
        required_constants=("BOX_CAPACITIES", "ITEM_WEIGHTS"),
        required_variables=("assignments",),
        description="One-dimensional bin packing",
    ),
    ProblemClass(
        name="2dbp",
        required_constants=(
            "NBOXES",
            "NITEMS",
            "ITEM_WIDTHS",
            "ITEM_HEIGHTS",
            "BOX_WIDTH_CAPACITIES",
            "BOX_HEIGHT_CAPACITIES",
        ),
        required_variables=("assignments", "x_positions", "y_positions"),
        description="Two-dimensional bin packing",
    ),
    ProblemClass(
        name="cvrp",
        required_constants=("DEPOT", "DEMANDS", "VEHICLE_CAPACITY", "N_CITIES", "N_VEHICLES"),
        required_variables=("arcs", "vehicle_used"),
        optional_variables=("u",),
        description="Capacitated vehicle routing (arc formulation)",
    ),
    ProblemClass(
        name="cvrp_tour",
        required_constants=("DEPOT", "DEMANDS", "VEHICLE_CAPACITY", "N_CITIES", "N_VEHICLES"),
        required_variables=("tour",),
        description="Capacitated vehicle routing (permutation formulation)",
    ),
    ProblemClass(
        name="jssp",
        required_constants=("N_JOBS", "N_MACHINES", "PROCESSING_TIMES", "MACHINE_SEQUENCE"),
        required_variables=("completion",),
        description="Job shop scheduling",
    ),
    ProblemClass(
        name="cutting_packing",
        required_constants=(
            "LAYER_LENGTH",
            "N_LAYERS",
            "N_SEGMENTS",
            "N_CUTS_PER_SEGMENT",
            "N_PIECES_PER_SEGMENT",
            "N_CUTS",
            "N_PIECES",
            "SEGMENT_LENGTHS",
        ),
        required_variables=("cut_positions", "piece_assignments"),
        description="One-dimensional cutting stock with layer packing",
    ),
    ProblemClass(
        name="woodcutting",
        required_constants=(
            "N_BOARDS",
            "MAX_BOARD_LENGTH",
            "MAX_N_CUTS_PER_BOARD",
            "N_PIECES",
            "BEAM_LENGTH",
            "BEAM_DEPTH",
            "GIVEN_INITIAL_BOARDS",
        ),
        required_variables=("cuts_list_list", "keep_decisions"),
        optional_variables=("swapping_decisions", "swapping_decisions_boards"),
        description="Woodcutting pipeline with reordering decisions",
    ),
)


@dataclass
class ProblemFingerprint:
    """How well a module matches each known problem class."""

    best: ProblemClass | None
    score: float
    missing_constants: list[str] = field(default_factory=list)
    missing_variables: list[str] = field(default_factory=list)
    candidates: list[tuple[ProblemClass, float]] = field(default_factory=list)

    @property
    def matched(self) -> bool:
        return self.best is not None and not self.missing_constants and not self.missing_variables

    def explain(self) -> str:
        if self.best is None:
            return "no known problem class matches this formulation"
        if self.matched:
            return f"matches '{self.best.name}' ({self.best.description})"
        parts = []
        if self.missing_constants:
            parts.append("missing constants: " + ", ".join(self.missing_constants))
        if self.missing_variables:
            parts.append("missing variables: " + ", ".join(self.missing_variables))
        return f"closest match '{self.best.name}' — " + "; ".join(parts)


def fingerprint(index: ModuleIndex) -> ProblemFingerprint:
    """Score ``index`` against every known problem class."""
    constants = set(index.constants)
    variables = set(index.variables)

    scored: list[tuple[ProblemClass, float, list[str], list[str]]] = []
    for problem_class in PROBLEM_CLASSES:
        missing_constants = [c for c in problem_class.required_constants if c not in constants]
        missing_variables = [v for v in problem_class.required_variables if v not in variables]

        total = len(problem_class.required_constants) + len(problem_class.required_variables)
        present = total - len(missing_constants) - len(missing_variables)
        score = present / total if total else 0.0

        # Optional markers break ties between formulations that share a
        # required set (e.g. CVRP arc vs tour).
        optional_total = len(problem_class.optional_constants) + len(problem_class.optional_variables)
        if optional_total:
            optional_present = sum(1 for c in problem_class.optional_constants if c in constants)
            optional_present += sum(1 for v in problem_class.optional_variables if v in variables)
            score += 0.01 * (optional_present / optional_total)

        scored.append((problem_class, score, missing_constants, missing_variables))

    scored.sort(key=lambda item: item[1], reverse=True)
    best_class, best_score, missing_constants, missing_variables = scored[0]
    candidates = [(problem_class, score) for problem_class, score, _, _ in scored]

    if best_score < MIN_MATCH_SCORE:
        return ProblemFingerprint(best=None, score=best_score, candidates=candidates)

    return ProblemFingerprint(
        best=best_class,
        score=best_score,
        missing_constants=missing_constants,
        missing_variables=missing_variables,
        candidates=candidates,
    )


def problem_key(index: ModuleIndex, problem: ProblemFingerprint | None = None) -> str:
    """A stable, file-name-safe identifier for the *formulation* of a model.

    Tuned LNS artifacts (operators, construction heuristic, run config) are
    keyed by this, so every instance of the same model shares them while data
    changes do not. A fully matched known class uses its name (``cvrp``); any
    other model is keyed by its structure — decision variable names and
    annotations plus constraint names — which is independent of constant values.
    """
    problem = problem if problem is not None else fingerprint(index)
    if problem.best is not None and problem.matched:
        return problem.best.name

    decisions = sorted(
        (name, variable.annotation_code or "")
        for name, variable in index.variables.items()
        if variable.is_decision
    )
    predicates = sorted(
        name for name, predicate in index.predicates.items() if not predicate.is_warm_start
    )
    sense = index.objective.sense if index.objective is not None else "satisfy"
    signature = repr((decisions, predicates, sense))
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:8]

    readable = "_".join(name for name, _ in decisions) or "model"
    readable = re.sub(r"[^A-Za-z0-9_]+", "_", readable).strip("_").lower()[:40] or "model"
    return f"{readable}_{digest}"


def problem_label(index: ModuleIndex, problem: ProblemFingerprint | None = None) -> str:
    """Human/LLM-readable name of the problem, used in prompts and reports."""
    problem = problem if problem is not None else fingerprint(index)
    if problem.best is not None and problem.matched:
        return f"{problem.best.name} ({problem.best.description})"
    decisions = [name for name, variable in index.variables.items() if variable.is_decision]
    names = ", ".join(decisions) if decisions else "none"
    return f"custom optimisation model (decision variables: {names})"
