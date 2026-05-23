"""Tests for the legacy ``SessionService`` alias of :class:`NoteService`.

The rename was introduced as part of Phase 00 (Pluggable Middle) — see
``docs/pluggable-middle/fases/00-FOUNDATIONS.md`` task T0.10. The legacy
import path must keep working while emitting a :class:`DeprecationWarning`.
"""

from __future__ import annotations

import importlib
import warnings


def test_importing_legacy_module_emits_deprecation_warning() -> None:
    # Make sure the module is reloaded so the import-time warning fires
    # again in this test even if another test already imported it.
    import cortex.services.session_service as legacy_mod

    importlib.reload(legacy_mod)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(legacy_mod)
    deprecation = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecation, "expected DeprecationWarning on import of session_service"
    assert "note_service" in str(deprecation[0].message)


def test_legacy_alias_is_same_class_as_note_service() -> None:
    from cortex.services.note_service import NoteService
    from cortex.services.session_service import SessionService

    # Exact same class object — not a subclass, not a wrapper.
    assert SessionService is NoteService


def test_services_package_exports_both_names() -> None:
    from cortex import services

    assert services.NoteService is services.SessionService


def test_top_level_cortex_still_exports_session_service() -> None:
    import cortex

    assert cortex.SessionService is cortex.NoteService
