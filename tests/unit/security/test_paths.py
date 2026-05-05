from __future__ import annotations

from pathlib import Path

import pytest

from cortex.security.paths import PathSecurityError, resolve_safe, validate_under_root


class TestResolveSafe:
    def test_resolves_normal_relative_path(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        result = resolve_safe(root, "docs/note.md")
        assert result == (root / "docs" / "note.md").resolve()

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(PathSecurityError):
            resolve_safe(root, "/etc/passwd")

    @pytest.mark.parametrize("bad", ["../secret.txt", "foo/../../../secret.txt", "a/../.."])
    def test_rejects_traversal(self, bad: str, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(PathSecurityError):
            resolve_safe(root, bad)

    def test_allows_dot_relative(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        result = resolve_safe(root, "./note.md")
        assert result == (root / "note.md").resolve()

    def test_rejects_traversal_via_symlink(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (root / "link").symlink_to(outside)
        # resolve() follows symlinks, so this should detect the escape
        with pytest.raises(PathSecurityError):
            resolve_safe(root, "link/secret.txt")


class TestValidateUnderRoot:
    def test_validates_path_under_root(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = root / "note.md"
        result = validate_under_root(path, root)
        assert result == path.resolve()

    def test_rejects_path_outside_root(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "secret.txt"
        outside.touch()
        with pytest.raises(PathSecurityError):
            validate_under_root(outside, root)

    def test_rejects_traversal_path(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        bad = root / ".." / "secret.txt"
        with pytest.raises(PathSecurityError):
            validate_under_root(bad, root)
