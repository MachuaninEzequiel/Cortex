"""Tests for VaultReader integrated with the chunker (Fase 07)."""

from __future__ import annotations

from pathlib import Path

from cortex.semantic.vault_reader import VaultReader
from cortex.semantic.vector_cache import VectorCache


def _write_long_adr(vault: Path, name: str = "ADR-007-auth") -> Path:
    """Create a multi-section ADR with enough words to trigger chunking."""
    body = (
        "## Context\n" + ("auth token expiry " * 80) + "\n\n"
        "## Decision\n" + ("adopt OAuth 2.0 with JWT " * 80) + "\n\n"
        "## Consequences\n" + ("servers need new validation library " * 80)
    )
    (vault / "decisions").mkdir(parents=True, exist_ok=True)
    path = vault / "decisions" / f"{name}.md"
    path.write_text(
        f"---\ntitle: {name}\n---\n{body}", encoding="utf-8",
    )
    return path


def _write_short_session(vault: Path) -> Path:
    (vault / "sessions").mkdir(parents=True, exist_ok=True)
    path = vault / "sessions" / "2026-05-14_brief.md"
    path.write_text(
        "---\ntitle: brief\n---\nShort recap of what we did today.",
        encoding="utf-8",
    )
    return path


def test_sync_chunks_long_adr(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_long_adr(vault)
    _write_short_session(vault)

    r = VaultReader(str(vault))
    r.sync()
    # 1 doc has 4 chunks (prefix omitted, 3 sections), 1 doc has 1 chunk.
    assert len(r._index) == 2
    assert len(r._chunks) >= 4


def test_session_not_chunked(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_short_session(vault)
    r = VaultReader(str(vault))
    r.sync()
    # SESSION DocType has chunking_enabled=False in the routing table.
    sessions_chunks = [c for c in r._chunks.values() if "sessions" in c.parent_path]
    assert len(sessions_chunks) == 1


def test_search_returns_matched_chunk_info(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_long_adr(vault)
    r = VaultReader(str(vault))
    r.sync()

    results = r.search("OAuth JWT", top_k=3)
    assert results, "search returned nothing"
    top = results[0]
    assert top.matched_chunk_id is not None
    assert top.matched_section_title in {"Context", "Decision", "Consequences"}
    assert "h2-" in top.matched_chunk_id


def test_score_is_max_of_chunk_scores(tmp_path: Path) -> None:
    """The aggregated doc score equals the score of its best chunk."""
    vault = tmp_path / "vault"
    _write_long_adr(vault)
    r = VaultReader(str(vault))
    r.sync()

    results = r.search("authentication token", top_k=1)
    assert results
    doc_score = results[0].score
    # Recompute scores manually and confirm doc_score is the max chunk score.
    query_vec = r._embedder.embed("authentication token")
    chunk_scores = []
    for cid, vec in r._embeddings.items():
        ch = r._chunks.get(cid)
        if ch and ch.parent_path == "decisions\\ADR-007-auth.md" or (
            ch and ch.parent_path == "decisions/ADR-007-auth.md"
        ):
            chunk_scores.append(r._cosine_similarity(query_vec, vec))
    if chunk_scores:
        assert abs(doc_score - max(chunk_scores)) < 1e-5


def test_modify_doc_purges_old_chunks(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    path = _write_long_adr(vault)
    r = VaultReader(str(vault))
    r.sync()
    # Discover the parent_path used internally (Windows-vs-POSIX agnostic).
    parent_path = next(iter(r._chunks.values())).parent_path
    initial_count = sum(
        1 for c in r._chunks.values() if c.parent_path == parent_path
    )
    assert initial_count >= 3  # Context, Decision, Consequences

    # Rewrite the file with very different structure (no H2 sections, short).
    path.write_text(
        "---\ntitle: ADR-007-auth\n---\nshort body no sections",
        encoding="utf-8",
    )
    r.index_file(parent_path)
    new_count = sum(
        1 for c in r._chunks.values() if c.parent_path == parent_path
    )
    # Old multi-section chunks are gone, replaced by a single chunk.
    assert new_count == 1
    assert new_count < initial_count


def test_chunking_with_cache(tmp_path: Path) -> None:
    """Re-syncing a vault with the same cache hits on every chunk."""
    vault = tmp_path / "vault"
    _write_long_adr(vault)
    cache = VectorCache(tmp_path / ".cortex" / "vectors")

    r1 = VaultReader(str(vault), vector_cache=cache)
    r1.sync()
    misses_after_cold = cache.stats().miss_count
    hits_after_cold = cache.stats().hit_count

    r2 = VaultReader(str(vault), vector_cache=cache)
    r2.sync()
    s2 = cache.stats()
    assert s2.miss_count == misses_after_cold  # no new misses
    assert s2.hit_count > hits_after_cold


def test_resolve_doc_type_handles_unknown_folder(tmp_path: Path) -> None:
    """Notes in unexpected folders fall back to a single chunk."""
    vault = tmp_path / "vault"
    (vault / "weird").mkdir(parents=True)
    (vault / "weird" / "x.md").write_text(
        "---\ntitle: x\n---\nbody " * 200, encoding="utf-8",
    )
    r = VaultReader(str(vault))
    r.sync()
    # No crash, single chunk per doc.
    weird_chunks = [c for c in r._chunks.values() if "weird" in c.parent_path]
    assert len(weird_chunks) == 1
