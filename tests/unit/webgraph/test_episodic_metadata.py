"""Tests for episodic doc_type metadata + legend (Item #6 deuda residual)."""

from __future__ import annotations

from datetime import UTC, datetime

from cortex.models import MemoryEntry
from cortex.webgraph.episodic_source import EpisodicSource
from cortex.webgraph.style import build_legend, style_for_doc_type


class _FakeStore:
    def __init__(self, entries: list[MemoryEntry]) -> None:
        self._entries = entries
        self.embedder = None

    def list_entries(self) -> list[MemoryEntry]:
        return list(self._entries)


class _FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [0.1, 0.2]


def _make_source(entries: list[MemoryEntry]) -> EpisodicSource:
    source = EpisodicSource.__new__(EpisodicSource)
    source.store = _FakeStore(entries)  # type: ignore[assignment]
    source.embedder = _FakeEmbedder()  # type: ignore[assignment]
    return source


def test_episodic_record_carries_doc_type_episodic() -> None:
    entry = MemoryEntry(
        id="mem_1",
        content="Session content",
        memory_type="session",
        tags=["session"],
        files=[],
        timestamp=datetime.now(UTC),
        metadata={},
    )
    source = _make_source([entry])
    records = source.load_records(include_embeddings=False)
    assert records[0].metadata["doc_type"] == "episodic"


def test_existing_doc_type_in_metadata_wins_over_default() -> None:
    entry = MemoryEntry(
        id="mem_2",
        content="Promoted ADR",
        memory_type="general",
        tags=[],
        files=[],
        timestamp=datetime.now(UTC),
        metadata={"doc_type": "adr"},
    )
    source = _make_source([entry])
    records = source.load_records(include_embeddings=False)
    assert records[0].metadata["doc_type"] == "adr"


def test_style_for_doc_type_resolves_episodic() -> None:
    style = style_for_doc_type("episodic")
    assert style.color == "#9b59b6"
    assert style.shape == "diamond"


def test_legend_includes_episodic_entry() -> None:
    legend = build_legend()
    types = {entry["type"] for entry in legend["doc_types"]}
    assert "episodic" in types
