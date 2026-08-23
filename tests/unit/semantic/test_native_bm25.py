"""Gate G3 — paridad de la ruta BM25 nativa Rust vs Python pura.

El scoring Python cuenta SUBSTRINGS sobre el texto bajado; la réplica Rust es
bit-exacta (mismo orden de operaciones f64). Salta sin módulo compilado.
"""

from __future__ import annotations

import pytest

from cortex.semantic.vault_reader import VaultReader

from .test_native_scoring import requires_native


def _topk_bm25(reader: VaultReader, queries: list[str], k: int = 5):
    out = []
    for q in queries:
        hits = reader.search(q, top_k=k, use_embeddings=False)
        out.append([(h.path, h.score) for h in hits])
    return out


@requires_native
def test_bm25_scores_bit_exactos(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    terms = "auth login".lower().split()
    nativos = vault_reader._native_bm25_scores(terms, 1.5, 0.75)
    assert nativos is not None
    # Réplica EXACTA del loop Python de _bm25_search.
    idf = vault_reader._idf
    avgdl = vault_reader._avgdl
    esperados = []
    for doc in vault_reader._index.values():
        text = f"{doc.title} {doc.content}".lower()
        score = 0.0
        for term in terms:
            i = idf.get(term, 0.0)
            if i == 0:
                continue
            tf = text.count(term)
            num = tf * (1.5 + 1)
            den = tf + 1.5 * (1 - 0.75 + 0.75 * vault_reader._doc_lengths.get(
                next(p for p, dd in vault_reader._index.items() if dd is doc), 1
            ) / avgdl)
            score += i * (num / den)
        esperados.append(score)
    assert nativos == esperados


@requires_native
def test_bm25_topk_identico_con_y_sin_flag(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    queries = ["auth login", "api rest", "payments", "xyzzy", "token middleware"]
    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    py = _topk_bm25(vault_reader, queries)
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    nat = _topk_bm25(vault_reader, queries)
    assert nat == py


@requires_native
def test_rebuild_despues_de_mutacion(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    """Crear una nota tras la primera query debe reflejarse en la siguiente."""
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    vault_reader.search("auth login", use_embeddings=False)  # construye índice nativo
    assert vault_reader._native_bm25_index is not None

    vault_reader.create_note("Quantum Widget", "quantum widget flux capacitor único.")
    assert vault_reader._native_bm25_dirty, "la mutación debe ensuciar el caché"

    hits = vault_reader.search("quantum widget flux capacitor", use_embeddings=False)
    assert hits and "Quantum Widget" in hits[0].title, "el rebuild no tomó el doc nuevo"


def test_flag_apagado_ruta_python(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    assert vault_reader._native_bm25_scores(["auth"], 1.5, 0.75) is None
