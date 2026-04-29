from __future__ import annotations

from pathlib import Path

from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.episodic_source import EpisodicSource
from cortex.webgraph.semantic_source import SemanticSource
from cortex.webgraph.service import WebGraphService


def test_hybrid_snapshot_links_semantic_and_episodic(vault_reader, episodic_store, tmp_path: Path) -> None:
    episodic_store.add(
        "Specification: Auth Login Flow Goal: Refresh tokens and login middleware",
        memory_type="spec",
        tags=["spec", "auth"],
        files=["auth.md"],
    )
    episodic_store.add(
        "Session: Auth Login Flow Specification: Auth Login Flow Changes: Updated auth.md",
        memory_type="session",
        tags=["session", "auth"],
        files=["auth.md"],
    )

    config = WebGraphConfig(enable_semantic_neighbors=False)
    service = WebGraphService(
        tmp_path,
        config=config,
        semantic_source=SemanticSource(tmp_path, reader=vault_reader, embedder=vault_reader._embedder),
        episodic_source=EpisodicSource(tmp_path, store=episodic_store, embedder=episodic_store.embedder),
    )

    snapshot = service.build_snapshot(mode="hybrid", use_cache=False)

    assert any(node.source == "semantic" for node in snapshot.nodes)
    assert any(node.source == "episodic" for node in snapshot.nodes)
    assert any(edge.edge_type == "same_file_reference" for edge in snapshot.edges)


def test_subgraph_is_centered_on_requested_node(vault_reader, episodic_store, tmp_path: Path) -> None:
    episodic_store.add(
        "Specification: Auth Goal: Login flow and middleware",
        memory_type="spec",
        tags=["spec", "auth"],
        files=["auth.md"],
    )
    service = WebGraphService(
        tmp_path,
        config=WebGraphConfig(enable_semantic_neighbors=False),
        semantic_source=SemanticSource(tmp_path, reader=vault_reader, embedder=vault_reader._embedder),
        episodic_source=EpisodicSource(tmp_path, store=episodic_store, embedder=episodic_store.embedder),
    )
    snapshot = service.build_snapshot(mode="hybrid", use_cache=False)
    center = next(node.id for node in snapshot.nodes if node.source == "episodic")

    subgraph = service.get_subgraph(center, depth=1, mode="hybrid")

    assert any(node.id == center for node in subgraph.nodes)
    assert subgraph.stats.node_count <= snapshot.stats.node_count


def test_export_snapshot_writes_json(vault_reader, episodic_store, tmp_path: Path) -> None:
    service = WebGraphService(
        tmp_path,
        config=WebGraphConfig(enable_semantic_neighbors=False),
        semantic_source=SemanticSource(tmp_path, reader=vault_reader, embedder=vault_reader._embedder),
        episodic_source=EpisodicSource(tmp_path, store=episodic_store, embedder=episodic_store.embedder),
    )

    output = tmp_path / "snapshot.json"
    path = service.export_snapshot(output_path=output, mode="semantic", use_cache=False)

    assert path.exists()
    assert '"mode":"semantic"' in path.read_text(encoding="utf-8").replace(" ", "")


def test_enterprise_nodes_are_added_and_scope_filter_works(vault_reader, episodic_store, tmp_path: Path) -> None:
    # Minimal enterprise config
    org_dir = tmp_path / ".cortex"
    org_dir.mkdir(parents=True, exist_ok=True)
    (org_dir / "org.yaml").write_text(
        "schema_version: 1\n"
        "organization:\n"
        "  name: Example Org\n"
        "  profile: small-company\n"
        "memory:\n"
        "  mode: layered\n"
        "  enterprise_vault_path: vault-enterprise\n"
        "  enterprise_memory_path: .memory/enterprise/chroma\n"
        "  enterprise_semantic_enabled: true\n"
        "  enterprise_episodic_enabled: false\n"
        "  project_memory_mode: isolated\n"
        "  branch_isolation_enabled: false\n"
        "  retrieval_default_scope: local\n"
        "  retrieval_local_weight: 1.0\n"
        "  retrieval_enterprise_weight: 1.0\n"
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
    (tmp_path / "vault-enterprise").mkdir()

    config = WebGraphConfig(enable_semantic_neighbors=False)
    service = WebGraphService(
        tmp_path,
        config=config,
        semantic_source=SemanticSource(tmp_path, reader=vault_reader, embedder=vault_reader._embedder),
        episodic_source=EpisodicSource(tmp_path, store=episodic_store, embedder=episodic_store.embedder),
    )

    snapshot = service.build_snapshot(mode="semantic", use_cache=False)
    assert any(node.id == "enterprise:org" for node in snapshot.nodes)
    assert any(node.metadata.get("scope") == "enterprise" for node in snapshot.nodes)

    enterprise_only = service.build_snapshot(mode="semantic", use_cache=False, scope="enterprise")
    assert all(node.metadata.get("scope") == "enterprise" for node in enterprise_only.nodes)
