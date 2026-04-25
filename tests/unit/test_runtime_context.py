from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cortex.runtime_context import resolve_episodic_persist_dir, slugify


def test_slugify_normalizes_values() -> None:
    assert slugify(" Feature/Auth Flow ") == "feature-auth-flow"


def test_resolve_episodic_dir_project_mode(tmp_path: Path) -> None:
    result = resolve_episodic_persist_dir(
        tmp_path,
        {"persist_dir": ".memory/chroma", "namespace_mode": "project"},
    )
    assert result == (tmp_path / ".memory" / "chroma").resolve()


def test_resolve_episodic_dir_branch_mode(tmp_path: Path) -> None:
    with patch("cortex.runtime_context.detect_git_branch", return_value="feature/my-branch"):
        result = resolve_episodic_persist_dir(
            tmp_path,
            {"persist_dir": ".memory/chroma", "namespace_mode": "branch"},
        )
    assert result == (tmp_path / ".memory" / "chroma" / "branches" / "feature-my-branch").resolve()


def test_resolve_episodic_dir_custom_mode(tmp_path: Path) -> None:
    result = resolve_episodic_persist_dir(
        tmp_path,
        {"persist_dir": ".memory/chroma", "namespace_mode": "custom", "namespace_value": "qa team"},
    )
    assert result == (tmp_path / ".memory" / "chroma" / "custom" / "qa-team").resolve()

