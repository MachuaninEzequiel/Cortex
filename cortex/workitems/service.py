"""
cortex.workitems.service
------------------------
Service layer for importing and persisting tracked work items.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.models import MemoryEntry
from cortex.workitems.models import TrackedItem
from cortex.workitems.providers.base import WorkItemProvider

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader


class WorkItemService:
    """Imports, persists, and retrieves tracked items from optional providers."""

    def __init__(
        self,
        *,
        vault_path: str | Path,
        semantic: VaultReader,
        episodic: EpisodicMemoryStore,
        providers: dict[str, WorkItemProvider] | None = None,
        context_metadata: dict[str, str] | None = None,
    ) -> None:
        self._vault_path = Path(vault_path)
        self._semantic = semantic
        self._episodic = episodic
        self._providers = providers or {}
        self._context_metadata = dict(context_metadata or {})

    def import_item(
        self,
        external_id: str,
        *,
        provider: str = "jira",
        remember: bool = True,
    ) -> Path:
        provider_impl = self._provider(provider)
        item = provider_impl.get_item(external_id)
        path = self._write_item_note(item)
        rel_path = str(path.relative_to(self._vault_path))
        self._semantic.index_file(rel_path)
        if remember:
            self._store_episodic(item, rel_path)
        return path

    def get_item_note(self, item_id: str) -> Path:
        path = self._vault_path / "hu" / f"{self._slug(item_id)}.md"
        if not path.exists():
            raise FileNotFoundError(f"Tracked item not found in vault: {item_id}")
        return path

    def list_item_notes(self) -> list[Path]:
        hu_dir = self._vault_path / "hu"
        if not hu_dir.exists():
            return []
        return sorted(hu_dir.glob("*.md"))

    def has_provider(self, provider: str) -> bool:
        provider_impl = self._providers.get(provider)
        return bool(provider_impl and provider_impl.is_configured())

    def _provider(self, provider: str) -> WorkItemProvider:
        normalized = provider.strip().lower()
        provider_impl = self._providers.get(normalized)
        if provider_impl is None:
            raise KeyError(f"Unknown work item provider: {provider}")
        if not provider_impl.is_configured():
            raise RuntimeError(f"Provider '{provider}' is not configured.")
        return provider_impl

    def _write_item_note(self, item: TrackedItem) -> Path:
        from cortex.documentation import write_tracked_item_note

        return write_tracked_item_note(
            self._vault_path,
            item=item,
        )

    def _store_episodic(self, item: TrackedItem, rel_path: str) -> MemoryEntry:
        summary = [
            f"Tracked item: {item.id}",
            f"Title: {item.title}",
        ]
        if item.description:
            summary.append(f"Description: {item.description[:300]}")
        if item.acceptance_criteria:
            summary.append("Acceptance: " + "; ".join(item.acceptance_criteria[:5]))
        return self._episodic.add(
            content="\n".join(summary),
            memory_type="hu",
            tags=["hu", item.source.value, item.kind.value],
            files=[rel_path],
            extra_metadata=dict(self._context_metadata),
        )

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
        return slug or "item"
