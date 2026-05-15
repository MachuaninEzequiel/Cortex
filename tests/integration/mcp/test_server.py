from __future__ import annotations

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
    assert server.memory.last_call == {  # type: ignore[attr-defined]
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

    assert server.memory.last_call == {  # type: ignore[attr-defined]
        "changed_files": ["cortex/core.py", "tests/test_core.py"],
        "keywords": ["core", "memory"],
        "pr_title": "Core memory improvements",
    }


# Tests del MCP delegate experimental (cortex_delegate_task /
# cortex_delegate_batch / cortex_get_task_result) ELIMINADOS en Fase 5
# del plan multi-IDE & MCP hardening (2026-05-15). Esos tools del MCP
# server fueron retirados — la delegacion ahora es responsabilidad
# nativa del IDE. Ver `docs/multi-ide-mcp-hardening/FASE-5-REALIZACION.md`.


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


# Tests de _delegate_batch / _delegate_task ELIMINADOS en Fase 5: esos
# metodos privados ya no existen en el MCP server. La delegacion es
# responsabilidad nativa del IDE.
