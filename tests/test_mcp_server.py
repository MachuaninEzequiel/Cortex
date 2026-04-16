from __future__ import annotations


class FakeRetrievalResult:
    def to_prompt(self) -> str:
        return "retrieval prompt"


class FakeContext:
    def to_prompt_format(self) -> str:
        return "context prompt"


class FakeMemory:
    def retrieve(self, query: str, top_k: int = 5) -> FakeRetrievalResult:
        return FakeRetrievalResult()

    def enrich(self, changed_files: list[str], pr_title: str | None = None) -> FakeContext:
        return FakeContext()

    def save_session_note(self, **kwargs):
        return "vault/sessions/test.md"

    def create_spec_note(self, **kwargs):
        return "vault/specs/test.md"

    def sync_vault(self) -> int:
        return 3


def test_cortex_context_uses_prompt_format(monkeypatch) -> None:
    import cortex.mcp_server as mcp_server

    monkeypatch.setattr(mcp_server, "_memory", FakeMemory())
    result = mcp_server.cortex_context(["cortex/core.py"], pr_title="Release 2")
    assert result == "context prompt"


def test_cortex_save_session_tool(monkeypatch) -> None:
    import cortex.mcp_server as mcp_server

    monkeypatch.setattr(mcp_server, "_memory", FakeMemory())
    result = mcp_server.cortex_save_session(
        title="Release 2",
        spec_summary="Implement orchestrated workflow.",
        changes_made=["Added SDDwork"],
    )
    assert "Session persisted in Cortex" in result


def test_cortex_create_spec_tool(monkeypatch) -> None:
    import cortex.mcp_server as mcp_server

    monkeypatch.setattr(mcp_server, "_memory", FakeMemory())
    result = mcp_server.cortex_create_spec(
        title="Release 2",
        goal="Introduce subagent orchestration.",
    )
    assert "Specification persisted in Cortex" in result
