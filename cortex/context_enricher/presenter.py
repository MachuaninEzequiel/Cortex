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
                }
                for item in ctx.items
            ],
        }
        return json.dumps(data, indent=2)
