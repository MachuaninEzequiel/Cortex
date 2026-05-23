"""cortex.autopilot.errors — Exceptions raised by the Autopilot module.

Phase 03 removed ``SessionNotFoundError`` from this module: callers now
import :class:`cortex.session.errors.SessionNotFound` from the canonical
session primitive. The legacy name is re-exported as a deprecated alias
so external code does not break instantly; the alias will be removed in
the next major release.
"""

from __future__ import annotations

from cortex.session.errors import SessionNotFound as _CanonicalSessionNotFound


class AutopilotError(Exception):
    """Base exception for all Autopilot errors."""


class ConfigError(AutopilotError):
    """Raised when the Autopilot configuration is invalid or missing."""


class NoActiveSessionError(AutopilotError):
    """Raised when an operation requires an active session and none exists."""


# Deprecated alias — kept for legacy importers; remove in the next major.
SessionNotFoundError = _CanonicalSessionNotFound


__all__ = [
    "AutopilotError",
    "ConfigError",
    "NoActiveSessionError",
    "SessionNotFoundError",
]
