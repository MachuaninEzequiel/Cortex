"""Tests for the ``cortex_session_task_*`` MCP tools (Phase 09.C)."""

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


@pytest.fixture
def server_with_session(cortex_repo: Path) -> tuple[CortexMCPServer, str]:
    server = CortexMCPServer(project_root=cortex_repo)
    record = server.memory.open_session(
        spec_id="2026-05-17_mcp-tasks",
        spec_path=Path("vault/specs/x.md"),
    )
    return server, record.session_id


class TestSessionTaskUpdateAutoCreates:
    def test_create_then_done(
        self, server_with_session: tuple[CortexMCPServer, str]
    ) -> None:
        server, session_id = server_with_session
        # First call: create the task (description supplied).
        create_resp = server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T1",
                "status": "pending",
                "description": "explore auth module",
            }
        )
        assert "status" in create_resp
        # Second call: mark done.
        done_resp = server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T1",
                "status": "done",
            }
        )
        payload = json.loads(done_resp)
        assert payload["task_id"] == "T1"
        assert payload["status"] == "done"

    def test_update_unknown_without_description_fails(
        self, server_with_session: tuple[CortexMCPServer, str]
    ) -> None:
        server, session_id = server_with_session
        resp = server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T99",
                "status": "done",
            }
        )
        assert resp.startswith("❌")
        assert "description" in resp


class TestSessionTaskList:
    def test_lists_after_creation(
        self, server_with_session: tuple[CortexMCPServer, str]
    ) -> None:
        server, session_id = server_with_session
        server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T1",
                "status": "pending",
                "description": "a",
            }
        )
        server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T2",
                "status": "pending",
                "description": "b",
            }
        )
        resp = server._session_task_list_text(  # noqa: SLF001
            {"session_id": session_id}
        )
        payload = json.loads(resp)
        assert {t["id"] for t in payload} == {"T1", "T2"}

    def test_filters_by_status(
        self, server_with_session: tuple[CortexMCPServer, str]
    ) -> None:
        server, session_id = server_with_session
        server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T1",
                "status": "pending",
                "description": "a",
            }
        )
        server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T2",
                "status": "pending",
                "description": "b",
            }
        )
        server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "T1",
                "status": "done",
            }
        )
        done_resp = server._session_task_list_text(  # noqa: SLF001
            {"session_id": session_id, "status": "done"}
        )
        assert [t["id"] for t in json.loads(done_resp)] == ["T1"]

    def test_missing_task_id_rejected(
        self, server_with_session: tuple[CortexMCPServer, str]
    ) -> None:
        server, session_id = server_with_session
        resp = server._session_task_update_text(  # noqa: SLF001
            {
                "session_id": session_id,
                "task_id": "",
                "status": "done",
            }
        )
        assert resp.startswith("❌")
