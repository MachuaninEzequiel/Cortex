"""cortex.context_enricher.filters - Structural filters for enrichment.

The motor of retrieval is content-driven (vector similarity + BM25). The
filters in this module sit on top of that result set and remove items that
the caller knows are irrelevant *because of their metadata*:

    - ``doc_types``     keep only items of the given DocType(s).
    - ``statuses_*``    keep items in/out of given statuses.
    - ``tags_*``        AND/OR semantics over frontmatter tags.
    - ``vault_scope``   local-only, enterprise-only, or both.
    - ``max_age_days``  drop items older than the window.
    - ``project_ids``   multi-tenant filter for enterprise.
    - ``strict``        in strict mode, items without ``doc_type`` are
                        excluded when ``doc_types`` is set.

All fields are optional. With every field at its default (``filters=None``
or an empty ``EnrichmentFilters()``), ``apply_filters`` is a no-op.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from cortex.documentation.doc_type import DocType
from cortex.models import EnrichedItem


class EnrichmentFilters(BaseModel):
    """Structural filters applied after retrieval but before budget."""

    doc_types: list[DocType] | None = None
    exclude_doc_types: list[DocType] = Field(default_factory=list)

    statuses_allowed: list[str] | None = None
    statuses_excluded: list[str] = Field(default_factory=list)

    tags_required: list[str] = Field(default_factory=list)   # AND
    tags_excluded: list[str] = Field(default_factory=list)
    tags_any_of: list[str] = Field(default_factory=list)     # OR

    vault_scope: str = "all"  # "local" | "enterprise" | "all"

    max_age_days: int | None = None

    project_ids: list[str] | None = None

    strict: bool = False

    def is_empty(self) -> bool:
        """Return ``True`` when every field is at its default."""
        return (
            self.doc_types is None
            and not self.exclude_doc_types
            and self.statuses_allowed is None
            and not self.statuses_excluded
            and not self.tags_required
            and not self.tags_excluded
            and not self.tags_any_of
            and self.vault_scope == "all"
            and self.max_age_days is None
            and self.project_ids is None
            and not self.strict
        )


def apply_filters(
    items: list[EnrichedItem],
    filters: EnrichmentFilters | None,
) -> list[EnrichedItem]:
    """Apply ``filters`` to ``items``. Returns a new list (never mutates).

    Filters are AND-composed: every active predicate must pass for an item
    to be kept.
    """
    if filters is None or filters.is_empty():
        return list(items)

    now = datetime.now(UTC)
    out: list[EnrichedItem] = []
    for item in items:
        if _passes(item, filters, now):
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Internal predicates
# ---------------------------------------------------------------------------


def _passes(item: EnrichedItem, f: EnrichmentFilters, now: datetime) -> bool:
    item_doc_type = getattr(item, "doc_type", None)

    # doc_types
    if f.doc_types is not None:
        if item_doc_type is None:
            if f.strict:
                return False
        else:
            if item_doc_type not in f.doc_types:
                return False

    if f.exclude_doc_types and item_doc_type in f.exclude_doc_types:
        return False

    # status
    item_status = getattr(item, "status", None)
    if f.statuses_allowed is not None:
        if item_status is None or item_status not in f.statuses_allowed:
            return False
    if item_status is not None and item_status in f.statuses_excluded:
        return False

    # tags
    item_tags = set(item.tags or [])
    if f.tags_required and not set(f.tags_required).issubset(item_tags):
        return False
    if f.tags_excluded and item_tags & set(f.tags_excluded):
        return False
    if f.tags_any_of and not (item_tags & set(f.tags_any_of)):
        return False

    # scope
    if f.vault_scope != "all":
        item_scope = getattr(item, "vault_scope", "local") or "local"
        if item_scope != f.vault_scope:
            return False

    # age
    if f.max_age_days is not None and f.max_age_days > 0 and item.date is not None:
        cutoff = now - timedelta(days=f.max_age_days)
        item_date = item.date
        if item_date.tzinfo is None:
            item_date = item_date.replace(tzinfo=UTC)
        if item_date < cutoff:
            return False

    # project
    if f.project_ids is not None:
        proj = getattr(item, "origin_project_id", None)
        if not proj or proj not in f.project_ids:
            return False

    return True


__all__ = ["EnrichmentFilters", "apply_filters"]
