"""Regression tests: A4 — duplicate slugged section titles collide on chunk_id."""

from __future__ import annotations

from cortex.documentation.doc_type import DocType
from cortex.semantic.chunker import chunk_document


def _chunk_two_same_titles(boundary: str = "h2"):
    content = (
        "## Context\n"
        "First context section body with words.\n\n"
        "## Decision\n"
        "Some decision body words here.\n\n"
        "## Context\n"
        "Second context section body, different words.\n"
    )
    return chunk_document(
        title="ADR-001",
        content=content,
        doc_type=DocType.ADR,
        tags=("adr",),
        parent_path="decisions/ADR-001.md",
        min_words=1,
        boundary=boundary,
    )


def test_duplicate_h2_titles_get_distinct_chunk_ids() -> None:
    chunks = _chunk_two_same_titles()
    ids = [c.chunk_id for c in chunks]
    # No silent overwrite: every section keeps its own identity.
    assert len(ids) == len(set(ids))
    context_chunks = [c for c in chunks if c.section_title == "Context"]
    assert len(context_chunks) == 2
    texts = sorted(c.text.split()[0] for c in context_chunks)
    assert texts == ["First", "Second"]


def test_first_occurrence_keeps_stable_id() -> None:
    """No collision -> existing IDs unchanged; collision gets -2 suffix."""
    chunks = _chunk_two_same_titles()
    by_title = {}
    for c in chunks:
        by_title.setdefault(c.section_title, []).append(c.chunk_id)
    assert "decisions/ADR-001.md#h2-context" in by_title["Context"]
    assert "decisions/ADR-001.md#h2-context-2" in by_title["Context"]
    assert "decisions/ADR-001.md#h2-decision" in [c.chunk_id for c in chunks]


def test_duplicate_h3_boundary_titles_distinct() -> None:
    chunks = _chunk_two_same_titles(boundary="h3")
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_duplicate_paragraphs_distinct() -> None:
    content = "Para alpha with several words here.\n\nPara alpha with other words now."
    chunks = chunk_document(
        title="T", content=content, doc_type=DocType.GLOSSARY, tags=(),
        parent_path="notes/t.md", min_words=1, boundary="paragraph",
    )
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
