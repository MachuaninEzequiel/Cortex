from __future__ import annotations

from cortex.mcp.server import CortexMCPServer


class FakeRetrievalResult:
    def to_prompt(self) -> str:
        return "retrieval prompt"


class FakeContext:
    def to_prompt_format(self) -> str:
        return "context prompt"


class FakeMemory:
    def retrieve(self, query: str, top_k: int = 5) -> FakeRetrievalResult:
        return FakeRetrievalResult()

    def enrich(
        self,
        changed_files: list[str],
        keywords: list[str] | None = None,
        pr_title: str | None = None,
        *,
        top_k: int | None = None,
    ) -> FakeContext:
        return FakeContext()

    def save_session_note(self, **kwargs: object) -> str:
        return "vault/sessions/test.md"

    def create_spec_note(self, **kwargs: object) -> str:
        return "vault/specs/test.md"

    def import_work_item(self, external_id: str, **kwargs: object) -> str:
        return f"vault/hu/{external_id.lower()}.md"

    def get_work_item_note(self, item_id: str) -> str:
        return f"vault/hu/{item_id.lower()}.md"

    def sync_vault(self) -> int:
        return 3


def test_cortex_context_uses_prompt_format() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._context_text({"query": "Release 2 context", "changed_files": ["cortex/core.py"]})

    assert result == "context prompt"


def test_cortex_save_session_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._save_session_text(
        {
            "title": "Release 2",
            "spec_summary": "Implement orchestrated workflow.",
            "changes_made": ["Added SDDwork"],
        }
    )

    assert result == "Session note saved -> vault/sessions/test.md"


def test_cortex_create_spec_tool_requires_sync() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]
    server._called_tools = set()

    result = server._create_spec_text(
        {
            "title": "Release 2",
            "goal": "Introduce subagent orchestration.",
        }
    )

    assert "VIOLACI" in result


def test_cortex_create_spec_tool_after_sync() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]
    server._called_tools = {"cortex_sync_ticket"}

    result = server._create_spec_text(
        {
            "title": "Release 2",
            "goal": "Introduce subagent orchestration.",
        }
    )

    assert result == "Specification saved -> vault/specs/test.md"


def test_cortex_sync_vault_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    assert server._sync_vault_text() == "Vault synced - 3 documents indexed."


def test_cortex_import_hu_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._import_hu_text({"external_id": "PROJ-123"})

    assert result == "Tracked item imported -> vault/hu/proj-123.md"


def test_cortex_get_hu_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._get_hu_text({"item_id": "PROJ-123"})

    assert result == "Tracked item note -> vault/hu/proj-123.md"
