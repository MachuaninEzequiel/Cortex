"""Tests for the unified `cortex ide ...` CLI surface (Obra 02, Fase 3).

Covers:
* exit codes, human output and --json parseability of every new command;
* --dry-run never writes or removes anything (tmp_path tree snapshot);
* explicit --project-root works from a DIFFERENT cwd (no Path.cwd() leaks);
* the 4 legacy commands emit deprecation warnings and stay behaviorally
  equivalent to their `cortex ide ...` replacements (parity test).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.ide import ide_app
from cortex.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Minimal Cortex-ish project root. No config.yaml needed: discovery and
    prompt builders degrade gracefully."""
    root = tmp_path / "proj"
    (root / ".cortex" / "skills").mkdir(parents=True)
    return root


def snapshot(root: Path) -> dict[str, bytes]:
    """Full recursive file snapshot used by dry-run no-write assertions."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def invoke_ide(runner: CliRunner, args: list[str]):
    return runner.invoke(ide_app, args)


def invoke_main(runner: CliRunner, args: list[str]):
    return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# cortex ide list
# ---------------------------------------------------------------------------


class TestIdeList:
    def test_list_exits_zero_and_shows_all_adapters(self, runner: CliRunner) -> None:
        result = invoke_ide(runner, ["list"])
        assert result.exit_code == 0, result.output
        for name in ("claude_code", "opencode", "pi", "codex", "cursor", "zed"):
            assert name in result.output

    def test_list_json_is_parseable_and_tiered(self, runner: CliRunner) -> None:
        result = invoke_ide(runner, ["list", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        by_name = {row["name"]: row for row in payload}
        assert by_name["codex"]["tier"] == "target"
        assert by_name["cursor"]["tier"] == "community"
        assert by_name["zed"]["tier"] == "experimental"
        # Fase 2 complete: every adapter overrides uninstall.
        assert all(row["uninstall_supported"] is True for row in payload)
        for key in ("name", "display_name", "tier", "uninstall_supported", "validated"):
            assert key in by_name["claude_code"]


# ---------------------------------------------------------------------------
# cortex ide setup
# ---------------------------------------------------------------------------


class TestIdeSetup:
    def test_setup_claude_code_writes_project_files(
        self, runner: CliRunner, project: Path
    ) -> None:
        result = invoke_ide(
            runner, ["setup", "--ide", "claude_code", "--project-root", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert (project / "CLAUDE.md").exists()
        assert (project / ".mcp.json").exists()

    def test_setup_requires_ide_no_interactive_prompt(self, runner: CliRunner) -> None:
        result = invoke_ide(runner, ["setup"])
        assert result.exit_code == 2
        assert "--ide is required" in result.output
        assert "target:" in result.output and "codex" in result.output

    def test_setup_unknown_ide_exit_code_2(self, runner: CliRunner) -> None:
        result = invoke_ide(runner, ["setup", "--ide", "not-an-ide"])
        assert result.exit_code == 2
        assert "Unknown IDE" in result.output

    def test_setup_alias_resolution(self, runner: CliRunner, project: Path) -> None:
        result = invoke_ide(
            runner, ["setup", "--ide", "claude-code", "--project-root", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert (project / "CLAUDE.md").exists()

    def test_setup_dry_run_writes_nothing(
        self, runner: CliRunner, project: Path
    ) -> None:
        before = snapshot(project)
        result = invoke_ide(
            runner,
            ["setup", "--ide", "claude_code", "--project-root", str(project), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert snapshot(project) == before, "dry-run must not write anything"
        assert "Dry-run" in result.output
        assert "CLAUDE.md" in result.output  # lists planned targets

    def test_setup_explicit_root_from_other_cwd(
        self, runner: CliRunner, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        result = invoke_ide(
            runner, ["setup", "--ide", "claude_code", "--project-root", str(project)]
        )
        assert result.exit_code == 0, result.output
        assert (project / "CLAUDE.md").exists()
        assert not (elsewhere / "CLAUDE.md").exists()

    def test_setup_accepts_no_sync_canonical_flag(
        self, runner: CliRunner, project: Path
    ) -> None:
        result = invoke_ide(
            runner,
            ["setup", "--ide", "claude_code", "--project-root", str(project),
             "--no-sync-canonical"],
        )
        assert result.exit_code == 0, result.output

    def test_setup_is_idempotent(self, runner: CliRunner, project: Path) -> None:
        """Re-running setup succeeds and creates no NEW managed paths.

        (Byte-equality needs frozen timestamps in _generate_autogen_header —
        tracked separately in Obra 02 Fase 0/1.)
        """
        args = ["setup", "--ide", "claude_code", "--project-root", str(project)]
        assert invoke_ide(runner, args).exit_code == 0
        first = relative_tree(project)
        second = invoke_ide(runner, args)
        assert second.exit_code == 0, second.output
        assert relative_tree(project) == first


# ---------------------------------------------------------------------------
# cortex ide remove
# ---------------------------------------------------------------------------


class TestIdeRemove:
    def _setup(self, runner: CliRunner, project: Path) -> None:
        result = invoke_ide(
            runner, ["setup", "--ide", "claude_code", "--project-root", str(project)]
        )
        assert result.exit_code == 0, result.output

    def test_remove_cleans_cortex_content(
        self, runner: CliRunner, project: Path
    ) -> None:
        self._setup(runner, project)
        assert (project / "CLAUDE.md").exists()
        result = invoke_ide(
            runner, ["remove", "--ide", "claude_code", "--project-root", str(project)]
        )
        assert result.exit_code == 0, result.output
        # CLAUDE.md was created entirely by Cortex (no user content) → removed.
        assert not (project / "CLAUDE.md").exists()

    def test_remove_dry_run_removes_nothing(
        self, runner: CliRunner, project: Path
    ) -> None:
        self._setup(runner, project)
        before = snapshot(project)
        result = invoke_ide(
            runner,
            ["remove", "--ide", "claude_code", "--project-root", str(project), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert snapshot(project) == before, "dry-run must not remove anything"
        assert "Dry-run" in result.output

    def test_remove_requires_ide(self, runner: CliRunner) -> None:
        result = invoke_ide(runner, ["remove"])
        assert result.exit_code == 2
        assert "--ide is required" in result.output

    def test_remove_unknown_ide_exit_code_2(self, runner: CliRunner) -> None:
        result = invoke_ide(runner, ["remove", "--ide", "bogus"])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# cortex ide status
# ---------------------------------------------------------------------------


class TestIdeStatus:
    def test_status_json_all_adapters(
        self, runner: CliRunner, project: Path
    ) -> None:
        result = invoke_ide(runner, ["status", "--project-root", str(project), "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        names = {row["ide"] for row in payload}
        assert {"claude_code", "codex", "cursor"} <= names
        claude = next(row for row in payload if row["ide"] == "claude_code")
        assert set(claude) >= {
            "expected_config_present", "mcp_configured", "hooks_installed",
            "config_checks", "tier",
        }
        assert claude["expected_config_present"] is False
        assert claude["mcp_configured"] is False  # .mcp.json missing yet

    def test_status_reflects_setup(
        self, runner: CliRunner, project: Path
    ) -> None:
        assert invoke_ide(
            runner, ["setup", "--ide", "claude_code", "--project-root", str(project)]
        ).exit_code == 0
        result = invoke_ide(
            runner,
            ["status", "--ide", "claude_code", "--project-root", str(project), "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert len(payload) == 1
        row = payload[0]
        assert row["expected_config_present"] is True
        assert row["mcp_configured"] is True

    def test_status_unknown_ide_exit_code_2(self, runner: CliRunner) -> None:
        result = invoke_ide(runner, ["status", "--ide", "nope"])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Legacy commands: deprecation warnings + behavioral parity
# ---------------------------------------------------------------------------

LEGACY_SETUP_WARNING = "Deprecated: use `cortex ide setup --ide <name>` instead."
LEGACY_REMOVE_WARNING = "Deprecated: use `cortex ide remove --ide <name>` instead."


def relative_tree(root: Path) -> set[str]:
    """Managed file paths, excluding .cortex internals and timestamped backups."""
    return {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file()
        and ".cortex" not in p.parts
        and ".cortex_backup_" not in p.name
    }


class TestLegacyDeprecationAndParity:
    def test_inject_delegates_with_warning(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        new_root = tmp_path / "new"
        old_root = tmp_path / "old"
        for r in (new_root, old_root):
            (r / ".cortex" / "skills").mkdir(parents=True)

        fresh = invoke_ide(runner, ["setup", "--ide", "claude_code", "--project-root", str(new_root)])
        assert fresh.exit_code == 0, fresh.output

        legacy = invoke_main(
            runner, ["inject", "--ide", "claude_code", "--project-root", str(old_root)]
        )
        assert legacy.exit_code == 0, legacy.output
        assert LEGACY_SETUP_WARNING in legacy.output
        # Parity: same observable effect (same set of files created).
        assert relative_tree(old_root) == relative_tree(new_root)

    def test_install_ide_delegates_with_warning(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        new_root = tmp_path / "new"
        old_root = tmp_path / "old"
        for r in (new_root, old_root):
            (r / ".cortex" / "skills").mkdir(parents=True)

        assert invoke_ide(
            runner, ["setup", "--ide", "claude_code", "--project-root", str(new_root)]
        ).exit_code == 0

        legacy = invoke_main(
            runner, ["install-ide", "--ide", "claude_code", "--project-root", str(old_root)]
        )
        assert legacy.exit_code == 0, legacy.output
        assert LEGACY_SETUP_WARNING in legacy.output
        assert relative_tree(old_root) == relative_tree(new_root)

    def test_uninstall_ide_delegates_with_warning(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        old_root = tmp_path / "old"
        (old_root / ".cortex" / "skills").mkdir(parents=True)
        assert invoke_ide(
            runner, ["setup", "--ide", "claude_code", "--project-root", str(old_root)]
        ).exit_code == 0

        legacy = invoke_main(
            runner, ["uninstall-ide", "--ide", "claude_code", "--project-root", str(old_root)]
        )
        assert legacy.exit_code == 0, legacy.output
        assert LEGACY_REMOVE_WARNING in legacy.output
        assert not (old_root / "CLAUDE.md").exists()  # same effect as `ide remove`

    def test_sync_ide_delegates_with_notice(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        new_root = tmp_path / "new"
        old_root = tmp_path / "old"
        for r in (new_root, old_root):
            (r / ".cortex" / "skills").mkdir(parents=True)

        assert invoke_ide(
            runner, ["setup", "--ide", "claude_code", "--project-root", str(new_root)]
        ).exit_code == 0

        legacy = invoke_main(
            runner, ["sync-ide", "--ide", "claude_code", "--project-root", str(old_root)]
        )
        assert legacy.exit_code == 0, legacy.output
        assert "sync-ide is deprecated" in legacy.output
        assert "setup es idempotente" in legacy.output
        assert relative_tree(old_root) == relative_tree(new_root)

    def test_legacy_commands_still_visible_in_help(self, runner: CliRunner) -> None:
        result = invoke_main(runner, ["--help"])
        assert result.exit_code == 0
        assert "inject" in result.output
        assert "install-ide" in result.output
        assert "uninstall-ide" in result.output
        assert "sync-ide" in result.output
        assert "ide" in result.output
