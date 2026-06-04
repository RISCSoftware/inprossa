from __future__ import annotations

from time import perf_counter

from .components import AcceptanceCriterion, Evaluator, Initializer, LNSLogger, NeighborhoodSelector, StopCriterion
from .models import LNSContext, LNSResult, LNSState, LNSSolution


class LargeNeighborhoodSearchEngine:
    def __init__(
        self,
        initializer: Initializer,
        selector: NeighborhoodSelector,
        evaluator: Evaluator,
        acceptance: AcceptanceCriterion,
        stop: StopCriterion,
        logger: LNSLogger | None = None,
    ) -> None:
        self.initializer = initializer
        self.selector = selector
        self.evaluator = evaluator
        self.acceptance = acceptance
        self.stop = stop
        self.logger = logger

    def run(self, context: LNSContext) -> LNSResult:
        initial_assignment = self.initializer.initialize(context)
        initial_score = self.evaluator.evaluate(initial_assignment, context)
        initial = LNSSolution(assignment=initial_assignment, score=initial_score)
        state = LNSState(current=initial, incumbent=initial)

        if not _is_infeasible_score(initial_score, context):
            _emit_feasible_solution_callback(
                assignment=initial_assignment,
                score=initial_score,
                iteration=0,
                event="initial",
                state=state,
                context=context,
            )

        if self.logger is not None:
            self.logger.on_start(state, context)

        while not self.stop.should_stop(state, context):
            state.stats.iterations += 1
            destroy, repair = self.selector.select(state, context)
            partial = destroy.destroy(_clone_assignment(state.current.assignment), context)
            candidate_assignment = repair.repair(partial, context)
            candidate_score = self.evaluator.evaluate(candidate_assignment, context)

            if _is_infeasible_score(candidate_score, context):
                fallback_initializer = context.extra.get("infeasible_fallback_initializer")
                if fallback_initializer is not None and hasattr(fallback_initializer, "initialize"):
                    fallback_assignment = fallback_initializer.initialize(context)
                    fallback_score = self.evaluator.evaluate(fallback_assignment, context)
                    if not _is_infeasible_score(fallback_score, context):
                        candidate_assignment = fallback_assignment
                        candidate_score = fallback_score

            if _is_infeasible_score(candidate_score, context):
                state.stats.infeasible_candidates += 1
            else:
                _emit_feasible_solution_callback(
                    assignment=candidate_assignment,
                    score=candidate_score,
                    iteration=state.stats.iterations,
                    event="candidate_feasible",
                    state=state,
                    context=context,
                )

            accepted = self.acceptance.accept(
                state.current.score,
                candidate_score,
                state.incumbent.score,
                state,
                context,
            )

            improved = False
            if accepted:
                state.stats.accepted += 1
                state.current = LNSSolution(assignment=candidate_assignment, score=candidate_score)
                if not _is_infeasible_score(candidate_score, context):
                    _emit_feasible_solution_callback(
                        assignment=candidate_assignment,
                        score=candidate_score,
                        iteration=state.stats.iterations,
                        event="accepted_feasible",
                        state=state,
                        context=context,
                    )

            if _is_better(candidate_score, state.incumbent.score, context.objective_sense):
                state.stats.improvements += 1
                improved = True
                state.incumbent = LNSSolution(assignment=candidate_assignment, score=candidate_score)
                if not _is_infeasible_score(candidate_score, context):
                    _emit_feasible_solution_callback(
                        assignment=candidate_assignment,
                        score=candidate_score,
                        iteration=state.stats.iterations,
                        event="incumbent_update",
                        state=state,
                        context=context,
                    )

            if self.logger is not None:
                self.logger.on_iteration(
                    state.stats.iterations,
                    destroy.name,
                    repair.name,
                    candidate_score,
                    accepted,
                    improved,
                    state,
                    context,
                )

        state.stats.finished_at = perf_counter()

        if self.logger is not None:
            self.logger.on_finish(state, context)

        return LNSResult(incumbent=state.incumbent, stats=state.stats)


def _clone_assignment(assignment: dict[str, object]) -> dict[str, object]:
    cloned: dict[str, object] = {}
    for key, value in assignment.items():
        if isinstance(value, list):
            cloned[key] = value.copy()
        else:
            cloned[key] = value
    return cloned


def _is_better(candidate: float, best: float, objective_sense: str) -> bool:
    if objective_sense == "maximize":
        return candidate > best
    return candidate < best


def _is_infeasible_score(score: float, context: LNSContext) -> bool:
    if score == float("inf"):
        return True
    penalty_base = context.extra.get("penalty_base")
    if not isinstance(penalty_base, (int, float)):
        return False
    if context.objective_sense == "maximize":
        return score <= -float(penalty_base)
    return score >= float(penalty_base)


def _emit_feasible_solution_callback(
    assignment: dict[str, object],
    score: float,
    iteration: int,
    event: str,
    state: LNSState,
    context: LNSContext,
) -> None:
    callback = context.extra.get("on_feasible_solution")
    if not callable(callback):
        return
    callback(
        _clone_assignment(assignment),
        score,
        {
            "event": event,
            "iteration": iteration,
            "iterations_completed": state.stats.iterations,
            "accepted": state.stats.accepted,
            "improvements": state.stats.improvements,
            "infeasible_candidates": state.stats.infeasible_candidates,
        },
        context,
    )
