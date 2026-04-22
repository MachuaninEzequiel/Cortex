"""
cortex.embedders.onnx
---------------------
ONNX backend — the default, recommended embedder.

Wraps chromadb's bundled ``ONNXMiniLM_L6_V2`` embedding function.
Identical model quality to the ``local`` backend (all-MiniLM-L6-v2)
but runs on ONNX Runtime (~10 MB) instead of PyTorch (~2.5 GB).

No extra dependencies beyond chromadb, which is already required.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

logger = logging.getLogger(__name__)


class OnnxEmbedder:
    """
    Embedding backend powered by chromadb's built-in ONNX runtime.

    This is the default backend. It has no additional dependencies
    beyond chromadb itself and delivers sub-millisecond embedding
    for typical document sizes.

    Args:
        model_name: HuggingFace model slug (informational only;
                    chromadb's ONNX function uses all-MiniLM-L6-v2).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def backend(self) -> Literal["onnx"]:
        return "onnx"

    def embed(self, text: str) -> list[float]:
        """Embed a single string via ONNX runtime."""
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text.")
        fn = self._get_onnx_fn()
        result = fn([text])
        return [float(x) for x in result[0]]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings efficiently (single ONNX session call)."""
        fn = self._get_onnx_fn()
        result = fn(texts)
        return [[float(x) for x in v] for v in result]

    @lru_cache(maxsize=1)
    def _get_onnx_fn(self):  # type: ignore[return]
        """Lazy-load chromadb's ONNX embedding function."""
        try:
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2  # type: ignore
            logger.info("Loading ONNX embedding function (ONNXMiniLM_L6_V2)...")
            return ONNXMiniLM_L6_V2()
        except ImportError:
            # chromadb >= 0.5 moved the import path
            try:
                from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import (  # type: ignore
                    ONNXMiniLM_L6_V2,
                )
                logger.info("Loading ONNX embedding function (alt path)...")
                return ONNXMiniLM_L6_V2()
            except ImportError as exc:
                raise ImportError(
                    "Could not load the ONNX embedding function from chromadb. "
                    "Ensure chromadb>=0.5 is installed, or switch to "
                    "embedding_backend: local in config.yaml."
                ) from exc
