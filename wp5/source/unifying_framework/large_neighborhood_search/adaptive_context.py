"""Adaptive operator context for LNS.

Tracks search dynamics (convergence, operator success rates, iteration history)
and provides utilities for adaptive parameter modulation in destroy/repair operators.

Shared infrastructure reusable across all problem classes (CVRP, 2DBP, JSSP).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperatorStats:
    """Statistics for a single destroy/repair operator pair."""
    name: str  # E.g., "CVRPRouteBreakDestroy + CVRPInsertionRepair"
    applications: int = 0
    successful_applications: int = 0
    avg_improvement: float = 0.0
    last_improvement_iteration: int = 0
    
    @property
    def success_rate(self) -> float:
        """Ratio of successful applications."""
        if self.applications == 0:
            return 0.0
        return self.successful_applications / self.applications

    def recency_score(self, current_iteration: int) -> float:
        """Score based on recency of last improvement (for adaptive selection)."""
        if self.last_improvement_iteration == 0:
            return 0.0
        iterations_since = max(0, current_iteration - self.last_improvement_iteration)
        # Higher score for recent improvements; decay over iterations
        return max(0.0, 1.0 - (iterations_since / 1000.0))


@dataclass
class AdaptiveOperatorContext:
    """Context for adaptive operator behavior.
    
    Tracks convergence metrics, operator performance, and provides
    configuration utilities for adaptive destroy/repair strategies.
    
    Attributes:
        iteration_count: Current iteration number
        best_objective: Best objective value found so far
        best_objective_iteration: Iteration when best was found
        operator_stats: Per-operator performance tracking
        convergence_stalled_iterations: Consecutive iterations without improvement
        destroy_intensity: Adaptive destroy parameter (0.1 - 1.0)
        repair_strategy: Adaptive repair selection mode
    """
    
    iteration_count: int = 0
    best_objective: float = float("inf")
    best_objective_iteration: int = 0
    convergence_stalled_iterations: int = 0
    
    # Per-operator statistics
    operator_stats: dict[str, OperatorStats] = field(default_factory=dict)
    
    # Adaptive parameters
    destroy_intensity: float = 0.5  # Range [0.1, 1.0]; controls destroy neighborhood size
    repair_strategy: str = "greedy"  # "greedy", "regret", "lookahead", or adaptive
    
    # Configuration thresholds
    stall_threshold_easy: int = 100  # Iters without improvement before increasing intensity (easy instances)
    stall_threshold_hard: int = 200  # Iters without improvement before increasing intensity (hard instances)
    convergence_threshold: int = 300  # Stop if no improvement for N iterations
    
    # Search phase tracking
    phase: str = "exploration"  # "exploration" (early, diverse) or "exploitation" (refined, local)
    phase_transition_iteration: int = 0
    
    def record_operator_application(
        self,
        operator_name: str,
        was_successful: bool,
        improvement: float = 0.0,
    ) -> None:
        """Record application of an operator pair.
        
        Args:
            operator_name: Identifier for destroy/repair pair
            was_successful: True if candidate was accepted or improved
            improvement: Magnitude of improvement (if any)
        """
        if operator_name not in self.operator_stats:
            self.operator_stats[operator_name] = OperatorStats(name=operator_name)
        
        stats = self.operator_stats[operator_name]
        stats.applications += 1
        if was_successful:
            stats.successful_applications += 1
            if improvement > 0:
                # Update running average
                old_avg = stats.avg_improvement * (stats.successful_applications - 1)
                stats.avg_improvement = (old_avg + improvement) / stats.successful_applications
                stats.last_improvement_iteration = self.iteration_count
    
    def record_candidate(
        self,
        candidate_objective: float,
        was_accepted: bool,
        is_improvement: bool,
    ) -> None:
        """Record a candidate solution evaluation.
        
        Args:
            candidate_objective: Objective value of candidate
            was_accepted: True if candidate was accepted
            is_improvement: True if candidate improves best known
        """
        if is_improvement:
            self.best_objective = candidate_objective
            self.best_objective_iteration = self.iteration_count
            self.convergence_stalled_iterations = 0
        else:
            self.convergence_stalled_iterations += 1
        
        self.iteration_count += 1
    
    def update_adaptive_parameters(self) -> None:
        """Update adaptive parameters based on search state.
        
        Called after each iteration to modulate destroy/repair behavior.
        Increases destroy intensity if search is stalling.
        Transitions between exploration and exploitation phases.
        """
        # Increase destroy intensity if stalled
        stall_threshold = (
            self.stall_threshold_hard if self.phase == "exploration"
            else self.stall_threshold_easy
        )
        
        if self.convergence_stalled_iterations > 0:
            # Gradual intensity increase as function of stagnation
            stall_ratio = min(1.0, self.convergence_stalled_iterations / stall_threshold)
            # Map [0, 1] to [0.3, 0.9] for destroy intensity
            self.destroy_intensity = 0.3 + (0.6 * stall_ratio)
        else:
            # Reset to moderate value on improvement
            self.destroy_intensity = 0.5
        
        # Transition phases if enough iterations have passed
        if self.phase == "exploration" and self.iteration_count > 1000:
            self.phase = "exploitation"
            self.phase_transition_iteration = self.iteration_count
        
        # Select repair strategy adaptively
        if self.operator_stats:
            # Use operator with best recent success rate
            best_op = max(
                self.operator_stats.values(),
                key=lambda s: s.success_rate + 0.1 * s.recency_score(self.iteration_count),
                default=None,
            )
            if best_op and best_op.success_rate > 0.5:
                self.repair_strategy = "regret"  # Use higher-quality repairs when operators work well
            else:
                self.repair_strategy = "greedy"  # Fall back to faster repairs
    
    def get_destroy_size(self, total_items: int) -> int:
        """Calculate destroy neighborhood size based on adaptive intensity.
        
        Args:
            total_items: Total number of items/cities/jobs in problem
        
        Returns:
            Number of items to destroy (for variable-sized destroy operators)
        """
        # Map destroy_intensity [0.1, 1.0] to destroy_size [1, max_size]
        max_destroy = max(1, total_items // 2)  # Destroy up to 50% in worst case
        min_destroy = max(1, total_items // 10)  # Destroy at least 10%
        
        return int(min_destroy + (max_destroy - min_destroy) * (self.destroy_intensity - 0.1) / 0.9)
    
    def should_use_lookahead_repair(self) -> bool:
        """Determine if repair should use lookahead (slower, better quality).
        
        Returns:
            True if in exploitation phase or search is progressing well
        """
        if self.phase == "exploitation":
            return True
        # Use lookahead if no stagnation
        return self.convergence_stalled_iterations < 50
    
    def get_operator_selection_weights(self) -> dict[str, float]:
        """Get adaptive weights for operator selection.
        
        Returns:
            Dict mapping operator name to selection weight (proportional to success)
        """
        if not self.operator_stats:
            return {}
        
        weights = {}
        for name, stats in self.operator_stats.items():
            # Weight by success rate and recency
            base_weight = stats.success_rate
            recency = stats.recency_score(self.iteration_count)
            weights[name] = base_weight + 0.2 * recency
        
        # Normalize to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            for name in weights:
                weights[name] /= total
        
        return weights
    
    @property
    def is_converged(self) -> bool:
        """Check if search has converged (no improvement for threshold iterations)."""
        return self.convergence_stalled_iterations >= self.convergence_threshold
    
    def summary(self) -> dict[str, Any]:
        """Return summary of adaptive context state for logging."""
        return {
            "iteration": self.iteration_count,
            "best_objective": self.best_objective,
            "best_at_iteration": self.best_objective_iteration,
            "stalled_iterations": self.convergence_stalled_iterations,
            "phase": self.phase,
            "destroy_intensity": self.destroy_intensity,
            "repair_strategy": self.repair_strategy,
            "num_operators": len(self.operator_stats),
            "operator_success_rates": {
                name: stats.success_rate
                for name, stats in self.operator_stats.items()
            },
        }
