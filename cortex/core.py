"""
cortex.core
-----------
Main AgentMemory class. Unified interface that wires together
episodic memory, semantic memory and the hybrid retrieval engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from cortex.episodic.memory_store import EpisodicMemoryStore
from cortex.episodic.summarizer import Summarizer
from cortex.models import (
    EnrichedContext,
    GeneratedDoc,
    MemoryEntry,
    PRContext,
    RetrievalResult,
)
from cortex.retrieval.hybrid_search import HybridSearch
from cortex.semantic.vault_reader import VaultReader

# ------------------------------------------------------------------
# Config models — validated with Pydantic
# ------------------------------------------------------------------

class EpisodicConfig(BaseModel):
    persist_dir: str = ".memory/chroma"
    collection_name: str = "cortex_episodic"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_backend: Literal["onnx", "local", "openai"] = "onnx"


class SemanticConfig(BaseModel):
    vault_path: str = "vault"


class RetrievalConfig(BaseModel):
    top_k: int = Field(default=5, ge=1, le=100)
    episodic_weight: float = Field(default=1.0, gt=0)
    semantic_weight: float = Field(default=1.0, gt=0)


class LLMConfig(BaseModel):
    provider: Literal["none", "openai", "anthropic", "ollama"] = "none"
    model: str = ""


class CortexConfig(BaseModel):
    episodic: EpisodicConfig = Field(default_factory=EpisodicConfig)
    semantic: SemanticConfig = Field(default_factory=SemanticConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


class AgentMemory:
    """
    Hybrid cognitive memory for LLM agents.

    Combines:
    - Episodic memory  → vector DB (Chroma by default)
    - Semantic memory  → markdown knowledge base (Obsidian-compatible,
      **vector-embedded** for true semantic search)
    - Hybrid retrieval → cross-source Reciprocal Rank Fusion

    Quick start::

        memory = AgentMemory()
        memory.remember("Fixed login refresh token bug in auth.ts", tags=["bugfix", "auth"])
        results = memory.retrieve("login bug")
        print(results.to_prompt())
    """

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        self._config_path = Path(config_path)
        self._raw_config = self._load_config(self._config_path)
        self.config = self._validate_config(self._raw_config)

        self.episodic = EpisodicMemoryStore(
            persist_dir=self.config.episodic.persist_dir,
            embedding_model=self.config.episodic.embedding_model,
            embedding_backend=self.config.episodic.embedding_backend,
            collection_name=self.config.episodic.collection_name,
        )
        self.summarizer = Summarizer(
            provider=self.config.llm.provider,
            model=self.config.llm.model,
        )
        self.semantic = VaultReader(
            vault_path=self.config.semantic.vault_path,
            embedding_model=self.config.episodic.embedding_model,
            embedding_backend=self.config.episodic.embedding_backend,
        )
        self.retriever = HybridSearch(
            episodic=self.episodic,
            semantic=self.semantic,
            top_k=self.config.retrieval.top_k,
            episodic_weight=self.config.retrieval.episodic_weight,
            semantic_weight=self.config.retrieval.semantic_weight,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        *,
        memory_type: str = "general",
        tags: list[str] | None = None,
        files: list[str] | None = None,
        summarize: bool = False,
    ) -> MemoryEntry:
        """
        Store a new episodic memory.

        Args:
            content:     Raw description of what happened / was done.
            memory_type: Category label (e.g. "bugfix", "feature", "conversation").
            tags:        Optional list of tags for filtering.
            files:       Source files involved in the operation.
            summarize:   If True, compress content with LLM before storing.

        Returns:
            The stored MemoryEntry with its generated ID.
        """
        text = self.summarizer.compress(content) if summarize else content
        entry = self.episodic.add(
            content=text,
            memory_type=memory_type,
            tags=tags or [],
            files=files or [],
        )
        return entry

    def retrieve(self, query: str, *, top_k: int | None = None) -> RetrievalResult:
        """
        Query both memory layers and return ranked, fused results.

        Uses **true cross-source Reciprocal Rank Fusion** so episodic
        and semantic results compete on the same ranking scale.

        Args:
            query:  Natural-language query string.
            top_k:  Override default top-k from config.

        Returns:
            RetrievalResult with episodic hits, semantic hits, and
            a unified RRF-fused list accessible via ``result.unified_hits``
            and ``result.to_prompt()``.
        """
        return self.retriever.search(query, top_k=top_k)

    def create_note(
        self,
        title: str,
        content: str,
        *,
        tags: list[str] | None = None,
        subfolder: str = "",
    ) -> Path:
        """
        Create a new markdown note in the semantic vault.

        This is a convenience delegation to ``self.semantic.create_note``.

        Args:
            title:      Note title.
            content:    Markdown body.
            tags:       Front-matter tags.
            subfolder:  Optional subdirectory inside the vault.

        Returns:
            Path to the newly created file.
        """
        return self.semantic.create_note(title, content, tags=tags, subfolder=subfolder)

    def sync_vault(self) -> int:
        """
        Re-index the markdown vault (parse + embed all documents).

        Returns:
            Number of documents indexed.
        """
        return self.semantic.sync()

    def forget(self, memory_id: str) -> bool:
        """Delete a specific episodic memory by ID."""
        return self.episodic.delete(memory_id)

    def stats(self) -> dict[str, Any]:
        """Return basic stats about both memory stores."""
        return {
            "episodic_count": self.episodic.count(),
            "semantic_docs": self.semantic.count(),
            "vault_path": str(self.semantic.vault_path),
            "persist_dir": str(self.episodic.persist_dir),
        }

    # ------------------------------------------------------------------
    # PR Context & Documentation methods — DevSecDocOps
    # ------------------------------------------------------------------

    def store_pr_context(
        self,
        ctx: PRContext,
        *,
        lint_result: str | None = None,
        audit_result: str | None = None,
        test_result: str | None = None,
    ) -> MemoryEntry:
        """
        Store a PR context as an episodic memory.

        Args:
            ctx: The PR context to store.
            lint_result: ESLint/SAST result.
            audit_result: npm audit/SCA result.
            test_result: Test suite result.

        Returns:
            The stored MemoryEntry.
        """
        from cortex.pr_capture import enrich_with_pipeline

        ctx = enrich_with_pipeline(
            ctx,
            lint_result=lint_result,
            audit_result=audit_result,
            test_result=test_result,
        )

        summary = (
            f"PR #{ctx.pr_number}: {ctx.title} by {ctx.author} "
            f"({ctx.source_branch} -> {ctx.target_branch})"
        )
        content_parts = [summary]
        if ctx.body:
            content_parts.append(f"\nDescription: {ctx.body[:500]}")
        if ctx.diff_summary:
            content_parts.append(f"\nDiff:\n{ctx.diff_summary}")
        content_parts.append(f"\nLint: {ctx.lint_result or 'n/a'}")
        content_parts.append(f"\nAudit: {ctx.audit_result or 'n/a'}")
        content_parts.append(f"\nTests: {ctx.test_result or 'n/a'}")

        return self.remember(
            content="\n".join(content_parts),
            memory_type="pr",
            tags=["pr", ctx.author] + ctx.labels,
            files=ctx.files_changed[:20],
        )

    def generate_pr_docs(
        self,
        ctx: PRContext,
        *,
        skip_types: list[str] | None = None,
    ) -> list[GeneratedDoc]:
        """
        Generate documentation from a PR context.

        Args:
            ctx: The PR context to generate from.
            skip_types: Document types to skip.

        Returns:
            List of GeneratedDoc objects (not yet written to disk).
        """
        from cortex.doc_generator import DocGenerator

        gen = DocGenerator(vault_path=self.config.semantic.vault_path)
        return gen.generate_all(ctx, skip_types=skip_types or [])

    def write_pr_docs(self, docs: list[GeneratedDoc]) -> list[str]:
        """
        Write generated PR documents to the vault.

        Args:
            docs: List of GeneratedDoc to write.

        Returns:
            List of written file paths.
        """
        from cortex.doc_generator import DocGenerator

        gen = DocGenerator(vault_path=self.config.semantic.vault_path)
        written = gen.write_docs(docs)
        return [str(p) for p in written]

    def get_pr_context(self, query: str, *, top_k: int = 3) -> RetrievalResult:
        """
        Search for past PRs similar to the current one.

        Args:
            query: Natural language query (e.g. PR title + body).
            top_k: Max results.

        Returns:
            RetrievalResult with related memories.
        """
        return self.retrieve(query, top_k=top_k)

    # ------------------------------------------------------------------
    # Context Enricher — Proactive context injection
    # ------------------------------------------------------------------

    def enrich(
        self,
        changed_files: list[str],
        keywords: list[str] | None = None,
        pr_title: str | None = None,
        pr_body: str | None = None,
        pr_labels: list[str] | None = None,
        *,
        top_k: int | None = None,
    ) -> EnrichedContext:
        """
        Proactively search and build enriched context.

        Observes the work context, executes multi-strategy search,
        deduplicates, ranks, and returns enriched context ready
        for LLM prompt injection.

        Args:
            changed_files: Files being modified.
            keywords: Extracted keywords from the work.
            pr_title: PR title (if from a PR).
            pr_body: PR body (if from a PR).
            pr_labels: PR labels (if from a PR).
            top_k: Override default max items.

        Returns:
            EnrichedContext with deduplicated, ranked items.
        """
        from cortex.context_enricher import (
            ContextEnricher,
            ContextObserver,
        )

        # Build observer input
        observer = ContextObserver()
        work = observer.observe_from_files(
            files=changed_files,
            keywords=keywords or [],
            pr_title=pr_title,
            pr_body=pr_body,
            pr_labels=pr_labels or [],
        )

        # Get config from YAML if available
        enricher_config = self._get_enricher_config()

        # Enrich
        enricher = ContextEnricher(
            episodic=self.episodic,
            semantic=self.semantic,
            config=enricher_config,
        )
        return enricher.enrich(work, top_k=top_k)

    def _get_enricher_config(self):
        """
        Build ContextEnricherConfig from YAML config.

        Falls back to defaults if the section is missing.
        """
        from cortex.context_enricher import ContextEnricherConfig

        try:
            raw = self._raw_config.get("context_enricher", {})
            return ContextEnricherConfig(**raw)
        except Exception:
            return ContextEnricherConfig()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(
                f"Config file not found: {path}. Run `cortex init` first."
            )
        with open(path) as f:
            return yaml.safe_load(f)

    @staticmethod
    def _validate_config(raw: dict) -> CortexConfig:
        """
        Validate and normalise config using Pydantic.

        Accepts a plain dict (from YAML) and raises clear errors
        if values are invalid (e.g. negative top_k, unknown provider).
        """
        return CortexConfig.model_validate(raw)
