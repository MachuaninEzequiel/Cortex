"""Tests for the MCP ``cortex_search`` structural-filter dispatch (Item #8)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from cortex.mcp.server import CortexMCPServer


class _FakeRetrievalResult:
    def to_prompt(self) -> str:
        return "[legacy-rrf]"


class _FakeEnrichedContext:
    def to_prompt_format(self) -> str:
        return "[structural-enricher]"


class _FakeMemory:
    def retrieve(self, query: str, top_k: int = 5) -> _FakeRetrievalResult:
        return _FakeRetrievalResult()

    # ContextEnricher needs episodic/semantic stores; expose harmless stubs.
    episodic: Any = None
    semantic: Any = None


def _build_server() -> CortexMCPServer:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = _FakeMemory()  # type: ignore[assignment]
    return server


def test_legacy_path_used_when_no_structural_filters() -> None:
    server = _build_server()
    out = server._search_text_dispatch({"query": "auth"})
    assert out == "[legacy-rrf]"


def test_structural_path_used_with_doc_type_filter() -> None:
    server = _build_server()

    class _FakeEnricher:
        def __init__(self, **kwargs: object) -> None:
            pass

        def enrich(self, work: Any, *, top_k: int, filters: Any) -> _FakeEnrichedContext:
            # The structural path passed the filter through.
            assert filters.doc_types is not None
            return _FakeEnrichedContext()

    with patch("cortex.context_enricher.enricher.ContextEnricher", _FakeEnricher):
        out = server._search_text_dispatch(
            {"query": "auth", "doc_type": ["adr"]}
        )
    assert out == "[structural-enricher]"


def test_structural_path_used_when_scope_is_enterprise() -> None:
    server = _build_server()

    class _FakeEnricher:
        def __init__(self, **kwargs: object) -> None:
            pass

        def enrich(self, work: Any, *, top_k: int, filters: Any) -> _FakeEnrichedContext:
            assert filters.vault_scope == "enterprise"
            return _FakeEnrichedContext()

    with patch("cortex.context_enricher.enricher.ContextEnricher", _FakeEnricher):
        out = server._search_text_dispatch(
            {"query": "auth", "scope": "enterprise"}
        )
    assert out == "[structural-enricher]"


def test_structural_path_returns_error_on_invalid_doc_type() -> None:
    server = _build_server()
    out = server._search_text_dispatch(
        {"query": "auth", "doc_type": ["banana"]}
    )
    assert "invalid filter" in out
    assert "banana" in out
