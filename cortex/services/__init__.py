"""
cortex.services
---------------
Domain service layer for Cortex.

This package contains the business-logic services extracted from
the AgentMemory orchestrator. Each service has a single, clear
responsibility (SRP).

Services
--------
- ``SpecService`` → Create and persist implementation specifications.
- ``NoteService`` → Create and persist session notes (vault Markdown).
- ``PRService``   → Store PR context and generate fallback documentation.

The legacy name ``SessionService`` is kept as a deprecated alias of
``NoteService``; new code should not use it. The Session *primitive*
(open / checkpoint / close lifecycle) lives in :mod:`cortex.session`.

Usage
-----
    from cortex.services import SpecService, NoteService, PRService
"""

from cortex.services.note_service import NoteService
from cortex.services.pr_service import PRService
from cortex.services.spec_service import SpecCreationResult, SpecService

# Backward-compatible alias for callers that still reference the old name.
# Importing the legacy module path also continues to work (with a
# DeprecationWarning) — see ``cortex.services.session_service``.
SessionService = NoteService

__all__ = [
    "NoteService",
    "PRService",
    "SessionService",  # deprecated alias for NoteService
    "SpecCreationResult",
    "SpecService",
]
