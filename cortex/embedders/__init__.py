"""
cortex.embedders
----------------
Strategy-based embedding backends for Cortex.

Provides a unified Embedder protocol and a factory for selecting
the correct backend at runtime based on configuration.

Supported backends
------------------
- ``onnx``   → ONNXMiniLM (default, lightweight, fast)
- ``local``  → sentence-transformers (backup, flexible)
- ``openai`` → OpenAI text-embedding-3-small (enterprise)

Usage
-----
    from cortex.embedders import EmbedderFactory, EmbeddingConfig

    config = EmbeddingConfig(backend="onnx", model_name="all-MiniLM-L6-v2")
    embedder = EmbedderFactory.create(config)
    vector = embedder.embed("Fix login refresh token bug")
"""

from cortex.embedders.base import EmbedderProtocol, EmbeddingBackend
from cortex.embedders.factory import EmbedderFactory, EmbeddingConfig

__all__ = [
    "EmbeddingBackend",
    "EmbedderProtocol",
    "EmbedderFactory",
    "EmbeddingConfig",
]
