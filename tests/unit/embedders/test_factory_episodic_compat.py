"""A6 — compatibilidad factory ↔ episodic.

Verifica que ``EmbedderFactory`` produce backends que satisfacen lo que
``cortex.episodic`` necesita: misma interfaz (embed / embed_batch /
model_name / backend) y dimensión consistente entre embed() y embed_batch().
"""
from __future__ import annotations

import pytest

from cortex.embedders import EmbedderFactory, EmbeddingConfig
from cortex.embedders.base import EmbedderProtocol


@pytest.fixture(params=["onnx", "local", "openai"])
def backend(request):
    name = request.param
    if name == "local":
        pytest.importorskip("sentence_transformers")
    return name


class _FakeOpenAIResponse:
    def __init__(self, n: int, dim: int):
        self.data = [type("Item", (), {"embedding": [0.5] * dim})() for _ in range(n)]


class _FakeEmbeddingsAPI:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, *, input, model):
        self.calls.append({"input": list(input), "model": model})
        return _FakeOpenAIResponse(len(input), dim=384)


class _FakeClient:
    def __init__(self):
        self.embeddings = _FakeEmbeddingsAPI()

    @property
    def calls(self):
        return self.embeddings.calls


@pytest.fixture
def fake_openai_client(monkeypatch):
    from cortex.embedders.openai import OpenAIEmbedder

    client = _FakeClient()
    monkeypatch.setattr(OpenAIEmbedder, "_get_client", lambda self: client)
    return client


def make_embedder(name, **kwargs):
    return EmbedderFactory.create(EmbeddingConfig(backend=name, **kwargs))


def test_factory_backends_satisfy_episodic_contract(backend, fake_openai_client):
    """Cada backend registrado cumple el protocolo que episodic consume."""
    emb = make_embedder(backend)
    assert isinstance(emb, EmbedderProtocol)

    vec = emb.embed("session context text")
    assert isinstance(vec, list) and len(vec) > 0
    assert all(isinstance(x, float) for x in vec)

    batch = emb.embed_batch(["alpha text", "beta text"])
    assert len(batch) == 2
    for v in batch:
        assert len(v) == len(vec), "dimensión inconsistente entre embed() y embed_batch()"
        assert all(isinstance(x, float) for x in v)

    assert emb.model_name == "all-MiniLM-L6-v2" or backend == "openai"
    assert emb.backend == backend


def test_factory_openai_batches_single_http_request(fake_openai_client):
    """FIX A6: embed_batch OpenAI debe hacer UN request, no N requests."""
    texts = ["uno", "dos", "tres", "cuatro"]
    emb = make_embedder("openai")
    result = emb.embed_batch(texts)

    assert len(result) == 4
    assert all(v == [0.5] * 384 for v in result)
    assert len(fake_openai_client.calls) == 1, (
        f"Esperaba 1 request HTTP para {len(texts)} textos, "
        f"se hicieron {len(fake_openai_client.calls)}."
    )
    assert fake_openai_client.calls[0]["input"] == texts
