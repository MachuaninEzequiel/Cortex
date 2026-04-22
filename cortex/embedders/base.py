"""
cortex.embedders.base
---------------------
The Embedder Protocol — the single interface that ALL embedding backends
must satisfy. Using ``typing.Protocol`` (structural subtyping) means:

1. Backends don't need to inherit from a base class.
2. Any class with the right shape automatically satisfies the contract.
3. ``runtime_checkable`` enables isinstance() checks at startup.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

EmbeddingBackend = Literal["onnx", "local", "openai"]


@runtime_checkable
class EmbedderProtocol(Protocol):
    """
    Structural protocol for all embedding backends.

    A class satisfies this protocol if it implements ``embed`` and
    ``embed_batch`` with the correct signatures. No inheritance needed.
    """

    @property
    def model_name(self) -> str:
        """Name of the underlying embedding model."""
        ...

    @property
    def backend(self) -> EmbeddingBackend:
        """Which backend this embedder uses."""
        ...

    def embed(self, text: str) -> list[float]:
        """
        Compute the dense vector for a single text string.

        Args:
            text: Non-empty input string.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            ValueError: If text is empty.
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Compute dense vectors for multiple texts efficiently.

        Args:
            texts: List of non-empty input strings.

        Returns:
            List of embedding vectors, one per input text.
        """
        ...
