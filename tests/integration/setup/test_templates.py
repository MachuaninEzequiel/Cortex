"""
tests.setup.test_templates
--------------------------
Tests for the template rendering system.
"""

from __future__ import annotations

import pytest
import yaml

from cortex.setup.detector import CIInfo, EnvInfo, ProjectContext, StackInfo
from cortex.setup.templates import (
    render_architecture_md,
    render_cd_deploy,
    render_ci_feature,
    render_ci_pull_request,
    render_config_yaml,
    render_decisions_md,
    render_runbooks_md,
)


@pytest.fixture
def node_ctx() -> ProjectContext:
    return ProjectContext(
        stack=StackInfo(
            language="javascript",
            package_manager="npm",
            project_name="my-app",
            frameworks=["React", "Express"],
            has_tests=True,
            test_command="npm test",
            lint_command="npm run lint",
            build_command="npm run build",
        ),
        ci=CIInfo(has_github_actions=True, workflows=["ci.yml"], ci_type="github-actions"),
        env=EnvInfo(has_openai_key=False),
    )


@pytest.fixture
def python_ctx() -> ProjectContext:
    return ProjectContext(
        stack=StackInfo(
            language="python",
            package_manager="pip",
            project_name="my-python-lib",
            frameworks=["FastAPI"],
            has_tests=True,
            test_command="pytest",
            lint_command="ruff check .",
        ),
        ci=CIInfo(has_github_actions=False, ci_type="none"),
        env=EnvInfo(has_openai_key=True),
    )


@pytest.fixture
def generic_ctx() -> ProjectContext:
    return ProjectContext(
        stack=StackInfo(),
        ci=CIInfo(),
        env=EnvInfo(),
    )


# ------------------------------------------------------------------
# config.yaml rendering
# ------------------------------------------------------------------

class TestConfigYaml:
    def test_renders_valid_yaml(self, node_ctx: ProjectContext) -> None:
        content = render_config_yaml(node_ctx)
        data = yaml.safe_load(content)

        assert "episodic" in data
        assert "semantic" in data
        assert "retrieval" in data
        assert "llm" in data

    def test_defaults_to_onnx_embedding(self, node_ctx: ProjectContext) -> None:
        content = render_config_yaml(node_ctx)
        data = yaml.safe_load(content)

        assert data["episodic"]["embedding_backend"] == "onnx"
        assert data["llm"]["provider"] == "none"

    def test_uses_openai_when_key_detected(self, python_ctx: ProjectContext) -> None:
        content = render_config_yaml(python_ctx)
        data = yaml.safe_load(content)

        assert data["llm"]["provider"] == "openai"

    def test_includes_project_comment(self, node_ctx: ProjectContext) -> None:
        content = render_config_yaml(node_ctx)

        assert "my-app" in content
        assert "javascript" in content


# ------------------------------------------------------------------
# Workflow rendering
# ------------------------------------------------------------------

class TestCIPullRequest:
    def test_contains_cortex_commands(self, node_ctx: ProjectContext) -> None:
        content = render_ci_pull_request(node_ctx)

        assert "cortex pr-context capture" in content
        assert "cortex pr-context store" in content
        assert "cortex pr-context search" in content
        assert "cortex pr-context generate" in content
        assert "cortex sync-vault" in content

    def test_uses_project_test_command(self, node_ctx: ProjectContext) -> None:
        content = render_ci_pull_request(node_ctx)

        assert "npm test" in content

    def test_uses_project_lint_command(self, node_ctx: ProjectContext) -> None:
        content = render_ci_pull_request(node_ctx)

        assert "npm run lint" in content

    def test_generates_for_python(self, python_ctx: ProjectContext) -> None:
        content = render_ci_pull_request(python_ctx)

        assert "cortex" in content.lower()
        assert "pytest" in content


class TestCIFeature:
    def test_contains_cortex_remember(self, node_ctx: ProjectContext) -> None:
        content = render_ci_feature(node_ctx)

        assert "cortex remember" in content

    def test_triggers_on_feature_branches(self, node_ctx: ProjectContext) -> None:
        content = render_ci_feature(node_ctx)

        assert "feature/**" in content


class TestCDDeploy:
    def test_contains_cortex_integration(self, node_ctx: ProjectContext) -> None:
        content = render_cd_deploy(node_ctx)

        assert "cortex remember" in content
        assert "deploy" in content.lower()


# ------------------------------------------------------------------
# Vault docs rendering
# ------------------------------------------------------------------

class TestVaultDocs:
    def test_architecture_contains_project_name(self, node_ctx: ProjectContext) -> None:
        content = render_architecture_md(node_ctx)

        assert "my-app" in content
        assert "javascript" in content

    def test_decisions_contains_adr_template(self, node_ctx: ProjectContext) -> None:
        content = render_decisions_md(node_ctx)

        assert "ADR" in content
        assert "Context" in content
        assert "Decision" in content

    def test_runbooks_contains_test_commands(self, node_ctx: ProjectContext) -> None:
        content = render_runbooks_md(node_ctx)

        assert "npm test" in content

    def test_runbooks_for_python(self, python_ctx: ProjectContext) -> None:
        content = render_runbooks_md(python_ctx)

        assert "pytest" in content
        assert "ruff" in content


# ------------------------------------------------------------------
# Generic context handling
# ------------------------------------------------------------------

class TestGenericContext:
    def test_renders_workflows_for_generic(self, generic_ctx: ProjectContext) -> None:
        content = render_ci_pull_request(generic_ctx)

        # Should still produce valid workflow even with unknown stack
        assert "cortex" in content.lower()

    def test_renders_config_for_generic(self, generic_ctx: ProjectContext) -> None:
        content = render_config_yaml(generic_ctx)
        data = yaml.safe_load(content)

        assert data is not None
        assert "episodic" in data


# ------------------------------------------------------------------
# Layout-aware cache paths (Ola 2)
# ------------------------------------------------------------------


class _FakeLayout:
    """Minimal stand-in for WorkspaceLayout used by template tests."""

    def __init__(self, *, is_new_layout: bool) -> None:
        self.is_new_layout = is_new_layout
        self.is_legacy_layout = not is_new_layout


class TestLayoutAwareCachePaths:
    """The memory cache path inside workflows must match the active layout.

    Ola 2 regression: previously workflows hardcoded ``.memory/chroma``
    even when the adopter ran new layout. Now the cache step uses the
    same path that ``WorkspaceLayout.episodic_memory_path`` resolves to.
    """

    def test_new_layout_uses_cortex_memory(self, node_ctx: ProjectContext) -> None:
        layout = _FakeLayout(is_new_layout=True)
        content = render_ci_pull_request(node_ctx, layout=layout)
        # New layout caches the .cortex/memory directory.
        assert "path: .cortex/memory" in content
        assert ".memory/chroma" not in content

    def test_legacy_layout_uses_memory_chroma(self, node_ctx: ProjectContext) -> None:
        layout = _FakeLayout(is_new_layout=False)
        content = render_ci_pull_request(node_ctx, layout=layout)
        assert "path: .memory/chroma" in content
        assert ".cortex/memory" not in content

    def test_no_layout_falls_back_to_legacy(self, node_ctx: ProjectContext) -> None:
        # Backwards-compat: no layout passed → legacy path (safest default).
        content = render_ci_pull_request(node_ctx)
        assert "path: .memory/chroma" in content

    def test_ci_feature_respects_layout(self, node_ctx: ProjectContext) -> None:
        layout = _FakeLayout(is_new_layout=True)
        content = render_ci_feature(node_ctx, layout=layout)
        assert "path: .cortex/memory" in content
        # Cache steps must be both restore + save.
        assert "actions/cache/restore@v4" in content
        assert "actions/cache/save@v4" in content

    def test_cd_deploy_respects_layout(self, node_ctx: ProjectContext) -> None:
        layout = _FakeLayout(is_new_layout=True)
        content = render_cd_deploy(node_ctx, layout=layout)
        assert "path: .cortex/memory" in content
        assert "actions/cache/restore@v4" in content
        assert "actions/cache/save@v4" in content


class TestCliAlignment:
    """Every ``cortex <subcmd>`` mentioned in the generated workflows must
    exist in the CLI with the flags shown. If a refactor renames or removes
    a command, this test fails before adopters notice via CI breakage.
    """

    @pytest.fixture
    def all_workflows(self, node_ctx: ProjectContext) -> list[str]:
        return [
            render_ci_pull_request(node_ctx),
            render_ci_feature(node_ctx),
            render_cd_deploy(node_ctx),
        ]

    def test_workflows_reference_known_subcommands(self, all_workflows: list[str]) -> None:
        """All ``cortex <subcmd>`` calls land on registered Typer commands."""
        import re

        from cortex.cli.main import app

        # Collect every "cortex <subcmd>" token across the workflows.
        cortex_calls: set[tuple[str, ...]] = set()
        for content in all_workflows:
            # Capture cortex + 1 or 2 tokens (subcmd, optional sub-subcmd).
            for match in re.finditer(
                r"cortex\s+([a-z][a-z0-9-]*)(?:\s+([a-z][a-z0-9-]*))?",
                content,
            ):
                head = match.group(1)
                sub = match.group(2)
                if sub:
                    cortex_calls.add((head, sub))
                else:
                    cortex_calls.add((head,))

        # Build the set of registered top-level commands (and sub-app names).
        # Typer infers a command name from the function name when ``name`` is
        # None, so we fall back to that to cover all commands.
        def _cmd_name(cmd) -> str:
            return cmd.name or (cmd.callback.__name__.replace("_", "-") if cmd.callback else "")

        known_top = {_cmd_name(cmd) for cmd in app.registered_commands}
        known_top.discard("")
        known_sub_apps = {grp.name for grp in app.registered_groups if grp.name}
        # Walk sub-apps for their commands.
        known_pairs: set[tuple[str, str]] = set()
        for grp in app.registered_groups:
            if not grp.name:
                continue
            for cmd in grp.typer_instance.registered_commands:
                known_pairs.add((grp.name, _cmd_name(cmd)))

        for call in cortex_calls:
            head = call[0]
            # Allow shell builtins or words that follow a `cortex` literal
            # but aren't actually subcommands (e.g. ``cortex doctor`` then
            # a pipe). We only flag tokens that look like commands.
            if head in known_top or head in known_sub_apps:
                if len(call) == 2:
                    sub = call[1]
                    # Sub-app calls must match a registered sub-command.
                    if head in known_sub_apps:
                        assert (head, sub) in known_pairs, (
                            f"Workflow calls `cortex {head} {sub}` "
                            f"but `{sub}` is not a registered sub-command "
                            f"of `cortex {head}`."
                        )
                continue
            # Common false positives that grep-match but aren't subcommands.
            if head in {"memory", "context"}:
                continue
            raise AssertionError(
                f"Workflow calls `cortex {head}` but `{head}` is not a "
                f"registered top-level command nor sub-app. "
                f"Known top: {sorted(known_top)[:8]}... "
                f"Known sub-apps: {sorted(known_sub_apps)}"
            )


class TestCommandsAcrossStacks:
    """Workflows must emit stack-correct commands for Node, Python and Go."""

    def test_node_workflow_uses_npm_commands(self, node_ctx: ProjectContext) -> None:
        content = render_ci_pull_request(node_ctx)
        assert "npm ci" in content  # install
        assert "npm test" in content
        assert "npm run lint" in content
        assert "npm audit" in content
        assert "actions/setup-node@v4" in content

    def test_python_workflow_uses_pytest_and_ruff(self, python_ctx: ProjectContext) -> None:
        content = render_ci_pull_request(python_ctx)
        assert "pytest" in content
        assert "ruff check" in content
        assert "pip audit" in content
        assert "actions/setup-python@v5" in content

    def test_go_workflow_uses_go_commands(self) -> None:
        go_ctx = ProjectContext(
            stack=StackInfo(
                language="go",
                package_manager="go",
                project_name="my-go-svc",
                frameworks=[],
                has_tests=True,
                test_command="",
                lint_command="",
            ),
            ci=CIInfo(has_github_actions=True),
            env=EnvInfo(),
        )
        content = render_ci_pull_request(go_ctx)
        assert "go test ./..." in content
        assert "golangci-lint run" in content
        assert "govulncheck ./..." in content
        assert "actions/setup-go@v5" in content
