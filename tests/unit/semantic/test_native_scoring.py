"""Gate G1 — paridad de la ruta nativa Rust (CORTEX_NATIVE=1) vs Python pura.

Regla dura del HANDOFF §TAREA-RUST R5.2: resultado distinto = gate inválido.
Estos tests verifican que la ruta nativa produce los MISMOS BITS que la ruta
Python y que el flag apagado conserva el comportamiento idéntico al histórico.

Los tests saltan limpiamente si ``cortex_core._native`` no está compilado
(``.venv/bin/python -m maturin develop --release -m rust/crates/cortex-py/Cargo.toml``);
el lado Rust puro lo cubre el job cargo del CI.
"""

from __future__ import annotations

import math

import pytest

from cortex.semantic.vault_reader import VaultReader


def _native_available() -> bool:
    try:
        from cortex_core import _native  # noqa: F401
    except ImportError:
        return False
    return True


requires_native = pytest.mark.skipif(
    not _native_available(),
    reason="cortex_core._native no compilado (maturin develop -m rust/crates/cortex-py)",
)


def _cosine_python(a: list[float], b: list[float]) -> float:
    """Réplica exacta de VaultReader._cosine_similarity (referencia)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _topk(reader: VaultReader, queries: list[str], k: int = 5) -> list[tuple[str | None, float]]:
    """Top-k estabilizado: (matched_chunk_id|title, score) por query."""
    out = []
    for q in queries:
        hits = reader.search(q, top_k=k)
        out.extend((h.matched_chunk_id or h.title, h.score) for h in hits)
    return out


# ── flag apagado = comportamiento idéntico al histórico ──────────────────


def test_flag_apagado_no_usa_nativa(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    assert vault_reader._native_scores([0.1, 0.2]) is None


def test_flag_activo_sin_modulo_degrada_con_warning(
    tmp_path, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """CORTEX_NATIVE=1 sin módulo compilado → ruta Python + WARNING (no crash)."""
    import builtins
    import logging

    # El vault necesita contenido: un índice vacío sale por la guardia BM25
    # de search() antes de alcanzar la ruta nativa.
    (tmp_path / "auth.md").write_text(
        "---\ntitle: Auth\n---\n\nLogin token middleware.\n", encoding="utf-8"
    )

    real_import = builtins.__import__

    def _sin_native(name, *args, **kwargs):
        if name.startswith("cortex_core"):
            raise ImportError(f"simulado: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setenv("CORTEX_NATIVE", "1")
    monkeypatch.setattr(builtins, "__import__", _sin_native)
    with patch_embedder():
        reader = VaultReader(vault_path=str(tmp_path))
        reader.sync()
        with caplog.at_level(logging.WARNING):
            hits = reader.search("auth login")
    assert isinstance(hits, list)
    assert any("no está compilado" in r.getMessage() for r in caplog.records)


class patch_embedder:
    """MockEmbedder inline para no depender del fixture en este test."""

    def __enter__(self):
        from unittest.mock import patch as _patch

        from tests.conftest import MockEmbedder

        self.p = _patch(
            "cortex.semantic.vault_reader.Embedder", return_value=MockEmbedder()
        )
        self.p.start()
        return self

    def __exit__(self, *exc):
        self.p.stop()
        return False


# ── paridad bit-a-bit de scores ───────────────────────────────────────────


@requires_native
def test_scores_nativos_son_bit_exactos(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    query_vec = vault_reader._embedder.embed("auth login middleware")
    nativos = vault_reader._native_scores(query_vec)
    assert nativos is not None
    esperados = [_cosine_python(query_vec, v) for v in vault_reader._embeddings.values()]
    # Igualdad ESTRICTA (==), no aproximada: la regla es paridad de bits.
    assert nativos == esperados


@requires_native
def test_topk_identico_con_y_sin_flag(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    queries = ["auth login", "api rest endpoints", "payments stripe", "xyzzy sin match"]
    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    python_topk = _topk(vault_reader, queries)
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    native_topk = _topk(vault_reader, queries)
    assert native_topk == python_topk


@requires_native
def test_binding_dim_parametrica(monkeypatch: pytest.MonkeyPatch) -> None:
    """dim JAMÁS constante: dims arbitrarias pasan con paridad exacta."""
    import random

    from cortex_core import _native

    rng = random.Random(42)
    for dim in (1, 5, 64, 384, 1024):
        q = [rng.uniform(-1, 1) for _ in range(dim)]
        rows = [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(7)]
        import numpy as np

        m = np.asarray(rows, dtype=np.float64)
        scores = _native.cosine_scores(np.asarray(q, dtype=np.float64), m).tolist()
        assert scores == [_cosine_python(q, r) for r in rows], f"dim={dim}"


# ── invalidación del caché de matriz ─────────────────────────────────────


@requires_native
def test_matriz_empacada_se_invalida_al_mutar_indice(
    vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un doc creado tras empacar debe aparecer en la próxima búsqueda."""
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    vault_reader.search("auth login")  # fuerza empacado inicial
    assert vault_reader._native_matrix is not None

    vault_reader.create_note("Quantum Widget", "quantum widget flux capacitor único.")

    # La mutación (create_note → index_file) debió invalidar la matriz...
    # pero el re-empacado lazy usa shape como sanity-check: forzamos verificación
    # real comprobando que el nuevo doc ES recuperable (si el caché estuviera
    # stale, el doc no existiría en la matriz vieja y no podría salir top-1).
    hits = vault_reader.search("quantum widget flux capacitor")
    assert hits, "la búsqueda nativa no devolvió resultados"
    assert any("Quantum Widget" in h.title for h in hits[:1]), (
        "el doc nuevo no aparece top-1: caché de matriz stale"
    )


@requires_native
def test_segunda_query_reusa_matriz_empacada(vault_reader: VaultReader, monkeypatch: pytest.MonkeyPatch) -> None:
    """El empacado ocurre UNA vez por estado de índice (regla batch/gruesa)."""
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    vault_reader.search("auth")  # primer empacado
    primera = vault_reader._native_matrix
    assert primera is not None
    vault_reader.search("payments")
    assert vault_reader._native_matrix is primera  # misma instancia = sin re-empacado
