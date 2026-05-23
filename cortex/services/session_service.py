"""Deprecated alias for :mod:`cortex.services.note_service`.

This module used to host the ``SessionService`` class that creates and
persists *session notes*. As of the Pluggable Middle architecture, the
class was renamed to ``NoteService`` and moved to
``cortex.services.note_service`` to disambiguate from the new Session
primitive at :mod:`cortex.session.service`.

Importing from this module emits a :class:`DeprecationWarning` and re-
exports ``NoteService`` under the legacy name ``SessionService``. New
code should import from ``cortex.services.note_service`` instead.
"""

from __future__ import annotations

import warnings

from cortex.services.note_service import NoteService

warnings.warn(
    "cortex.services.session_service is deprecated; "
    "import NoteService from cortex.services.note_service instead. "
    "This alias will be removed in a future major release.",
    DeprecationWarning,
    stacklevel=2,
)

# Legacy alias — same class object exposed under the old name so that
# ``isinstance`` checks against either name continue to work.
SessionService = NoteService

__all__ = ["SessionService"]
