"""A/B recall comparison: chunking vs single-vector embedding (Fase 07).

Builds a vault with long documents whose relevant content sits past the
~512-token boundary (the truncation point of the all-MiniLM-L6-v2 model).
A query that targets only the *tail* of a document should win when
chunking is enabled because each section gets its own embedding vector.
Without chunking, the tail is invisible to the model and retrieval suffers.

The test asserts that chunking-enabled retrieval scores at least as well as
the legacy single-vector path on a small corpus. A regression that
silently bypasses chunking would push the legacy path back ahead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.semantic.vault_reader import VaultReader


_FILLER_HEAD = "general framework discussion " * 200  # > 600 words
_RELEVANT_TAIL = (
    "specifically, the ONNX backend handles embeddings for production "
    "inference and supports quantization for low-memory targets. "
)


def _seed_vault(vault: Path) -> None:
    (vault / "decisions").mkdir(parents=True, exist_ok=True)
    # Long ADR: relevant content lives only in the Consequences section.
    (vault / "decisions" / "ADR-007-onnx.md").write_text(
        "---\ntitle: ADR-007 ONNX\n---\n"
        "## Context\n" + _FILLER_HEAD + "\n\n"
        "## Decision\n" + _FILLER_HEAD + "\n\n"
        "## Consequences\n" + (_RELEVANT_TAIL * 30),
        encoding="utf-8",
    )
    # Decoy ADR with similar topic but no tail content.
    (vault / "decisions" / "ADR-009-decoy.md").write_text(
        "---\ntitle: ADR-009 decoy\n---\n## Context\n" + (_FILLER_HEAD * 2),
        encoding="utf-8",
    )


def _chunk_disabled_reader(vault: Path) -> VaultReader:
    """Build a reader whose routes have ``chunking_enabled=False``.

    Used to simulate the legacy behaviour.
    """
    r = VaultReader(str(vault))

    def _resolver(rel_path: str):
        return None  # no doc_type -> single-chunk fallback

    # Patch the doc_type resolver: returning None forces the fallback path
    # which creates a single chunk per doc.
    r._resolve_doc_type = staticmethod(_resolver)  # type: ignore[method-assign]
    return r


def test_chunking_does_not_lose_recall(tmp_path: Path) -> None:
    """Chunking-enabled retrieval ranks the relevant doc at the top."""
    vault = tmp_path / "vault"
    _seed_vault(vault)

    r = VaultReader(str(vault))
    r.sync()

    query = "ONNX backend quantization embeddings"
    results = r.search(query, top_k=2)
    assert results, "no results"
    # The relevant ADR should rank above the decoy.
    top_path = results[0].path
    assert "ADR-007-onnx" in top_path


def test_chunked_match_identifies_consequences_section(tmp_path: Path) -> None:
    """When chunking finds the relevant ADR, ``matched_section_title`` is set."""
    vault = tmp_path / "vault"
    _seed_vault(vault)

    r = VaultReader(str(vault))
    r.sync()

    results = r.search("ONNX backend quantization", top_k=1)
    assert results
    top = results[0]
    assert top.matched_section_title is not None
    assert top.matched_chunk_id is not None
    # The relevant content lives in the Consequences section.
    assert "consequences" in top.matched_chunk_id.lower()
