"""
cortex.embedders.local
----------------------
Local backend — sentence-transformers + PyTorch.

BACKUP option for when you need to use a custom HuggingFace model
that isn't available as ONNX. Requires a large PyTorch download
(~2.5 GB). Enable with:

    episodic:
      embedding_backend: local

Install the extra: pip install cortex-memory[local]
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """
    Embedding backend powered by sentence-transformers (PyTorch).

    Supports any HuggingFace model by name, but requires PyTorch
    which is a heavy dependency (~2.5 GB). Use the ONNX backend
    unless you need a custom model.

    Args:
        model_name: Any HuggingFace model identifier.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def backend(self) -> Literal["local"]:
        return "local"

    def embed(self, text: str) -> list[float]:
        """Embed a single string using sentence-transformers."""
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text.")
        model = self._get_model()
        vector = model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings in an efficient batched call."""
        model = self._get_model()
        vectors = model.encode(texts, convert_to_numpy=True, batch_size=32)
        return [v.tolist() for v in vectors]

    @lru_cache(maxsize=1)
    def _get_model(self):  # type: ignore[return]
        """Lazy-load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for the 'local' backend.\n"
                "Install with: pip install cortex-memory[local]\n"
                "Or switch to the default ONNX backend in config.yaml: "
                "embedding_backend: onnx"
            ) from exc

        logger.info("Loading local sentence-transformers model: %s", self._model_name)
        return SentenceTransformer(self._model_name)
