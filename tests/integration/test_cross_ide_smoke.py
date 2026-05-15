"""Integration smoke for ``cortex inject --ide <name>`` on a clean workspace
(Items #13-#16 PLAN-DEUDA-RESIDUAL).

Each smoke creates a minimal workspace in ``tmp_path`` with the canonical
.cortex/ scaffold, invokes the adapter via ``cortex.ide.inject`` and asserts
the Tripartita Refinada markers expected by each Plan (03 / 04 / 05 / 06).

These tests replace the "manual checklist" gate in the original plan: the
markers are verified automatically so the gate cannot regress silently.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import cortex.ide as cortex_ide

REPO_ROOT = Path(__file__).resolve().parents[2]


def _seed_workspace(tmp_path: Path) -> Path:
    """Copy the source repo's ``.cortex/`` scaffolding into a fresh root."""
    src = REPO_ROOT / ".cortex"
    if not src.exists():
        pytest.skip("repo .cortex/ scaffold not available")
    dst_root = tmp_path / "adopter-repo"
    dst_root.mkdir()
    shutil.copytree(src, dst_root / ".cortex")
    # Mark as a git repo so WorkspaceLayout finds the root deterministically.
    (dst_root / ".git").mkdir()
    return dst_root


def _files_contain(paths: list[Path], marker: str) -> bool:
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if marker in text:
            return True
    return False


# ---------------------------------------------------------------------------
# Item #13 — cortex inject --ide claude-code
# ---------------------------------------------------------------------------


def test_smoke_inject_claude_code(tmp_path: Path) -> None:
    root = _seed_workspace(tmp_path)
    files = cortex_ide.inject("claude-code", project_root=root)
    assert files, "claude-code inject produced no files"

    written = [Path(f) if Path(f).is_absolute() else (root / f) for f in files]
    rendered_paths = [str(p).replace("\\", "/").lower() for p in written]
    # Required artifacts: skills and subagents materialized under .claude/.
    assert any("cortex-sync" in p for p in rendered_paths), "cortex-sync skill missing"
    assert any("cortex-documenter" in p for p in rendered_paths), "cortex-documenter agent missing"

    # Tripartita Refinada markers per Plan 03.
    markers = [
        "cortex-sync",
        "cortex-documenter",
    ]
    for marker in markers:
        assert _files_contain(written, marker), f"marker {marker!r} missing"


# ---------------------------------------------------------------------------
# Item #14 — cortex inject --ide opencode
# ---------------------------------------------------------------------------


def test_smoke_inject_opencode(tmp_path: Path) -> None:
    root = _seed_workspace(tmp_path)
    files = cortex_ide.inject("opencode", project_root=root)
    assert files, "opencode inject produced no files"

    written = [Path(f) if Path(f).is_absolute() else (root / f) for f in files]
    rendered_paths = [str(p).replace("\\", "/").lower() for p in written]
    assert any("cortex-sync" in p for p in rendered_paths), "cortex-sync prompt missing"

    # Plan 04 — at minimum the canonical prompts must reach the opencode
    # bundle and a config file must exist.
    markers = ["cortex-sync", "cortex-documenter"]
    for marker in markers:
        assert _files_contain(written, marker), f"marker {marker!r} missing"


# ---------------------------------------------------------------------------
# Item #15 — cortex inject --ide pi
# ---------------------------------------------------------------------------


def test_smoke_inject_pi(tmp_path: Path) -> None:
    root = _seed_workspace(tmp_path)
    # sync_canonical=False keeps the smoke deterministic on machines that
    # don't have a cortex-pi/ checkout next to the project.
    files = cortex_ide.inject("pi", project_root=root, sync_canonical=False)
    assert files, "pi inject produced no files"

    written = [Path(f) if Path(f).is_absolute() else (root / f) for f in files]
    # Plan 05 markers.
    markers = ["cortex-sync"]
    for marker in markers:
        assert _files_contain(written, marker), f"marker {marker!r} missing"


# ---------------------------------------------------------------------------
# Item #16 — cortex inject --ide codex
# ---------------------------------------------------------------------------


def test_smoke_inject_codex(tmp_path: Path) -> None:
    """Smoke test del adapter Codex post-Fase 4 del plan multi-IDE.

    Validacion clave (Decision 2 firmada 2026-05-15):
    - AGENTS.md va al PROJECT ROOT, NO ``.codex/AGENTS.md``.
    - MCP config en ``.codex/config.toml`` (TOML), NO JSON.
    - NO se generan ``.codex/agents/*.md`` ni ``.codex/skills/*.md``.
    """
    import tomllib

    root = _seed_workspace(tmp_path)
    files = cortex_ide.inject("codex", project_root=root)
    assert files, "codex inject produced no files"

    # AGENTS.md en project root
    agents_md = root / "AGENTS.md"
    assert agents_md.exists(), "AGENTS.md (project root) missing"
    text = agents_md.read_text(encoding="utf-8", errors="ignore")
    assert "Cortex Workflow for Codex" in text
    assert "cortex_validate_handoff" in text
    assert "cortex_verify_session_claims" in text
    assert "cortex_ping" in text  # pre-flight check (Fase 2)

    # MCP config en TOML
    config_toml = root / ".codex" / "config.toml"
    assert config_toml.exists(), ".codex/config.toml (TOML MCP config) missing"
    parsed = tomllib.loads(config_toml.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["cortex"]["command"] == "cortex"
    assert parsed["mcp_servers"]["cortex"]["enabled"] is True

    # Paths obsoletos NO deben existir post-Fase 4
    assert not (root / ".codex" / "AGENTS.md").exists()
    assert not (root / ".codex" / "mcp.json").exists()
    assert not (root / ".codex" / "agents").exists()
    assert not (root / ".codex" / "skills").exists()
