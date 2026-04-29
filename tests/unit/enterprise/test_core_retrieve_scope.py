from __future__ import annotations

from pathlib import Path

import pytest

from cortex.core import AgentMemory
from cortex.models import RetrievalResult


class _DummyEpisodicStore:
    def __init__(self, **kwargs):  # noqa: ANN003
        self.kwargs = kwargs


class _DummySummarizer:
    def __init__(self, **kwargs):  # noqa: ANN003
        self.kwargs = kwargs


class _DummyVaultReader:
    def __init__(self, **kwargs):  # noqa: ANN003
        self.kwargs = kwargs


class _DummyHybridSearch:
    def __init__(self, **kwargs):  # noqa: ANN003
        self.kwargs = kwargs

    def search(self, query: str, top_k: int | None = None, use_embeddings: bool = True) -> RetrievalResult:
        return RetrievalResult(query=query)


class _DummyService:
    def __init__(self, **kwargs):  # noqa: ANN003
        self.kwargs = kwargs


def _write_minimal_config(root: Path) -> None:
    (root / "config.yaml").write_text(
        "episodic:\n"
        "  persist_dir: .memory/chroma\n"
        "  collection_name: cortex_episodic\n"
        "  embedding_model: all-MiniLM-L6-v2\n"
        "  embedding_backend: onnx\n"
        "semantic:\n"
        "  vault_path: vault\n"
        "retrieval:\n"
        "  top_k: 5\n"
        "  episodic_weight: 1.0\n"
        "  semantic_weight: 1.0\n",
        encoding="utf-8",
    )


def test_agent_memory_retrieve_enterprise_scope_requires_org_config(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_config(tmp_path)
    monkeypatch.setattr("cortex.core.EpisodicMemoryStore", _DummyEpisodicStore)
    monkeypatch.setattr("cortex.core.Summarizer", _DummySummarizer)
    monkeypatch.setattr("cortex.core.VaultReader", _DummyVaultReader)
    monkeypatch.setattr("cortex.core.HybridSearch", _DummyHybridSearch)
    monkeypatch.setattr("cortex.core.SpecService", _DummyService)
    monkeypatch.setattr("cortex.core.SessionService", _DummyService)
    monkeypatch.setattr("cortex.core.PRService", _DummyService)

    memory = AgentMemory(config_path=tmp_path / "config.yaml")
    with pytest.raises(ValueError):
        memory.retrieve("auth", scope="enterprise")


def test_agent_memory_retrieve_local_scope_uses_hybrid_search(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_config(tmp_path)
    called = {"hybrid": False}

    class _Hybrid(_DummyHybridSearch):
        def search(self, query: str, top_k: int | None = None, use_embeddings: bool = True) -> RetrievalResult:
            called["hybrid"] = True
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.core.EpisodicMemoryStore", _DummyEpisodicStore)
    monkeypatch.setattr("cortex.core.Summarizer", _DummySummarizer)
    monkeypatch.setattr("cortex.core.VaultReader", _DummyVaultReader)
    monkeypatch.setattr("cortex.core.HybridSearch", _Hybrid)
    monkeypatch.setattr("cortex.core.SpecService", _DummyService)
    monkeypatch.setattr("cortex.core.SessionService", _DummyService)
    monkeypatch.setattr("cortex.core.PRService", _DummyService)

    memory = AgentMemory(config_path=tmp_path / "config.yaml")
    memory.retrieve("auth", scope="local")
    assert called["hybrid"] is True


def test_agent_memory_retrieve_uses_org_default_scope_when_none(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_config(tmp_path)
    (tmp_path / ".cortex").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".cortex" / "org.yaml").write_text(
        "schema_version: 1\n"
        "organization:\n"
        "  name: Acme Org\n"
        "  profile: multi-project-team\n"
        "memory:\n"
        "  mode: layered\n"
        "  enterprise_vault_path: vault-enterprise\n"
        "  enterprise_memory_path: .memory/enterprise/chroma\n"
        "  enterprise_semantic_enabled: true\n"
        "  enterprise_episodic_enabled: false\n"
        "  project_memory_mode: isolated\n"
        "  branch_isolation_enabled: false\n"
        "  retrieval_default_scope: all\n"
        "promotion:\n"
        "  enabled: true\n"
        "  allowed_doc_types: [spec, decision, runbook, hu, incident]\n"
        "  require_review: true\n"
        "  default_targets: [enterprise_vault]\n"
        "governance:\n"
        "  git_policy: balanced\n"
        "  ci_profile: advisory\n"
        "  version_sessions_in_git: false\n"
        "integration:\n"
        "  github_actions_enabled: true\n"
        "  webgraph_workspace_enabled: true\n"
        "  ide_profiles: []\n",
        encoding="utf-8",
    )

    captured = {"scope": None}

    class _EnterpriseService:
        def __init__(self, **kwargs):  # noqa: ANN003
            self.kwargs = kwargs

        def search(self, *, query, scope, top_k, use_embeddings=True, project_id=None):  # noqa: ANN001
            captured["scope"] = scope
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.core.EpisodicMemoryStore", _DummyEpisodicStore)
    monkeypatch.setattr("cortex.core.Summarizer", _DummySummarizer)
    monkeypatch.setattr("cortex.core.VaultReader", _DummyVaultReader)
    monkeypatch.setattr("cortex.core.HybridSearch", _DummyHybridSearch)
    monkeypatch.setattr("cortex.core.SpecService", _DummyService)
    monkeypatch.setattr("cortex.core.SessionService", _DummyService)
    monkeypatch.setattr("cortex.core.PRService", _DummyService)
    monkeypatch.setattr("cortex.core.EnterpriseRetrievalService", _EnterpriseService)

    memory = AgentMemory(config_path=tmp_path / "config.yaml")
    memory.retrieve("auth", scope=None)
    assert captured["scope"] == "all"
