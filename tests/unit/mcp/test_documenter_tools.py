"""Tests for the four MCP tools that back the ``/cortex-documenter`` skill.

Phase 09.A+ / May 2026:

* ``cortex_documenter_briefing`` — read-only reconstruction returning JSON
* ``cortex_close_session`` — terminate an OPEN session without re-running
* ``cortex_write_doc`` — generic dispatch over the 11 canonical doc types
* ``cortex_self_review_note`` — pure inspection of a draft body

The tests exercise each handler directly on a fixture server so the
behaviour is decoupled from the MCP transport.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from cortex.mcp.server import CortexMCPServer


@pytest.fixture
def cortex_repo(tmp_path: Path) -> Path:
    """Cortex-aware git repo with seed commit + active session ready."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\n",
        encoding="utf-8",
    )
    (cortex_dir / "vault").mkdir()
    (cortex_dir / "vault" / "specs").mkdir()
    (cortex_dir / "memory").mkdir()
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


def _server_with_session(repo: Path) -> tuple[CortexMCPServer, str]:
    server = CortexMCPServer(project_root=repo)
    server._called_tools.add("cortex_sync_ticket")
    result_text = server._create_spec_text(
        {"title": "doc-test", "goal": "test docs"}
    )
    assert "Specification saved" in result_text
    active = server.memory.get_active_session()
    assert active is not None
    return server, active.session_id


# ---------------------------------------------------------------------------
# cortex_documenter_briefing
# ---------------------------------------------------------------------------


class TestDocumenterBriefing:
    def test_briefing_returns_full_json_payload(self, cortex_repo: Path) -> None:
        server, session_id = _server_with_session(cortex_repo)
        result = server._documenter_briefing_text({})
        payload = json.loads(result)

        # The contract documented in the skill prompt.
        for key in (
            "session_id",
            "spec",
            "diff_text",
            "diff_entries",
            "files_touched",
            "files_verified_by_git",
            "files_declared_only",
            "in_scope_files",
            "out_of_scope_files",
            "unimplemented_files",
            "verification_results",
            "contradictions",
            "suggested_status",
            "suggested_adrs",
            "raw_checkpoints",
            "end_commit",
            "gitless",
        ):
            assert key in payload, f"briefing missing key {key!r}"

        assert payload["session_id"] == session_id
        assert isinstance(payload["spec"], dict)
        assert "title" in payload["spec"]
        assert "files_in_scope" in payload["spec"]

    def test_briefing_does_not_close_session(self, cortex_repo: Path) -> None:
        server, session_id = _server_with_session(cortex_repo)
        server._documenter_briefing_text({})
        # Session must still be OPEN — briefing is read-only.
        record = server.memory.get_session(session_id)
        assert record.status.value == "open"

    def test_briefing_no_active_session_returns_error(
        self, cortex_repo: Path
    ) -> None:
        server = CortexMCPServer(project_root=cortex_repo)
        result = server._documenter_briefing_text({})
        assert result.startswith("❌")


# ---------------------------------------------------------------------------
# cortex_close_session
# ---------------------------------------------------------------------------


class TestCloseSession:
    def test_close_session_terminates_record(self, cortex_repo: Path) -> None:
        server, session_id = _server_with_session(cortex_repo)
        result = server._close_session_text(
            {"status": "closed", "session_note_path": "/tmp/note.md"}
        )
        payload = json.loads(result)
        assert payload["final_status"] == "closed"
        # On Windows ``str(Path("/tmp/note.md"))`` becomes "\\tmp\\note.md";
        # compare via Path for cross-platform parity.
        assert Path(payload["session_note_path"]) == Path("/tmp/note.md")

        record = server.memory.get_session(session_id)
        assert record.status.value == "closed"

    def test_close_with_handoff_records_state(self, cortex_repo: Path) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._close_session_text({"status": "handoff"})
        payload = json.loads(result)
        assert payload["final_status"] == "handoff"

    def test_close_missing_status_returns_error(self, cortex_repo: Path) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._close_session_text({})
        assert result.startswith("❌")
        assert "status" in result

    def test_close_invalid_status_returns_error(self, cortex_repo: Path) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._close_session_text({"status": "open"})  # not terminal
        assert result.startswith("❌")

    def test_close_records_adrs(self, cortex_repo: Path) -> None:
        server, session_id = _server_with_session(cortex_repo)
        result = server._close_session_text(
            {
                "status": "closed",
                "adrs_created": ["/tmp/adr-1.md", "/tmp/adr-2.md"],
            }
        )
        payload = json.loads(result)
        # Cross-platform path comparison.
        assert [Path(p) for p in payload["adrs_created"]] == [
            Path("/tmp/adr-1.md"),
            Path("/tmp/adr-2.md"),
        ]
        record = server.memory.get_session(session_id)
        assert record.adrs_created == [
            Path("/tmp/adr-1.md"),
            Path("/tmp/adr-2.md"),
        ]


# ---------------------------------------------------------------------------
# cortex_write_doc — dispatch across doc types
# ---------------------------------------------------------------------------


class TestWriteDocDispatch:
    def test_session_doc_persists_to_sessions_folder(
        self, cortex_repo: Path
    ) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._write_doc_text(
            {
                "doc_type": "session",
                "payload": {
                    "title": "session-via-skill",
                    "spec_summary": "summary",
                    "session_id": "abc123",
                },
            }
        )
        payload = json.loads(result)
        assert payload["doc_type"] == "session"
        path = Path(payload["path"])
        assert path.is_file()
        assert path.parent.name == "sessions"

    def test_adr_doc_persists_to_decisions_folder(self, cortex_repo: Path) -> None:
        """ADRs live under ``decisions/`` per the canonical routing
        (see cortex.documentation.routing.DOC_TYPE_ROUTING)."""
        server, _ = _server_with_session(cortex_repo)
        result = server._write_doc_text(
            {
                "doc_type": "adr",
                "payload": {
                    "title": "Use ONNX over PyTorch",
                    "context": "We had to pick an embedding runtime.",
                    "decision": "Use chromadb's ONNX runtime.",
                },
            }
        )
        payload = json.loads(result)
        assert payload["doc_type"] == "adr"
        path = Path(payload["path"])
        assert path.is_file()
        # ADRs share the ``decisions/`` folder with regular decisions but
        # use the ``ADR-<n>-<slug>.md`` filename pattern.
        assert path.parent.name == "decisions"
        assert path.name.startswith("ADR-")

    def test_decision_doc_persists_to_decisions_folder(
        self, cortex_repo: Path
    ) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._write_doc_text(
            {
                "doc_type": "decision",
                "payload": {
                    "title": "Cache TTL = 5min",
                    "context": "Need a cache window.",
                    "decision": "5 minutes.",
                },
            }
        )
        payload = json.loads(result)
        assert payload["doc_type"] == "decision"
        path = Path(payload["path"])
        assert path.parent.name == "decisions"
        # Decisions don't use the ``ADR-`` prefix.
        assert not path.name.startswith("ADR-")

    def test_runbook_doc_persists_to_runbooks_folder(
        self, cortex_repo: Path
    ) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._write_doc_text(
            {
                "doc_type": "runbook",
                "payload": {
                    "title": "Deploy backend",
                    "runbook_kind": "deploy",
                    "procedure": ["pull image", "restart service"],
                },
            }
        )
        payload = json.loads(result)
        assert payload["doc_type"] == "runbook"
        assert Path(payload["path"]).parent.name == "runbooks"

    def test_unknown_doc_type_returns_error(self, cortex_repo: Path) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._write_doc_text(
            {"doc_type": "nonsense", "payload": {"title": "x"}}
        )
        assert result.startswith("❌")
        assert "doc_type" in result

    def test_extra_payload_fields_are_dropped_silently(
        self, cortex_repo: Path
    ) -> None:
        """An over-eager LLM that includes fields not on the dataclass
        must NOT cause a crash — extras are dropped at dispatch time."""
        server, _ = _server_with_session(cortex_repo)
        result = server._write_doc_text(
            {
                "doc_type": "decision",
                "payload": {
                    "title": "T",
                    "context": "c",
                    "decision": "d",
                    "imaginary_field": "ignored",
                },
            }
        )
        payload = json.loads(result)
        assert payload["doc_type"] == "decision"


# ---------------------------------------------------------------------------
# cortex_self_review_note
# ---------------------------------------------------------------------------


class TestSelfReviewNote:
    def test_clean_body_returns_passed(self, cortex_repo: Path) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._self_review_note_text(
            {
                "body": "Implementation complete. See [[spec-123]] for context.",
                "verification_hooks_passed": True,
            }
        )
        payload = json.loads(result)
        assert payload["passed"] is True
        assert payload["warnings"] == []

    def test_placeholder_token_triggers_warning(self, cortex_repo: Path) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._self_review_note_text(
            {
                "body": "TODO: add tests later",
                "verification_hooks_passed": True,
            }
        )
        payload = json.loads(result)
        assert payload["passed"] is False
        assert any("todo" in w.lower() for w in payload["warnings"])

    def test_hollow_success_claim_triggers_warning(
        self, cortex_repo: Path
    ) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._self_review_note_text(
            {
                "body": "All tests pass and lint passed.",
                "verification_hooks_passed": False,
            }
        )
        payload = json.loads(result)
        assert payload["passed"] is False
        assert any("hollow" in w.lower() for w in payload["warnings"])

    def test_success_claim_ok_when_hooks_passed(self, cortex_repo: Path) -> None:
        server, _ = _server_with_session(cortex_repo)
        result = server._self_review_note_text(
            {
                "body": "All tests pass.",
                "verification_hooks_passed": True,
            }
        )
        payload = json.loads(result)
        assert payload["passed"] is True
