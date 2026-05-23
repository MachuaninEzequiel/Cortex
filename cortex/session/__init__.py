"""cortex.session — Session primitive for the Pluggable Middle architecture.

This package implements the core lifecycle primitive that unites
``cortex-sync``, the (pluggable) middle and ``cortex-documenter``. A Session
is opened automatically when a spec is persisted and closed when the user
runs ``cortex finish-session``.

See ``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §5 for the
full design.
"""

from __future__ import annotations

from cortex.session.errors import (
    InvalidStateTransition,
    NoActiveSession,
    SessionAlreadyExists,
    SessionError,
    SessionNotFound,
    SessionStorageCorrupted,
)
from cortex.session.models import (
    GITLESS_COMMIT_PLACEHOLDER,
    MAX_VERIFICATION_OUTPUT_BYTES,
    Checkpoint,
    CheckpointSource,
    SessionMode,
    SessionRecord,
    SessionStatus,
    Task,
    TaskStatus,
    VerificationHook,
    VerificationHookResult,
)

__all__ = [
    "GITLESS_COMMIT_PLACEHOLDER",
    "MAX_VERIFICATION_OUTPUT_BYTES",
    "Checkpoint",
    "CheckpointSource",
    "InvalidStateTransition",
    "NoActiveSession",
    "SessionAlreadyExists",
    "SessionError",
    "SessionMode",
    "SessionNotFound",
    "SessionRecord",
    "SessionStatus",
    "SessionStorageCorrupted",
    "Task",
    "TaskStatus",
    "VerificationHook",
    "VerificationHookResult",
]
