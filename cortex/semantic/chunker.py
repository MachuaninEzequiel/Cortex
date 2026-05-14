"""cortex.semantic.chunker - Split markdown documents into embedding-sized chunks.

Long notes (e.g. runbooks, postmortems, ADRs > 1000 words) lose information
when embedded as a single vector because the underlying model truncates
inputs past ~512 tokens. Chunking by H2/H3 boundaries preserves recall by
producing one vector per logical section.

The chunker is content-agnostic; it accepts a ``doc_type`` and ``tags`` so
the structural signal can be injected into the embedding text:

    embedding_text = "<doc_type> <tags> <section_title> <text>"

Routing decides whether a document is chunked at all (``chunking_enabled``,
``chunking_min_words``, ``chunking_boundary`` in ``RouteSpec``). The
``VaultReader`` calls this module on every ``index_file`` invocation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from cortex.documentation.common import slugify
from cortex.documentation.doc_type import DocType

# ---------------------------------------------------------------------------
# Constants & regex
# ---------------------------------------------------------------------------

_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_H3_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """One indexable slice of a document.

    For short documents the chunker returns a single ``Chunk`` whose
    ``chunk_id`` equals the parent ``rel_path``. For multi-section
    documents each section is its own chunk and ``chunk_id`` carries the
    boundary level and slugified section title.
    """

    parent_path: str           # ej: "decisions/ADR-007-foo.md"
    chunk_id: str              # ej: "decisions/ADR-007-foo.md#h2-decision"
    section_title: str
    section_position: int      # 0 = (prefix) or single, 1+ = per-section index
    text: str
    doc_type: DocType
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0

    @property
    def embedding_text(self) -> str:
        """Text that should be fed to the embedder.

        Injects ``doc_type``, ``tags`` and ``section_title`` so the
        resulting vector encodes structural signal in addition to body
        content.
        """
        tags_part = " ".join(self.tags) if self.tags else ""
        title_part = self.section_title if self.section_title else ""
        body = self.text or ""
        return " ".join(
            part for part in (self.doc_type.value, tags_part, title_part, body)
            if part
        ).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_document(
    title: str,
    content: str,
    doc_type: DocType,
    tags: Iterable[str],
    *,
    parent_path: str,
    min_words: int = 500,
    boundary: str = "h2",
    overlap_words: int = 0,
) -> list[Chunk]:
    """Split ``content`` into indexable chunks.

    Args:
        title:        Document title (used as section_title for the single-chunk
                      fallback or the prefix chunk).
        content:      Markdown body (no frontmatter).
        doc_type:     DocType of the parent document (informs embedding text).
        tags:         Frontmatter tags (joined into embedding text).
        parent_path:  ``rel_path`` of the parent inside the vault.
        min_words:    Below this threshold the document stays as a single chunk.
        boundary:     ``"h2"`` | ``"h3"`` | ``"paragraph"``.
        overlap_words: Tail of the previous chunk carried into the next one.

    Returns:
        Non-empty list of ``Chunk``. Even an empty document returns a single
        empty-text chunk so the parent stays addressable.
    """
    tags_t = tuple(tags or ())
    safe_title = title or "(untitled)"

    if not content or not content.strip() or _word_count(content) < min_words:
        return [
            _single_chunk(
                content=content or "",
                section_title=safe_title,
                doc_type=doc_type,
                tags=tags_t,
                parent_path=parent_path,
            )
        ]

    if boundary == "h2":
        return _split_with_pattern(
            content, _H2_RE, safe_title, doc_type, tags_t, parent_path, overlap_words
        )
    if boundary == "h3":
        # Combine both h2 and h3 boundaries; sort matches by position.
        return _split_with_pattern(
            content, _combined_h2_h3(), safe_title, doc_type, tags_t,
            parent_path, overlap_words,
        )
    if boundary == "paragraph":
        return _split_paragraphs(
            content, safe_title, doc_type, tags_t, parent_path, overlap_words
        )
    raise ValueError(f"Unknown boundary {boundary!r}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _word_count(text: str) -> int:
    return len(text.split())


def _single_chunk(
    *,
    content: str,
    section_title: str,
    doc_type: DocType,
    tags: tuple[str, ...],
    parent_path: str,
) -> Chunk:
    return Chunk(
        parent_path=parent_path,
        chunk_id=parent_path,
        section_title=section_title,
        section_position=0,
        text=content.strip(),
        doc_type=doc_type,
        tags=tags,
    )


def _make_chunk(
    *,
    text: str,
    section_title: str,
    position: int,
    doc_type: DocType,
    tags: tuple[str, ...],
    parent_path: str,
    boundary_level: str,
) -> Chunk:
    section_slug = slugify(section_title) or "section"
    chunk_id = f"{parent_path}#{boundary_level}-{section_slug}"
    return Chunk(
        parent_path=parent_path,
        chunk_id=chunk_id,
        section_title=section_title,
        section_position=position,
        text=text.strip(),
        doc_type=doc_type,
        tags=tags,
    )


def _split_with_pattern(
    content: str,
    pattern: "re.Pattern[str]",
    fallback_title: str,
    doc_type: DocType,
    tags: tuple[str, ...],
    parent_path: str,
    overlap_words: int,
) -> list[Chunk]:
    matches = list(pattern.finditer(content))
    if not matches:
        return [
            _single_chunk(
                content=content, section_title=fallback_title,
                doc_type=doc_type, tags=tags, parent_path=parent_path,
            )
        ]

    chunks: list[Chunk] = []
    boundary_level = "h2"  # all sections collapse under H2 prefix for chunk_id

    # Prefix (text before the first header).
    prefix_text = content[: matches[0].start()].strip()
    if prefix_text:
        chunks.append(
            _make_chunk(
                text=prefix_text, section_title="(prefix)", position=0,
                doc_type=doc_type, tags=tags, parent_path=parent_path,
                boundary_level=boundary_level,
            )
        )

    # Each section.
    for i, match in enumerate(matches):
        section_title = match.group(1).strip()
        section_start = match.end()
        section_end = matches[i + 1].start() if (i + 1) < len(matches) else len(content)
        section_text = content[section_start:section_end].strip()

        if overlap_words > 0 and chunks:
            previous = chunks[-1].text
            tail = " ".join(previous.split()[-overlap_words:])
            if tail:
                section_text = (tail + " " + section_text).strip()

        chunks.append(
            _make_chunk(
                text=section_text, section_title=section_title,
                position=i + 1, doc_type=doc_type, tags=tags,
                parent_path=parent_path, boundary_level=boundary_level,
            )
        )

    return chunks


def _split_paragraphs(
    content: str,
    fallback_title: str,
    doc_type: DocType,
    tags: tuple[str, ...],
    parent_path: str,
    overlap_words: int,
) -> list[Chunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", content) if p.strip()]
    if not paragraphs:
        return [
            _single_chunk(
                content=content, section_title=fallback_title,
                doc_type=doc_type, tags=tags, parent_path=parent_path,
            )
        ]
    chunks: list[Chunk] = []
    for i, para in enumerate(paragraphs):
        text = para
        if overlap_words > 0 and chunks:
            tail = " ".join(chunks[-1].text.split()[-overlap_words:])
            if tail:
                text = (tail + " " + para).strip()
        chunks.append(
            _make_chunk(
                text=text, section_title=f"paragraph-{i + 1}",
                position=i + 1, doc_type=doc_type, tags=tags,
                parent_path=parent_path, boundary_level="p",
            )
        )
    return chunks


def _combined_h2_h3() -> "re.Pattern[str]":
    """Pattern matching both H2 and H3 headers."""
    return re.compile(r"^(?:##|###)\s+(.+?)\s*$", re.MULTILINE)


__all__ = ["Chunk", "chunk_document"]
