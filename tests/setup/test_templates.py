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

    def test_defaults_to_local_embedding(self, node_ctx: ProjectContext) -> None:
        content = render_config_yaml(node_ctx)
        data = yaml.safe_load(content)

        assert data["episodic"]["embedding_backend"] == "local"
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
