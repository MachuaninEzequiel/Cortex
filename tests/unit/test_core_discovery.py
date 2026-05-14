"""Tests for the layout-discovery-first behaviour of ``AgentMemory``.

Regression of Ola 3.B: previously ``AgentMemory("config.yaml")`` defaulted
to a fixed relative path, breaking new-layout repos when the user did not
``cd`` into ``.cortex/`` first. Now ``AgentMemory()`` discovers the layout
from CWD and uses ``layout.config_path`` automatically.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _write_minimal_workspace(workspace: Path) -> None:
    """Create the minimum files an ``AgentMemory`` needs to boot."""
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "config.yaml").write_text(
        "episodic:\n"
        "  persist_dir: memory\n"
        "  embedding_backend: onnx\n"
        "semantic:\n"
        "  vault_path: vault\n",
        encoding="utf-8",
    )
    (workspace / "memory").mkdir(parents=True, exist_ok=True)
    (workspace / "vault").mkdir(parents=True, exist_ok=True)


class TestAgentMemoryDiscoversNewLayout:
    def test_discovers_config_from_cwd_in_new_layout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``AgentMemory()`` without args must locate ``.cortex/config.yaml``."""
        from cortex.core import AgentMemory

        cortex_dir = tmp_path / ".cortex"
        _write_minimal_workspace(cortex_dir)
        (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        memory = AgentMemory()

        assert memory.workspace_root == cortex_dir
        assert memory._config_path == cortex_dir / "config.yaml"

    def test_discovers_config_from_subdirectory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Discovery must walk up from a nested CWD to find the workspace."""
        from cortex.core import AgentMemory

        cortex_dir = tmp_path / ".cortex"
        _write_minimal_workspace(cortex_dir)
        (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
        nested = tmp_path / "src" / "auth"
        nested.mkdir(parents=True)

        monkeypatch.chdir(nested)
        memory = AgentMemory()

        assert memory.workspace_root == cortex_dir

    def test_explicit_config_path_still_honored(self, tmp_path: Path) -> None:
        """Backwards compat: explicit path must still work for legacy callers."""
        from cortex.core import AgentMemory

        # Legacy layout: config.yaml at repo root.
        _write_minimal_workspace(tmp_path)
        memory = AgentMemory(config_path=str(tmp_path / "config.yaml"))

        assert memory._config_path == tmp_path / "config.yaml"

    def test_missing_config_raises_actionable_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no config is found, the error must mention ``cortex setup``."""
        from cortex.core import AgentMemory

        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError) as info:
            AgentMemory()

        msg = str(info.value)
        assert "no está configurado" in msg or "Cortex no está" in msg
        assert "cortex setup" in msg
