from __future__ import annotations

import time
from pathlib import Path

from cortex.enterprise.config import build_enterprise_org_config
from cortex.enterprise.retrieval_service import EnterpriseRetrievalService
from cortex.models import EpisodicHit, MemoryEntry, SemanticDocument


def test_enterprise_retrieval_smoke_performance(monkeypatch) -> None:
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
            SemanticDocument(path=f"doc-{i}.md", title=f"D{i}", content="semantic", origin_scope="local")
            for i in range(20)
        ],
    )
    monkeypatch.setattr(
        "cortex.enterprise.sources.MultiEpisodicReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            EpisodicHit(entry=MemoryEntry(content=f"episodic-{i}"), score=0.9, origin_scope="enterprise")
            for i in range(20)
        ],
    )

    start = time.perf_counter()
    result = service.search(query="auth", scope="all", top_k=10)
    elapsed = time.perf_counter() - start

    assert len(result.unified_hits) <= 10
    assert elapsed < 0.5
