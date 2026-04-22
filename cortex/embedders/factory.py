"""
cortex.embedders.factory
------------------------
EmbedderFactory — centralized registry for embedding backend selection.

This is the single creation point for all embedders. It maps backend
names from config.yaml to their concrete implementation classes.

Adding a new backend
--------------------
1. Create ``cortex/embedders/my_backend.py`` with a class that satisfies
   ``EmbedderProtocol`` (structurally — no inheritance needed).
2. Register it in ``EmbedderFactory._REGISTRY``.
3. That's it. No changes needed anywhere else.

Usage
-----
    from cortex.embedders import EmbedderFactory, EmbeddingConfig

    config = EmbeddingConfig(backend="onnx")
    embedder = EmbedderFactory.create(config)
    vector = embedder.embed("session context text")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cortex.embedders.base import EmbeddingBackend, EmbedderProtocol

if TYPE_CHECKING:
    pass


# ------------------------------------------------------------------
# Configuration data class
# ------------------------------------------------------------------

@dataclass
class EmbeddingConfig:
    """
    Configuration for selecting and initialising an embedding backend.

    Args:
        backend:    One of ``"onnx"`` (default), ``"local"``, ``"openai"``.
        model_name: Model identifier passed to the backend.
        options:    Backend-specific kwargs forwarded to the constructor.
    """
    backend: EmbeddingBackend = "onnx"
    model_name: str = "all-MiniLM-L6-v2"
    options: dict = field(default_factory=dict)


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------

class UnsupportedBackendError(ValueError):
    """Raised when an unknown embedding backend is requested."""


class EmbedderFactory:
    """
    Registry-based factory for creating embedding backends.

    Backends are registered by name. The factory resolves the correct
    class at runtime based on ``EmbeddingConfig.backend``.
    """

    # Registry maps backend name → module.ClassName (lazy import strings
    # to avoid importing heavy dependencies at module load time).
    _REGISTRY: dict[str, tuple[str, str]] = {
        "onnx":   ("cortex.embedders.onnx",   "OnnxEmbedder"),
        "local":  ("cortex.embedders.local",  "LocalEmbedder"),
        "openai": ("cortex.embedders.openai", "OpenAIEmbedder"),
    }

    @classmethod
    def create(cls, config: EmbeddingConfig) -> EmbedderProtocol:
        """
        Instantiate the correct embedder for the given config.

        Args:
            config: EmbeddingConfig with backend selection and options.

        Returns:
            An object satisfying EmbedderProtocol.

        Raises:
            UnsupportedBackendError: If backend is not in the registry.
            ImportError: If backend's optional dependencies are missing.
        """
        entry = cls._REGISTRY.get(config.backend)
        if entry is None:
            supported = ", ".join(cls._REGISTRY)
            raise UnsupportedBackendError(
                f"Unknown embedding backend: '{config.backend}'. "
                f"Supported backends: {supported}."
            )

        module_path, class_name = entry
        embedder_class = cls._import_class(module_path, class_name)

        return embedder_class(
            model_name=config.model_name,
            **config.options,
        )

    @classmethod
    def create_from_params(
        cls,
        backend: EmbeddingBackend = "onnx",
        model_name: str = "all-MiniLM-L6-v2",
        **options,
    ) -> EmbedderProtocol:
        """
        Convenience method: create an embedder directly from params
        without constructing an EmbeddingConfig first.

        Args:
            backend:    Backend name.
            model_name: Model identifier.
            **options:  Backend-specific kwargs.

        Returns:
            An object satisfying EmbedderProtocol.
        """
        return cls.create(EmbeddingConfig(
            backend=backend,
            model_name=model_name,
            options=options,
        ))

    @staticmethod
    def _import_class(module_path: str, class_name: str) -> type:
        """Lazy-import a class from a module path string."""
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    @classmethod
    def supported_backends(cls) -> list[str]:
        """Return the list of registered backend names."""
        return list(cls._REGISTRY)
