"""
Tests for cortex.workspace.layout.WorkspaceLayout.

Covers discovery, new-layout paths, legacy-layout paths,
resolve_workspace_relative, and edge cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cortex.workspace.layout import WorkspaceLayout, _find_git_root


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────

@pytest.fixture
def new_layout_project(tmp_path: Path) -> dict:
    """Create a minimal new-layout project on disk."""
    repo = tmp_path / "myproject"
    repo.mkdir()
    cortex = repo / ".cortex"
    cortex.mkdir()
    (cortex / "config.yaml").write_text("episodic:\n  persist_dir: memory\n", encoding="utf-8")
    (cortex / "vault").mkdir()
    (cortex / "workspace.yaml").write_text(
        yaml.safe_dump({"layout_version": 2, "projects": [{"id": "primary", "path": ".", "role": "owner"}]}),
        encoding="utf-8",
    )
    (repo / ".git").mkdir()  # fake git root marker
    return {"repo": repo, "cortex": cortex}


@pytest.fixture
def new_layout_project_no_workspace_yaml(tmp_path: Path) -> dict:
    """New layout project without workspace.yaml (setup in progress)."""
    repo = tmp_path / "myproject"
    repo.mkdir()
    cortex = repo / ".cortex"
    cortex.mkdir()
    (cortex / "config.yaml").write_text("episodic:\n  persist_dir: memory\n", encoding="utf-8")
    (cortex / "vault").mkdir()
    # No .cortex/config.yaml at root → this is new layout
    assert not (repo / "config.yaml").exists()
    (repo / ".git").mkdir()
    return {"repo": repo, "cortex": cortex}


@pytest.fixture
def legacy_layout_project(tmp_path: Path) -> dict:
    """Create a minimal legacy-layout project on disk."""
    repo = tmp_path / "legacyproject"
    repo.mkdir()
    (repo / "config.yaml").write_text("episodic:\n  persist_dir: .memory/chroma\n", encoding="utf-8")
    (repo / "vault").mkdir()
    (repo / ".memory").mkdir()
    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "org.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    (cortex_dir / "skills").mkdir()
    (cortex_dir / "subagents").mkdir()
    (repo / ".git").mkdir()
    return {"repo": repo, "cortex": cortex_dir}


# ────────────────────────────────────────────────────────────────────
# Discovery tests
# ────────────────────────────────────────────────────────────────────

class TestDiscovery:
    """Tests for WorkspaceLayout.discover()."""

    def test_discover_new_layout_with_workspace_yaml(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        assert layout.is_new_layout is True
        assert layout.is_legacy_layout is False
        assert layout.workspace_root == new_layout_project["cortex"]
        assert layout.repo_root == new_layout_project["repo"]

    def test_discover_new_layout_from_subdirectory(self, new_layout_project):
        sub = new_layout_project["cortex"] / "vault" / "sessions"
        sub.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout.discover(sub)
        assert layout.is_new_layout is True
        assert layout.workspace_root == new_layout_project["cortex"]

    def test_discover_legacy_layout(self, legacy_layout_project):
        layout = WorkspaceLayout.discover(legacy_layout_project["repo"])
        assert layout.is_legacy_layout is True
        assert layout.is_new_layout is False
        assert layout.workspace_root == legacy_layout_project["repo"]
        assert layout.repo_root == legacy_layout_project["repo"]

    def test_discover_legacy_from_subdirectory(self, legacy_layout_project):
        sub = legacy_layout_project["repo"] / "vault" / "specs"
        sub.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout.discover(sub)
        assert layout.is_legacy_layout is True

    def test_discover_bootstrap_no_project(self, tmp_path):
        empty = tmp_path / "nowhere"
        empty.mkdir()
        layout = WorkspaceLayout.discover(empty)
        # Bootstrap returns new layout pointing at start (or git root)
        assert layout.is_new_layout is True

    def test_discover_prefers_new_over_legacy_both_present(self, tmp_path):
        """If both config.yaml at root AND .cortex/config.yaml exist,
        new layout should win because the inner config.yaml is found first."""
        repo = tmp_path / "both"
        repo.mkdir()
        # Legacy marker
        (repo / "config.yaml").write_text("legacy: true\n", encoding="utf-8")
        (repo / "vault").mkdir()
        # New layout marker — this takes precedence
        cortex = repo / ".cortex"
        cortex.mkdir()
        (cortex / "config.yaml").write_text("new: true\n", encoding="utf-8")
        (cortex / "workspace.yaml").write_text(
            yaml.safe_dump({"layout_version": 2, "projects": []}),
            encoding="utf-8",
        )
        (repo / ".git").mkdir()

        # Note: the discover method checks workspace.yaml first,
        # then .cortex/config.yaml, then root config.yaml.
        # With .cortex/workspace.yaml present, it's new layout.
        layout = WorkspaceLayout.discover(repo)
        assert layout.is_new_layout is True

    def test_from_repo_root_new_layout(self, tmp_path):
        repo = tmp_path / "explicit"
        repo.mkdir()
        layout = WorkspaceLayout.from_repo_root(repo)
        assert layout.is_new_layout is True
        assert layout.workspace_root == repo / ".cortex"
        assert layout.repo_root == repo


# ────────────────────────────────────────────────────────────────────
# New layout paths
# ────────────────────────────────────────────────────────────────────

class TestNewLayoutPaths:
    """Verify all path properties in new layout mode."""

    @pytest.fixture
    def layout(self, new_layout_project):
        return WorkspaceLayout.discover(new_layout_project["repo"])

    def test_config_path(self, layout, new_layout_project):
        assert layout.config_path == new_layout_project["cortex"] / "config.yaml"

    def test_org_config_path(self, layout, new_layout_project):
        assert layout.org_config_path == new_layout_project["cortex"] / "org.yaml"

    def test_vault_path(self, layout, new_layout_project):
        assert layout.vault_path == new_layout_project["cortex"] / "vault"

    def test_enterprise_vault_path(self, layout, new_layout_project):
        assert layout.enterprise_vault_path == new_layout_project["cortex"] / "vault-enterprise"

    def test_episodic_memory_path(self, layout, new_layout_project):
        assert layout.episodic_memory_path == new_layout_project["cortex"] / "memory"

    def test_enterprise_memory_path(self, layout, new_layout_project):
        assert layout.enterprise_memory_path == new_layout_project["cortex"] / "enterprise-memory"

    def test_skills_dir(self, layout, new_layout_project):
        assert layout.skills_dir == new_layout_project["cortex"] / "skills"

    def test_subagents_dir(self, layout, new_layout_project):
        assert layout.subagents_dir == new_layout_project["cortex"] / "subagents"

    def test_agent_guidelines_path(self, layout, new_layout_project):
        assert layout.agent_guidelines_path == new_layout_project["cortex"] / "AGENT.md"

    def test_system_prompt_path(self, layout, new_layout_project):
        assert layout.system_prompt_path == new_layout_project["cortex"] / "system-prompt.md"

    def test_workspace_yaml_path(self, layout, new_layout_project):
        assert layout.workspace_yaml_path == new_layout_project["cortex"] / "workspace.yaml"

    def test_webgraph_dir(self, layout, new_layout_project):
        assert layout.webgraph_dir == new_layout_project["cortex"] / "webgraph"

    def test_webgraph_config_path(self, layout, new_layout_project):
        assert layout.webgraph_config_path == new_layout_project["cortex"] / "webgraph" / "config.yaml"

    def test_webgraph_workspace_path(self, layout, new_layout_project):
        assert layout.webgraph_workspace_path == new_layout_project["cortex"] / "webgraph" / "workspace.yaml"

    def test_webgraph_cache_dir(self, layout, new_layout_project):
        assert layout.webgraph_cache_dir == new_layout_project["cortex"] / "webgraph" / "cache"

    def test_logs_dir(self, layout, new_layout_project):
        assert layout.logs_dir == new_layout_project["cortex"] / "logs"

    def test_scripts_dir(self, layout, new_layout_project):
        assert layout.scripts_dir == new_layout_project["cortex"] / "scripts"

    def test_workflows_dir_outside_cortex(self, layout, new_layout_project):
        assert layout.workflows_dir == new_layout_project["repo"] / ".github" / "workflows"

    def test_promotion_records_path(self, layout, new_layout_project):
        assert layout.promotion_records_path == (
            new_layout_project["cortex"] / "vault-enterprise" / "promotion" / "records.jsonl"
        )

    def test_vault_index_path(self, layout, new_layout_project):
        assert layout.vault_index_path == new_layout_project["cortex"] / "vault" / ".cortex_index.json"

    def test_gitignore_path(self, layout, new_layout_project):
        assert layout.gitignore_path == new_layout_project["repo"] / ".gitignore"

    def test_no_nested_cortex_cortex(self, layout, new_layout_project):
        """Ensure no path produces .cortex/.cortex/..."""
        for attr in [
            "config_path", "vault_path", "enterprise_vault_path",
            "episodic_memory_path", "skills_dir", "org_config_path",
            "promotion_records_path", "webgraph_dir", "scripts_dir",
        ]:
            path_str = str(getattr(layout, attr))
            assert ".cortex/.cortex" not in path_str, f"{attr} has nested .cortex: {path_str}"


# ────────────────────────────────────────────────────────────────────
# Legacy layout paths
# ────────────────────────────────────────────────────────────────────

class TestLegacyLayoutPaths:
    """Verify all path properties in legacy layout mode."""

    @pytest.fixture
    def layout(self, legacy_layout_project):
        return WorkspaceLayout.discover(legacy_layout_project["repo"])

    def test_config_path_legacy(self, layout, legacy_layout_project):
        assert layout.config_path == legacy_layout_project["repo"] / "config.yaml"

    def test_org_config_path_legacy(self, layout, legacy_layout_project):
        assert layout.org_config_path == legacy_layout_project["cortex"] / "org.yaml"

    def test_vault_path_legacy(self, layout, legacy_layout_project):
        assert layout.vault_path == legacy_layout_project["repo"] / "vault"

    def test_enterprise_vault_path_legacy(self, layout, legacy_layout_project):
        assert layout.enterprise_vault_path == legacy_layout_project["repo"] / "vault-enterprise"

    def test_episodic_memory_path_legacy(self, layout, legacy_layout_project):
        assert layout.episodic_memory_path == legacy_layout_project["repo"] / ".memory"

    def test_enterprise_memory_path_legacy(self, layout, legacy_layout_project):
        assert layout.enterprise_memory_path == legacy_layout_project["repo"] / ".memory" / "enterprise"

    def test_skills_dir_legacy(self, layout, legacy_layout_project):
        assert layout.skills_dir == legacy_layout_project["cortex"] / "skills"

    def test_workspace_root_is_repo_root_legacy(self, layout, legacy_layout_project):
        assert layout.workspace_root == legacy_layout_project["repo"]

    def test_promotion_records_path_legacy(self, layout, legacy_layout_project):
        assert layout.promotion_records_path == (
            legacy_layout_project["repo"] / "vault-enterprise" / ".cortex" / "promotion" / "records.jsonl"
        )

    def test_scripts_dir_legacy(self, layout, legacy_layout_project):
        assert layout.scripts_dir == legacy_layout_project["repo"] / "scripts"


# ────────────────────────────────────────────────────────────────────
# resolve_workspace_relative
# ────────────────────────────────────────────────────────────────────

class TestResolveWorkspaceRelative:

    def test_new_layout_relative(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        assert layout.resolve_workspace_relative("vault") == new_layout_project["cortex"] / "vault"
        assert layout.resolve_workspace_relative("memory") == new_layout_project["cortex"] / "memory"
        assert layout.resolve_workspace_relative("vault-enterprise") == new_layout_project["cortex"] / "vault-enterprise"

    def test_legacy_layout_relative(self, legacy_layout_project):
        layout = WorkspaceLayout.discover(legacy_layout_project["repo"])
        # In legacy mode, workspace_root = repo_root
        assert layout.resolve_workspace_relative("vault") == legacy_layout_project["repo"] / "vault"
        assert layout.resolve_workspace_relative(".memory") == legacy_layout_project["repo"] / ".memory"

    def test_absolute_path_passthrough(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        # Use a truly absolute path (drive-specific on Windows)
        absolute = new_layout_project["repo"].drive + "/absolute/path/to/something"
        absolute_path = Path(absolute)
        # On Windows, Path("/...") becomes relative to drive, so test
        # with a real absolute path instead
        result = layout.resolve_workspace_relative(absolute_path)
        assert result.is_absolute()

    def test_path_object(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        assert layout.resolve_workspace_relative(Path("vault")) == new_layout_project["cortex"] / "vault"


# ────────────────────────────────────────────────────────────────────
# Workspace YAML parsing
# ────────────────────────────────────────────────────────────────────

class TestWorkspaceYamlParsing:

    def test_layout_version_2(self, tmp_path):
        repo = tmp_path / "v2project"
        repo.mkdir()
        cortex = repo / ".cortex"
        cortex.mkdir()
        (cortex / "workspace.yaml").write_text(
            yaml.safe_dump({"layout_version": 2, "projects": [{"id": "primary", "path": ".", "role": "owner"}]}),
            encoding="utf-8",
        )
        (cortex / "config.yaml").write_text("x: y\n", encoding="utf-8")
        layout = WorkspaceLayout.discover(repo)
        assert layout.is_new_layout is True
        assert layout.is_legacy_layout is False

    def test_layout_version_1_is_legacy(self, tmp_path):
        repo = tmp_path / "v1project"
        repo.mkdir()
        cortex = repo / ".cortex"
        cortex.mkdir()
        (cortex / "workspace.yaml").write_text(
            yaml.safe_dump({"layout_version": 1, "projects": []}),
            encoding="utf-8",
        )
        (repo / "config.yaml").write_text("x: y\n", encoding="utf-8")
        (repo / ".git").mkdir()
        # layout_version 1 → should be treated as legacy
        # But workspace.yaml exists in .cortex/, so discover may pick it up.
        # The discover method checks layout_version >= 2 first.
        # For version 1, it falls through to legacy detection.
        layout = WorkspaceLayout.discover(repo)
        assert layout.is_legacy_layout is True

    def test_missing_workspace_yaml_falls_through(self, tmp_path):
        repo = tmp_path / "nowsyaml"
        repo.mkdir()
        cortex = repo / ".cortex"
        cortex.mkdir()
        (cortex / "skills").mkdir()
        (repo / "config.yaml").write_text("x: y\n", encoding="utf-8")
        (repo / ".git").mkdir()
        layout = WorkspaceLayout.discover(repo)
        assert layout.is_legacy_layout is True


# ────────────────────────────────────────────────────────────────────
# Legacy compatibility helpers
# ────────────────────────────────────────────────────────────────────

class TestLegacyCompatibility:

    def test_legacy_config_path(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        # Even in new layout, legacy_config_path points to root
        assert layout.legacy_config_path == new_layout_project["repo"] / "config.yaml"

    def test_legacy_vault_path(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        assert layout.legacy_vault_path == new_layout_project["repo"] / "vault"

    def test_legacy_memory_path(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        assert layout.legacy_memory_path == new_layout_project["repo"] / ".memory"


# ────────────────────────────────────────────────────────────────────
# Representation
# ────────────────────────────────────────────────────────────────────

class TestRepr:

    def test_repr_new_layout(self, new_layout_project):
        layout = WorkspaceLayout.discover(new_layout_project["repo"])
        r = repr(layout)
        assert "mode=new" in r
        assert "WorkspaceLayout" in r

    def test_repr_legacy_layout(self, legacy_layout_project):
        layout = WorkspaceLayout.discover(legacy_layout_project["repo"])
        r = repr(layout)
        assert "mode=legacy" in r


# ────────────────────────────────────────────────────────────────────
# Git root helper
# ────────────────────────────────────────────────────────────────────

class TestFindGitRoot:

    def test_finds_git_dir(self, tmp_path):
        project = tmp_path / "myproject"
        project.mkdir()
        (project / ".git").mkdir()
        assert _find_git_root(project) == project

    def test_finds_parent_git_dir(self, tmp_path):
        project = tmp_path / "myproject"
        project.mkdir()
        (project / ".git").mkdir()
        sub = project / "src" / "pkg"
        sub.mkdir(parents=True)
        assert _find_git_root(sub) == project

    def test_returns_none_no_git(self, tmp_path):
        empty = tmp_path / "nogit"
        empty.mkdir()
        assert _find_git_root(empty) is None