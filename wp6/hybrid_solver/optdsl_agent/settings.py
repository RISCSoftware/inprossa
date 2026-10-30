"""Persistent settings: named profiles of model, endpoint and key.

Repeating ``--model``, ``--base-url`` and ``--api-key`` on every invocation is
the main friction in using the harness, and putting the key on the command line
leaks it into shell history. This module stores those three values once, under a
named profile, in a per-user config file.

Precedence, highest first:

1. CLI flag
2. Environment variable
3. Stored profile
4. Built-in default

Environment beating the file is deliberate: it lets a CI job or a one-off shell
override a stored profile without editing it.

The file is plaintext. It is written with owner-only permissions where the
platform supports them, and it lives in the per-user config directory, which is
already user-scoped on Windows. It is not a secret store; if you need one, keep
the key in ``OPTDSL_AGENT_API_KEY`` and store only the model and endpoint here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

#: Profile name used when none is given.
DEFAULT_PROFILE = "default"

#: Environment variable that relocates the settings file, mainly for tests.
SETTINGS_PATH_ENV = "OPTDSL_AGENT_SETTINGS"


@dataclass
class Profile:
    """One stored model configuration."""

    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    temperature: float | None = None

    def is_empty(self) -> bool:
        return not any(
            value is not None
            for value in (self.model, self.base_url, self.api_key, self.temperature)
        )

    def to_dict(self, *, redact: bool = False) -> dict[str, Any]:
        payload = {key: value for key, value in asdict(self).items() if value is not None}
        if redact and "api_key" in payload:
            payload["api_key"] = _mask(payload["api_key"])
        return payload


@dataclass
class Settings:
    """The whole settings file."""

    default_profile: str = DEFAULT_PROFILE
    profiles: dict[str, Profile] = field(default_factory=dict)

    # -- persistence -------------------------------------------------------

    @classmethod
    def path(cls) -> Path:
        """Location of the settings file.

        ``OPTDSL_AGENT_SETTINGS`` wins so tests never touch the real file.
        """
        override = os.environ.get(SETTINGS_PATH_ENV)
        if override:
            return Path(override)
        return _config_dir() / "settings.json"

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        """Read the settings file, tolerating absence and corruption.

        A malformed file must not make the CLI unusable, so it is treated as
        empty. The user can inspect it with ``optdsl_agent settings show``.
        """
        target = path or cls.path()
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()

        if not isinstance(raw, dict):
            return cls()

        profiles: dict[str, Profile] = {}
        for name, values in (raw.get("profiles") or {}).items():
            if isinstance(values, dict):
                profiles[name] = Profile(
                    model=values.get("model"),
                    base_url=values.get("base_url"),
                    api_key=values.get("api_key"),
                    temperature=values.get("temperature"),
                )

        return cls(
            default_profile=raw.get("default_profile") or DEFAULT_PROFILE,
            profiles=profiles,
        )

    def save(self, path: Path | None = None) -> Path:
        """Write the settings file with owner-only permissions."""
        target = path or self.path()
        target.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "default_profile": self.default_profile,
            "profiles": {
                name: profile.to_dict() for name, profile in sorted(self.profiles.items())
            },
        }
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _restrict_permissions(target)
        return target

    # -- access ------------------------------------------------------------

    def profile(self, name: str | None = None) -> Profile:
        """The named profile, or an empty one when it does not exist."""
        return self.profiles.get(name or self.default_profile, Profile())

    def set_profile(self, name: str, profile: Profile) -> None:
        self.profiles[name] = profile

    def remove_profile(self, name: str) -> bool:
        return self.profiles.pop(name, None) is not None

    def to_dict(self, *, redact: bool = True) -> dict[str, Any]:
        return {
            "path": str(self.path()),
            "default_profile": self.default_profile,
            "profiles": {
                name: profile.to_dict(redact=redact)
                for name, profile in sorted(self.profiles.items())
            },
        }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _config_dir() -> Path:
    """Per-user configuration directory for this platform."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "optdsl_agent"
        return Path.home() / "AppData" / "Roaming" / "optdsl_agent"

    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "optdsl_agent"
    return Path.home() / ".config" / "optdsl_agent"


def _restrict_permissions(path: Path) -> None:
    """Make the file readable only by its owner, where that is possible.

    On POSIX this is ``chmod 0600``. On Windows the file already lives in a
    per-user directory, so the inherited ACL is adequate; ``icacls`` is applied
    as a best-effort hardening step and a failure is ignored rather than leaving
    the file in a half-modified state.
    """
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if not user:
            return
        try:
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        return

    try:
        path.chmod(0o600)
    except OSError:
        pass


def _mask(value: str) -> str:
    """Show enough of a key to identify it, never enough to use it."""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def warn_if_insecure(path: Path) -> str | None:
    """Return a warning when the settings file is readable by others."""
    if os.name == "nt":
        return None
    try:
        mode = path.stat().st_mode
    except OSError:
        return None
    if mode & 0o077:
        return (
            f"{path} is readable by other users (mode {oct(mode & 0o777)}); "
            "run `chmod 600` on it or move the key to OPTDSL_AGENT_API_KEY."
        )
    return None


def describe_platform() -> str:
    """One line describing where settings live, for ``settings show``."""
    return f"{Settings.path()} ({sys.platform})"
