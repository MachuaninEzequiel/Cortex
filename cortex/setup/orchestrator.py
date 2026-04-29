"""
cortex.setup.orchestrator
-------------------------
Orchestration engine for modular setup (agent, pipeline, full).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import typer

from cortex.enterprise.config import render_enterprise_config_yaml
from cortex.enterprise.models import EnterpriseOrgConfig
from cortex.setup.cortex_workspace import ensure_cortex_workspace
from cortex.setup.detector import ProjectContext, ProjectDetector
from cortex.setup.enterprise_presets import resolve_enterprise_setup
from cortex.setup.templates import (
    DEVSECDOCSOPS_SCRIPT,
    render_architecture_md,
    render_cd_deploy,
    render_ci_enterprise_governance,
    render_ci_feature,
    render_ci_pull_request,
    render_config_yaml,
    render_decisions_md,
    render_enterprise_vault_readme,
    render_enterprise_runbook_md,
    render_org_yaml,
    render_git_vault_policy_md,
    render_runbooks_md,
)


class SetupMode(str, Enum):
    AGENT = "agent"
    PIPELINE = "pipeline"
    FULL = "full"
    WEBGRAPH = "webgraph"
    ENTERPRISE = "enterprise"

class SetupOrchestrator:
    """Runs the setup pipeline based on mode and reports results."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path.cwd()
        self.detector = ProjectDetector(self.root)
        self.ctx: ProjectContext | None = None
        self.created: list[str] = []
        self.skipped: list[str] = []
        self.warnings: list[str] = []

    def run(
        self,
        mode: SetupMode = SetupMode.FULL,
        git_depth: int = 50,
        ide: str | None = None,
        attach_project_root: str | None = None,
        dry_run: bool = False,
        enterprise_profile: str = "small-company",
        enterprise_overrides: dict[str, Any] | None = None,
    ) -> dict:
        """Execute the setup pipeline based on mode. Returns a summary dict."""
        self.git_depth = git_depth
        self.ide = ide
        self.attach_project_root = attach_project_root
        self.dry_run = dry_run
        self.ctx = self.detector.detect()
        if mode == SetupMode.AGENT:
            self._run_agent_flow()
        elif mode == SetupMode.PIPELINE:
            self._run_pipeline_flow()
        elif mode == SetupMode.WEBGRAPH:
            self._run_webgraph_flow()
        elif mode == SetupMode.ENTERPRISE:
            self._run_enterprise_flow(profile=enterprise_profile, overrides=enterprise_overrides or {})
        else:
            self._run_full_flow()
        return self._summary()

    def _run_enterprise_flow(self, profile: str, overrides: dict[str, Any]) -> None:
        """Run guided enterprise setup (interactive or non-interactive)."""
        if self.dry_run:
            self._simulate_enterprise_flow()
            return

        self._create_directories()
        self._create_config()
        self._create_enterprise_org_config(profile=profile, overrides=overrides)
        self._create_vault_docs()
        self._create_enterprise_vault()
        self._create_workflows()
        self._create_devsecdocops_script()
        self._create_enterprise_workspace()

    def _run_agent_flow(self) -> None:
        """Setup only local agent/cognitive components."""
        self._create_directories(only_agent=True)
        self._create_config()
        self._create_enterprise_org_config()
        self._create_vault_docs()
        self._create_enterprise_vault()
        self._create_agent_guidelines()
        self._install_skills()
        self._init_memory()
        if self.ide:
            self._install_ide()

    def _run_pipeline_flow(self) -> None:
        """Setup only CI/CD / DevOps components."""
        self._check_vault_pipeline_interactive()
        self._create_config()
        self._create_enterprise_org_config()
        self._create_enterprise_vault()
        self._create_workflows()
        self._create_devsecdocops_script()

    def _run_full_flow(self) -> None:
        """Run everything."""
        self._create_directories()
        self._create_config()
        self._create_enterprise_org_config()
        self._create_vault_docs()
        self._create_enterprise_vault()
        self._create_workflows()
        self._create_devsecdocops_script()
        self._create_agent_guidelines()
        self._install_skills()
        self._init_memory()
        self._install_ide()

    def _run_webgraph_flow(self) -> None:
        """Setup only the webgraph module with minimal supporting files."""
        self._install_webgraph()

    def _create_directories(self, only_agent: bool = False) -> None:
        dirs = [
            ".memory",
            "vault",
            "vault/sessions",
            "vault/decisions",
            "vault/runbooks",
            "vault/incidents",
            "vault/hu",
            "vault/specs",
        ]
        for d in dirs:
            path = self.root / d
            if path.exists():
                self.skipped.append(f"{d}/ (already exists)")
            else:
                path.mkdir(parents=True, exist_ok=True)
                self.created.append(f"{d}/")

    def _create_config(self) -> None:
        if not self.ctx:
            return
        path = self.root / "config.yaml"
        if path.exists():
            self.skipped.append("config.yaml (already exists)")
            return
        path.write_text(render_config_yaml(self.ctx), encoding="utf-8")
        self.created.append("config.yaml")

    def _create_vault_docs(self) -> None:
        if not self.ctx:
            return
        vault = self.root / "vault"
        vault.mkdir(exist_ok=True)
        for filename, renderer in [
            ("architecture.md", render_architecture_md),
            ("decisions.md", render_decisions_md),
            ("runbooks.md", render_runbooks_md),
            ("runbooks/enterprise-runbook.md", render_enterprise_runbook_md),
            ("runbooks/git-vault-policy.md", render_git_vault_policy_md),
        ]:
            path = vault / filename
            if path.exists():
                self.skipped.append(f"vault/{filename} (already exists)")
            else:
                path.write_text(renderer(self.ctx), encoding="utf-8")
                self.created.append(f"vault/{filename}")

    def _create_enterprise_org_config(
        self,
        profile: str = "small-company",
        overrides: dict[str, Any] | None = None,
    ) -> None:
        if not self.ctx:
            return
        path = self.root / ".cortex" / "org.yaml"
        if path.exists():
            self.skipped.append(".cortex/org.yaml (already exists)")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        resolved = resolve_enterprise_setup(
            project_name=self.ctx.stack.project_name or self.root.name,
            profile=profile,
            overrides=overrides or {},
            github_actions_enabled=self.ctx.ci.has_github_actions,
        )
        config = EnterpriseOrgConfig.model_validate(resolved.overrides)
        path.write_text(render_enterprise_config_yaml(config), encoding="utf-8")
        self.created.append(".cortex/org.yaml")

    def _create_enterprise_workspace(self) -> None:
        path = self.root / ".cortex" / "workspace.yaml"
        if path.exists():
            self.skipped.append(".cortex/workspace.yaml (already exists)")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "version: 1\n"
            "projects:\n"
            "  - id: primary\n"
            "    path: .\n"
            "    role: owner\n",
            encoding="utf-8",
        )
        self.created.append(".cortex/workspace.yaml")

    def _simulate_enterprise_flow(self) -> None:
        simulated = [
            ".memory/",
            "vault/",
            "vault/sessions/",
            "vault/decisions/",
            "vault/runbooks/",
            "vault/incidents/",
            "vault/hu/",
            "vault/specs/",
            "config.yaml",
            ".cortex/org.yaml",
            "vault/architecture.md",
            "vault/decisions.md",
            "vault/runbooks.md",
            "vault/runbooks/enterprise-runbook.md",
            "vault/runbooks/git-vault-policy.md",
            "vault-enterprise/runbooks/",
            "vault-enterprise/decisions/",
            "vault-enterprise/incidents/",
            "vault-enterprise/hu/",
            "vault-enterprise/README.md",
            ".github/workflows/ci-pull-request.yml",
            ".github/workflows/ci-feature.yml",
            ".github/workflows/cd-deploy.yml",
            ".github/workflows/ci-enterprise-governance.yml",
            "scripts/devsecdocops.sh",
            ".cortex/workspace.yaml",
        ]
        for item in simulated:
            self.created.append(f"{item} (dry-run)")

    def _create_enterprise_vault(self) -> None:
        if not self.ctx:
            return
        enterprise_root = self.root / "vault-enterprise"
        created_any = False
        for dirname in ("runbooks", "decisions", "incidents", "hu"):
            target = enterprise_root / dirname
            if target.exists():
                self.skipped.append(f"vault-enterprise/{dirname}/ (already exists)")
            else:
                target.mkdir(parents=True, exist_ok=True)
                self.created.append(f"vault-enterprise/{dirname}/")
                created_any = True

        readme_path = enterprise_root / "README.md"
        if readme_path.exists():
            self.skipped.append("vault-enterprise/README.md (already exists)")
        else:
            enterprise_root.mkdir(parents=True, exist_ok=True)
            readme_path.write_text(render_enterprise_vault_readme(self.ctx), encoding="utf-8")
            self.created.append("vault-enterprise/README.md")
            created_any = True

        if not created_any and not enterprise_root.exists():
            enterprise_root.mkdir(parents=True, exist_ok=True)

    def _create_workflows(self) -> None:
        if not self.ctx:
            return
        wdir = self.root / ".github" / "workflows"
        wdir.mkdir(parents=True, exist_ok=True)
        for fn, rd in [
            ("ci-pull-request.yml", render_ci_pull_request),
            ("ci-feature.yml", render_ci_feature),
            ("cd-deploy.yml", render_cd_deploy),
            ("ci-enterprise-governance.yml", render_ci_enterprise_governance),
        ]:
            path = wdir / fn
            if path.exists():
                self.skipped.append(f".github/workflows/{fn} (already exists)")
            else:
                path.write_text(rd(self.ctx), encoding="utf-8")
                self.created.append(f".github/workflows/{fn}")

    def _create_devsecdocops_script(self) -> None:
        sdir = self.root / "scripts"
        sdir.mkdir(exist_ok=True)
        path = sdir / "devsecdocops.sh"
        if path.exists():
            self.skipped.append("scripts/devsecdocops.sh (already exists)")
        else:
            path.write_text(DEVSECDOCSOPS_SCRIPT, encoding="utf-8")
            path.chmod(0o755)
            self.created.append("scripts/devsecdocops.sh")

    def _create_agent_guidelines(self) -> None:
        result = ensure_cortex_workspace(self.root)
        self.created.extend(result["created"])
        self.skipped.extend(f"{path} (already exists)" for path in result["skipped"])

    def _install_skills(self) -> None:
        """Copy bundled Obsidian skills into project's .cortex/skills/ and .qwen/skills/."""
        from cortex.skills import install_skills as _inst

        # Primary: .cortex/skills/ (Release 2 location)
        cortex_skills = self.root / ".cortex" / "skills"
        installed = _inst(cortex_skills)
        for skill in installed:
            if "already exists" in skill:
                self.skipped.append(f".cortex/skills/{skill}")
            else:
                self.created.append(f".cortex/skills/{skill}")

        # Legacy: .qwen/skills/ (backward-compatible location for Qwen-based IDEs)
        qwen_skills = self.root / ".qwen" / "skills"
        legacy_installed = _inst(qwen_skills)
        for skill in legacy_installed:
            if "already exists" in skill:
                self.skipped.append(f".qwen/skills/{skill} (already exists)")
            else:
                self.created.append(f".qwen/skills/{skill}")

    def _check_vault_pipeline_interactive(self) -> None:
        vp = self.root / "vault"
        if vp.exists():
            msg = (
                f"\n[?] Se detecto un vault en '{vp}'.\n"
                "    ¿Es el de Cortex? [yes] para usarlo, [no] para crear uno nuevo."
            )
            if typer.confirm(msg, default=True):
                self.skipped.append("vault/ (existing)")
                return
        self._create_directories()

    def _install_ide(self) -> None:
        if not self.ide:
            return
        try:
            from cortex.ide import inject
            inject(self.ide, project_root=self.root)
            self.created.append(f"IDE Profiles Injected ({self.ide})")
        except Exception as e:
            self.warnings.append(f"IDE profile injection fail: {e}")

    def _install_webgraph(self) -> None:
        try:
            from cortex.webgraph.setup import (
                attach_project_root,
                get_missing_webgraph_dependencies,
                install_webgraph,
            )

            if install_webgraph(self.root, interactive=False):
                self.created.append(".cortex/webgraph/ (configured)")
                if self.attach_project_root:
                    workspace_file = attach_project_root(self.root, Path(self.attach_project_root))
                    self.created.append(str(workspace_file.relative_to(self.root)))
            else:
                missing = get_missing_webgraph_dependencies()
                if missing:
                    self.warnings.append(
                        "Webgraph dependencies could not be installed automatically: "
                        + ", ".join(missing)
                        + ". Retry with: pip install -e '.[webgraph]' or pip install 'cortex-memory[webgraph]'"
                    )
                else:
                    self.warnings.append("Webgraph setup did not complete.")
        except Exception as e:
            self.warnings.append(f"Webgraph setup fail: {e}")

    def _init_memory(self) -> None:
        try:
            from cortex.core import AgentMemory
            config_path = self.root / "config.yaml"
            if config_path.exists():
                mem = AgentMemory(config_path=str(config_path))
                from cortex.setup.cold_start import run_cold_start
                # Pasamos el git_depth aquí
                cs_res = run_cold_start(self.root, mem.episodic, self.root / "vault", git_depth=self.git_depth)
                
                # Capturamos warnings de Git/README para el resumen final
                if cs_res.get("warnings"):
                    self.warnings.extend(cs_res["warnings"])
                    
                mem.sync_vault()
                mem.remember("Cortex setup complete", memory_type="setup")
        except Exception as e:
            self.warnings.append(f"Mem fail: {e}")

    def _summary(self) -> dict:
        return {
            "project_name": self.ctx.stack.project_name if self.ctx else "unknown",
            "language": self.ctx.stack.language if self.ctx else "unknown",
            "package_manager": self.ctx.stack.package_manager if self.ctx else "unknown",
            "created": self.created,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "dry_run": getattr(self, "dry_run", False),
        }

def format_summary(summary: dict) -> str:
    lines = ["", "═"*55, "🧠 Cortex Setup Complete", "═"*55, ""]
    lines.append(f"  Project: {summary['project_name']}")
    lines.append(f"  Language: {summary['language']} ({summary['package_manager']})")
    lines.append("")
    if summary["created"]:
        lines.append(f"  ✅ Created ({len(summary['created'])} items):")
        for f in summary["created"]:
            lines.append(f"    • {f}")
    if summary["skipped"]:
        lines.append(f"  ⏭ Skipped ({len(summary['skipped'])}):")
        for f in summary["skipped"]:
            lines.append(f"    • {f}")
    if summary["warnings"]:
        lines.append("  ⚠ Warnings:")
        for w in summary["warnings"]:
            lines.append(f"    • {w}")
    lines.append("═"*55)
    lines.append("")
    lines.append("🚀 Next steps:")
    lines.append("  1. Open this project in VS Code, Cursor, or your preferred IDE.")
    lines.append("  2. Install the Cortex MCP extension and connect it.")
    lines.append("  3. Run `cortex setup pipeline` to configure CI/CD workflows.")
    lines.append("  4. Use cortex-sync inside the IDE to start a session.")
    lines.append("")
    return "\n".join(lines)
