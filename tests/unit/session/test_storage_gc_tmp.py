"""GC de tmp files huérfanos en session/storage (deuda V12, Obra 01 P8).

Un crash entre ``open(tmp)`` y ``os.replace`` deja un ``<id>.yaml.tmp``
huérfano para siempre. Regla: los tmp con más de 1 hora se eliminan al
guardar; los recientes se conservan (puede haber un writer activo).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from cortex.session.models import SessionRecord
from cortex.session.storage import SessionStorage


def _storage(tmp_path: Path) -> SessionStorage:
    return SessionStorage(sessions_dir=tmp_path)


def _record(session_id: str) -> SessionRecord:
    from datetime import UTC, datetime

    return SessionRecord(
        session_id=session_id,
        spec_path=Path("vault/specs/x.md"),
        spec_summary="x",
        start_commit="a" * 40,
        start_branch="main",
        opened_at=datetime.now(UTC),
    )


class TestGcTmpHuerfanos:
    def test_tmp_viejo_se_elimina_al_guardar(self, tmp_path: Path) -> None:
        st = _storage(tmp_path)
        viejo = tmp_path / "2026-08-01_viejo.yaml.tmp"
        viejo.write_text("basura", encoding="utf-8")
        # retroceder mtime 2 horas
        antiguo = time.time() - 2 * 3600
        os.utime(viejo, (antiguo, antiguo))

        st.save(_record("2026-08-23_nuevo"))

        assert not viejo.exists()

    def test_tmp_reciente_se_conserva(self, tmp_path: Path) -> None:
        st = _storage(tmp_path)
        reciente = tmp_path / "2026-08-01_activo.yaml.tmp"
        reciente.write_text("escritura en curso", encoding="utf-8")

        st.save(_record("2026-08-23_nuevo"))

        assert reciente.exists()

    def test_los_finales_nunca_se_tocan(self, tmp_path: Path) -> None:
        st = _storage(tmp_path)
        final = st.save(_record("2026-08-01_final"))
        # backdate del FINAL: no debe ser borrado por el GC
        antiguo = time.time() - 2 * 3600
        os.utime(final, (antiguo, antiguo))

        st.save(_record("2026-08-23_otro"))

        assert final.exists()
