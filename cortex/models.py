"""
cortex.models
-------------
Shared Pydantic models used across the cortex package.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single episodic memory record."""

    id: str = Field(default_factory=lambda: f"mem_{uuid4().hex[:8]}")
    content: str
    memory_type: str = "general"
    tags: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class SemanticDocument(BaseModel):
    """A parsed markdown note from the vault."""

    path: str
    title: str
    content: str
    links: list[str] = Field(default_factory=list)   # [[wiki-links]]
    tags: list[str] = Field(default_factory=list)    # #tags
    score: float = 0.0


class EpisodicHit(BaseModel):
    """A retrieved episodic memory with its relevance score."""

    entry: MemoryEntry
    score: float


class UnifiedHit(BaseModel):
    """
    A single hit from the unified RRF-fused retrieval.

    Can represent either an episodic memory or a semantic document,
    with a common score space from Reciprocal Rank Fusion.
    """

    source: Literal["episodic", "semantic"]
    score: float
    # Episodic fields (set when source == "episodic")
    entry: MemoryEntry | None = None
    # Semantic fields (set when source == "semantic")
    doc: SemanticDocument | None = None

    @property
    def display_title(self) -> str:
        if self.source == "episodic" and self.entry:
            return f"[{self.entry.memory_type}] {self.entry.content[:100]}"
        elif self.source == "semantic" and self.doc:
            return self.doc.title
        return "(unknown)"

    @property
    def display_content(self) -> str:
        if self.source == "episodic" and self.entry:
            return self.entry.content
        elif self.source == "semantic" and self.doc:
            return self.doc.content
        return ""

    @property
    def display_path(self) -> str:
        if self.source == "episodic" and self.entry:
            return f"id={self.entry.id}, files={', '.join(self.entry.files) or 'none'}"
        elif self.source == "semantic" and self.doc:
            return self.doc.path
        return ""


class RetrievalResult(BaseModel):
    """Combined result from the hybrid retrieval engine."""

    query: str
    episodic_hits: list[EpisodicHit] = Field(default_factory=list)
    semantic_hits: list[SemanticDocument] = Field(default_factory=list)
    unified_hits: list[UnifiedHit] = Field(default_factory=list)

    def to_prompt(self, max_chars: int = 4000) -> str:
        """
        Serialize results into a ready-to-inject LLM prompt string.
        Uses unified (RRF-fused) ranking when available, falls back
        to separate lists otherwise.
        Truncates to max_chars to stay within context limits.
        """
        parts: list[str] = [f"## Context for: '{self.query}'\n"]

        if self.unified_hits:
            # Use the truly fused ranking
            for hit in self.unified_hits:
                if hit.source == "episodic" and hit.entry:
                    e = hit.entry
                    parts.append(
                        f"- [EPISODIC:{e.memory_type}] {e.content}"
                        f"  (files: {', '.join(e.files) or 'none'}, score: {hit.score:.4f})"
                    )
                elif hit.source == "semantic" and hit.doc:
                    d = hit.doc
                    parts.append(f"- [SEMANTIC] **{d.title}** ({d.path})")
                    excerpt = d.content[:300].replace("\n", " ")
                    parts.append(f"  > {excerpt}…")
        else:
            # Fallback to separate lists (backward compat)
            if self.episodic_hits:
                parts.append("### Episodic Memory (past experiences)")
                for hit in self.episodic_hits:
                    e = hit.entry
                    parts.append(
                        f"- [{e.memory_type}] {e.content}"
                        f"  (files: {', '.join(e.files) or 'none'}, score: {hit.score:.2f})"
                    )

            if self.semantic_hits:
                parts.append("\n### Semantic Knowledge (docs / notes)")
                for doc in self.semantic_hits:
                    parts.append(f"- **{doc.title}** ({doc.path})")
                    excerpt = doc.content[:300].replace("\n", " ")
                    parts.append(f"  > {excerpt}…")

        result = "\n".join(parts)
        return result[:max_chars]


# ------------------------------------------------------------------
# PR Context & Documentation models — DevSecDocOps
# ------------------------------------------------------------------

class PRContext(BaseModel):
    """
    Structured context for a pull request.

    Captured automatically from the PR metadata and git diff.
    Used as input for documentation generation and memory storage.
    """

    pr_number: int = 0
    title: str
    body: str = ""
    author: str
    source_branch: str
    target_branch: str = "main"
    commit_sha: str
    files_changed: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    db_migrations: list[str] = Field(default_factory=list)
    api_changes: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    lint_result: str | None = None
    audit_result: str | None = None
    test_result: str | None = None

    def hu_references(self) -> list[str]:
        """Extract HU (user story) references from PR body."""
        import re
        patterns = [
            r"HU[-_]?(\d+)",
            r"(?:user[\s-]?story|us)[-\s](\d+)",
            r"#(\d+)",
        ]
        refs: list[str] = []
        for pattern in patterns:
            refs.extend(f"HU-{m}" for m in re.findall(pattern, self.body, re.IGNORECASE))
        return list(set(refs))

    def has_db_changes(self) -> bool:
        return bool(self.db_migrations) or any(
            "migration" in f or "schema" in f or f.endswith(".sql")
            for f in self.files_changed
        )

    def has_api_changes(self) -> bool:
        return bool(self.api_changes) or any(
            "route" in f or "controller" in f or "endpoint" in f
            for f in self.files_changed
        )

    def has_adr_label(self) -> bool:
        return any("adr" in lbl.lower() or "decision" in lbl.lower() for lbl in self.labels)


class GeneratedDoc(BaseModel):
    """
    A documentation artifact generated by Cortex from a PR.

    Each doc has a type (session, hu, adr, incident, changelog, security)
    and maps to a vault subfolder.
    """

    doc_type: Literal["session", "hu", "adr", "incident", "changelog", "security"]
    title: str
    content: str
    vault_subfolder: str  # e.g. "sessions", "hu", "architecture"
    filename: str  # e.g. "2026-04-13_fix-login-bug.md"

    @property
    def full_path(self) -> str:
        return f"{self.vault_subfolder}/{self.filename}"


# ------------------------------------------------------------------
# Context Enricher models — Proactive Context Engine
# ------------------------------------------------------------------

class WorkContext(BaseModel):
    """
    Structured representation of what the agent is currently working on.

    Produced by the ContextObserver from git diffs, PR metadata, or
    manual input. Feeds the ContextEnricher with search strategies.
    """

    source: Literal["git_diff", "pr", "manual"]
    changed_files: list[str] = Field(default_factory=list)
    new_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    function_names: list[str] = Field(default_factory=list)
    class_names: list[str] = Field(default_factory=list)
    detected_domain: str | None = None
    domain_confidence: float = 0.0
    pr_title: str | None = None
    pr_body: str | None = None
    pr_labels: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)


class EnrichedItem(BaseModel):
    """
    A single enriched context item — a memory that was found relevant
    to the current work, with explainability metadata.
    """

    source: Literal["episodic", "semantic"]
    source_id: str                     # mem_abc123 or vault path
    title: str
    content: str
    score: float                       # Original retrieval score
    enriched_score: float              # After multi-match + co-occurrence boost
    matched_by: list[str] = Field(default_factory=list)  # Strategy names that matched
    files_mentioned: list[str] = Field(default_factory=list)
    date: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class EnrichedContext(BaseModel):
    """
    Full enriched context for a work session or PR.

    Contains deduplicated, ranked items from multiple search strategies,
    with budget tracking.
    """

    work: WorkContext
    items: list[EnrichedItem] = Field(default_factory=list)
    total_searches: int = 0
    total_raw_hits: int = 0
    total_items: int = 0
    total_chars: int = 0
    within_budget: bool = True

    def to_prompt_format(self, *, compact: bool = False, expand: bool = False) -> str:
        """
        Format enriched context for LLM prompt injection.

        Args:
            compact: Use compact single-line format.
            expand: Show full content (truncates to 500 chars per item).
        """
        if not self.items:
            return "🧠 Cortex Context — No related memories found."

        if compact:
            parts = [f"## 🧠 Cortex Context ({self.total_items} memories found)\n"]
            for item in self.items:
                source_tag = "EPISODIC" if item.source == "episodic" else "SEMANTIC"
                parts.append(f"### {item.title} [{source_tag}]")
                parts.append(item.content[:300].replace("\n", " "))
                meta_parts = []
                if item.files_mentioned:
                    meta_parts.append(f"Files: {', '.join(item.files_mentioned)}")
                if item.date:
                    meta_parts.append(item.date.strftime("%Y-%m-%d"))
                if item.matched_by:
                    meta_parts.append(f"Matched by: {', '.join(m.replace('_search', '').replace('_query', '') for m in item.matched_by)}")
                if meta_parts:
                    parts.append(" | ".join(meta_parts))
                parts.append("")
            return "\n".join(parts)

        # Full markdown format
        parts = [f"🧠 Cortex Context — Found {self.total_items} related memories\n"]
        for item in self.items:
            source_tag = "EPISODIC" if item.source == "episodic" else "SEMANTIC"
            parts.append(f"### [{source_tag}] {item.title}")
            meta_parts = []
            if item.date:
                meta_parts.append(item.date.strftime("%Y-%m-%d"))
            if item.files_mentioned:
                meta_parts.append(", ".join(item.files_mentioned))
            if item.tags:
                meta_parts.append(", ".join(item.tags))
            if meta_parts:
                parts.append(f"  {' • '.join(meta_parts)}")

            if expand:
                parts.append(f"  {item.content[:500]}")
            else:
                parts.append(f"  {item.content[:150]}…")

            if item.matched_by:
                parts.append(f"  Matched by: {', '.join(item.matched_by)}")
            parts.append("")

        parts.append("Run `cortex context --expand` for full details")
        return "\n".join(parts)
