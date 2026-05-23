"""Tests for the ``write_design_note_canonical`` MCP tool (Phase 09.B).

Exercises the JSON-RPC layer end to end: the tool builds a
:class:`DesignDocData`, invokes the canonical writer with the discovered
workspace vault path, and returns a JSON payload pointing at the
persisted file. Failures (missing required fields) surface as ``❌ …``
text errors so the LLM can recover.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from cortex.mcp.server import CortexMCPServer


@pytest.fixture
def cortex_repo(tmp_path: Path) -> Path:
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


def _server(repo: Path) -> CortexMCPServer:
    return CortexMCPServer(project_root=repo)


class TestWriteDesignNoteCanonical:
    def test_persists_design_doc_to_vault_designs(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        payload_text = server._write_design_note_text(  # noqa: SLF001 — test of internal
            {
                "title": "Refactor auth",
                "session_id": "2026-05-17_refactor-auth",
                "spec_path": "vault/specs/2026-05-17_refactor-auth.md",
                "architecture_decision": "Move logic into middleware.",
                "data_model_changes": ["Add token rotation column"],
                "api_contracts": ["def refresh(token: str) -> Token"],
                "test_plan": ["tests/auth/test_refresh.py"],
            }
        )
        payload = json.loads(payload_text)
        path = Path(payload["path"])
        assert path.is_file()
        assert path.parent.name == "designs"
        body = path.read_text(encoding="utf-8")
        assert "Move logic into middleware." in body
        assert "Add token rotation column" in body

    def test_missing_session_id_returns_error(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        result = server._write_design_note_text(  # noqa: SLF001
            {
                "title": "x",
                "session_id": "",
                "spec_path": "vault/specs/x.md",
            }
        )
        assert result.startswith("❌")
        assert "session_id" in result

    def test_missing_spec_path_returns_error(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        result = server._write_design_note_text(  # noqa: SLF001
            {
                "title": "x",
                "session_id": "2026-05-17_x",
                "spec_path": "",
            }
        )
        assert result.startswith("❌")
        assert "spec_path" in result

    def test_default_title_when_omitted(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        payload_text = server._write_design_note_text(  # noqa: SLF001
            {
                "session_id": "2026-05-17_default-title",
                "spec_path": "vault/specs/x.md",
            }
        )
        payload = json.loads(payload_text)
        body = Path(payload["path"]).read_text(encoding="utf-8")
        assert "Design for 2026-05-17_default-title" in body
