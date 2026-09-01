"""E2E scenarios: finish behaviour — persistence, no duplicates, safe draft.

Cierre Obra 07 (T5): actualizado a la arquitectura post-recatorización.

Contrato ACTUAL de ``autopilot finish --auto`` (payload JSON):
    {session_id, status (SessionStatus), documented (bool), summary,
     warnings, session_note_path}

Cambios respecto de la versión pre-recatorización (justificación una-por-una):
- ``saved``/``status="documented"`` → hoy ``documented`` (bool) y
  ``status`` es el SessionStatus terminal ("closed").
- ``draft_confidence``/``draft_warnings`` fueron retirados del payload;
  los escenarios que los exigían se retiraron (TestFinishNoData::
  test_safe_draft_no_evidence, TestFinishBlocked ×2: el bloqueo
  AutoCheckpointPolicy sobre ``finish --auto`` no está cableado hoy; la
  capa de policies existe nativa en Rust con gate propio, P12B-5).
- El state file ``.cortex/run/autopilot/sessions/<sid>.json`` ya no existe:
  la ruta física de la nota viaja en el payload.
- La indexación automática post-finish (TestFinishIndexesAutomatically) ya
  no ocurre en este flujo; el sync/search se hace vía ``memory.sync_vault``
  y queda cubierto por los gates unitarios del persister.

La sesión la abre ``SessionService.open`` (fixture ``autopilot_session``):
post-recatorización, ``autopilot start`` ADOPTA la sesión activa, no la crea.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cortex.autopilot.cli import app

runner = CliRunner()


def _json_out(result) -> dict:
    """Extrae el payload JSON (finish emite una línea informativa previa)."""
    out = result.output
    return json.loads(out[out.find("{") :])


class TestFinishPersistsToDisk:
    """Regression: ``finish --auto`` must create the session note on disk.

    Previously ``saved=True`` was reported but no file was written,
    breaking the Cortex contract that finishing a session documents it.
    """

    def test_session_note_file_exists_after_finish_auto(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                autopilot_session,
                "--note",
                "Implemented feature X",
                "--artifact",
                "src/feature_x.py",
                "--verified-claim",
                "Implemented feature X",
                "--json",
            ],
        )

        r3 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                autopilot_session,
                "--auto",
                "--json",
            ],
        )
        assert r3.exit_code == 0, r3.output
        fin = _json_out(r3)
        assert fin["documented"] is True

        # The contract: documented ⇒ a real file in the vault.
        note_path = Path(fin["session_note_path"])
        assert note_path.is_absolute(), note_path
        assert note_path.exists(), f"Session note missing: {note_path}"
        # New-layout fixture places vault under .cortex/vault
        expected_parent = autopilot_workspace / ".cortex" / "vault" / "sessions"
        assert note_path.parent == expected_parent

        content = note_path.read_text(encoding="utf-8")
        assert "session_id:" in content


class TestFinishNoData:
    """Scenario 5 — Finish with no observed data must not invent evidence."""

    def test_no_invented_files_or_tests(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        r2 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                autopilot_session,
                "--auto",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        fin = _json_out(r2)
        assert fin["documented"] is True
        # Anti-alucinación sobre el ARTEFACTO real: la nota generada sin
        # checkpoints observados no debe declarar verificaciones ni toques
        # de archivos que nadie reportó.
        note_text = Path(fin["session_note_path"]).read_text(encoding="utf-8")
        body_lower = note_text.lower()
        assert "tests pass" not in body_lower
        assert "build exitoso" not in body_lower
        assert "linter clean" not in body_lower


class TestFinishDuplicate:
    """Second finish must not duplicate the session note."""

    def test_no_duplicate_session_note(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                autopilot_session,
                "--note",
                "ck1",
                "--json",
            ],
        )

        r2 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                autopilot_session,
                "--auto",
                "--json",
            ],
        )
        fin1 = _json_out(r2)
        assert fin1["documented"] is True

        r3 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                autopilot_session,
                "--auto",
                "--json",
            ],
        )
        # La sesión ya está cerrada: el segundo finish es un no-op honesto
        # (documented=False) y NO genera una segunda nota.
        assert r3.exit_code == 0, r3.output
        fin2 = _json_out(r3)
        assert fin2["documented"] is False
        notes = list((autopilot_workspace / ".cortex" / "vault" / "sessions").glob("*.md"))
        assert len(notes) == 1, f"Notas duplicadas: {notes}"
