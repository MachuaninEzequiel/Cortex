"""
cortex.workitems.providers.base
-------------------------------
Provider contracts for optional external work item integrations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cortex.workitems.models import TrackedItem


class WorkItemProvider(ABC):
    """Abstract read-only provider for external work items."""

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable provider identifier."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether the provider has enough configuration to operate."""

    @abstractmethod
    def get_item(self, external_id: str) -> TrackedItem:
        """Fetch and normalize one external work item."""
