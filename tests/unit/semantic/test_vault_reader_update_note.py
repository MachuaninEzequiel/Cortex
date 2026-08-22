"""Regression tests: A5 — update_note destroys frontmatter + dead BM25 meta."""

from __future__ import annotations

import json
from pathlib import Path

from cortex.semantic.vault_reader import VaultReader


def _make_reader(tmp_path: Path) -> VaultReader:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    note = vault / "note.md"
    note.write_text(
        "---\n"
        "title: My Note\n"
        "tags: [alpha, beta]\n"
        "custom_key: keep-me\n"
        "---\n"
        "\n"
        "Old body words.\n",
        encoding="utf-8",
    )
    r = VaultReader(str(vault))
    r.sync()
    return r


def test_update_note_preserves_frontmatter(tmp_path: Path) -> None:
    r = _make_reader(tmp_path)
    assert r.update_note("note.md", "Brand new body text.")
    raw = (tmp_path / "vault" / "note.md").read_text(encoding="utf-8")
    assert raw.startswith("---\n")
    assert "title: My Note" in raw
    assert "custom_key: keep-me" in raw
    assert "- alpha" in raw or "alpha" in raw
    assert "Brand new body text." in raw
    assert "Old body words." not in raw


def test_update_note_reindexes_new_body(tmp_path: Path) -> None:
    r = _make_reader(tmp_path)
    r.update_note("note.md", "Unique zebra queryset marker.")
    hits = r.search("zebra", top_k=3, use_embeddings=False)
    assert len(hits) == 1


def test_note_without_frontmatter_untouched(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "plain.md").write_text("Just a plain body.\n", encoding="utf-8")
    r = VaultReader(str(vault))
    r.sync()
    r.update_note("plain.md", "Updated plain body.\n")
    raw = (vault / "plain.md").read_text(encoding="utf-8")
    assert raw == "Updated plain body.\n"


def test_full_document_content_wins(tmp_path: Path) -> None:
    """If the caller passes a complete document (with frontmatter), use it."""
    r = _make_reader(tmp_path)
    full = "---\ntitle: Replaced\ntags: [new]\n---\n\nFresh doc.\n"
    r.update_note("note.md", full)
    raw = (tmp_path / "vault" / "note.md").read_text(encoding="utf-8")
    assert raw == full


def test_index_meta_on_disk_matches_memory(tmp_path: Path) -> None:
    r = _make_reader(tmp_path)
    r.update_note("note.md", "Body after update with words.")
    on_disk = json.loads((tmp_path / "vault" / ".cortex_index.json").read_text())
    assert on_disk["doc_lengths"] == r._doc_lengths
    assert abs(on_disk["avgdl"] - r._avgdl) < 1e-9
    assert on_disk["idf"] == r._idf


def test_load_index_meta_is_gone() -> None:
    """Decision recorded by Fix A5: the dead BM25-meta loader is removed."""
    assert not hasattr(VaultReader, "_load_index_meta")
