"""
cortex.episodic.embedder
------------------------
Thin wrapper around embedding backends.

Supported backends
------------------
- ``onnx``   → ONNXMiniLM via chromadb (DEFAULT — zero extra deps, fast, lightweight)
- ``local``  → sentence-transformers (BACKUP — flexible but heavy ~2.5 GB PyTorch)
- ``openai`` → text-embedding-3-small via the OpenAI API (enterprise option)

Backend Selection
-----------------
The default backend is ``onnx``. It uses the same ``all-MiniLM-L6-v2`` model
as the ``local`` backend but runs it through ONNX Runtime instead of PyTorch.
This means no PyTorch download (saving ~2.5 GB), faster cold starts, and
lower RAM usage — with identical embedding quality.

To switch backends, set ``embedding_backend`` in your ``config.yaml``:

    episodic:
      embedding_backend: onnx    # default — recommended
      # embedding_backend: local # backup (requires sentence-transformers)
      # embedding_backend: openai
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Literal

logger = logging.getLogger(__name__)

EmbeddingBackend = Literal["onnx", "local", "openai"]


class Embedder:
    """
    Produce dense vector embeddings for text.

    Args:
        model_name:  HuggingFace model name (local/onnx) or OpenAI model name.
        backend:     ``"onnx"``   uses chromadb's built-in ONNX runtime (default);
                     ``"local"``  uses sentence-transformers (backup, needs PyTorch);
                     ``"openai"`` calls the OpenAI Embeddings API.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        backend: EmbeddingBackend = "onnx",
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
        if self.backend == "local":
            return self._embed_local(text)
        # Default: onnx
        return self._embed_onnx(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        if self.backend == "openai":
            return [self._embed_openai(t) for t in texts]
        if self.backend == "local":
            return self._embed_local_batch(texts)
        # Default: onnx
        return self._embed_onnx_batch(texts)

    # ------------------------------------------------------------------
    # ONNX Backend (DEFAULT — lightweight, fast, no PyTorch required)
    # Uses chromadb's bundled ONNXMiniLM_L6_V2 embedding function.
    # Same model quality as "local", but powered by onnxruntime (~10 MB)
    # instead of PyTorch (~2.5 GB).
    # ------------------------------------------------------------------

    def _embed_onnx(self, text: str) -> list[float]:
        fn = self._get_onnx_fn()
        result = fn([text])
        return [float(x) for x in result[0]]

    def _embed_onnx_batch(self, texts: list[str]) -> list[list[float]]:
        fn = self._get_onnx_fn()
        result = fn(texts)
        return [[float(x) for x in v] for v in result]

    @lru_cache(maxsize=1)
    def _get_onnx_fn(self):
        """Lazy-load chromadb's ONNX embedding function (no PyTorch needed)."""
        try:
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2  # type: ignore
            logger.info("Loading ONNX embedding function (ONNXMiniLM_L6_V2)...")
            return ONNXMiniLM_L6_V2()
        except ImportError:
            # Fallback: chromadb >= 0.5 may use a different import path
            try:
                from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import (  # type: ignore
                    ONNXMiniLM_L6_V2,
                )
                logger.info("Loading ONNX embedding function (alt path)...")
                return ONNXMiniLM_L6_V2()
            except ImportError as e:
                raise ImportError(
                    "Could not load the ONNX embedding function from chromadb. "
                    "Make sure chromadb>=0.5 is installed. "
                    "Alternatively, switch to backend='local' in your config.yaml."
                ) from e

    # ------------------------------------------------------------------
    # Local Backend (BACKUP — sentence-transformers + PyTorch)
    # Kept for flexibility: supports any HuggingFace model by name.
    # Requires: pip install cortex-memory[local]  (~2.5 GB PyTorch download)
    # ------------------------------------------------------------------

    def _embed_local(self, text: str) -> list[float]:
        model = self._get_local_model()
        vector = model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def _embed_local_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        vectors = model.encode(texts, convert_to_numpy=True, batch_size=32)
        return [v.tolist() for v in vectors]

    @lru_cache(maxsize=1)
    def _get_local_model(self):  # type: ignore[return]
        """
        Lazy-load sentence-transformers model.
        BACKUP backend — supports any HuggingFace model but requires PyTorch.
        Enable with: embedding_backend: local in config.yaml
        """
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for the 'local' backend.\n"
                "Install with: pip install cortex-memory[local]\n"
                "Or switch to the default ONNX backend in config.yaml: "
                "embedding_backend: onnx"
            ) from e

        logger.info("Loading local sentence-transformers model: %s", self.model_name)
        return SentenceTransformer(self.model_name)

    # ------------------------------------------------------------------
    # OpenAI Backend (enterprise — requires OPENAI_API_KEY)
    # ------------------------------------------------------------------

    def _embed_openai(self, text: str) -> list[float]:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise ImportError(
                "openai package is required for OpenAI embeddings. "
                "Install with: pip install cortex-memory[openai]"
            ) from e

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OSError("OPENAI_API_KEY environment variable not set.")

        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(input=text, model=self.model_name)
        return response.data[0].embedding
