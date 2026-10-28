"""Tuned LNS configurations: what ``/tune`` developed, and how ``/lns`` uses it.

``/tune`` produces problem-specific artifacts — a construction heuristic
(initializer) and destroy/repair operators — as self-contained modules in the
generated operator directory. Those modules alone do not say *how* to run LNS,
so tuning also writes a small JSON config per problem::

    <operator_dir>/<problem_key>.lns.json

``problem_key`` identifies the formulation, not the data file (see
:func:`optdsl_tooling.fingerprint.problem_key`), so every instance of the same
model picks up the tuned configuration. ``/lns`` and ``optdsl-agent lns`` load
it automatically unless operators are given explicitly, and every run reports
which configuration it used.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from optdsl_tooling.analysis import analyze
from optdsl_tooling.fingerprint import fingerprint, problem_key, problem_label

from .initializer import InitializerArtifact, load_initializer_file

CONFIG_SUFFIX = ".lns.json"


@dataclass
class TunedLNSConfig:
    """A persisted LNS setup for one problem formulation."""

    problem_key: str
    problem_label: str = ""
    #: ``{"class_name": ..., "file": ...}``; ``file`` is relative to the
    #: operator directory. ``None`` keeps the default (``auto``) construction.
    initializer: dict[str, str] | None = None
    #: Registry names; the selector pairs every destroy with every repair.
    destroys: list[str] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    #: Generated operators in this config: ``{"name", "kind", "file"}``.
    generated: list[dict[str, str]] = field(default_factory=list)
    adaptive: bool = True
    acceptance: str = "improving"
    instances: list[str] = field(default_factory=list)
    created_at: str = ""
    #: LNS result before and after tuning (objective, feasible, iterations).
    baseline: dict[str, Any] = field(default_factory=dict)
    tuned: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TunedLNSConfig":
        known = {name for name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in data.items() if key in known})

    def initializer_artifact(self, operator_dir: str | Path) -> InitializerArtifact | None:
        if not self.initializer:
            return None
        return load_initializer_file(
            Path(operator_dir) / self.initializer["file"], self.initializer.get("class_name")
        )

    def describe(self) -> str:
        """One line for logs: construction and operators."""
        construction = self.initializer["class_name"] if self.initializer else "auto"
        return (
            f"construction {construction}; destroys: {', '.join(self.destroys) or 'default'}; "
            f"repairs: {', '.join(self.repairs) or 'default'}"
            + ("; adaptive selection" if self.adaptive else "")
        )


def problem_identity(source: str) -> tuple[str, str]:
    """``(problem_key, problem_label)`` for an OptDSL source text."""
    index = analyze(source)
    problem = fingerprint(index)
    return problem_key(index, problem), problem_label(index, problem)


def config_path(operator_dir: str | Path, key: str) -> Path:
    return Path(operator_dir) / f"{key}{CONFIG_SUFFIX}"


def load_tuned_config(operator_dir: str | Path, key: str) -> TunedLNSConfig | None:
    path = config_path(operator_dir, key)
    if not path.exists():
        return None
    try:
        return TunedLNSConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return None


def save_tuned_config(config: TunedLNSConfig, operator_dir: str | Path) -> Path:
    path = config_path(operator_dir, config.problem_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not config.created_at:
        config.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(config.to_dict(), indent=2, default=str), encoding="utf-8")
    return path


@dataclass
class LNSRunSettings:
    """Operators/initializer for one run, plus the log record of where they came from."""

    destroys: list[str]
    repairs: list[str]
    initializer: Any
    adaptive: bool
    log: dict[str, Any]


def resolve_run_settings(
    source: str,
    operator_dir: str | Path,
    *,
    destroys: list[str] | None = None,
    repairs: list[str] | None = None,
    initializer: str | Any = "auto",
    adaptive: bool = False,
    use_tuned: bool = True,
) -> LNSRunSettings:
    """Decide which LNS configuration a run uses.

    Explicit operators win. Otherwise the tuned config for the model's problem
    key is applied: its operators always, its construction heuristic only when
    the requested initializer is ``"auto"`` (an explicit initializer wins).
    Operators the registry cannot resolve are dropped and reported in the log.
    Generated operators must already be loaded (``load_generated_operators``).
    """
    destroys = list(destroys or [])
    repairs = list(repairs or [])

    if destroys or repairs:
        return LNSRunSettings(
            destroys, repairs, initializer, adaptive,
            {"source": "explicit", "destroys": destroys, "repairs": repairs},
        )

    tuned: TunedLNSConfig | None = None
    key: str | None = None
    if use_tuned:
        try:
            key, _ = problem_identity(source)
            tuned = load_tuned_config(operator_dir, key)
        except Exception:  # noqa: BLE001 - a broken model must not break /lns
            tuned = None

    if tuned is None:
        return LNSRunSettings(
            [], [], initializer, adaptive, {"source": "default", "problemKey": key}
        )

    import large_neighborhood_search.builtin_operators  # noqa: F401 - populate registry
    from large_neighborhood_search.registry import describe

    usable_destroys = [name for name in tuned.destroys if describe(name) is not None]
    usable_repairs = [name for name in tuned.repairs if describe(name) is not None]
    missing = [name for name in tuned.destroys + tuned.repairs if describe(name) is None]

    effective_initializer: Any = initializer
    construction = None
    if initializer == "auto":
        artifact = tuned.initializer_artifact(operator_dir)
        if artifact is not None:
            effective_initializer = artifact.instantiate()
            construction = artifact.class_name

    log: dict[str, Any] = {
        "source": "tuned",
        "problemKey": tuned.problem_key,
        "path": str(config_path(operator_dir, tuned.problem_key)),
        "initializer": construction or (initializer if isinstance(initializer, str) else type(initializer).__name__),
        "destroys": usable_destroys,
        "repairs": usable_repairs,
        "adaptive": tuned.adaptive or adaptive,
    }
    if missing:
        log["missingOperators"] = missing

    return LNSRunSettings(
        usable_destroys,
        usable_repairs,
        effective_initializer,
        tuned.adaptive or adaptive,
        log,
    )


def describe_run(log: dict[str, Any] | None, result: dict[str, Any] | None = None) -> str:
    """Render the ``lnsConfig`` log record (plus what actually ran) as one line."""
    if not log:
        return ""
    result = result or {}
    source = log.get("source", "default")
    if source == "tuned":
        head = f"LNS config: tuned ({Path(log.get('path', '')).name})"
    elif source == "explicit":
        head = "LNS config: explicit operators"
    else:
        head = "LNS config: default (no tuned config for this model; run /tune)"
    parts = [f"construction {result.get('initializer') or log.get('initializer') or 'auto'}"]
    neighborhoods = result.get("neighborhoods") or []
    if neighborhoods:
        parts.append("neighborhoods " + ", ".join(neighborhoods))
    if log.get("missingOperators"):
        parts.append("missing: " + ", ".join(log["missingOperators"]))
    return head + " — " + "; ".join(parts)
