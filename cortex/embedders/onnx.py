"""
cortex.embedders.onnx
---------------------
ONNX backend — the default, recommended embedder.

Wraps chromadb's bundled ``ONNXMiniLM_L6_V2`` embedding function.
Identical model quality to the ``local`` backend (all-MiniLM-L6-v2)
but runs on ONNX Runtime (~10 MB) instead of PyTorch (~2.5 GB).

No extra dependencies beyond chromadb, which is already required.

Fase 1 — Capa 4 del plan multi-IDE & MCP hardening:
La carga del modelo ONNX se protege con un lock class-level + doble-check
locking. Sin esto, dos requests concurrentes al MCP que disparen la primera
inferencia pueden iniciar dos cargas en paralelo (~10 MB cada una), con
race condition en la inicializacion interna de chromadb. El lock garantiza
que UNA sola carga ocurre.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Literal

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

    # Lock y singleton class-level: comparten todas las instancias del embedder.
    # El modelo ONNX subyacente (ONNXMiniLM_L6_V2) es process-wide, no
    # per-instance, asi que cachearlo class-level evita doble carga aun cuando
    # multiples adapters/services creen sus propios OnnxEmbedder.
    _load_lock: threading.Lock = threading.Lock()
    _onnx_fn: Any = None

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

    @classmethod
    def _get_onnx_fn(cls) -> Any:
        """Lazy-load chromadb's ONNX embedding function (thread-safe).

        Doble-check locking:
        - Fast path sin lock: si ``_onnx_fn`` ya esta cargado, devolverlo.
        - Slow path con lock: adquirir el lock, re-chequear (otro hilo pudo
          haber cargado mientras esperabamos), y cargar si todavia es None.

        El lock garantiza que solo UN hilo ejecuta la carga, aun con N hilos
        compitiendo. Caso real: 2 requests concurrentes al MCP server que
        ambos disparen ``cortex_search_vector`` la primera vez.
        """
        fn = cls._onnx_fn
        if fn is not None:
            return fn
        with cls._load_lock:
            # Re-check tras adquirir el lock — otro hilo pudo haber cargado.
            if cls._onnx_fn is not None:
                return cls._onnx_fn
            cls._onnx_fn = cls._load_onnx_fn()
            return cls._onnx_fn

    @staticmethod
    def _load_onnx_fn() -> Any:
        """Importa y construye el embedding function de chromadb.

        Aislado del get-or-load para que el lock cubra solo el camino
        critico y el caller no haga import + construction mientras
        sostiene el lock por nada cuando ya esta cacheado.
        """
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
