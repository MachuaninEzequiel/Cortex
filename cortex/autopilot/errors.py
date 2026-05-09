"""cortex.autopilot.errors — Exceptions raised by the Autopilot module."""
from __future__ import annotations


class AutopilotError(Exception):
    """Base exception for all Autopilot errors."""


class SessionNotFoundError(AutopilotError):
    """Raised when a requested session does not exist in the StateStore."""


class ConfigError(AutopilotError):
    """Raised when the Autopilot configuration is invalid or missing."""
