"""Tests for cortex.semantic.chunker (Fase 07)."""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from cortex.documentation.doc_type import DocType
from cortex.semantic.chunker import Chunk, chunk_document


# ---------------------------------------------------------------------------
# Short docs -> single chunk
# ---------------------------------------------------------------------------


def test_short_doc_returns_single_chunk() -> None:
    chunks = chunk_document(
        title="Short", content="just a few words here",
        doc_type=DocType.ADR, tags=["test"], parent_path="x.md",
        min_words=500,
    )
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "x.md"
    assert chunks[0].section_title == "Short"
    assert chunks[0].section_position == 0


def test_empty_content_returns_single_chunk() -> None:
    chunks = chunk_document(
        title="Empty", content="", doc_type=DocType.ADR, tags=[],
        parent_path="x.md", min_words=10,
    )
    assert len(chunks) == 1
    assert chunks[0].text == ""


def test_whitespace_only_content_returns_single_chunk() -> None:
    chunks = chunk_document(
        title="Whitespace", content="   \n\n   ", doc_type=DocType.ADR,
        tags=[], parent_path="x.md", min_words=10,
    )
    assert len(chunks) == 1


def test_missing_title_falls_back_to_untitled() -> None:
    chunks = chunk_document(
        title="", content="brief body", doc_type=DocType.SPEC, tags=[],
        parent_path="x.md", min_words=500,
    )
    assert chunks[0].section_title == "(untitled)"


# ---------------------------------------------------------------------------
# H2 splitting
# ---------------------------------------------------------------------------


def test_h2_splits_sections() -> None:
    body = (
        "Intro paragraph.\n\n"
        "## Context\n" + ("Context text " * 50) + "\n\n"
        "## Decision\n" + ("Decision text " * 50) + "\n\n"
        "## Consequences\n" + ("Conseq text " * 50)
    )
    chunks = chunk_document(
        title="ADR", content=body, doc_type=DocType.ADR,
        tags=["adr"], parent_path="decisions/ADR-1.md", min_words=50,
    )
    # prefix + 3 sections = 4
    assert len(chunks) == 4
    titles = [c.section_title for c in chunks]
    assert titles == ["(prefix)", "Context", "Decision", "Consequences"]


def test_h2_chunk_ids_unique_and_slugged() -> None:
    body = (
        "## Section A\n" + ("alpha word " * 50) + "\n\n"
        "## Section B\n" + ("beta word " * 50) + "\n\n"
        "## Section C\n" + ("gamma word " * 50)
    )
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.ADR, tags=[],
        parent_path="x.md", min_words=50,
    )
    ids = [c.chunk_id for c in chunks]
    assert len(set(ids)) == len(ids)
    # The header-derived chunk_ids must follow the slug convention.
    section_ids = [cid for cid in ids if "#" in cid]
    assert len(section_ids) >= 3
    for cid in section_ids:
        assert cid.startswith("x.md#h2-")


def test_no_h2_returns_single_chunk_even_when_long() -> None:
    body = "Plain text no headers " * 200
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.SPEC, tags=[],
        parent_path="x.md", min_words=50,
    )
    assert len(chunks) == 1


def test_prefix_appears_only_when_text_before_first_header() -> None:
    body = "## First\n" + ("body " * 200)
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.ADR, tags=[],
        parent_path="x.md", min_words=50,
    )
    # No prefix: 1 section only.
    assert [c.section_title for c in chunks] == ["First"]


# ---------------------------------------------------------------------------
# H3 boundary
# ---------------------------------------------------------------------------


def test_h3_boundary_includes_h2_and_h3() -> None:
    body = (
        "## H2 section\nBody " * 100 + "\n\n"
        "### H3 nested\nBody " * 100 + "\n\n"
        "## H2 second\nBody " * 100
    )
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.ADR, tags=[],
        parent_path="x.md", min_words=50, boundary="h3",
    )
    # The combined regex catches both header levels.
    titles = [c.section_title for c in chunks]
    assert any("H3" in t for t in titles)


# ---------------------------------------------------------------------------
# Paragraph boundary
# ---------------------------------------------------------------------------


def test_paragraph_boundary_splits_on_blank_lines() -> None:
    body = "first paragraph " * 30 + "\n\n" + "second paragraph " * 30 + "\n\n" + "third paragraph " * 30
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.SPEC, tags=[],
        parent_path="x.md", min_words=10, boundary="paragraph",
    )
    assert len(chunks) == 3
    assert all(c.section_title.startswith("paragraph-") for c in chunks)


def test_paragraph_boundary_empty_content_returns_single() -> None:
    chunks = chunk_document(
        title="T", content="\n\n   \n\n", doc_type=DocType.SPEC, tags=[],
        parent_path="x.md", min_words=10, boundary="paragraph",
    )
    assert len(chunks) == 1


def test_paragraph_boundary_with_overlap_carries_tail() -> None:
    body = (
        " ".join(f"word{i}" for i in range(50)) + "\n\n"
        + " ".join(f"other{i}" for i in range(50))
    )
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.SPEC, tags=[],
        parent_path="x.md", min_words=10, boundary="paragraph",
        overlap_words=3,
    )
    assert len(chunks) == 2
    # Tail of the first paragraph should be prepended to the second.
    second = chunks[1].text
    assert "word47" in second or "word48" in second or "word49" in second


def test_paragraph_boundary_whitespace_paragraphs_filtered() -> None:
    """A document whose ``re.split`` yields no non-empty paragraphs falls
    back to a single chunk."""
    chunks = chunk_document(
        title="T", content="    \n\n   \n\n   ", doc_type=DocType.SPEC,
        tags=[], parent_path="x.md", min_words=0, boundary="paragraph",
    )
    assert len(chunks) == 1


def test_unknown_boundary_raises() -> None:
    with pytest.raises(ValueError, match="boundary"):
        chunk_document(
            title="T", content="a b c " * 200, doc_type=DocType.SPEC,
            tags=[], parent_path="x.md", min_words=10, boundary="weird",
        )


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------


def test_overlap_carries_tail_into_next_chunk() -> None:
    body = "## A\n" + " ".join(f"word{i}" for i in range(100)) + "\n\n## B\nbeta " * 30
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.ADR, tags=[],
        parent_path="x.md", min_words=10, overlap_words=5,
    )
    section_b = next(c for c in chunks if c.section_title == "B")
    # Last 5 words of section A should be prepended.
    assert "word95" in section_b.text or "word96" in section_b.text


def test_overlap_zero_no_carry() -> None:
    body = "## A\n" + ("alpha " * 30) + "\n\n## B\n" + ("beta " * 30)
    chunks = chunk_document(
        title="T", content=body, doc_type=DocType.ADR, tags=[],
        parent_path="x.md", min_words=10, overlap_words=0,
    )
    section_b = next(c for c in chunks if c.section_title == "B")
    assert "alpha" not in section_b.text


# ---------------------------------------------------------------------------
# Embedding text
# ---------------------------------------------------------------------------


def test_embedding_text_includes_doc_type_and_tags() -> None:
    chunks = chunk_document(
        title="T", content="body content", doc_type=DocType.RUNBOOK,
        tags=["deploy", "auth"], parent_path="x.md", min_words=500,
    )
    et = chunks[0].embedding_text
    assert "runbook" in et
    assert "deploy" in et
    assert "auth" in et
    assert "body content" in et


def test_embedding_text_handles_missing_section_title() -> None:
    """A chunk with empty section_title still produces a usable embedding text."""
    chunk = Chunk(
        parent_path="x.md", chunk_id="x.md", section_title="",
        section_position=0, text="body", doc_type=DocType.SPEC, tags=(),
    )
    assert "body" in chunk.embedding_text


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


def test_chunk_word_count_property() -> None:
    c = Chunk(
        parent_path="x.md", chunk_id="x.md", section_title="t",
        section_position=0, text="one two three four", doc_type=DocType.SPEC, tags=(),
    )
    assert c.word_count == 4


def test_chunk_word_count_empty_text() -> None:
    c = Chunk(
        parent_path="x.md", chunk_id="x.md", section_title="t",
        section_position=0, text="", doc_type=DocType.SPEC, tags=(),
    )
    assert c.word_count == 0


@given(content=st.text(min_size=0, max_size=2000))
def test_chunk_document_always_returns_at_least_one_chunk(content: str) -> None:
    chunks = chunk_document(
        title="T", content=content, doc_type=DocType.SPEC, tags=[],
        parent_path="x.md", min_words=50,
    )
    assert len(chunks) >= 1
