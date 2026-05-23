"""cortex.session.hooks.adapters.claude_code — Claude Code hook adapter.

Installs a Cortex-managed entry into Claude Code's native ``hooks`` block
inside ``.claude/settings.json`` so that every ``Edit`` / ``Write`` /
``MultiEdit`` tool-use emits a checkpoint to the active Cortex session.

The hook command is short, runs in the background (``>/dev/null 2>&1``)
and is suffixed with ``|| true`` so a Cortex failure never blocks Claude
Code. The entry carries a ``_cortex_managed: true`` marker so install /
uninstall are precise even if the user adds other hooks manually.

Format of the Claude Code settings (subset we care about)::

    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [
              {"type": "command", "command": "cortex session checkpoint ..."}
            ],
            "_cortex_managed": true
          }
        ]
      }
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cortex.session.hooks.installer import (
    HookStatus,
    InstallResult,
    UninstallResult,
)

CORTEX_HOOK_MARKER = "_cortex_managed"
CLAUDE_SETTINGS_RELATIVE = ".claude/settings.json"
HOOK_MATCHER = "Edit|Write|MultiEdit"
HOOK_COMMAND = (
    "cortex session checkpoint --source ide-hook "
    "--note 'edit via Claude Code' >/dev/null 2>&1 || true"
)


class ClaudeCodeHookAdapter:
    """Manage the ``PostToolUse`` Cortex entry in ``.claude/settings.json``."""

    name = "claude-code"

    def is_supported(self) -> bool:
        # Settings file is plain JSON; no IDE binary required to manage it.
        return True

    # ── Public API ─────────────────────────────────────────────────

    def install(self, target_dir: Path) -> InstallResult:
        path = self._settings_path(target_dir)
        settings = self._load(path)
        if _has_cortex_hook(settings):
            return InstallResult(
                ide=self.name,
                installed=True,
                modified_paths=[],
                message=f"already installed in {path}",
            )
        _inject_cortex_hook(settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return InstallResult(
            ide=self.name,
            installed=True,
            modified_paths=[path],
            message=f"installed PostToolUse hook in {path}",
        )

    def uninstall(self, target_dir: Path) -> UninstallResult:
        path = self._settings_path(target_dir)
        if not path.exists():
            return UninstallResult(
                ide=self.name,
                uninstalled=False,
                removed_paths=[],
                message=f"{path} does not exist",
            )
        settings = self._load(path)
        if not _has_cortex_hook(settings):
            return UninstallResult(
                ide=self.name,
                uninstalled=False,
                removed_paths=[],
                message=f"no cortex-managed entry in {path}",
            )
        _remove_cortex_hook(settings)
        if settings:
            path.write_text(
                json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            path.write_text("{}\n", encoding="utf-8")
        return UninstallResult(
            ide=self.name,
            uninstalled=True,
            removed_paths=[path],
            message=f"removed cortex-managed entry from {path}",
        )

    def status(self, target_dir: Path) -> HookStatus:
        path = self._settings_path(target_dir)
        if not path.exists():
            return HookStatus(
                ide=self.name,
                installed=False,
                detail=f"{path} does not exist",
            )
        try:
            settings = self._load(path)
        except ValueError as exc:
            return HookStatus(
                ide=self.name,
                installed=False,
                detail=f"could not parse {path}: {exc}",
            )
        if _has_cortex_hook(settings):
            return HookStatus(
                ide=self.name,
                installed=True,
                detail=f"PostToolUse hook present in {path}",
            )
        return HookStatus(
            ide=self.name,
            installed=False,
            detail=f"no cortex-managed entry in {path}",
        )

    # ── Internals ─────────────────────────────────────────────────

    @staticmethod
    def _settings_path(target_dir: Path) -> Path:
        return Path(target_dir) / CLAUDE_SETTINGS_RELATIVE

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Expected an object at the root of {path}, got {type(data).__name__}")
        return data


# ── Helpers — pure functions over the settings dict ─────────────────


def _cortex_hook_entry() -> dict[str, Any]:
    return {
        "matcher": HOOK_MATCHER,
        "hooks": [{"type": "command", "command": HOOK_COMMAND}],
        CORTEX_HOOK_MARKER: True,
    }


def _has_cortex_hook(settings: dict[str, Any]) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    entries = hooks.get("PostToolUse")
    if not isinstance(entries, list):
        return False
    return any(isinstance(e, dict) and e.get(CORTEX_HOOK_MARKER) for e in entries)


def _inject_cortex_hook(settings: dict[str, Any]) -> None:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"settings.hooks must be an object, got {type(hooks).__name__}")
    entries = hooks.setdefault("PostToolUse", [])
    if not isinstance(entries, list):
        raise ValueError(f"settings.hooks.PostToolUse must be a list, got {type(entries).__name__}")
    entries.append(_cortex_hook_entry())


def _remove_cortex_hook(settings: dict[str, Any]) -> None:
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return
    entries = hooks.get("PostToolUse", [])
    if not isinstance(entries, list):
        return
    hooks["PostToolUse"] = [
        e for e in entries if not (isinstance(e, dict) and e.get(CORTEX_HOOK_MARKER))
    ]
    if not hooks["PostToolUse"]:
        hooks.pop("PostToolUse", None)
    if not hooks:
        settings.pop("hooks", None)


__all__ = ["ClaudeCodeHookAdapter", "CORTEX_HOOK_MARKER", "HOOK_COMMAND"]
