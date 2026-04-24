from __future__ import annotations

from pathlib import Path

import pytest

import cortex.ide as ide


class FakeAdapter:
    def __init__(self, name: str, files: list[str] | None = None, *, fail: bool = False) -> None:
        self.name = name
        self.display_name = name.title()
        self._files = files or []
        self._fail = fail
        self.inject_calls: list[tuple[Path, dict[str, str]]] = []
        self.uninstall_calls = 0

    def inject_all(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        if self._fail:
            raise RuntimeError(f"{self.name} failed")
        self.inject_calls.append((project_root, prompts))
        return self._files

    def uninstall(self) -> list[str]:
        self.uninstall_calls += 1
        if self._fail:
            raise RuntimeError(f"{self.name} failed")
        return self._files


def test_inject_uses_adapter_and_prompts(monkeypatch, tmp_path: Path) -> None:
    adapter = FakeAdapter("cursor", ["cursor.json"])
    prompts = {"cortex-sync": "sync"}

    monkeypatch.setattr(ide, "get_adapter", lambda _: adapter)
    monkeypatch.setattr(ide, "build_all_prompts", lambda _: prompts)
    monkeypatch.setattr(ide, "build_cursor_prompts", lambda _: prompts)

    files = ide.inject("cursor", project_root=tmp_path)

    assert files == ["cursor.json"]
    assert adapter.inject_calls == [(tmp_path, prompts)]


def test_inject_all_collects_results_and_tolerates_failures(monkeypatch, tmp_path: Path) -> None:
    ok = FakeAdapter("cursor", ["cursor.json"])
    fail = FakeAdapter("windsurf", fail=True)

    monkeypatch.setattr(ide, "get_all_adapters", lambda include_experimental=False: [ok, fail])
    monkeypatch.setattr(ide, "build_all_prompts", lambda _: {"cortex-SDDwork": "work"})

    results = ide.inject_all(project_root=tmp_path)

    assert results["cursor"] == ["cursor.json"]
    assert results["windsurf"] == []


def test_uninstall_single_adapter(monkeypatch) -> None:
    adapter = FakeAdapter("cursor", ["cursor.json"])
    monkeypatch.setattr(ide, "get_adapter", lambda _: adapter)

    files = ide.uninstall("cursor")

    assert files == ["cursor.json"]
    assert adapter.uninstall_calls == 1


def test_uninstall_all_collects_results(monkeypatch) -> None:
    ok = FakeAdapter("cursor", ["cursor.json"])
    fail = FakeAdapter("windsurf", fail=True)

    monkeypatch.setattr(ide, "get_all_adapters", lambda include_experimental=False: [ok, fail])

    results = ide.uninstall_all()

    assert results["cursor"] == ["cursor.json"]
    assert results["windsurf"] == []


def test_find_project_root_walks_upwards(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    nested = project_root / "src" / "pkg"
    (project_root / ".cortex").mkdir(parents=True)
    nested.mkdir(parents=True)

    monkeypatch.setattr(ide.Path, "cwd", staticmethod(lambda: nested))

    assert ide._find_project_root() == project_root


def test_find_project_root_raises_without_cortex(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ide.Path, "cwd", staticmethod(lambda: tmp_path))
    
    # Mock exists to never find .cortex
    original_exists = ide.Path.exists
    def fake_exists(self):
        if self.name == ".cortex":
            return False
        return original_exists(self)
    
    monkeypatch.setattr(ide.Path, "exists", fake_exists)

    with pytest.raises(FileNotFoundError):
        ide._find_project_root()
