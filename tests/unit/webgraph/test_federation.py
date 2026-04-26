from __future__ import annotations

from pathlib import Path

from cortex.webgraph.federation import FederatedWebGraphService, load_workspace_projects


def _init_project(root: Path) -> None:
    (root / "vault").mkdir(parents=True, exist_ok=True)
    (root / ".memory" / "chroma").mkdir(parents=True, exist_ok=True)
    (root / "config.yaml").write_text(
        "episodic:\n"
        "  persist_dir: .memory/chroma\n"
        "semantic:\n"
        "  vault_path: vault\n",
        encoding="utf-8",
    )


def test_load_workspace_projects(tmp_path: Path) -> None:
    project_a = tmp_path / "app-a"
    project_b = tmp_path / "app-b"
    _init_project(project_a)
    _init_project(project_b)

    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        "projects:\n"
        f"  - id: app-a\n    root: {project_a.as_posix()}\n"
        f"  - id: app-b\n    root: {project_b.as_posix()}\n",
        encoding="utf-8",
    )

    projects = load_workspace_projects(workspace)
    assert [p.project_id for p in projects] == ["app-a", "app-b"]


def test_federated_snapshot_builds(tmp_path: Path) -> None:
    project_a = tmp_path / "app-a"
    project_b = tmp_path / "app-b"
    _init_project(project_a)
    _init_project(project_b)
    (project_a / "vault" / "architecture.md").write_text("# A", encoding="utf-8")
    (project_b / "vault" / "architecture.md").write_text("# B", encoding="utf-8")

    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        "projects:\n"
        f"  - id: app-a\n    root: {project_a.as_posix()}\n"
        f"  - id: app-b\n    root: {project_b.as_posix()}\n",
        encoding="utf-8",
    )

    service = FederatedWebGraphService(workspace)
    snapshot = service.build_snapshot(mode="semantic", use_cache=False)

    assert snapshot.stats.node_count >= 2
    assert all("::" in node.id for node in snapshot.nodes)
    assert all(node.metadata.get("project_id") in {"app-a", "app-b"} for node in snapshot.nodes)


def test_workspace_projects_support_explicit_vault_and_memory_paths(tmp_path: Path) -> None:
    project = tmp_path / "app-a"
    _init_project(project)
    custom_vault = project / "knowledge"
    custom_memory = project / "runtime-memory"
    custom_vault.mkdir()
    custom_memory.mkdir()

    workspace = tmp_path / "workspace.yaml"
    workspace.write_text(
        "projects:\n"
        f"  - id: app-a\n    root: {project.as_posix()}\n"
        "    vault: knowledge\n"
        "    memory: runtime-memory\n",
        encoding="utf-8",
    )

    [loaded] = load_workspace_projects(workspace)

    assert loaded.vault_path == custom_vault.resolve()
    assert loaded.memory_path == custom_memory.resolve()
