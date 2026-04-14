"""
tests.setup.test_detector
-------------------------
Tests for the project detection system.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cortex.setup.detector import ProjectDetector


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project root."""
    return tmp_path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


# ------------------------------------------------------------------
# Node.js detection
# ------------------------------------------------------------------

class TestNodeDetection:
    def test_detects_node_project(self, tmp_project: Path) -> None:
        pkg = {
            "name": "my-app",
            "version": "1.0.0",
            "scripts": {"test": "jest", "lint": "eslint .", "build": "tsc"},
            "dependencies": {"express": "^4.18"},
            "devDependencies": {"typescript": "^5.0"},
        }
        _write_json(tmp_project / "package.json", pkg)

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.language == "javascript"
        assert ctx.stack.package_manager == "npm"
        assert ctx.stack.project_name == "my-app"
        assert "Express" in ctx.stack.frameworks

    def test_detects_yarn(self, tmp_project: Path) -> None:
        _write_json(tmp_project / "package.json", {"name": "test"})
        (tmp_project / "yarn.lock").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.package_manager == "yarn"

    def test_detects_pnpm(self, tmp_project: Path) -> None:
        _write_json(tmp_project / "package.json", {"name": "test"})
        (tmp_project / "pnpm-lock.yaml").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.package_manager == "pnpm"

    def test_detects_react_framework(self, tmp_project: Path) -> None:
        pkg = {"name": "react-app", "dependencies": {"react": "^18.0", "next": "^14.0"}}
        _write_json(tmp_project / "package.json", pkg)

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert "React" in ctx.stack.frameworks
        assert "Next.js" in ctx.stack.frameworks

    def test_detects_nestjs(self, tmp_project: Path) -> None:
        pkg = {
            "name": "api-server",
            "dependencies": {"@nestjs/core": "^10.0"},
            "scripts": {"test": "jest"},
        }
        _write_json(tmp_project / "package.json", pkg)

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert "NestJS" in ctx.stack.frameworks


# ------------------------------------------------------------------
# Python detection
# ------------------------------------------------------------------

class TestPythonDetection:
    def test_detects_python_project(self, tmp_project: Path) -> None:
        # Python project has pyproject.toml
        (tmp_project / "pyproject.toml").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        # Should fall through to python since no package.json
        assert ctx.stack.language == "python"


# ------------------------------------------------------------------
# Go detection
# ------------------------------------------------------------------

class TestGoDetection:
    def test_detects_go_project(self, tmp_project: Path) -> None:
        (tmp_project / "go.mod").write_text("module github.com/user/my-go-app\n\ngo 1.22\n")

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.language == "go"
        assert ctx.stack.package_manager == "go"
        assert ctx.stack.project_name == "github.com/user/my-go-app"
        assert ctx.stack.test_command == "go test ./..."

    def test_detects_go_test_files(self, tmp_project: Path) -> None:
        (tmp_project / "go.mod").write_text("module test\n\ngo 1.22\n")
        (tmp_project / "main_test.go").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.has_tests is True


# ------------------------------------------------------------------
# Rust detection
# ------------------------------------------------------------------

class TestRustDetection:
    def test_detects_rust_project(self, tmp_project: Path) -> None:
        (tmp_project / "Cargo.toml").write_text('[package]\nname = "my-crate"\nversion = "0.1.0"\n')

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.language == "rust"
        assert ctx.stack.package_manager == "cargo"
        assert ctx.stack.project_name == "my-crate"
        assert ctx.stack.test_command == "cargo test"


# ------------------------------------------------------------------
# Java detection
# ------------------------------------------------------------------

class TestJavaDetection:
    def test_detects_gradle_project(self, tmp_project: Path) -> None:
        (tmp_project / "build.gradle").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.language == "java"
        assert ctx.stack.package_manager == "gradle"

    def test_detects_maven_project(self, tmp_project: Path) -> None:
        (tmp_project / "pom.xml").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.language == "java"
        assert ctx.stack.package_manager == "maven"


# ------------------------------------------------------------------
# Ruby detection
# ------------------------------------------------------------------

class TestRubyDetection:
    def test_detects_rails_project(self, tmp_project: Path) -> None:
        (tmp_project / "Gemfile").write_text("source 'https://rubygems.org'\ngem 'rails'\ngem 'rspec'\n")
        (tmp_project / "spec").mkdir()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.stack.language == "ruby"
        assert "rails" in ctx.stack.frameworks
        assert "rspec" in ctx.stack.frameworks


# ------------------------------------------------------------------
# CI/CD detection
# ------------------------------------------------------------------

class TestCIDetection:
    def test_detects_github_actions(self, tmp_project: Path) -> None:
        workflows = tmp_project / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.ci.has_github_actions is True
        assert "ci.yml" in ctx.ci.workflows

    def test_detects_gitlab_ci(self, tmp_project: Path) -> None:
        (tmp_project / ".gitlab-ci.yml").touch()

        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.ci.has_other_ci is True
        assert ctx.ci.ci_type == "gitlab-ci"

    def test_detects_no_ci(self, tmp_project: Path) -> None:
        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        assert ctx.ci.ci_type == "none"


# ------------------------------------------------------------------
# Environment detection
# ------------------------------------------------------------------

class TestEnvDetection:
    def test_no_env_keys_by_default(self, tmp_project: Path) -> None:
        # This test runs without OPENAI_API_KEY set
        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        # In test environment, keys shouldn't be present unless set
        # We just verify the detection runs without errors
        assert isinstance(ctx.env.has_openai_key, bool)


# ------------------------------------------------------------------
# Fallback / unknown
# ------------------------------------------------------------------

class TestFallback:
    def test_unknown_project_type(self, tmp_project: Path) -> None:
        detector = ProjectDetector(tmp_project)
        ctx = detector.detect()

        # Should default to generic
        assert ctx.project_type == "generic"
        assert ctx.stack.language == "unknown"
        assert ctx.stack.project_name == tmp_project.name
