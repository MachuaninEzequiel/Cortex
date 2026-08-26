"""E2E scenarios: basic Autopilot flows (question, fast-code, docs-only, deep-track, cleanup).

These tests exercise the real CLI deterministically using ``CliRunner``.
No external agents, no network, no token consumption.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cortex.autopilot.cli import app

runner = CliRunner()


def _json_out(result) -> dict:
    """Extrae el payload JSON (algunos comandos anteponen líneas informativas)."""
    out = result.output
    return json.loads(out[out.find("{") :])


class TestQuestionOnly:
    """Scenario 1 — Simple question: no heavy retrieval, zero budget."""

    def test_detects_question_only(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        # Post-recatorización: la sesión la abre SessionService (fixture);
        # `autopilot start` adopta la activa.
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        assert r1.exit_code == 0, r1.output
        sid = json.loads(r1.output)["session_id"]
        assert sid == autopilot_session

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--request",
                "What is the auth flow?",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        data = json.loads(r2.output)
        assert data["task_type"] == "question-only"
        # (can_proceed retirado del payload: la decisión hoy vive en policies,
        # no en preflight que es un dry-run stateless.)

    def test_no_embeddings_budget(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]
        assert sid == autopilot_session

        runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--request",
                "How do I reset my password?",
                "--json",
            ],
        )
        # finish auto — question-only does not trigger embeddings
        r3 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        assert r3.exit_code == 0, r3.output
        fin = _json_out(r3)
        # Budget profile question_only => no context injected by default path,
        # but finish still documents because policies allow it.
        assert fin["documented"] is True
        # (Assert `not vault/specs` retirado: contrato viejo donde `start`
        # creaba sesiones sin spec; hoy toda sesión nace de un spec — el
        # fixture crea 2026-08-25_demo.md.)


class TestFastCode:
    """Scenario 2 — Simple change: Fast Track, session draft on finish.

    Known limitation (documented in evals.md):
    ``finish --auto`` sets ``session_note_path`` but does NOT write a physical
    file to vault. Only the path is recorded in state.
    """

    def test_fast_track_draft_on_finish(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]
        assert sid == autopilot_session

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--request",
                "Implement user profile page",
                "--file",
                "profiles.py",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        pre = _json_out(r2)
        assert pre["task_type"] == "fast-code"

        r3 = runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(autopilot_workspace),
                "--note",
                "Fixed login validation",
                "--artifact",
                "login.py",
                "--verified-claim",
                "Fixed login validation",
                "--json",
            ],
        )
        assert r3.exit_code == 0, r3.output

        r4 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        assert r4.exit_code == 0, r4.output
        fin = _json_out(r4)
        assert fin["documented"] is True
        assert fin["status"] == "closed"

        # The contract: documented implies the session note exists on disk
        # (hoy la ruta viaja en el propio payload; el state file fue retirado).
        assert fin["session_note_path"] is not None
        note_physical = Path(fin["session_note_path"])
        assert note_physical.is_absolute(), note_physical
        assert note_physical.exists(), (
            f"Session note must be persisted under vault/sessions/: {note_physical}"
        )


class TestDocsOnly:
    """Scenario 3 — Docs-only: low budget, docs-only profile."""

    def test_docs_only_profile(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]
        assert sid == autopilot_session

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--request",
                "Document the new API endpoints in README.md",
                "--file",
                "README.md",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        pre = _json_out(r2)
        assert pre["task_type"] == "docs-only"

        # finish auto — docs-only should produce a draft with low complexity
        r3 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        assert r3.exit_code == 0, r3.output
        fin = _json_out(r3)
        assert fin["documented"] is True


class TestDeepTrack:
    """Scenario 4 — Complex task: Deep Track suggestion, delegation stub."""

    def test_deep_track_suggestion(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]
        assert sid == autopilot_session

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--request",
                "Migrate legacy payment modules",
                "--file",
                "module1.py",
                "--file",
                "module2.py",
                "--file",
                "module3.py",
                "--file",
                "module4.py",
                "--file",
                "module5.py",
                "--file",
                "module6.py",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        pre = _json_out(r2)
        # LargeRefactorDetector triggers deep-code when >5 files
        assert pre["task_type"] == "deep-code"
        # La razón del deep track hoy viaja en el payload de preflight
        # (el StateStore fue retirado en la recatorización).
        assert pre.get("suggested_complexity") == "deep"
        assert len(pre.get("reason", "")) > 0

    def test_cleanup_older_than_expects_integer(self, autopilot_workspace: Path) -> None:
        """CLI ``cleanup --older-than`` expects an integer (days), not ``30d``."""
        r1 = runner.invoke(
            app,
            [
                "cleanup",
                "--project-root",
                str(autopilot_workspace),
                "--older-than",
                "30d",
                "--json",
            ],
        )
        # Typer will reject "30d" because the option expects an int
        assert r1.exit_code != 0
