"""cortex.embedders.fastembedder
--------------------------------
Generic ONNX embedding backend powered by `fastembed` (Qdrant).

Unlocks ANY of fastembed's supported models (multilingual-e5,
paraphrase-multilingual-*, arctic, etc.) without PyTorch — pure ONNX
Runtime, consistent with Cortex's battery-efficiency goals.

Optional dependency: ``pip install cortex-memory[fastembed]`` or
``uv pip install fastembed``.

Obra 04 Fase B/D — model evaluation + language-aware config.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Literal


def cortex_fastembed_cache() -> Path:
    """Cache persistente de modelos fastembed para Cortex.

    El default de fastembed (0.8) es ``/tmp/fastembed_cache`` — en distros con
    ``/tmp`` como tmpfs (CachyOS, Arch, Fedora…) eso significa modelos de
    GBs viviendo en RAM y desapareciendo en cada reboot. Cortex fija su propio
    cache en disco: ``~/.cache/cortex/fastembed``, respetando
    ``FASTEMBED_CACHE_PATH`` si el usuario lo define (comportamiento upstream).
    """
    env = os.getenv("FASTEMBED_CACHE_PATH")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "cortex" / "fastembed"


class FastEmbedder:
    """Embedding backend wrapping fastembed's ONNX models.

    Args:
        model_name: any slug supported by ``fastembed.TextEmbedding``
            (e.g. ``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2``).
    """

    _load_lock: threading.Lock = threading.Lock()
    _models: dict[str, Any] = {}

    def __init__(self, model_name: str) -> None:
        if not model_name or model_name == "all-MiniLM-L6-v2":
            # Avoid silently falling back to the chromadb MiniLM path:
            # fastembed requires an explicit supported slug.
            self._model_name = "sentence-transformers/all-MiniLM-L6-v2"
        else:
            self._model_name = model_name
        self._dim: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def backend(self) -> Literal["fastembed"]:
        return "fastembed"

    # E5-family models are trained with explicit task prefixes; without
    # them quality drops sharply (see Obra 04 spec, riesgos).
    def _prefix(self, kind: str) -> str:
        if "e5" in self._model_name.lower():
            return "query: " if kind == "query" else "passage: "
        return ""

    def _model(self) -> Any:
        from fastembed import TextEmbedding  # optional dep

        with self._load_lock:
            model = FastEmbedder._models.get(self._model_name)
            if model is None:
                model = TextEmbedding(
                    model_name=self._model_name,
                    cache_dir=str(cortex_fastembed_cache()),
                )
                FastEmbedder._models[self._model_name] = model
            return model

    def embed(self, text: str) -> list[float]:
        """Embed a single string (treated as a query)."""
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")
        vec = next(iter(self._model().embed([self._prefix("query") + text.strip()])))
        vals = [float(x) for x in vec]
        self._dim = len(vals)
        return vals

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings (treated as passages/documents)."""
        cleaned = [self._prefix("passage") + t.strip() for t in texts]
        if not cleaned:
            return []
        out = [[float(x) for x in vec] for vec in self._model().embed(cleaned)]
        if out:
            self._dim = len(out[0])
        return out
