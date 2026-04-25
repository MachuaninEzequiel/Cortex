"""
cortex.core
-----------
``AgentMemory`` — the unified public façade for the Cortex memory system.

Architecture (v2.3 — Hexagonal / Services Layer)
-------------------------------------------------
``AgentMemory`` is now a **thin façade**. It wires together the
infrastructure layer (episodic store, semantic store, retriever) and
delegates all business logic to dedicated domain services:

- ``SpecService``    → create_spec_note()
- ``SessionService`` → save_session_note()
- ``PRService``      → store_pr_context(), generate_pr_docs(), write_pr_docs()

The façade keeps a stable public API so that no consumer (CLI, MCP
server, hooks, external code) needs to change.

Infrastructure dependencies are wired via dependency injection in
``__init__``, making each component independently testable.

Quick start::

    memory = AgentMemory()
    memory.remember("Fixed login refresh token bug in auth.ts", tags=["bugfix", "auth"])
    results = memory.retrieve("login bug")
    print(results.to_prompt())
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
from cortex.services.pr_service import PRService
from cortex.services.session_service import SessionService
from cortex.services.spec_service import SpecService
from cortex.workitems.providers.jira import JiraProvider
from cortex.workitems.service import WorkItemService

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


class JiraIntegrationConfig(BaseModel):
    enabled: bool = False
    base_url: str = ""
    email_env: str = "JIRA_EMAIL"
    token_env: str = "JIRA_API_TOKEN"


class IntegrationsConfig(BaseModel):
    jira: JiraIntegrationConfig = Field(default_factory=JiraIntegrationConfig)


class CortexConfig(BaseModel):
    episodic: EpisodicConfig = Field(default_factory=EpisodicConfig)
    semantic: SemanticConfig = Field(default_factory=SemanticConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)


# ------------------------------------------------------------------
# AgentMemory — the public façade
# ------------------------------------------------------------------

class AgentMemory:
    """
    Hybrid cognitive memory for LLM agents.

    Combines:
    - Episodic memory  → vector DB (Chroma by default)
    - Semantic memory  → markdown knowledge base (Obsidian-compatible,
      **vector-embedded** for true semantic search)
    - Hybrid retrieval → cross-source Reciprocal Rank Fusion

    Business logic is delegated to domain services:
    - :class:`~cortex.services.SpecService`
    - :class:`~cortex.services.SessionService`
    - :class:`~cortex.services.PRService`

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

        # --- Infrastructure layer (wired here, injected into services) ---
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

        # --- Domain services (injected with infrastructure dependencies) ---
        self._spec_service = SpecService(
            vault_path=self.config.semantic.vault_path,
            semantic=self.semantic,
            episodic=self.episodic,
        )
        self._session_service = SessionService(
            vault_path=self.config.semantic.vault_path,
            semantic=self.semantic,
            episodic=self.episodic,
        )
        self._pr_service = PRService(
            vault_path=self.config.semantic.vault_path,
            episodic=self.episodic,
        )
        self._workitem_service: WorkItemService | None = None

    # ------------------------------------------------------------------
    # Core memory API
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
        return self.episodic.add(
            content=text,
            memory_type=memory_type,
            tags=tags or [],
            files=files or [],
        )

    def store_memory(
        self,
        content: str,
        memory_id: str | None = None,
        memory_type: str = "general",
        tags: list[str] | None = None,
        files: list[str] | None = None,
    ) -> MemoryEntry:
        """Backward compatibility alias for remember()."""
        # Note: memory_id is ignored in the new implementation as IDs are auto-generated
        return self.remember(content, memory_type=memory_type, tags=tags, files=files)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        use_embeddings: bool = True,
    ) -> RetrievalResult:
        """
        Query both memory layers and return ranked, fused results.

        Uses **true cross-source Reciprocal Rank Fusion** so episodic
        and semantic results compete on the same ranking scale.

        Args:
            query:          Natural-language query string.
            top_k:          Max results (overrides config).
            use_embeddings: If False, skips vector search (bypasses ONNX load).

        Returns:
            RetrievalResult with ranked, deduplicated hits.
        """
        return self.retriever.search(query, top_k=top_k, use_embeddings=use_embeddings)

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
    # Semantic vault API
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Spec workflow — delegated to SpecService
    # ------------------------------------------------------------------

    def create_spec_note(
        self,
        *,
        title: str,
        goal: str,
        requirements: list[str] | None = None,
        files_in_scope: list[str] | None = None,
        constraints: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        tags: list[str] | None = None,
        sync_vault: bool = False,
        remember: bool = True,
    ) -> Path:
        """
        Persist an implementation spec into the vault.

        Delegates to :class:`~cortex.services.SpecService`.
        See its ``create()`` method for full parameter documentation.
        """
        return self._spec_service.create(
            title=title,
            goal=goal,
            requirements=requirements,
            files_in_scope=files_in_scope,
            constraints=constraints,
            acceptance_criteria=acceptance_criteria,
            tags=tags,
            sync_vault=sync_vault,
            remember=remember,
        )

    # ------------------------------------------------------------------
    # Session workflow — delegated to SessionService
    # ------------------------------------------------------------------

    def save_session_note(
        self,
        *,
        title: str,
        spec_summary: str,
        changes_made: list[str] | None = None,
        files_touched: list[str] | None = None,
        key_decisions: list[str] | None = None,
        next_steps: list[str] | None = None,
        tags: list[str] | None = None,
        sync_vault: bool = False,
        remember: bool = True,
    ) -> Path:
        """
        Persist a structured session note into the vault.

        Delegates to :class:`~cortex.services.SessionService`.
        See its ``create()`` method for full parameter documentation.
        """
        return self._session_service.create(
            title=title,
            spec_summary=spec_summary,
            changes_made=changes_made,
            files_touched=files_touched,
            key_decisions=key_decisions,
            next_steps=next_steps,
            tags=tags,
            sync_vault=sync_vault,
            remember=remember,
        )

    # ------------------------------------------------------------------
    # PR / DevSecDocOps workflow — delegated to PRService
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

        Delegates to :class:`~cortex.services.PRService`.

        Args:
            ctx:          The PR context to store.
            lint_result:  ESLint/SAST result.
            audit_result: npm audit/SCA result.
            test_result:  Test suite result.

        Returns:
            The stored MemoryEntry.
        """
        return self._pr_service.store_pr_context(
            ctx,
            lint_result=lint_result,
            audit_result=audit_result,
            test_result=test_result,
        )

    def generate_pr_docs(
        self,
        ctx: PRContext,
        *,
        skip_types: list[str] | None = None,
    ) -> list[GeneratedDoc]:
        """
        Generate fallback documentation from a PR context.

        Delegates to :class:`~cortex.services.PRService`.
        """
        return self._pr_service.generate_pr_docs(ctx, skip_types=skip_types)

    def write_pr_docs(self, docs: list[GeneratedDoc]) -> list[str]:
        """
        Write generated PR documents to the vault.

        Delegates to :class:`~cortex.services.PRService`.
        """
        return self._pr_service.write_pr_docs(docs)

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

    def import_work_item(
        self,
        external_id: str,
        *,
        provider: str = "jira",
        remember: bool = True,
    ) -> Path:
        """Import one tracked item from an optional external provider."""
        return self._get_workitem_service().import_item(
            external_id,
            provider=provider,
            remember=remember,
        )

    def get_work_item_note(self, item_id: str) -> Path:
        """Return the local vault note path for one imported tracked item."""
        return self._get_workitem_service().get_item_note(item_id)

    def list_work_item_notes(self) -> list[Path]:
        """List tracked item notes already imported into ``vault/hu/``."""
        return self._get_workitem_service().list_item_notes()

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
            keywords:      Extracted keywords from the work.
            pr_title:      PR title (if from a PR).
            pr_body:       PR body (if from a PR).
            pr_labels:     PR labels (if from a PR).
            top_k:         Override default max items.

        Returns:
            EnrichedContext with deduplicated, ranked items.
        """
        from cortex.context_enricher import ContextEnricher, ContextObserver

        observer = ContextObserver()
        work = observer.observe_from_files(
            files=changed_files,
            keywords=keywords or [],
            pr_title=pr_title,
            pr_body=pr_body,
            pr_labels=pr_labels or [],
        )

        enricher_config = self._get_enricher_config()
        enricher = ContextEnricher(
            episodic=self.episodic,
            semantic=self.semantic,
            config=enricher_config,
        )
        return enricher.enrich(work, top_k=top_k)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_enricher_config(self):
        """Build ContextEnricherConfig from raw YAML config."""
        from cortex.context_enricher import ContextEnricherConfig
        try:
            raw = self._raw_config.get("context_enricher", {})
            return ContextEnricherConfig(**raw)
        except Exception:
            return ContextEnricherConfig()

    def _get_workitem_service(self) -> WorkItemService:
        if self._workitem_service is None:
            providers = {}
            if self.config.integrations.jira.enabled:
                providers["jira"] = JiraProvider.from_config(self._raw_config)
            self._workitem_service = WorkItemService(
                vault_path=self.config.semantic.vault_path,
                semantic=self.semantic,
                episodic=self.episodic,
                providers=providers,
            )
        return self._workitem_service

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
