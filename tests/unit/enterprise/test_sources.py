from __future__ import annotations

from cortex.enterprise.sources import EpisodicSource, MultiEpisodicReader, MultiVaultReader, VaultSource
from cortex.models import EpisodicHit, MemoryEntry, SemanticDocument


def test_multi_vault_reader_one_source(monkeypatch) -> None:
    monkeypatch.setattr(
        "cortex.enterprise.sources.VaultReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            SemanticDocument(path="a.md", title="A", content="x")
        ],
    )
    reader = MultiVaultReader(
        sources=[VaultSource(path="vault", scope="local", project_id="proj-a")],
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )
    hits = reader.search("auth", top_k=5)
    assert len(hits) == 1
    assert hits[0].origin_scope == "local"
    assert hits[0].origin_project_id == "proj-a"


def test_multi_vault_reader_three_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        "cortex.enterprise.sources.VaultReader.search",
        lambda self, query, top_k, use_embeddings=True: [
            SemanticDocument(path=f"{self.vault_path}/a.md", title="A", content="x")
        ],
    )
    reader = MultiVaultReader(
        sources=[
            VaultSource(path="vault-a", scope="local", project_id="a"),
            VaultSource(path="vault-b", scope="enterprise", project_id="b"),
            VaultSource(path="vault-c", scope="enterprise", project_id="c"),
        ],
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )
    hits = reader.search("auth", top_k=5)
    assert len(hits) == 3


def test_multi_episodic_reader_two_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        "cortex.enterprise.sources.EpisodicMemoryStore.search",
        lambda self, query, top_k, use_embeddings=True: [
            EpisodicHit(entry=MemoryEntry(content="memo"), score=0.9)
        ],
    )
    reader = MultiEpisodicReader(
        sources=[
            EpisodicSource(
                persist_dir=".memory/chroma",
                scope="local",
                project_id="proj-a",
                collection_name="cortex_local",
            ),
            EpisodicSource(
                persist_dir=".memory/enterprise/chroma",
                scope="enterprise",
                project_id="proj-org",
                collection_name="cortex_enterprise",
            ),
        ],
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )
    hits = reader.search("auth", top_k=5)
    assert len(hits) == 2
    scopes = {h.origin_scope for h in hits}
    assert "local" in scopes and "enterprise" in scopes
