from __future__ import annotations

import asyncio
from pathlib import Path

from cortex.mcp.server import CortexMCPServer


class FakeContext:
    def to_prompt_format(self) -> str:
        return "context prompt"


class FakeRetrieval:
    def to_prompt(self) -> str:
        return "historical prompt"


class FakeMemory:
    def __init__(self) -> None:
        self.last_call: dict[str, object] | None = None

    def retrieve(self, query: str, top_k: int = 5) -> FakeRetrieval:
        self.last_call = {
            "retrieve_query": query,
            "retrieve_top_k": top_k,
        }
        return FakeRetrieval()

    def enrich(
        self,
        changed_files: list[str],
        keywords: list[str] | None = None,
        pr_title: str | None = None,
        pr_body: str | None = None,
        pr_labels: list[str] | None = None,
        *,
        top_k: int | None = None,
    ) -> FakeContext:
        self.last_call = {
            "changed_files": changed_files,
            "keywords": keywords,
            "pr_title": pr_title,
        }
        return FakeContext()


def test_enrich_context_derives_keywords_from_query() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    context = server._enrich_context({"query": "auth refresh token flow"})

    assert context.to_prompt_format() == "context prompt"
    assert server.memory.last_call == {
        "changed_files": [],
        "keywords": ["auth", "refresh", "token", "flow"],
        "pr_title": "auth refresh token flow",
    }


def test_enrich_context_preserves_explicit_files_and_keywords() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    server._enrich_context(
        {
            "query": "ignored fallback",
            "changed_files": ["cortex/core.py", "tests/test_core.py"],
            "keywords": ["core", "memory"],
            "pr_title": "Core memory improvements",
        }
    )

    assert server.memory.last_call == {
        "changed_files": ["cortex/core.py", "tests/test_core.py"],
        "keywords": ["core", "memory"],
        "pr_title": "Core memory improvements",
    }


def test_get_task_result_returns_saved_delegate_output() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server._task_results = {
        "cortex-code-explorer": {
            "status": "success",
            "task": "inspect auth flow",
            "message": "found auth entrypoints",
        }
    }

    result = server._get_task_result("cortex-code-explorer")

    assert "Estado: success" in result
    assert "inspect auth flow" in result
    assert "found auth entrypoints" in result


def test_sync_ticket_context_infers_scope_and_combines_historical_context(tmp_path: Path) -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.project_root = tmp_path
    server.memory = FakeMemory()  # type: ignore[assignment]
    (tmp_path / "login.html").write_text("<html></html>", encoding="utf-8")

    result = server._build_sync_ticket_context(
        {"user_request": "Moderniza login.html y quita colores pastel"}
    )

    assert "## Ticket actual" in result
    assert "login.html" in result
    assert "historical prompt" in result
    assert "context prompt" in result


def test_delegate_batch_summarizes_each_subagent(monkeypatch) -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server._task_results = {}

    async def fake_delegate(agent_name: str, task: str, timeout_seconds=None) -> str:
        server._store_task_result(agent_name, "success", f"done: {task}", task)
        return f"done: {task}"

    monkeypatch.setattr(server, "_delegate_task", fake_delegate)

    result = asyncio.run(
        server._delegate_batch(
            [
                {"agent": "cortex-code-explorer", "task": "inspect login flow"},
                {"agent": "cortex-code-planner", "task": "plan login redesign"},
            ]
        )
    )

    assert "Subagente: cortex-code-explorer" in result
    assert "Subagente: cortex-code-planner" in result
    assert "todos los subagentes" in result


def test_delegate_task_reports_missing_opencode(monkeypatch, tmp_path: Path) -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.project_root = tmp_path
    server._task_results = {}
    subagents = tmp_path / ".cortex" / "subagents"
    subagents.mkdir(parents=True)
    (subagents / "cortex-code-explorer.md").write_text("name: cortex-code-explorer", encoding="utf-8")

    monkeypatch.setattr("cortex.mcp.server.shutil.which", lambda _: None)

    result = asyncio.run(server._delegate_task("cortex-code-explorer", "inspect auth flow"))

    assert "opencode" in result
    assert "cortex-code-explorer" in server._task_results
