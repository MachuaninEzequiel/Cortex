"""Tests for cortex.autopilot.renderers."""
from __future__ import annotations

from cortex.autopilot.models import AutopilotSessionState, AutopilotCheckpoint
from cortex.autopilot.renderers.minimal import MinimalSessionRenderer
from cortex.autopilot.renderers.implementation import ImplementationSessionRenderer
from cortex.autopilot.renderers.docs_only import DocsOnlySessionRenderer
from cortex.autopilot.renderers.fallback_draft import FallbackDraftRenderer


class TestMinimalSessionRenderer:
    def test_basic(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            user_request="Fix typo",
            changed_files=["README.md"],
        )
        r = MinimalSessionRenderer()
        draft = r.render(state)
        assert draft.title == "Fix typo"
        assert "## Request" in draft.body
        assert "README.md" in draft.body
        assert draft.confidence == "medium"

    def test_no_data(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        r = MinimalSessionRenderer()
        draft = r.render(state)
        assert draft.confidence == "auto-draft"
        assert any("No user request" in w for w in draft.warnings)

    def test_checkpoints(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            checkpoints=[
                AutopilotCheckpoint(timestamp=__import__("datetime").datetime.now(), summary="ck1", verified=True)
            ],
        )
        r = MinimalSessionRenderer()
        draft = r.render(state)
        assert "ck1" in draft.body
        assert "✅" in draft.body


class TestImplementationSessionRenderer:
    def test_full(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            user_request="Implement auth",
            detected_task_type="fast-code",
            complexity="fast",
            changed_files=["auth.py", "models.py"],
            spec_path="vault/specs/auth.md",
            tools_seen=["cortex_context"],
            commands_seen=["pytest"],
            checkpoints=[
                AutopilotCheckpoint(timestamp=__import__("datetime").datetime.now(), summary="Added JWT", verified=True),
            ],
        )
        r = ImplementationSessionRenderer()
        draft = r.render(state)
        assert "Implement auth" in draft.body
        assert "auth.py" in draft.body
        assert "vault/specs/auth.md" in draft.body
        assert "cortex_context" in draft.body
        assert "pytest" in draft.body
        assert "Added JWT" in draft.body
        assert draft.confidence == "medium"

    def test_no_files(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            user_request="Implement auth",
        )
        r = ImplementationSessionRenderer()
        draft = r.render(state)
        assert draft.confidence == "auto-draft"
        assert any("No file changes" in w for w in draft.warnings)

    def test_unverified_checkpoints(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            changed_files=["a.py"],
            checkpoints=[
                AutopilotCheckpoint(timestamp=__import__("datetime").datetime.now(), summary="ck", verified=False),
            ],
        )
        r = ImplementationSessionRenderer()
        draft = r.render(state)
        assert any("No verified checkpoints" in w for w in draft.warnings)


class TestDocsOnlySessionRenderer:
    def test_docs_files(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            user_request="Update README",
            changed_files=["README.md", "CHANGELOG.md", "setup.py"],
        )
        r = DocsOnlySessionRenderer()
        draft = r.render(state)
        assert "README.md" in draft.body
        assert "CHANGELOG.md" in draft.body
        assert "setup.py" in draft.body
        assert draft.confidence == "medium"

    def test_no_docs(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            changed_files=["main.py"],
        )
        r = DocsOnlySessionRenderer()
        draft = r.render(state)
        assert draft.confidence == "auto-draft"
        assert any("No documentation" in w for w in draft.warnings)


class TestFallbackDraftRenderer:
    def test_fallback(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        r = FallbackDraftRenderer()
        draft = r.render(state)
        assert draft.confidence == "auto-draft"
        assert "auto-generated draft" in draft.body
        assert any("incomplete data" in w.lower() for w in draft.warnings)

    def test_with_request(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            user_request="Fix something",
        )
        r = FallbackDraftRenderer()
        draft = r.render(state)
        assert "Fix something" in draft.body
        assert draft.confidence == "auto-draft"
