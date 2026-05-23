"""Tests para el comportamiento singleton del Embedder ONNX.

Garantiza que el legacy ``cortex.episodic.embedder.Embedder`` delega
en el singleton class-level de ``cortex.embedders.onnx.OnnxEmbedder``,
evitando cargas redundantes del modelo ONNX cuando varios servicios
instancian su propio ``Embedder``.

Regresion guard contra el bug observado en ``cortex_sync_ticket`` cold
start: 5-8 cargas de ``ONNXMiniLM_L6_V2`` por flujo (uno por adapter
distinto que llamaba a ``embed()``), causando ~3-5s de latencia.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from cortex.embedders.onnx import OnnxEmbedder
from cortex.episodic.embedder import Embedder


@pytest.fixture(autouse=True)
def _reset_onnx_singleton():
    """Reset class-level singleton state between tests."""
    OnnxEmbedder._onnx_fn = None
    yield
    OnnxEmbedder._onnx_fn = None


def test_legacy_embedder_uses_onnx_singleton():
    """``Embedder._get_onnx_fn`` returns the same object as ``OnnxEmbedder``."""
    sentinel = object()
    with patch.object(OnnxEmbedder, "_load_onnx_fn", return_value=sentinel):
        legacy = Embedder(backend="onnx")
        fn_legacy = legacy._get_onnx_fn()
        fn_singleton = OnnxEmbedder._get_onnx_fn()

    assert fn_legacy is sentinel
    assert fn_legacy is fn_singleton


def test_multiple_legacy_instances_share_singleton():
    """N instancias del legacy ``Embedder`` cargan ONNX UNA sola vez."""
    call_count = {"n": 0}

    def fake_loader():
        call_count["n"] += 1
        return object()

    with patch.object(OnnxEmbedder, "_load_onnx_fn", side_effect=fake_loader):
        embedders = [Embedder(backend="onnx") for _ in range(5)]
        fns = [e._get_onnx_fn() for e in embedders]

    assert call_count["n"] == 1, (
        f"Esperaba 1 sola carga del modelo ONNX para 5 instancias, "
        f"se ejecuto {call_count['n']} veces."
    )
    # Todos los fn devueltos son el mismo objeto.
    assert all(fn is fns[0] for fn in fns)


def test_legacy_and_onnx_embedder_share_singleton():
    """Un ``Embedder`` legacy y un ``OnnxEmbedder`` directo comparten ONNX."""
    call_count = {"n": 0}

    def fake_loader():
        call_count["n"] += 1
        return object()

    with patch.object(OnnxEmbedder, "_load_onnx_fn", side_effect=fake_loader):
        legacy = Embedder(backend="onnx")
        direct = OnnxEmbedder()

        fn_legacy = legacy._get_onnx_fn()
        fn_direct = direct._get_onnx_fn()

    assert call_count["n"] == 1
    assert fn_legacy is fn_direct
