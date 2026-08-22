"""
cortex.episodic.embedder
------------------------
Thin compatibility wrapper around the consolidated embedding stack.

Historia (A6)
-------------
Este módulo duplicaba Onnx/Local/OpenAI en paralelo a ``cortex/embedders/*``
y su path OpenAI hacía un request HTTP por texto. Desde la consolidación A6,
:class:`Embedder` delega 100% en :class:`cortex.embedders.factory.EmbedderFactory`
— un único punto donde "elegir modelo" existe.

Supported backends
------------------
- ``onnx``   → ONNXMiniLM via chromadb (DEFAULT — zero extra deps, fast)
- ``local``  → sentence-transformers (BACKUP — heavy ~2.5 GB PyTorch)
- ``openai`` → OpenAI Embeddings API (enterprise option)

To switch backends, set ``embedding_backend`` in your ``config.yaml``:

    episodic:
      embedding_backend: onnx    # default — recommended
      # embedding_backend: local # backup (requires sentence-transformers)
      # embedding_backend: openai

Deprecation note: importar backends concretos desde ``cortex.embedders``
es preferible; esta clase se mantiene para no romper imports existentes
(``cortex.episodic.memory_store``, ``cortex.semantic.vault_reader``,
``cortex.webgraph.*``, ``cortex.context_enricher.domain_detector``).
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.embedders.base import EmbeddingBackend  # noqa: F401  (re-export)
from cortex.embedders.factory import EmbedderFactory, EmbeddingConfig

logger = logging.getLogger(__name__)


class Embedder:
    """
    Produce dense vector embeddings for text.

    Compatibilidad wrapper: delega en el backend producido por
    :class:`EmbedderFactory` (mismo stack que usa ``cortex.semantic``).

    Args:
        model_name:  HuggingFace model name (local/onnx) or OpenAI model name.
        backend:     ``"onnx"`` (default), ``"local"`` or ``"openai"``.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        backend: EmbeddingBackend = "onnx",
    ) -> None:
        self.model_name = model_name
        self.backend = backend
        self._delegate = EmbedderFactory.create(
            EmbeddingConfig(backend=backend, model_name=model_name)
        )

    # ------------------------------------------------------------------
    # Public API (delegation)
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        """Return the embedding vector for a single text string."""
        return self._delegate.embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently (single call per backend)."""
        return self._delegate.embed_batch(texts)

    def _get_onnx_fn(self) -> Any:
        """Process-wide ONNX embedding function (compat shim).

        Delegates to the class-level thread-safe singleton of
        :class:`cortex.embedders.onnx.OnnxEmbedder`, so the ONNX model loads
        exactly once per process regardless of how many wrappers exist.
        """
        from cortex.embedders.onnx import OnnxEmbedder
        return OnnxEmbedder._get_onnx_fn()
