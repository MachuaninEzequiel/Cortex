from __future__ import annotations

from pathlib import Path

from cortex.enterprise.config import build_enterprise_org_config
from cortex.enterprise.retrieval_service import EnterpriseRetrievalService
from cortex.models import EpisodicHit, MemoryEntry, SemanticDocument


def test_enterprise_retrieval_service_local_scope_only(monkeypatch) -> None:
    config = build_enterprise_org_config(project_name="Acme", profile="small-company")
    service = EnterpriseRetrievalService(
        enterprise_config=config,
        local_project_id="acme-project",
        project_root=Path.cwd(),
        local_vault_path="vault",
        local_episodic_dir=".memory/chroma",
        local_collection_name="cortex_episodic",
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )

    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiVaultReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            SemanticDocument(path="a.md", title="A", content="local", origin_scope="local", origin_project_id="acme-project", origin_vault="vault")
        ],
    )
    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiEpisodicReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            EpisodicHit(
                entry=MemoryEntry(content="mem", metadata={"scope": "local"}),
                score=0.9,
                origin_scope="local",
                origin_project_id="acme-project",
                origin_persist_dir=".memory/chroma",
            )
        ],
    )

    result = service.search(query="auth", scope="local", top_k=5)
    assert result.unified_hits
    assert all(hit.metadata.get("scope") == "local" for hit in result.unified_hits)


def test_enterprise_retrieval_service_all_scope_has_mixed_sources(monkeypatch) -> None:
    config = build_enterprise_org_config(project_name="Acme", profile="multi-project-team")
    service = EnterpriseRetrievalService(
        enterprise_config=config,
        local_project_id="acme-project",
        project_root=Path.cwd(),
        local_vault_path="vault",
        local_episodic_dir=".memory/chroma",
        local_collection_name="cortex_episodic",
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )

    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiVaultReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            SemanticDocument(path="local.md", title="Local", content="L", origin_scope="local"),
            SemanticDocument(path="ent.md", title="Enterprise", content="E", origin_scope="enterprise"),
        ],
    )
    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiEpisodicReader.search",
        lambda self, query, top_k, use_embeddings=True: [],
    )

    result = service.search(query="policy", scope="all", top_k=5)
    scopes = {hit.metadata.get("scope") for hit in result.unified_hits}
    assert "local" in scopes
    assert "enterprise" in scopes
    assert result.source_breakdown["local"] >= 1
    assert result.source_breakdown["enterprise"] >= 1


def test_enterprise_retrieval_service_filters_by_project_id(monkeypatch) -> None:
    config = build_enterprise_org_config(project_name="Acme", profile="multi-project-team")
    service = EnterpriseRetrievalService(
        enterprise_config=config,
        local_project_id="acme-project",
        project_root=Path.cwd(),
        local_vault_path="vault",
        local_episodic_dir=".memory/chroma",
        local_collection_name="cortex_episodic",
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )

    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiVaultReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            SemanticDocument(path="local.md", title="Local", content="L", origin_scope="local", origin_project_id="acme-project"),
            SemanticDocument(path="ent.md", title="Enterprise", content="E", origin_scope="enterprise", origin_project_id="acme-org"),
        ],
    )
    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiEpisodicReader.search",
        lambda self, query, top_k, use_embeddings=True: [],
    )

    result = service.search(query="policy", scope="all", top_k=5, project_id="acme-project")
    assert result.unified_hits
    assert all(hit.metadata.get("project_id") == "acme-project" for hit in result.unified_hits)


def test_enterprise_retrieval_service_deduplicates_same_semantic_path(monkeypatch) -> None:
    config = build_enterprise_org_config(project_name="Acme", profile="multi-project-team")
    service = EnterpriseRetrievalService(
        enterprise_config=config,
        local_project_id="acme-project",
        project_root=Path.cwd(),
        local_vault_path="vault",
        local_episodic_dir=".memory/chroma",
        local_collection_name="cortex_episodic",
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )

    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiVaultReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            SemanticDocument(path="runbook/auth.md", title="Auth", content="Local", origin_scope="local"),
            SemanticDocument(path="runbook/auth.md", title="Auth", content="Enterprise", origin_scope="enterprise"),
        ],
    )
    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiEpisodicReader.search",
        lambda self, query, top_k, use_embeddings=True: [],
    )

    result = service.search(query="auth", scope="all", top_k=5)
    semantic_hits = [hit for hit in result.unified_hits if hit.source == "semantic"]
    assert len(semantic_hits) == 1


def test_enterprise_retrieval_service_scope_enterprise_without_sources_fails() -> None:
    config = build_enterprise_org_config(project_name="Acme", profile="small-company")
    config.memory.enterprise_semantic_enabled = False
    config.memory.enterprise_episodic_enabled = False
    service = EnterpriseRetrievalService(
        enterprise_config=config,
        local_project_id="acme-project",
        project_root=Path.cwd(),
        local_vault_path="vault",
        local_episodic_dir=".memory/chroma",
        local_collection_name="cortex_episodic",
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )

    try:
        service.search(query="policy", scope="enterprise", top_k=5)
        assert False, "Expected ValueError for enterprise scope without sources"
    except ValueError as exc:
        assert "no enterprise sources" in str(exc).lower()
