from __future__ import annotations

from abc import ABC, abstractmethod

from .models import LNSContext, LNSState


class DestroyOperator(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def destroy(self, assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        raise NotImplementedError


class RepairOperator(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def repair(self, partial_assignment: dict[str, object], context: LNSContext) -> dict[str, object]:
        raise NotImplementedError


class NeighborhoodSelector(ABC):
    @abstractmethod
    def select(self, state: LNSState, context: LNSContext) -> tuple[DestroyOperator, RepairOperator]:
        raise NotImplementedError


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


class StopCriterion(ABC):
    @abstractmethod
    def should_stop(self, state: LNSState, context: LNSContext) -> bool:
        raise NotImplementedError


class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, assignment: dict[str, object], context: LNSContext) -> float:
        raise NotImplementedError


class Initializer(ABC):
    @abstractmethod
    def initialize(self, context: LNSContext) -> dict[str, object]:
        raise NotImplementedError


class LNSLogger(ABC):
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
