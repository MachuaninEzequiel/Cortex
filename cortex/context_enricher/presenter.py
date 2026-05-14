"""
cortex.context_enricher.presenter
-----------------------------------
Formats EnrichedContext for different output targets:
  - Markdown: human-readable for PR comments
  - Compact: single-line format for LLM prompt injection
  - JSON: structured for CI/CD pipelines
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.models import EnrichedContext


class ContextPresenter:
    """
    Formats enriched context for different consumers.

    - Markdown for PR comments and CLI display
    - Compact for LLM prompt injection (character-efficient)
    - JSON for CI/CD pipeline consumption
    """

    @staticmethod
    def to_markdown(ctx: EnrichedContext) -> str:
        """
        Format as human-readable markdown for PR comments.

        Shows a summary header + expandable items with metadata.
        """
        if not ctx.items:
            return "🧠 Cortex Context — No related memories found.\n\nThis might be a new area of the codebase."

        parts = [
            f"🧠 Cortex Context — Found {ctx.total_items} related memories",
            f"({ctx.total_searches} searches, {ctx.total_raw_hits} raw hits → {ctx.total_items} unique)\n",
        ]

        for i, item in enumerate(ctx.items, 1):
            source_emoji = "📝" if item.source == "episodic" else "📖"
            source_tag = "EPISODIC" if item.source == "episodic" else "SEMANTIC"

            parts.append(f"{source_emoji} **{i}. {item.title}** [{source_tag}]")

            # Metadata line
            meta_parts = []
            if item.date:
                meta_parts.append(item.date.strftime("%Y-%m-%d"))
            if item.files_mentioned:
                meta_parts.append(", ".join(item.files_mentioned))
            if item.tags:
                meta_parts.append(", ".join(f"`{t}`" for t in item.tags))
            if meta_parts:
                parts.append(f"  {' • '.join(meta_parts)}")

            # Content excerpt
            excerpt = item.content[:200]
            if len(item.content) > 200:
                excerpt += "…"
            parts.append(f"  > {excerpt}")

            # Strategy info
            if item.matched_by:
                strategy_labels = [
                    m.replace("_search", "").replace("_query", "")
                    for m in item.matched_by
                ]
                parts.append(f"  _Matched by: {', '.join(strategy_labels)}_")

            parts.append("")

        parts.append("---")
        parts.append("_Run `cortex context --expand` for full details._")

        return "\n".join(parts)

    @staticmethod
    def to_compact(ctx: EnrichedContext) -> str:
        """
        Format as compact text for LLM prompt injection.

        Character-efficient: single-line per item with pipe-separated metadata.
        """
        if not ctx.items:
            return "🧠 Cortex Context — No related memories found."

        parts = [f"## 🧠 Cortex Context ({ctx.total_items} memories found)\n"]

        for item in ctx.items:
            source_tag = "EPISODIC" if item.source == "episodic" else "SEMANTIC"
            parts.append(f"### {item.title} [{source_tag}]")
            parts.append(item.content[:300].replace("\n", " "))

            meta_parts = []
            if item.files_mentioned:
                meta_parts.append(f"Files: {', '.join(item.files_mentioned)}")
            if item.date:
                meta_parts.append(item.date.strftime("%Y-%m-%d"))
            if item.matched_by:
                strategy_labels = [
                    m.replace("_search", "").replace("_query", "")
                    for m in item.matched_by
                ]
                meta_parts.append(f"Matched by: {', '.join(strategy_labels)}")

            if meta_parts:
                parts.append(" | ".join(meta_parts))
            parts.append("")

        return "\n".join(parts)

    @staticmethod
    def to_markdown_grouped(ctx: "EnrichedContext") -> str:
        """Markdown grouped by ``doc_type`` (Fase 08).

        Groups are sorted by the max ``enriched_score`` of their items. Within
        each group items keep their score-descending order. Items without a
        ``doc_type`` (legacy episodic memories) collapse into an ``OTHER``
        section at the end.
        """
        if not ctx.items:
            return "🧠 Cortex Context — No related memories found."

        from collections import defaultdict

        groups: dict[str, list] = defaultdict(list)
        for item in ctx.items:
            label = (item.doc_type or "OTHER").upper()
            groups[label].append(item)

        ordered = sorted(
            groups.items(),
            key=lambda kv: max(i.enriched_score for i in kv[1]),
            reverse=True,
        )

        parts: list[str] = [
            f"# Cortex Context ({ctx.total_items} items, {ctx.total_chars} chars)\n",
        ]
        for label, items in ordered:
            parts.append(f"\n## {label} ({len(items)} items)")
            for item in items:
                parts.append(f"\n### {item.title}")
                meta = [f"score: {item.enriched_score:.3f}"]
                if item.matched_by:
                    meta.append(f"matched_by: {', '.join(item.matched_by)}")
                if item.matched_section_title:
                    meta.append(f"section: {item.matched_section_title}")
                if item.vault_scope and item.vault_scope != "local":
                    meta.append(f"scope: {item.vault_scope}")
                parts.append(" | ".join(meta))
                excerpt = (item.content or "")[:200]
                if len(item.content or "") > 200:
                    excerpt += "…"
                parts.append(f"> {excerpt}")
        return "\n".join(parts)

    @staticmethod
    def to_compact_grouped(ctx: "EnrichedContext") -> str:
        """Compact format grouped by ``doc_type`` (Fase 08)."""
        if not ctx.items:
            return "🧠 Cortex Context — No related memories found."

        from collections import defaultdict

        groups: dict[str, list] = defaultdict(list)
        for item in ctx.items:
            label = (item.doc_type or "other").lower()
            groups[label].append(item)

        ordered = sorted(
            groups.items(),
            key=lambda kv: max(i.enriched_score for i in kv[1]),
            reverse=True,
        )

        parts: list[str] = [f"## Cortex Context ({ctx.total_items} items)\n"]
        for label, items in ordered:
            parts.append(f"[{label.upper()}]")
            for item in items:
                section = (
                    f" §{item.matched_section_title}"
                    if item.matched_section_title else ""
                )
                parts.append(
                    f"- {item.title}{section} (score={item.enriched_score:.2f})"
                )
                parts.append(f"  {(item.content or '')[:200].replace(chr(10), ' ')}")
            parts.append("")
        return "\n".join(parts)

    @staticmethod
    def to_json(ctx: EnrichedContext) -> str:
        """
        Format as JSON for CI/CD pipeline consumption.

        Returns a JSON string with the full structured context.
        """
        data = {
            "has_context": bool(ctx.items),
            "total_searches": ctx.total_searches,
            "total_raw_hits": ctx.total_raw_hits,
            "total_items": ctx.total_items,
            "total_chars": ctx.total_chars,
            "within_budget": ctx.within_budget,
            "work": {
                "source": ctx.work.source,
                "changed_files": ctx.work.changed_files,
                "detected_domain": ctx.work.detected_domain,
                "domain_confidence": ctx.work.domain_confidence,
                "search_queries": ctx.work.search_queries,
            },
            "items": [
                {
                    "source": item.source,
                    "source_id": item.source_id,
                    "title": item.title,
                    "content": item.content,
                    "score": item.score,
                    "enriched_score": item.enriched_score,
                    "matched_by": item.matched_by,
                    "files_mentioned": item.files_mentioned,
                    "date": item.date.isoformat() if item.date else None,
                    "tags": item.tags,
                    # Structural metadata (Fase 08).
                    "doc_type": item.doc_type,
                    "status": item.status,
                    "vault_scope": item.vault_scope,
                    "origin_project_id": item.origin_project_id,
                    "matched_chunk_id": item.matched_chunk_id,
                    "matched_section_title": item.matched_section_title,
                }
                for item in ctx.items
            ],
        }
        return json.dumps(data, indent=2)
