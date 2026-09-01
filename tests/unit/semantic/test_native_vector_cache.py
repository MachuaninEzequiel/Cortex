"""Gate G2 — paridad del store vectorial nativo (schema v3) vs VectorCache v2.

Regla dura R5.2: mismos hits con los mismos fingerprints, dim paramétrica,
fallas ruidosas. Salta limpio si cortex_core._native no está compilado.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from cortex.semantic.vector_cache import VectorCache


def _native_available() -> bool:
    try:
        from cortex_core import _native  # noqa: F401
        from cortex.semantic.native_vector_cache import NativeVectorCache  # noqa: F401
    except ImportError:
        return False
    return True


requires_native = pytest.mark.skipif(
    not _native_available(),
    reason="cortex_core._native no compilado (maturin develop -m rust/crates/cortex-py)",
)


def _fps(n: int, salt: str = "fp") -> list[str]:
    """Fingerprints REALISTAS: mismo algoritmo sha256 que cache_fingerprint."""
    return [hashlib.sha256(f"{salt}-{i}".encode()).hexdigest() for i in range(n)]


@pytest.fixture()
def dataset():
    rng = np.random.default_rng(42)
    return {
        "fps": _fps(50),
        "cids": [f"docs/doc-{i // 5}.md#{i % 5}" for i in range(50)],
        "vecs": rng.standard_normal((50, 384)).astype(np.float32),
    }


@requires_native
def test_mismos_hits_bits_identicos(dataset, tmp_path):
    from cortex.semantic.native_vector_cache import NativeVectorCache

    py = VectorCache(tmp_path / "py", model_name="m", dim=384)
    nat = NativeVectorCache(tmp_path / "nat", model_name="m")
    items = list(zip(dataset["fps"], dataset["cids"], dataset["vecs"]))
    py.batch_put(items)
    nat.batch_put(items)

    for fp, vec_py in zip(dataset["fps"], dataset["vecs"]):
        vec_nat = nat.get(fp)
        assert vec_nat is not None, f"miss inesperado: {fp[:12]}"
        assert np.array_equal(vec_py, vec_nat), f"bits distintos: {fp[:12]}"
    # Misses idénticos también.
    assert nat.get("no-existe" * 8) is None
    assert py.get("no-existe" * 8) is None


@requires_native
def test_dim_parametrica_acepta_cualquier_modelo(tmp_path):
    """La lección de vector_cache.py:41: NINGUNA dim es 'la correcta'."""
    from cortex.semantic.native_vector_cache import NativeVectorCache

    for dim in (3, 384, 1024):
        d = tmp_path / f"dim{dim}"
        c = NativeVectorCache(d, model_name=f"modelo-dim-{dim}")
        fp = _fps(1, f"d{dim}")[0]
        vec = np.arange(dim, dtype=np.float32) * 0.5
        c.put(fp, "doc.md", vec)
        assert np.array_equal(c.get(fp), vec)


@requires_native
def test_dim_inferida_del_primer_vector(tmp_path):
    """Fix A1 paridad: sin dim explícita se infiere del primer vector."""
    from cortex.semantic.native_vector_cache import NativeVectorCache

    c = NativeVectorCache(tmp_path, model_name="m")
    fp = _fps(1)[0]
    c.put(fp, "a.md", np.ones(768, dtype=np.float32))
    assert len(c) == 1
    assert np.array_equal(c.get(fp), np.ones(768, dtype=np.float32))


@requires_native
def test_batch_put_transaccional_todo_o_nada(dataset, tmp_path):
    """Fix A2: un vector inválido aborta el lote SIN escribir nada."""
    from cortex.semantic.native_vector_cache import NativeVectorCache

    nat = NativeVectorCache(tmp_path / "nat", model_name="m")
    py = VectorCache(tmp_path / "py", model_name="m", dim=384)

    items_ok = [
        (dataset["fps"][i], dataset["cids"][i], dataset["vecs"][i]) for i in range(10)
    ]
    lote_roto = items_ok + [( _fps(1, "x")[0], "y.md", np.ones(7, dtype=np.float32))]

    with pytest.raises(ValueError):
        nat.batch_put(lote_roto)
    with pytest.raises(ValueError):
        py.batch_put(lote_roto)

    # Nada persistido en ninguno: los primeros 10 tampoco.
    for fp in dataset["fps"][:10]:
        assert nat.get(fp) is None
        assert py.get(fp) is None


@requires_native
def test_invalidacion_por_chunks_y_prefijo_paridad(dataset, tmp_path):
    from cortex.semantic.native_vector_cache import NativeVectorCache

    py = VectorCache(tmp_path / "py", model_name="m", dim=384)
    nat = NativeVectorCache(tmp_path / "nat", model_name="m")
    items = list(zip(dataset["fps"], dataset["cids"], dataset["vecs"]))
    py.batch_put(items)
    nat.batch_put(items)

    objetivo = dataset["cids"][0], dataset["cids"][1]
    assert nat.invalidate_chunks(list(objetivo)) == 2
    assert py.invalidate_chunks(list(objetivo)) == 2

    # Prefijo por doc: doc-0.md#* son cids 0..4 (los dos primeros ya muertos).
    assert nat.invalidate_by_chunk_id("docs/doc-0.md#") == 3
    assert py.invalidate_by_chunk_id("docs/doc-0.md#") == 3

    # Idempotencia paridad.
    assert nat.invalidate_by_chunk_id("docs/doc-0.md#") == 0

    for fp in dataset["fps"][:5]:
        assert (nat.get(fp) is None) == (py.get(fp) is None)


@requires_native
def test_modelo_distinto_resetea(tmp_path):
    from cortex.semantic.native_vector_cache import NativeVectorCache

    c = NativeVectorCache(tmp_path, model_name="modelo-A")
    c.put(_fps(1)[0], "a.md", np.ones(384, dtype=np.float32))

    otra = NativeVectorCache(tmp_path, model_name="modelo-B")
    assert len(otra) == 0, "vectores de otro modelo jamás se reutilizan"


@requires_native
def test_compact_preserva_solo_validos(dataset, tmp_path):
    from cortex.semantic.native_vector_cache import NativeVectorCache

    nat = NativeVectorCache(tmp_path, model_name="m")
    nat.batch_put(list(zip(dataset["fps"], dataset["cids"], dataset["vecs"])))
    nat.invalidate_chunks(dataset["cids"][:20])

    tam_pre = nat.stats().size_bytes
    nat.compact()
    tam_post = nat.stats().size_bytes

    assert len(nat) == 30
    assert tam_post < tam_pre, "compact debe recuperar espacio"
    # Los vivos siguen intactos tras compactar.
    for i in range(20, 50):
        assert np.array_equal(nat.get(dataset["fps"][i]), dataset["vecs"][i])


@requires_native
def test_stats_contadores_hit_miss(dataset, tmp_path):
    from cortex.semantic.native_vector_cache import NativeVectorCache

    nat = NativeVectorCache(tmp_path, model_name="m")
    nat.batch_put(list(zip(dataset["fps"][:5], dataset["cids"][:5], dataset["vecs"][:5])))
    nat.get(dataset["fps"][0])
    nat.get("miss-total")
    st = nat.stats()
    assert (st.hit_count, st.miss_count) == (1, 1)
