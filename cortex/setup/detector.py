"""
cortex.setup.detector
---------------------
Auto-detects project stack, CI/CD pipelines, and environment configuration.
Used by ``cortex setup`` to generate project-aware defaults.

EPIC 4: The detector now accepts an optional ``WorkspaceLayout``
to correctly locate ``.github/workflows/`` regardless of layout mode.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.workspace.layout import WorkspaceLayout


@dataclass
class StackInfo:
    """Detected project stack information."""

    language: str = "unknown"
    package_manager: str = "unknown"
    project_name: str = ""
    frameworks: list[str] = field(default_factory=list)
    has_tests: bool = False
    test_command: str = ""
    lint_command: str = ""
    build_command: str = ""
    dev_dependencies: list[str] = field(default_factory=list)


@dataclass
class CIInfo:
    """Detected CI/CD configuration."""

    has_github_actions: bool = False
    workflows: list[str] = field(default_factory=list)
    has_other_ci: bool = False
    ci_type: str = "none"  # github-actions, gitlab-ci, circleci, jenkins, none


@dataclass
class EnvInfo:
    """Detected environment variables relevant to Cortex."""

    has_openai_key: bool = False
    has_anthropic_key: bool = False
    has_ollama: bool = False
    ollama_base_url: str | None = None


@dataclass
class ProjectContext:
    """Complete detected project context."""

    stack: StackInfo = field(default_factory=StackInfo)
    ci: CIInfo = field(default_factory=CIInfo)
    env: EnvInfo = field(default_factory=EnvInfo)
    root: Path = field(default_factory=Path.cwd)
    layout: "WorkspaceLayout | None" = None

    @property
    def project_type(self) -> str:
        """High-level project type label for template selection."""
        s = self.stack
        if s.language == "python":
            return "python"
        if s.language == "javascript" or s.language == "typescript":
            return "node"
        if s.language == "go":
            return "go"
        if s.language == "rust":
            return "rust"
        if s.language == "java" or s.language == "kotlin":
            return "java"
        if s.language == "ruby":
            return "ruby"
        return "generic"


class ProjectDetector:
    """
    Detects the project's language, package manager, frameworks,
    CI/CD setup, and available environment variables.
    """

    def __init__(self, root: Path | None = None):
        self.root = root or Path.cwd()

    def detect(self) -> ProjectContext:
        """Run all detectors and return a combined ProjectContext."""
        from cortex.workspace.layout import WorkspaceLayout

        root = self.root
        try:
            layout = WorkspaceLayout.discover(root)
        except Exception:
            layout = None

        return ProjectContext(
            stack=self._detect_stack(),
            ci=self._detect_ci(),
            env=self._detect_env(),
            root=root,
            layout=layout,
        )

    # ------------------------------------------------------------------
    # Stack detection
    # ------------------------------------------------------------------

    def _detect_stack(self) -> StackInfo:
        info = StackInfo()

        # Check language-specific files in priority order
        detectors = [
            ("python", self._detect_python),
            ("javascript", self._detect_node),
            ("go", self._detect_go),
            ("rust", self._detect_rust),
            ("java", self._detect_java),
            ("ruby", self._detect_ruby),
        ]

        for lang, detector in detectors:
            result = detector()
            if result is not None:
                info.language = lang
                info.package_manager = result.get("package_manager", "unknown")
                info.project_name = result.get("project_name", "")
                info.frameworks = result.get("frameworks", [])
                info.has_tests = result.get("has_tests", False)
                info.test_command = result.get("test_command", "")
                info.lint_command = result.get("lint_command", "")
                info.build_command = result.get("build_command", "")
                info.dev_dependencies = result.get("dev_dependencies", [])
                break

        # Project name fallback
        if not info.project_name:
            info.project_name = self.root.name

        return info

    def _read_json(self, path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _detect_python(self) -> dict | None:
        pyproject = self.root / "pyproject.toml"
        setup_py = self.root / "setup.py"
        requirements = self.root / "requirements.txt"

        if pyproject.exists() or setup_py.exists() or requirements.exists():
            # Check for common Python test files
            has_tests = (
                any(self.root.rglob("test_*.py"))
                or any(self.root.rglob("*_test.py"))
                or (self.root / "tests").is_dir()
            )
            return {
                "package_manager": "pip",
                "project_name": self.root.name,
                "has_tests": has_tests,
                "test_command": "pytest" if has_tests else "python -m unittest",
                "lint_command": "ruff check .",
            }
        return None

    def _detect_go(self) -> dict | None:
        go_mod = self.root / "go.mod"
        if go_mod.exists():
            content = go_mod.read_text(encoding="utf-8")
            module_match = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
            name = module_match.group(1) if module_match else self.root.name
            return {
                "package_manager": "go",
                "project_name": name,
                "has_tests": (self.root / "go_test.go").exists()
                or any(self.root.rglob("*_test.go")),
                "test_command": "go test ./...",
                "lint_command": "golangci-lint run",
            }
        return None

    def _detect_rust(self) -> dict | None:
        # Cargo.toml isn't JSON, just check existence
        cargo_toml = self.root / "Cargo.toml"
        if cargo_toml.exists():
            content = cargo_toml.read_text(encoding="utf-8")
            name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
            return {
                "package_manager": "cargo",
                "project_name": name_match.group(1) if name_match else self.root.name,
                "has_tests": True,  # Rust projects typically have tests
                "test_command": "cargo test",
                "lint_command": "cargo clippy",
                "build_command": "cargo build --release",
            }
        return None

    def _detect_java(self) -> dict | None:
        gradle = self.root / "build.gradle"
        gradle_kts = self.root / "build.gradle.kts"
        maven = self.root / "pom.xml"

        if gradle.exists() or gradle_kts.exists():
            return {
                "package_manager": "gradle",
                "project_name": self.root.name,
                "has_tests": True,
                "test_command": "./gradlew test",
                "lint_command": "./gradlew check",
                "build_command": "./gradlew build",
            }
        if maven.exists():
            return {
                "package_manager": "maven",
                "project_name": self.root.name,
                "has_tests": True,
                "test_command": "mvn test",
                "lint_command": "mvn checkstyle:check",
                "build_command": "mvn package",
            }
        return None

    def _detect_ruby(self) -> dict | None:
        gemfile = self.root / "Gemfile"
        if gemfile.exists():
            content = gemfile.read_text(encoding="utf-8")
            frameworks = []
            if "rails" in content or "gem 'rails'" in content:
                frameworks.append("rails")
            if "rspec" in content or "gem 'rspec'" in content:
                frameworks.append("rspec")
            return {
                "package_manager": "bundler",
                "project_name": self.root.name,
                "frameworks": frameworks,
                "has_tests": (self.root / "spec").exists(),
                "test_command": "bundle exec rspec" if "rspec" in str(frameworks) else "bundle exec rake test",
                "lint_command": "bundle exec rubocop",
            }
        return None

    def _detect_node(self) -> dict | None:
        pkg_path = self.root / "package.json"
        if not pkg_path.exists():
            return None
        pkg = self._read_json(pkg_path)
        if pkg is None:
            return None
        return self._parse_node_json(pkg)

    def _parse_node_json(self, pkg: dict) -> dict:
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        frameworks = []

        # Detect frameworks
        framework_map = {
            "react": "React",
            "next": "Next.js",
            "next.js": "Next.js",
            "vue": "Vue",
            "nuxt": "Nuxt",
            "@angular/core": "Angular",
            "express": "Express",
            "fastify": "Fastify",
            "nestjs": "NestJS",
            "@nestjs/core": "NestJS",
            "svelte": "Svelte",
            "remix": "Remix",
            "@remix-run/node": "Remix",
            "django": "Django",
            "flask": "Flask",
            "fastapi": "FastAPI",
            "bullmq": "BullMQ",
            "bull": "Bull",
            "prisma": "Prisma",
            "sequelize": "Sequelize",
            "typeorm": "TypeORM",
        }
        for dep, fw_name in framework_map.items():
            if dep in deps:
                frameworks.append(fw_name)

        scripts = pkg.get("scripts", {})
        has_tests = bool(scripts.get("test"))
        test_command = scripts.get("test", "echo 'no test script'")
        lint_command = scripts.get("lint", "")
        build_command = scripts.get("build", "")

        return {
            "package_manager": "pnpm" if (self.root / "pnpm-lock.yaml").exists()
            else "yarn" if (self.root / "yarn.lock").exists()
            else "npm",
            "project_name": pkg.get("name", self.root.name),
            "frameworks": frameworks,
            "has_tests": has_tests,
            "test_command": test_command,
            "lint_command": lint_command,
            "build_command": build_command,
            "dev_dependencies": list(pkg.get("devDependencies", {}).keys()),
        }

    # ------------------------------------------------------------------
    # CI/CD detection
    # ------------------------------------------------------------------

    def _detect_ci(self) -> CIInfo:
        info = CIInfo()

        # GitHub Actions
        gh_workflows = self.root / ".github" / "workflows"
        if gh_workflows.exists():
            info.has_github_actions = True
            info.workflows = [
                f.name for f in gh_workflows.iterdir()
                if f.is_file() and f.suffix in (".yml", ".yaml")
            ]

        # GitLab CI
        if (self.root / ".gitlab-ci.yml").exists():
            info.has_other_ci = True
            info.ci_type = "gitlab-ci"

        # CircleCI
        if (self.root / ".circleci" / "config.yml").exists():
            info.has_other_ci = True
            info.ci_type = "circleci"

        # Jenkins
        if (self.root / "Jenkinsfile").exists():
            info.has_other_ci = True
            info.ci_type = "jenkins"

        if not info.has_github_actions and not info.has_other_ci:
            info.ci_type = "none"

        return info

    # ------------------------------------------------------------------
    # Environment detection
    # ------------------------------------------------------------------

    def _detect_env(self) -> EnvInfo:
        return EnvInfo(
            has_openai_key=bool(os.environ.get("OPENAI_API_KEY")),
            has_anthropic_key=bool(os.environ.get("ANTHROPIC_API_KEY")),
            has_ollama=bool(os.environ.get("OLLAMA_BASE_URL")),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL"),
        )
