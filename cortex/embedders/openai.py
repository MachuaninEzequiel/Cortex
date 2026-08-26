"""
cortex.embedders.openai
-----------------------
DEPRECATED (dueño, 2026-08-25 — doc 12 §4.3): backend remoto que contradice
el principio "todo local, cero keys" de Cortex. Sin porte a Rust planificado;
se elimina en la baja definitiva de Python. Migrar a `embedding.backend: onnx`
(MiniLM/e5 nativos vía cortex-embed).

OpenAI backend — text-embedding-3-small via API.

Legacy enterprise option for teams that want cloud-hosted embeddings.
Requires an ``OPENAI_API_KEY`` environment variable and the
``openai`` package.

Enable with:

    episodic:
      embedding_backend: openai
      embedding_model: text-embedding-3-small

Install the extra: pip install cortex-memory[openai]
"""

from __future__ import annotations

import logging
import os
import warnings
from typing import Literal

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """
    Embedding backend powered by the OpenAI Embeddings API.

    Supports all OpenAI embedding models (text-embedding-3-small,
    text-embedding-3-large, text-embedding-ada-002).

    Args:
        model_name: OpenAI model identifier.
    """

    def __init__(self, model_name: str = "text-embedding-3-small") -> None:
        warnings.warn(
            "OpenAIEmbedder está DEPRECATED (doc 12 §4.3): use embedding "
            "backend onnx (MiniLM/e5 nativos). Se elimina en la baja de Python.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def backend(self) -> Literal["openai"]:
        return "openai"

    def embed(self, text: str) -> list[float]:
        """Embed a single string via the OpenAI Embeddings API."""
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text.")
        client = self._get_client()
        response = client.embeddings.create(input=text, model=self._model_name)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple strings in a single API call.

        OpenAI supports batching natively, so this is efficient.
        Note: rate limiting is not handled here; wrap with retries
        at the application level if needed.
        """
        client = self._get_client()
        response = client.embeddings.create(input=texts, model=self._model_name)
        # API returns embeddings in the same order as input
        return [item.embedding for item in response.data]

    def _get_client(self):  # type: ignore[return]
        """Lazy-initialize the OpenAI client with API key validation."""
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAI embeddings. "
                "Install with: pip install cortex-memory[openai]"
            ) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OSError(
                "OPENAI_API_KEY environment variable not set. "
                "Export it before using the OpenAI embedding backend."
            )
        return OpenAI(api_key=api_key)
