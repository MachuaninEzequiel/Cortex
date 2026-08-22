"""APIs públicas de SessionService para CLI/TUI (Obra 05 Fase A, tarea 3).

Sustituyen los accesos privados ``service._storage`` / ``storage._file_for``
/ ``storage._active_pointer()`` que hacían ci/review_session, ci/validator
y cli/session_tui.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cortex.session.models import SessionRecord
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

VALID_SHA = "a" * 40


def _service(tmp_path: Path) -> SessionService:
    storage = SessionStorage(sessions_dir=tmp_path / "sessions")
    return SessionService(storage=storage, repo_root=tmp_path)


def _record(session_id: str = "2026-05-16_demo") -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        spec_path=Path("vault/specs/demo.md"),
        spec_summary="demo",
        start_commit=VALID_SHA,
        start_branch="main",
        opened_at=datetime(2026, 5, 16, 10, tzinfo=UTC),
    )


class TestSaveNewRecord:
    def test_persiste_sin_tocar_active_pointer(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        record = _record()
        devuelto = svc.save_new_record(record)

        assert devuelto.exists()
        pointer = tmp_path / "sessions" / "active.txt"
        assert not pointer.exists(), "save_new_record NO debe setear la sesión activa"

    def test_rechaza_duplicados(self, tmp_path: Path) -> None:
        from cortex.session.errors import SessionAlreadyExists

        svc = _service(tmp_path)
        svc.save_new_record(_record())
        with pytest.raises(SessionAlreadyExists):
            svc.save_new_record(_record())


class TestPathsPublicos:
    def test_path_for_devuelve_yaml_canonico(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        ruta = svc.path_for("2026-05-16_demo")
        assert ruta.name == "2026-05-16_demo.yaml"
        assert ruta.parent == tmp_path / "sessions"

    def test_active_pointer_path(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        assert svc.active_pointer_path().name == "active.txt"
