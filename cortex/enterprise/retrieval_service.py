from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cortex.enterprise.models import EnterpriseOrgConfig, RetrievalScope
from cortex.enterprise.sources import EpisodicSource, MultiEpisodicReader, MultiVaultReader, VaultSource
from cortex.models import EpisodicHit, RetrievalResult, SemanticDocument, UnifiedHit

_RRF_K = 60


@dataclass(frozen=True)
class RetrievalSourceConfig:
    local_weight: float = 1.0
    enterprise_weight: float = 1.0


class EnterpriseRetrievalService:
    def __init__(
        self,
        *,
        enterprise_config: EnterpriseOrgConfig,
        local_project_id: str,
        project_root: Path,
        local_vault_path: str,
        local_episodic_dir: str,
        local_collection_name: str,
        embedding_model: str,
        embedding_backend: str,
        source_config: RetrievalSourceConfig | None = None,
    ) -> None:
        self.enterprise_config = enterprise_config
        self.local_project_id = local_project_id
        self.project_root = project_root.resolve()
        self.local_vault_path = local_vault_path
        self.local_episodic_dir = local_episodic_dir
        self.local_collection_name = local_collection_name
        self.embedding_model = embedding_model
        self.embedding_backend = embedding_backend
        self.source_config = source_config or RetrievalSourceConfig()

    def search(
        self,
        *,
        query: str,
        scope: RetrievalScope,
        top_k: int,
        use_embeddings: bool = True,
        project_id: str | None = None,
    ) -> RetrievalResult:
        vault_sources = self._build_vault_sources(scope)
        episodic_sources = self._build_episodic_sources(scope)
        if scope == "enterprise" and not vault_sources and not episodic_sources:
            raise ValueError(
                "Enterprise scope requested but no enterprise sources are enabled "
                "(enterprise_semantic_enabled / enterprise_episodic_enabled)."
            )

        semantic_hits = MultiVaultReader(
            sources=vault_sources,
            embedding_model=self.embedding_model,
            embedding_backend=self.embedding_backend,
        ).search(query, top_k=top_k, use_embeddings=use_embeddings)

        episodic_hits = MultiEpisodicReader(
            sources=episodic_sources,
            embedding_model=self.embedding_model,
            embedding_backend=self.embedding_backend,
        ).search(query, top_k=top_k, use_embeddings=use_embeddings)

        if project_id:
            semantic_hits = [hit for hit in semantic_hits if hit.origin_project_id == project_id]
            episodic_hits = [hit for hit in episodic_hits if hit.origin_project_id == project_id]

        unified_hits = self._fuse_multi_scope(episodic_hits, semantic_hits, top_k=top_k)
        source_breakdown = self._build_source_breakdown(unified_hits)
        return RetrievalResult(
            query=query,
            episodic_hits=episodic_hits[:top_k],
            semantic_hits=semantic_hits[:top_k],
            unified_hits=unified_hits,
            source_breakdown=source_breakdown,
        )

    def _build_vault_sources(self, scope: RetrievalScope) -> list[VaultSource]:
        sources: list[VaultSource] = []
        if scope in ("local", "all"):
            sources.append(
                VaultSource(path=self.local_vault_path, scope="local", project_id=self.local_project_id)
            )
        if scope in ("enterprise", "all") and self.enterprise_config.memory.enterprise_semantic_enabled:
            enterprise_vault = self.enterprise_config.resolve_enterprise_vault_path(self.project_root)
            if enterprise_vault is None:
                return sources
            sources.append(
                VaultSource(
                    path=str(enterprise_vault),
                    scope="enterprise",
                    project_id=self.enterprise_config.organization.slug,
                )
            )
        return sources

    def _build_episodic_sources(self, scope: RetrievalScope) -> list[EpisodicSource]:
        sources: list[EpisodicSource] = []
        if scope in ("local", "all"):
            sources.append(
                EpisodicSource(
                    persist_dir=self.local_episodic_dir,
                    scope="local",
                    project_id=self.local_project_id,
                    collection_name=self.local_collection_name,
                )
            )
        if scope in ("enterprise", "all") and self.enterprise_config.memory.enterprise_episodic_enabled:
            enterprise_memory = self.enterprise_config.resolve_enterprise_memory_path(self.project_root)
            if enterprise_memory is None:
                return sources
            sources.append(
                EpisodicSource(
                    persist_dir=str(enterprise_memory),
                    scope="enterprise",
                    project_id=self.enterprise_config.organization.slug,
                    collection_name=f"{self.local_collection_name}_enterprise",
                )
            )
        return sources

    def _fuse_multi_scope(
        self,
        episodic_hits: list[EpisodicHit],
        semantic_hits: list[SemanticDocument],
        *,
        top_k: int,
    ) -> list[UnifiedHit]:
        scores: dict[str, float] = {}
        unified_map: dict[str, UnifiedHit] = {}

        for rank, hit in enumerate(episodic_hits, start=1):
            weight = self._scope_weight(hit.origin_scope)
            key = self._episodic_key(hit)
            scores[key] = scores.get(key, 0.0) + weight * (1.0 / (_RRF_K + rank))
            existing = unified_map.get(key)
            candidate = UnifiedHit(
                source="episodic",
                score=0.0,
                entry=hit.entry,
                metadata={
                    "scope": hit.origin_scope,
                    "project_id": hit.origin_project_id,
                    "origin_vault": hit.origin_vault,
                    "origin_persist_dir": hit.origin_persist_dir,
                },
            )
            if existing is None:
                unified_map[key] = candidate
            elif existing.metadata.get("scope") != "enterprise" and hit.origin_scope == "enterprise":
                unified_map[key] = candidate

        for rank, doc in enumerate(semantic_hits, start=1):
            weight = self._scope_weight(doc.origin_scope)
            key = self._semantic_key(doc)
            scores[key] = scores.get(key, 0.0) + weight * (1.0 / (_RRF_K + rank))
            existing = unified_map.get(key)
            candidate = UnifiedHit(
                source="semantic",
                score=0.0,
                doc=doc,
                metadata={
                    "scope": doc.origin_scope,
                    "project_id": doc.origin_project_id,
                    "origin_vault": doc.origin_vault,
                    "origin_persist_dir": doc.origin_persist_dir,
                },
            )
            if existing is None:
                unified_map[key] = candidate
            elif existing.metadata.get("scope") != "enterprise" and doc.origin_scope == "enterprise":
                unified_map[key] = candidate

        ranked_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
        output: list[UnifiedHit] = []
        for key in ranked_keys[:top_k]:
            hit = unified_map[key]
            output.append(hit.model_copy(update={"score": scores[key]}))
        return output

    def _scope_weight(self, scope: str) -> float:
        if scope == "enterprise":
            return self.source_config.enterprise_weight
        return self.source_config.local_weight

    @staticmethod
    def _semantic_key(doc: SemanticDocument) -> str:
        path = (doc.path or "").strip().lower()
        title = (doc.title or "").strip().lower()
        if path:
            return f"semantic:{path}"
        return f"semantic:title:{title}"

    @staticmethod
    def _episodic_key(hit: EpisodicHit) -> str:
        content = " ".join(hit.entry.content.split()).strip().lower()
        if not content:
            return f"episodic:{hit.entry.id}"
        return f"episodic:content:{content[:160]}"

    def _build_source_breakdown(self, unified_hits: list[UnifiedHit]) -> dict[str, int]:
        breakdown: dict[str, int] = {"local": 0, "enterprise": 0}
        for hit in unified_hits:
            scope = str(hit.metadata.get("scope", "local"))
            breakdown[scope] = breakdown.get(scope, 0) + 1
        return breakdown
