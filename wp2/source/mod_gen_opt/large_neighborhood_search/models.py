from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


@dataclass
class LNSContext:
    constants: dict[str, Any] = field(default_factory=dict)
    objective_sense: str = "minimize"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LNSStats:
    started_at: float = field(default_factory=perf_counter)
    finished_at: float | None = None
    iterations: int = 0
    accepted: int = 0
    improvements: int = 0
    infeasible_candidates: int = 0

    @property
    def elapsed_seconds(self) -> float:
        end_time = self.finished_at if self.finished_at is not None else perf_counter()
        return end_time - self.started_at


@dataclass
class LNSSolution:
    assignment: dict[str, Any]
    score: float


@dataclass
class LNSState:
    current: LNSSolution
    incumbent: LNSSolution
    stats: LNSStats = field(default_factory=LNSStats)


@dataclass
class LNSResult:
    incumbent: LNSSolution
    stats: LNSStats
