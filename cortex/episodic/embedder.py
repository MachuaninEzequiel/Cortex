"""
cortex.episodic.embedder
------------------------
Thin wrapper around embedding backends.

Supported backends
------------------
- ``local``  → sentence-transformers (default, zero API cost)
- ``openai`` → text-embedding-3-small via the OpenAI API
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Literal

logger = logging.getLogger(__name__)

EmbeddingBackend = Literal["local", "openai"]


class Embedder:
    """
    Produce dense vector embeddings for text.

    Args:
        model_name:  HuggingFace model name (local) or OpenAI model name.
        backend:     ``"local"`` uses sentence-transformers offline;
                     ``"openai"`` calls the OpenAI Embeddings API.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        backend: EmbeddingBackend = "local",
    ) -> None:
        self.model_name = model_name
        self.backend = backend
        self._model = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        """Return the embedding vector for a single text string."""
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text.")

        if self.backend == "openai":
            return self._embed_openai(text)
        return self._embed_local(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        if self.backend == "openai":
            return [self._embed_openai(t) for t in texts]
        return self._embed_local_batch(texts)

    # ------------------------------------------------------------------
    # Backends
    # ------------------------------------------------------------------

    def _embed_local(self, text: str) -> list[float]:
        model = self._get_local_model()
        vector = model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def _embed_local_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        vectors = model.encode(texts, convert_to_numpy=True, batch_size=32)
        return [v.tolist() for v in vectors]

    def _embed_openai(self, text: str) -> list[float]:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise ImportError(
                "openai package is required for OpenAI embeddings. "
                "Install with: pip install openai"
            ) from e

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(input=text, model=self.model_name)
        return response.data[0].embedding

    @lru_cache(maxsize=1)
    def _get_local_model(self):  # type: ignore[return]
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install sentence-transformers"
            ) from e

        logger.info("Loading local embedding model: %s", self.model_name)
        return SentenceTransformer(self.model_name)
