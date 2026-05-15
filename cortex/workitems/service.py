"""
cortex.workitems.service
------------------------
Service layer for importing and persisting tracked work items.
"""

from __future__ import annotations

import re
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.documentation import write_hu_note
from cortex.documentation.data import HUData
from cortex.documentation.writers import VaultLike
from cortex.models import MemoryEntry
from cortex.security.paths import resolve_safe
from cortex.workitems.models import TrackedItem
from cortex.workitems.providers.base import WorkItemProvider

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader


class _PathOnlyVault:
    """Minimal VaultLike that wraps a bare path for canonical writers."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:
        return False


_STATUS_MAP = {
    "imported": "backlog",
    "in_progress": "in-progress",
}


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
        path = resolve_safe(self._vault_path, Path("hu") / f"{self._slug(item_id)}.md")
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
        final_tags = ["hu", item.source.value, item.kind.value] + list(item.labels)
        title = f"{item.id}: {item.title}"
        legacy_status = item.status or "imported"
        status = _STATUS_MAP.get(legacy_status, legacy_status)

        synced_at = item.sync_timestamp
        if synced_at is not None and synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=UTC)

        data = HUData(
            title=title,
            tags=final_tags,
            status=status,
            external_id=item.id,
            source=item.source.value,
            kind=item.kind.value,
            description=item.description or "",
            acceptance_criteria=list(item.acceptance_criteria or []),
            assignee=item.assignee,
            external_url=item.external_url,
            synced_at=synced_at,
        )
        vault: VaultLike = _PathOnlyVault(self._vault_path)
        return write_hu_note(data, vault=vault)

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
