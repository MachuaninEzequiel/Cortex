"""Tests for the generic :class:`HookInstaller` orchestrator (T3.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from cortex.session.hooks import (
    HookInstaller,
    HookStatus,
    InstallResult,
    UninstallResult,
)
from cortex.session.hooks.installer import default_installer

# ── Test doubles ─────────────────────────────────────────────────────


@dataclass
class _FakeAdapter:
    """Minimal adapter that records calls and returns canned results."""

    name: str
    supported: bool = True
    is_installed: bool = False
    install_calls: list[Path] = field(default_factory=list)
    uninstall_calls: list[Path] = field(default_factory=list)

    def is_supported(self) -> bool:
        return self.supported

    def install(self, target_dir: Path) -> InstallResult:
        self.install_calls.append(target_dir)
        if self.is_installed:
            return InstallResult(
                ide=self.name,
                installed=True,
                modified_paths=[],
                message="already installed",
            )
        self.is_installed = True
        return InstallResult(
            ide=self.name,
            installed=True,
            modified_paths=[target_dir / f".{self.name}.hook"],
            message="installed",
        )

    def uninstall(self, target_dir: Path) -> UninstallResult:
        self.uninstall_calls.append(target_dir)
        if not self.is_installed:
            return UninstallResult(
                ide=self.name,
                uninstalled=False,
                removed_paths=[],
                message="not installed",
            )
        self.is_installed = False
        return UninstallResult(
            ide=self.name,
            uninstalled=True,
            removed_paths=[target_dir / f".{self.name}.hook"],
            message="removed",
        )

    def status(self, target_dir: Path) -> HookStatus:  # noqa: ARG002 - signature
        return HookStatus(
            ide=self.name,
            installed=self.is_installed,
            supported=self.supported,
            detail="installed" if self.is_installed else "not installed",
        )


# ── HookInstaller ────────────────────────────────────────────────────


class TestHookInstallerRegistry:
    def test_registers_from_iterable(self) -> None:
        a = _FakeAdapter("a")
        b = _FakeAdapter("b")
        inst = HookInstaller([a, b])
        assert inst.list_available_adapters() == ["a", "b"]

    def test_registers_from_dict(self) -> None:
        inst = HookInstaller({"x": _FakeAdapter("x")})
        assert inst.list_available_adapters() == ["x"]

    def test_unknown_ide_raises_with_actionable_message(self) -> None:
        inst = HookInstaller([_FakeAdapter("a")])
        with pytest.raises(KeyError, match="unknown IDE adapter 'nope'"):
            inst.get("nope")

    def test_list_supported_filters_unsupported(self) -> None:
        inst = HookInstaller(
            [_FakeAdapter("a", supported=True), _FakeAdapter("b", supported=False)]
        )
        assert inst.list_supported() == ["a"]


class TestHookInstallerInstall:
    def test_dispatches_to_adapter(self, tmp_path: Path) -> None:
        a = _FakeAdapter("a")
        inst = HookInstaller([a])
        result = inst.install("a", tmp_path)
        assert result.installed is True
        assert a.install_calls == [tmp_path]

    def test_returns_already_installed_message(self, tmp_path: Path) -> None:
        a = _FakeAdapter("a", is_installed=True)
        inst = HookInstaller([a])
        result = inst.install("a", tmp_path)
        assert "already installed" in result.message

    def test_install_unknown_adapter_raises(self, tmp_path: Path) -> None:
        inst = HookInstaller([_FakeAdapter("a")])
        with pytest.raises(KeyError):
            inst.install("missing", tmp_path)

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        a = _FakeAdapter("a")
        inst = HookInstaller([a])
        result = inst.install("a", tmp_path)
        assert isinstance(a.install_calls[0], Path)
        assert result.installed is True


class TestHookInstallerUninstall:
    def test_dispatches_to_adapter(self, tmp_path: Path) -> None:
        a = _FakeAdapter("a", is_installed=True)
        inst = HookInstaller([a])
        result = inst.uninstall("a", tmp_path)
        assert result.uninstalled is True
        assert a.uninstall_calls == [tmp_path]

    def test_uninstall_when_not_installed_is_noop(self, tmp_path: Path) -> None:
        a = _FakeAdapter("a", is_installed=False)
        inst = HookInstaller([a])
        result = inst.uninstall("a", tmp_path)
        assert result.uninstalled is False
        assert "not installed" in result.message


class TestHookInstallerStatus:
    def test_single(self, tmp_path: Path) -> None:
        a = _FakeAdapter("a", is_installed=True)
        inst = HookInstaller([a])
        status = inst.status("a", tmp_path)
        assert status.installed is True

    def test_status_all_sorted(self, tmp_path: Path) -> None:
        a = _FakeAdapter("b", is_installed=False)
        b = _FakeAdapter("a", is_installed=True)
        inst = HookInstaller([a, b])
        all_status = inst.status_all(tmp_path)
        assert [s.ide for s in all_status] == ["a", "b"]
        assert all_status[0].installed is True
        assert all_status[1].installed is False


# ── default_installer factory ───────────────────────────────────────


class TestDefaultInstaller:
    def test_bundled_adapters_present(self) -> None:
        inst = default_installer()
        names = inst.list_available_adapters()
        # Phase 03 shipped 3; Phase 05 added opencode.
        assert {"claude-code", "cursor", "opencode", "pi"} <= set(names)
