"""Gate G5-integración — embedder ONNX nativo vs chromadb (OnnxEmbedder).

Regla dura R5.2: los embeddings deben ser idénticos (cos ≥0.999, esperado
1.0) y el search() completo debe devolver el mismo top-k. Salta limpio si
cortex_core._native no está compilado o el modelo chroma no está cacheado.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cortex.embedders.onnx import OnnxEmbedder


def _native_available() -> bool:
    import os

    if os.environ.get("CORTEX_NATIVE") != "1":
        return False
    try:
        from cortex_core import _native  # noqa: F401
    except ImportError:
        return False
    return (Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx").exists()


requires_native = pytest.mark.skipif(
    not _native_available(),
    reason="requiere CORTEX_NATIVE=1 + cortex_core._native + modelo chroma cacheado",
)

TEXTS = [
    "login authentication middleware refresh token",
    "despliegue continuo kubernetes infraestructura",
    "ADR decisión de arquitectura sobre almacenamiento",
    "stripe payments integration webhook",
]


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


@requires_native
def test_embeddings_cos_igual_o_mejor_que_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    native = OnnxEmbedder()
    vectors = native.embed_batch(TEXTS)
    python = OnnxEmbedder()
    # flag apagado → chroma
    monkeypatch.delenv("CORTEX_NATIVE", raising=False)
    reference = python.embed_batch(TEXTS)
    worst = min(_cos(v, r) for v, r in zip(vectors, reference))
    assert worst >= 0.999, f"cos={worst}"
    assert len(vectors[0]) == len(reference[0])


@requires_native
def test_embed_single_y_batch_consistentes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    native = OnnxEmbedder()
    solo = native.embed(TEXTS[0])
    lote = native.embed_batch([TEXTS[0]])
    assert solo == lote[0]
    assert native.model_name == "all-MiniLM-L6-v2"
    assert native.backend == "onnx"


def test_texto_vacio_value_error_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    """ValueError en texto vacío en AMBAS rutas (validación antes de delegar)."""
    with pytest.raises(ValueError):
        OnnxEmbedder().embed("")
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    with pytest.raises(ValueError):
        OnnxEmbedder().embed("")


@requires_native
def test_flag_activo_sin_modulo_degrada(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    """Con el modelo ausente simulado, el singleton nativo no se construye."""
    import builtins

    real_import = builtins.__import__

    def _sin_native(name, *args, **kwargs):
        if name.startswith("cortex_core"):
            raise ImportError(f"simulado: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setenv("CORTEX_NATIVE", "1")
    monkeypatch.setattr(builtins, "__import__", _sin_native)
    OnnxEmbedder._native_embedder = None
    try:
        assert OnnxEmbedder._get_native() is None
        assert OnnxEmbedder._native_warned
    finally:
        OnnxEmbedder._native_embedder = None
        OnnxEmbedder._native_warned = False


@requires_native
def test_singleton_compartido_entre_instancias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_NATIVE", "1")
    a = OnnxEmbedder()._get_native()
    b = OnnxEmbedder()._get_native()
    assert a is b, "la sesión ort debe ser process-wide (paridad con lock chroma)"


# ── End-to-end: VaultReader.search con embeddings REALES ──────────────────


def _vault_real(tmp_path: Path):
    """Vault chico con contenido diferenciado para búsqueda real."""
    docs = {
        "auth.md": "# Auth\n\nLogin y refresh token middleware de autenticación.\n",
        "api.md": "# API\n\nREST endpoints JSON del servicio de pagos stripe.\n",
        "adr.md": "---\ntitle: ADR almacenamiento\ndoc_type: adr\n---\n\nDecisión de arquitectura sobre base de datos sqlite.\n",
        "deploy.md": "# Deploy\n\nDespliegue continuo con kubernetes e infraestructura como código.\n",
    }
    for name, content in docs.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    return tmp_path


@requires_native
def test_search_topk_identico_embeddings_reales(monkeypatch: pytest.MonkeyPatch) -> None:
    from cortex.semantic.vault_reader import VaultReader

    queries = ["autenticación login token", "pagos stripe api", "decisión sqlite", "kubernetes despliegue"]

    def construir(vault):
        reader = VaultReader(
            vault_path=str(vault),
            embedding_model="all-MiniLM-L6-v2",
            embedding_backend="onnx",
            vector_cache=None,
        )
        reader.sync()
        return reader

    import tempfile

    with tempfile.TemporaryDirectory() as d1:
        vault = _vault_real(Path(d1))
        monkeypatch.delenv("CORTEX_NATIVE", raising=False)
        r_py = construir(vault)
        py_out = [
            [(h.path, round(h.score, 10)) for h in r_py.search(q, top_k=4)]
            for q in queries
        ]
    with tempfile.TemporaryDirectory() as d2:
        vault = _vault_real(Path(d2))
        monkeypatch.setenv("CORTEX_NATIVE", "1")
        r_nat = construir(vault)
        nat_out = [
            [(h.path, round(h.score, 10)) for h in r_nat.search(q, top_k=4)]
            for q in queries
        ]

    # Orden idéntico; scores con tolerancia 1e-5 (plan §7-R1): ort/onnxruntime
    # puede reordenar kernels según el ancho de padding ⇒ diffs ~1e-7.
    assert [ [p.split("/")[-1] for p, _ in q] for q in nat_out ] == [
        [p.split("/")[-1] for p, _ in q] for q in py_out
    ], "top-k divergente"
    for q_nat, q_py in zip(nat_out, py_out):
        for (_, s_nat), (_, s_py) in zip(q_nat, q_py):
            assert abs(s_nat - s_py) <= 1e-5, f"score divergente {s_nat} vs {s_py}"
    # y los scores no son triviales (hay ranking real)
    assert any(score > 0 for _, score in py_out[0])
