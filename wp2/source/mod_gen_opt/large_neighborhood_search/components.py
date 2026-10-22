from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from .models import LNSContext, LNSState


class DestroyOperator(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        raise NotImplementedError

    def reset_for_run(self, context: LNSContext) -> None:
        """Called at engine start. Override to reset state (e.g., for stateful strategies).
        
        Default implementation does nothing. Stateful components should override this.
        """
        pass


class RepairOperator(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        raise NotImplementedError

    def reset_for_run(self, context: LNSContext) -> None:
        """Called at engine start. Override to reset state.
        
        Default implementation does nothing.
        """
        pass


class NeighborhoodSelector(ABC):
    @abstractmethod
    def select(self, state: LNSState, context: LNSContext) -> tuple[DestroyOperator, RepairOperator]:
        raise NotImplementedError

    def reset_for_run(self, context: LNSContext) -> None:
        """Called at engine start. Override to reset state.
        
        Default implementation does nothing.
        """
        pass


class AcceptanceCriterion(ABC):
    @abstractmethod
    def accept(
        self,
        current_score: float,
        candidate_score: float,
        best_score: float,
        state: LNSState,
        context: LNSContext,
    ) -> bool:
        raise NotImplementedError

    def reset_for_run(self, context: LNSContext) -> None:
        """Called at engine start. Override to reset state (e.g., temperature in SA).
        
        Default implementation does nothing.
        """
        pass


class StopCriterion(ABC):
    @abstractmethod
    def should_stop(self, state: LNSState, context: LNSContext) -> bool:
        raise NotImplementedError

    def reset_for_run(self, context: LNSContext) -> None:
        """Called at engine start. Override to reset state.
        
        Default implementation does nothing.
        """
        pass


class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, assignment: dict[str, object], context: LNSContext) -> float:
        raise NotImplementedError


class FeasibilityClassifier(ABC):
    """Determines if a score represents a feasible or infeasible solution.
    
    This interface centralizes the logic for classifying solutions as feasible or infeasible,
    decoupling it from specific penalty-base conventions. Implementations can use:
    - Failed constraint counts (OptDSL)
    - Penalty thresholds (generic)
    - Custom rules (application-specific)
    """

    @abstractmethod
    def is_feasible(self, score: float) -> bool:
        """Return True if score represents a feasible solution."""
        raise NotImplementedError

    @abstractmethod
    def is_infeasible(self, score: float) -> bool:
        """Return True if score represents an infeasible solution."""
        raise NotImplementedError


class Initializer(ABC):
    @abstractmethod
    def initialize(self, context: LNSContext) -> dict[str, object]:
        raise NotImplementedError

    def reset_for_run(self, context: LNSContext) -> None:
        """Called at engine start. Override to reset state.
        
        Default implementation does nothing.
        """
        pass


class LNSLogger(ABC):
    def reset_for_run(self, _context: LNSContext) -> None:
        """Called at engine start. Override to reset logger state between runs.

        Default implementation does nothing so stateless loggers remain compatible.
        """
        return None

    def on_start(self, _state: LNSState, _context: LNSContext) -> None:
        return None

    def on_restart(
        self,
        _iteration: int,
        _restart_count: int,
        _score: float,
        _state: LNSState,
        _context: LNSContext,
    ) -> None:
        return None

    def on_iteration(
        self,
        _iteration: int,
        _destroy_name: str,
        _repair_name: str,
        _candidate_score: float,
        _accepted: bool,
        _improved: bool,
        _state: LNSState,
        _context: LNSContext,
    ) -> None:
        return None

    def on_finish(self, _state: LNSState, _context: LNSContext) -> None:
        return None


# ---------------------------------------------------------------------------
# Generic MCMC (Metropolis-Hastings with simulated annealing)
# ---------------------------------------------------------------------------
# Encapsulated as a pure function so it can be reused by any initializer,
# tree-search warm start, code-discovery feasibility finder, etc.
# ---------------------------------------------------------------------------


@dataclass
class MCMCState:
    """Light-weight dataclass to carry the MCMC walk state around."""
    assignment: dict[str, object]
    failed: int
    objective: float
    temperature: float
    batch_size: int
    biased_keys: list[tuple[str, int | None]] | None = None


class _MCMCCallbacks(Protocol):
    """Protocol of callables the MCMC driver needs from its environment."""

    def clone(self, assignment: dict[str, object]) -> dict[str, object]: ...
    def evaluate_detailed(
        self, assignment: dict[str, object],
    ) -> tuple[int, float]: ...  # (failed, objective)
    def mutate(self, assignment: dict[str, object], batch_size: int, biased_keys: list[tuple[str, int | None]] | None) -> dict[str, object]: ...
    def better(self, a_failed: int, a_obj: float, b_failed: int, b_obj: float) -> bool: ...


def run_mcmc(
    *,
    seed_assignment: dict[str, object],
    callbacks: _MCMCCallbacks,
    rng: random.Random,
    max_steps: int = 5000,
    initial_temperature: float = 1000.0,
    cooling_rate: float = 0.998,
    min_temperature: float = 0.1,
    initial_batch_size: int = 3,
    max_batch_size: int = 20,
    stall_threshold: int = 200,
    stall_batch_increment: int = 3,
    penalty_scale: float = 100.0,
    objective_weight: float = 1.0,
    objective_sense: str = "minimize",
) -> dict[str, object]:
    """Run the MCMC walk and return the best-found assignment (feasible or lowest-violation).

    The walk is parameterised entirely through *callbacks*, making it reusable
    across LNS initialisation, tree-search warm starts, or any other component
    that needs to find a feasible/low-energy point in a coupled-constraint search
    space.
    """
    # --- helpers kept local for speed ---
    def energy(failed: int, obj: float) -> float:
        e = penalty_scale * max(0, failed)
        if math.isfinite(obj):
            e += objective_weight * (obj if objective_sense == "minimize" else -obj)
        return e

    def accept_probability(delta_e: float, temp: float) -> float:
        if delta_e <= 0:
            return 1.0
        try:
            return math.exp(-delta_e / max(temp, 1e-12))
        except OverflowError:
            return 0.0

    # --- initialise walk state ---
    failed, objective = callbacks.evaluate_detailed(seed_assignment)
    assignment = seed_assignment
    best_assignment = callbacks.clone(assignment)
    best_failed = failed
    best_objective = objective
    temperature = initial_temperature
    batch_size = initial_batch_size
    stall_counter = 0
    last_failed_for_stall = failed
    biased_keys = callbacks.mutate.__defaults__ and [None]  # dummy, computed below

    # Seed biased keys from initial evaluation
    biased_keys = assignment.get("__biased_decision_keys__")  # type: ignore[union-attr]
    if biased_keys is None or not isinstance(biased_keys, list):
        biased_keys = None

    for _ in range(max_steps):
        # --- proposal ---
        proposal = callbacks.mutate(assignment, batch_size, biased_keys)
        p_failed, p_objective = callbacks.evaluate_detailed(proposal)

        e_cur = energy(failed, objective)
        e_prop = energy(p_failed, p_objective)
        delta_e = e_prop - e_cur

        if rng.random() < accept_probability(delta_e, temperature):
            assignment = proposal
            failed = p_failed
            objective = p_objective

            if callbacks.better(failed, objective, best_failed, best_objective):
                best_assignment = callbacks.clone(assignment)
                best_failed = failed
                best_objective = objective
                if best_failed == 0:
                    return best_assignment

            # --- update biased keys (if evaluator set them) ---
            bk = assignment.get("__biased_decision_keys__")
            if bk is not None and isinstance(bk, list):
                biased_keys = bk

            # --- stalled plateau detection ---
            if failed == last_failed_for_stall:
                stall_counter += 1
            else:
                stall_counter = 0
                last_failed_for_stall = failed

            if stall_counter >= stall_threshold:
                if batch_size < max_batch_size:
                    batch_size = min(max_batch_size, batch_size + stall_batch_increment)
                else:
                    stall_counter = 0
                    last_failed_for_stall = failed

            # --- adaptive temperature boost if stuck ---
            if temperature < min_temperature and failed > 0:
                temperature = max(temperature * 1.5, min_temperature)
        else:
            stall_counter += 1
            if stall_counter >= stall_threshold:
                if batch_size < max_batch_size:
                    batch_size = min(max_batch_size, batch_size + stall_batch_increment)
                    stall_counter = 0

        # --- cool ---
        temperature *= cooling_rate
        if temperature < min_temperature:
            temperature = min_temperature

    return best_assignment
