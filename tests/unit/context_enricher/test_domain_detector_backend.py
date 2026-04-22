from __future__ import annotations

from cortex.context_enricher.domain_detector import DomainDetector


def test_embedding_fallback_uses_onnx_backend(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeEmbedder:
        def __init__(self, model_name: str, backend: str) -> None:
            captured["model_name"] = model_name
            captured["backend"] = backend

        def embed(self, text: str) -> list[float]:
            return [float(len(text))]

    monkeypatch.setattr("cortex.episodic.embedder.Embedder", FakeEmbedder)

    detector = DomainDetector()

    assert detector._embedder is not None
    assert captured == {
        "model_name": "all-MiniLM-L6-v2",
        "backend": "onnx",
    }
