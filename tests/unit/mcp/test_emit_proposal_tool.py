"""Tests for the ``cortex_emit_proposal`` MCP tool (Phase 09.A+).

Exercises:
    * Happy path: payload renders into the Markdown card and the server
      stamps ``_last_proposal_emitted_at``.
    * Validation errors propagate as ``❌ …`` text (no exceptions).
    * The ``cortex_create_spec`` enforcement gate rejects calls when
      ``proposal_mode='required' + proposal_confirmed=True`` arrives
      without a prior emit, or with one too recent for a real user turn
      to have elapsed.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cortex.mcp.server import CortexMCPServer


@pytest.fixture
def cortex_repo(tmp_path: Path) -> Path:
    """Bootstrap a minimal Cortex-aware git repo for MCP server tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)

    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\n",
        encoding="utf-8",
    )
    (cortex_dir / "vault").mkdir()
    (cortex_dir / "vault" / "specs").mkdir()
    (cortex_dir / "memory").mkdir()

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


def _server(repo: Path) -> CortexMCPServer:
    return CortexMCPServer(project_root=repo)


def _valid_payload() -> dict:
    return {
        "summary": "Refactor login into stateful AuthService",
        "alternatives": [
            {
                "id": "A",
                "description": "Inline rewrite",
                "rejected_reason": "Couples auth to view layer.",
            },
            {
                "id": "B",
                "description": "Extract AuthService singleton",
                "rejected_reason": "",
            },
        ],
        "recommendation_id": "B",
        "risks": ["touches session middleware"],
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestEmitProposalHandler:
    def test_emit_renders_card_and_stamps_timestamp(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        assert server._last_proposal_emitted_at is None

        before = datetime.now()
        card = server._emit_proposal_text(_valid_payload())  # noqa: SLF001
        after = datetime.now()

        assert "🎯 PROPUESTA" in card
        assert "✅ **[B]**" in card
        assert "❌ **[A]**" in card
        assert "touches session middleware" in card

        assert server._last_proposal_emitted_at is not None
        assert before <= server._last_proposal_emitted_at <= after

    def test_emit_with_invalid_payload_returns_error_text(
        self, cortex_repo: Path
    ) -> None:
        server = _server(cortex_repo)
        bad = _valid_payload()
        bad["recommendation_id"] = "Z"  # doesn't match any alternative

        result = server._emit_proposal_text(bad)  # noqa: SLF001

        assert result.startswith("❌")
        assert "cortex_emit_proposal" in result
        # The validation rejection must not have stamped the timestamp.
        assert server._last_proposal_emitted_at is None

    def test_emit_missing_summary_returns_error_text(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        bad = _valid_payload()
        bad["summary"] = ""

        result = server._emit_proposal_text(bad)  # noqa: SLF001
        assert result.startswith("❌")
        assert server._last_proposal_emitted_at is None

    def test_emit_with_single_alternative_returns_error(
        self, cortex_repo: Path
    ) -> None:
        server = _server(cortex_repo)
        bad = _valid_payload()
        bad["alternatives"] = [
            {"id": "A", "description": "only one", "rejected_reason": ""},
        ]
        bad["recommendation_id"] = "A"

        result = server._emit_proposal_text(bad)  # noqa: SLF001
        assert result.startswith("❌")


# ---------------------------------------------------------------------------
# Enforcement of the proposal -> create_spec gap (required mode)
# ---------------------------------------------------------------------------


class TestProposalGapEnforcement:
    def _create_spec_args(self, *, confirmed: bool = True) -> dict:
        return {
            "title": "Refactor auth",
            "goal": "Stabilise auth flows",
            "proposal_mode": "required",
            "proposal_confirmed": confirmed,
        }

    def test_required_without_prior_emit_blocks(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        # Satisfy the pre-existing cortex_sync_ticket governance guard so we
        # exercise specifically the new proposal-gap path.
        server._called_tools.add("cortex_sync_ticket")

        result = server._create_spec_text(self._create_spec_args())  # noqa: SLF001

        assert result.startswith("❌")
        assert "cortex_emit_proposal" in result

    def test_required_with_recent_emit_blocks(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        server._called_tools.add("cortex_sync_ticket")
        # Simulate a proposal emitted "right now" — same conversational turn.
        server._last_proposal_emitted_at = datetime.now()

        result = server._create_spec_text(self._create_spec_args())  # noqa: SLF001

        assert result.startswith("❌")
        assert "too recent" in result

    def test_required_with_aged_emit_passes_gap(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        server._called_tools.add("cortex_sync_ticket")
        # Simulate a proposal emitted long enough ago that a user turn is
        # plausible. Use 60s (well above the 2s heuristic threshold).
        server._last_proposal_emitted_at = datetime.now() - timedelta(seconds=60)

        result = server._create_spec_text(self._create_spec_args())  # noqa: SLF001

        # We do NOT assert success path (depends on SpecService internals,
        # tested elsewhere). We only assert the gap guard did not fire.
        assert "too recent" not in result
        assert "cortex_emit_proposal" not in result or "Specification" in result

    def test_required_without_confirmation_skips_gap_check(
        self, cortex_repo: Path
    ) -> None:
        """When proposal_confirmed=False, the SpecService own validator fires
        first; the timestamp gap is not the path of rejection."""
        server = _server(cortex_repo)
        server._called_tools.add("cortex_sync_ticket")

        result = server._create_spec_text(
            self._create_spec_args(confirmed=False)
        )  # noqa: SLF001

        # SpecService raises a ValueError that handler turns into "❌ …"
        assert result.startswith("❌")
        # The error must mention proposal_confirmed (the inner validation),
        # not the timestamp-gap message.
        assert "too recent" not in result

    def test_optional_mode_never_checks_gap(self, cortex_repo: Path) -> None:
        server = _server(cortex_repo)
        server._called_tools.add("cortex_sync_ticket")
        # No prior emit — but optional mode should not trip the new guard.
        result = server._create_spec_text(
            {
                "title": "Quick fix",
                "goal": "Touch up copy",
                "proposal_mode": "optional",
                "proposal_confirmed": False,
            }
        )  # noqa: SLF001

        assert "too recent" not in result
        assert "cortex_emit_proposal first" not in result

    def test_end_to_end_emit_then_create_spec_succeeds(
        self, cortex_repo: Path
    ) -> None:
        """Realistic flow: emit a proposal, jump the timestamp forward as
        if a user turn elapsed, then create the spec — succeeds."""
        server = _server(cortex_repo)
        server._called_tools.add("cortex_sync_ticket")

        emit_result = server._emit_proposal_text(_valid_payload())  # noqa: SLF001
        assert "🎯 PROPUESTA" in emit_result
        # Backdate the emit so the gap check passes deterministically.
        assert server._last_proposal_emitted_at is not None
        server._last_proposal_emitted_at -= timedelta(seconds=60)

        result = server._create_spec_text(self._create_spec_args())  # noqa: SLF001

        assert "Specification saved" in result
