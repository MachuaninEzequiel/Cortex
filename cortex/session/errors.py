"""cortex.session.errors — Domain exceptions for the Session primitive.

All exceptions inherit from :class:`SessionError`. Callers should catch the
base class when they want to translate any session failure into a generic
error response (e.g. MCP tool responses, CLI exit messages).

The hierarchy is intentionally flat — there is no need for sub-trees while
the surface area is small. New exceptions added later should also inherit
directly from :class:`SessionError` unless a real grouping exists.
"""

from __future__ import annotations


class SessionError(Exception):
    """Base class for all errors raised by :mod:`cortex.session`."""


class SessionNotFound(SessionError):
    """Raised when a ``session_id`` does not exist in storage."""


class SessionAlreadyExists(SessionError):
    """Raised when trying to open a Session whose id already exists.

    The service layer detects collisions and appends a numeric suffix to
    the slug instead of raising; this exception remains for low-level
    storage operations that need to enforce uniqueness explicitly.
    """


class InvalidStateTransition(SessionError):
    """Raised when an operation is incompatible with the current status.

    Examples:
        - Appending a checkpoint to a CLOSED session.
        - Closing an already-CLOSED session.
        - Setting active a session that is not OPEN.
    """


class SessionStorageCorrupted(SessionError):
    """Raised when a session YAML on disk cannot be parsed.

    The storage layer surfaces this exception with a path-bearing message
    so the user can inspect the offending file. Storage list/scan
    operations log and skip corrupted files instead of raising.
    """


class NoActiveSession(SessionError):
    """Raised when an operation needs an active session and none is set."""
