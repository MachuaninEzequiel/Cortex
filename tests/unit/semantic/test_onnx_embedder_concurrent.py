"""Tests para la carga thread-safe del modelo ONNX (Capa 4 del MCP defensive).

Verifica que dos invocaciones concurrentes al primer ``embed()`` no
disparen dos cargas paralelas del modelo (lo cual causa race condition
en chromadb y duplica memoria).
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from cortex.embedders.onnx import OnnxEmbedder


@pytest.fixture(autouse=True)
def _reset_onnx_singleton():
    """Asegurar que cada test empieza con el singleton class-level limpio."""
    OnnxEmbedder._onnx_fn = None
    yield
    OnnxEmbedder._onnx_fn = None


def test_single_load_under_serial_invocation():
    """Una sola carga aun llamando _get_onnx_fn N veces secuencialmente."""
    call_count = {"n": 0}

    def fake_loader():
        call_count["n"] += 1
        return MagicMock(name="onnx_fn")

    with patch.object(OnnxEmbedder, "_load_onnx_fn", side_effect=fake_loader):
        for _ in range(5):
            OnnxEmbedder._get_onnx_fn()

    assert call_count["n"] == 1, (
        f"Esperaba 1 sola carga del modelo, se ejecuto {call_count['n']} veces."
    )


def test_single_load_under_concurrent_invocation():
    """Bajo N hilos concurrentes, solo UNA carga del modelo ocurre."""
    call_count = {"n": 0}
    barrier = threading.Barrier(parties=10)

    def slow_loader():
        # Simular carga lenta para maximizar la ventana de race condition.
        # Sin el lock, varios hilos entrarian al loader simultaneamente.
        call_count["n"] += 1
        import time as _t
        _t.sleep(0.05)
        return MagicMock(name="onnx_fn")

    def worker():
        barrier.wait()  # Liberar los 10 hilos a la vez para forzar concurrencia
        OnnxEmbedder._get_onnx_fn()

    threads = [threading.Thread(target=worker) for _ in range(10)]

    with patch.object(OnnxEmbedder, "_load_onnx_fn", side_effect=slow_loader):
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

    assert call_count["n"] == 1, (
        f"Esperaba 1 sola carga del modelo con 10 hilos concurrentes, "
        f"se ejecuto {call_count['n']} veces. El doble-check locking esta roto."
    )


def test_cached_value_returned_on_subsequent_calls():
    """Tras la primera carga, llamadas subsiguientes devuelven el mismo objeto."""
    sentinel = object()

    with patch.object(OnnxEmbedder, "_load_onnx_fn", return_value=sentinel):
        first = OnnxEmbedder._get_onnx_fn()
        second = OnnxEmbedder._get_onnx_fn()

    assert first is sentinel
    assert second is sentinel
    assert first is second


def test_singleton_shared_across_instances():
    """Dos instancias del embedder comparten el singleton class-level."""
    sentinel = object()

    with patch.object(OnnxEmbedder, "_load_onnx_fn", return_value=sentinel):
        e1 = OnnxEmbedder()
        e2 = OnnxEmbedder()
        fn1 = e1._get_onnx_fn()
        fn2 = e2._get_onnx_fn()

    assert fn1 is sentinel
    assert fn2 is sentinel
    assert fn1 is fn2
