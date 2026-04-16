"""
cortex.setup.orchestrator
-------------------------
Orchestrates the full ``cortex setup`` flow:
detect → generate → write → initialize.
"""

from __future__ import annotations

from pathlib import Path

from cortex.setup.cortex_workspace import ensure_cortex_workspace
from cortex.setup.detector import ProjectContext, ProjectDetector
from cortex.setup.templates import (
    DEVSECDOCSOPS_SCRIPT,
    render_architecture_md,
    render_cd_deploy,
    render_ci_feature,
    render_ci_pull_request,
    render_config_yaml,
    render_decisions_md,
    render_runbooks_md,
)


class SetupOrchestrator:
    """Runs the full setup pipeline and reports results."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path.cwd()
        self.detector = ProjectDetector(self.root)
        self.ctx: ProjectContext | None = None
        self.created: list[str] = []
        self.skipped: list[str] = []
        self.warnings: list[str] = []

    def run(self) -> dict:
        """Execute the full setup pipeline. Returns a summary dict."""
        # Step 1: Detect
        self.ctx = self.detector.detect()

        # Step 2: Generate and write files
        self._create_directories()
        self._create_config()
        self._create_vault_docs()
        self._create_workflows()
        self._create_devsecdocops_script()
        self._create_agent_guidelines()
        self._install_skills()

        # Step 3: Initialize Cortex memory
        self._init_memory()

        # Step 4: Return summary
        return self._summary()

    # ------------------------------------------------------------------
    # Directory creation
    # ------------------------------------------------------------------

    def _create_directories(self) -> None:
        for d in [
            ".memory",
            "vault",
            "vault/sessions",
            "vault/decisions",
            "vault/runbooks",
            "vault/incidents",
            "vault/hu",
            "vault/specs",
        ]:
            path = self.root / d
            if path.exists():
                self.skipped.append(f"{d}/ (already exists)")
            else:
                path.mkdir(parents=True, exist_ok=True)
                self.created.append(f"{d}/")

    # ------------------------------------------------------------------
    # config.yaml
    # ------------------------------------------------------------------

    def _create_config(self) -> None:
        path = self.root / "config.yaml"
        if path.exists():
            self.skipped.append("config.yaml (already exists)")
            return

        content = render_config_yaml(self.ctx)
        path.write_text(content, encoding="utf-8")
        self.created.append("config.yaml")

    # ------------------------------------------------------------------
    # Vault docs
    # ------------------------------------------------------------------

    def _create_vault_docs(self) -> None:
        vault = self.root / "vault"
        vault.mkdir(exist_ok=True)

        docs = [
            ("architecture.md", render_architecture_md),
            ("decisions.md", render_decisions_md),
            ("runbooks.md", render_runbooks_md),
        ]

        for filename, renderer in docs:
            path = vault / filename
            if path.exists():
                self.skipped.append(f"vault/{filename} (already exists)")
            else:
                path.write_text(renderer(self.ctx), encoding="utf-8")
                self.created.append(f"vault/{filename}")

    # ------------------------------------------------------------------
    # GitHub Actions workflows
    # ------------------------------------------------------------------

    def _create_workflows(self) -> None:
        workflows_dir = self.root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        workflow_map = [
            ("ci-pull-request.yml", render_ci_pull_request),
            ("ci-feature.yml", render_ci_feature),
            ("cd-deploy.yml", render_cd_deploy),
        ]

        for filename, renderer in workflow_map:
            path = workflows_dir / filename
            if path.exists():
                self.skipped.append(f".github/workflows/{filename} (already exists)")
            else:
                path.write_text(renderer(self.ctx), encoding="utf-8")
                self.created.append(f".github/workflows/{filename}")

    # ------------------------------------------------------------------
    # devsecdocops.sh script
    # ------------------------------------------------------------------

    def _create_devsecdocops_script(self) -> None:
        scripts_dir = self.root / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        path = scripts_dir / "devsecdocops.sh"
        if path.exists():
            self.skipped.append("scripts/devsecdocops.sh (already exists)")
        else:
            path.write_text(DEVSECDOCSOPS_SCRIPT, encoding="utf-8")
            path.chmod(0o755)
            self.created.append("scripts/devsecdocops.sh")

    # ------------------------------------------------------------------
    # Agent behavior guidelines
    # ------------------------------------------------------------------

    def _create_agent_guidelines(self) -> None:
        """
        Create the full Release 2 Cortex workspace structure.
        """
        result = ensure_cortex_workspace(self.root)
        self.created.extend(result["created"])
        self.skipped.extend(f"{path} (already exists)" for path in result["skipped"])

    # ------------------------------------------------------------------
    # Install Qwen skills
    # ------------------------------------------------------------------

    def _install_skills(self) -> None:
        """Copy bundled Obsidian skills into project's .qwen/skills/."""
        from cortex.skills import install_skills as _install

        qwen_skills = self.root / ".qwen" / "skills"
        installed = _install(qwen_skills)

        for skill in installed:
            if "already exists" in skill:
                self.skipped.append(f".qwen/skills/{skill}")
            else:
                self.created.append(f".qwen/skills/{skill}")

    # ------------------------------------------------------------------
    # Initialize Cortex memory (ChromaDB) + Cold Start
    # ------------------------------------------------------------------

    def _init_memory(self) -> None:
        """Run a minimal sync to initialize ChromaDB with Cold Start."""
        try:
            # We try to import and initialize the memory store
            from cortex.core import AgentMemory
            
            config_path = self.root / "config.yaml"
            if config_path.exists():
                mem = AgentMemory(config_path=str(config_path))
                
                # Run Cold Start (3-layer bootstrap) if memory is empty
                from cortex.setup.cold_start import run_cold_start
                vault_path = self.root / "vault"
                cold_start_result = run_cold_start(
                    project_root=self.root,
                    memory_store=mem.episodic,
                    vault_path=vault_path,
                )
                
                # Sync vault and store setup memory
                mem.sync_vault()
                mem.remember(
                    f"Cortex initialized for project {self.ctx.stack.project_name} "
                    f"({self.ctx.stack.language}, {self.ctx.stack.package_manager})",
                    memory_type="setup",
                    tags=["cortex", "setup", self.ctx.stack.language],
                )
                
                # Add Cold Start info to warnings for visibility
                if cold_start_result.get("total", 0) > 0:
                    self.warnings.append(
                        f"Cold Start: {cold_start_result['total']} bootstrap memories created"
                    )
        except Exception as e:
            self.warnings.append(f"Memory init skipped: {e}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _summary(self) -> dict:
        return {
            "project_name": self.ctx.stack.project_name if self.ctx else "unknown",
            "language": self.ctx.stack.language if self.ctx else "unknown",
            "package_manager": self.ctx.stack.package_manager if self.ctx else "unknown",
            "frameworks": self.ctx.stack.frameworks if self.ctx else [],
            "ci_detected": self.ctx.ci.ci_type if self.ctx else "none",
            "created": self.created,
            "skipped": self.skipped,
            "warnings": self.warnings,
        }


def format_summary(summary: dict) -> str:
    """Format the setup summary for terminal output."""
    lines = []
    lines.append("")
    lines.append("═" * 55)
    lines.append("🧠 Cortex Setup Complete")
    lines.append("═" * 55)
    lines.append("")
    lines.append(f"  Project: {summary['project_name']}")
    lines.append(f"  Language: {summary['language']} ({summary['package_manager']})")
    if summary.get("frameworks"):
        lines.append(f"  Frameworks: {', '.join(summary['frameworks'])}")
    lines.append(f"  CI/CD: {summary.get('ci_detected', 'none')}")
    lines.append("")

    if summary["created"]:
        lines.append(f"  ✅ Created ({len(summary['created'])} files):")
        for f in summary["created"]:
            lines.append(f"    • {f}")
        lines.append("")

    if summary["skipped"]:
        lines.append(f"  ⏭ Skipped ({len(summary['skipped'])} - already exist):")
        for f in summary["skipped"]:
            lines.append(f"    • {f}")
        lines.append("")

    if summary["warnings"]:
        lines.append("  ⚠ Warnings:")
        for w in summary["warnings"]:
            lines.append(f"    • {w}")
        lines.append("")

    lines.append("  Next steps:")
    lines.append("    1. Review generated files in vault/, .github/workflows/, config.yaml")
    lines.append("    2. Commit and push to trigger CI/CD with Cortex integration")
    lines.append("    3. Or run manually: cortex remember \"my first memory\"")
    lines.append("")
    lines.append("  💡 Tip: Install the Cortex VS Code extension for a GUI interface.")
    lines.append("═" * 55)

    return "\n".join(lines)
