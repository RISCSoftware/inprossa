"""Report writers.

Two formats, because they answer different questions: JSON is what a script or a
later run reads, and Markdown is what a person reads. Both are produced from the
same object so they cannot disagree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .session import Session
from .tuning import TuningReport


def write_tuning_report(report: TuningReport, directory: str | Path, *, stem: str = "tuning") -> dict[str, str]:
    """Write the JSON and Markdown forms of a tuning report."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)

    json_path = target / f"{stem}.json"
    markdown_path = target / f"{stem}.md"

    json_path.write_text(json.dumps(report.to_dict(), indent=2, default=str), encoding="utf-8")
    markdown_path.write_text(report.to_markdown(), encoding="utf-8")

    return {"json": str(json_path), "markdown": str(markdown_path)}


def write_session_report(session: Session, directory: str | Path | None = None) -> dict[str, str]:
    """Persist the session: the current model as ``.dsl`` plus a transcript.

    The model file lets a newly built problem be saved and reloaded; the
    transcript keeps the session history and results for later inspection.
    Returns a mapping of kind → written path (``dsl`` and ``json``).
    """
    target = Path(directory) if directory is not None else session.config.output_dir
    target.mkdir(parents=True, exist_ok=True)

    dsl_path = target / f"{session.stem}.dsl"
    dsl_path.write_text(session.source, encoding="utf-8")

    json_path = target / f"{session.stem}.session.json"
    payload: dict[str, Any] = {
        "session": session.to_dict(),
        "config": session.config.to_dict(),
        "lastSolve": _strip(session.last_solve),
        "lastLns": _strip(session.last_lns),
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {"dsl": str(dsl_path), "json": str(json_path)}


def _strip(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop bulky fields so the transcript stays readable."""
    if payload is None:
        return None
    return {
        key: value
        for key, value in payload.items()
        if key not in {"solution", "assignment", "trajectory", "source"}
    }
