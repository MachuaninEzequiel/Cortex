"""cortex.autopilot.registry — Lightweight registries for extension points.

Autopilot is designed to be extended by adding files.  Each registry holds
instances of a single contract (detector, policy, renderer, adapter, etc.).
"""
from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry that maintains insertion order.

    Usage::

        detectors = Registry[AutopilotDetector]("detector")
        detectors.register(MyDetector())
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._items: list[T] = []

    def register(self, item: T) -> None:
        """Register an instance."""
        self._items.append(item)

    def list_all(self) -> list[T]:
        """Return all registered instances in insertion order."""
        return list(self._items)

    def clear(self) -> None:
        """Remove all registrations (useful mainly in tests)."""
        self._items.clear()


# Convenience registries for Autopilot extension points.
# These are populated in later phases; Fase 1 only creates the skeleton.

DetectorRegistry = Registry[object]
PolicyRegistry = Registry[object]
RendererRegistry = Registry[object]
AdapterRegistry = Registry[object]
BudgetProfileRegistry = Registry[object]
