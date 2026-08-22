"""A6 — el Embedder episódico delega 100% en cortex.embedders.

- Misma clase de backend que produce EmbedderFactory (delegación, no duplicación).
- embed_batch con backend openai hace UN solo request HTTP (batching nativo),
  no uno por texto.
"""
from __future__ import annotations

import sys

from cortex.episodic.embedder import Embedder


def test_embedder_onnx_delegates_to_factory_backend():
    """Embedder(onnx) debe envolver un OnnxEmbedder del stack consolidado."""
    from cortex.embedders.onnx import OnnxEmbedder

    emb = Embedder(backend="onnx")
    assert isinstance(emb._delegate, OnnxEmbedder)
    assert emb.model_name == emb._delegate.model_name
    assert emb.backend == "onnx"


def test_embedder_openai_batch_single_http_request(monkeypatch):
    """FIX A6: un request por batch, no uno por texto."""
    from cortex.embedders.openai import OpenAIEmbedder

    calls: list[list[str]] = []

    class _Item:
        embedding = [0.1] * 384

    class _Resp:
        data = [_Item(), _Item(), _Item()]

    class _API:
        @staticmethod
        def create(*, input, model):
            calls.append(list(input))
            return _Resp()

    monkeypatch.setattr(
        OpenAIEmbedder, "_get_client", lambda self: type("C", (), {"embeddings": _API})()
    )

    emb = Embedder(backend="openai", model_name="text-embedding-3-small")
    result = emb.embed_batch(["a", "b", "c"])

    assert len(result) == 3
    assert len(calls) == 1, f"Esperaba 1 request HTTP, se hicieron {len(calls)}."
    assert calls[0] == ["a", "b", "c"]


def test_episodic_module_no_duplicate_backend_logic():
    """El módulo episodic no debe re-implementar backends: sin imports de openai/
    sentence_transformers ni ramas por-backend."""
    import cortex.episodic.embedder as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "_embed_openai" not in src
    assert "_embed_local" not in src
    assert "_embed_onnx" not in src.replace("_embed_onnx_fn", "")
