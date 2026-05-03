"""
cortex.setup.orchestrator
-------------------------
Orchestration engine for modular setup (agent, pipeline, full).

EPIC 4: All file creation now writes exclusively through
``WorkspaceLayout`` so that a brand-new project generates the
new-layout structure (``.cortex/`` as workspace root) while
legacy projects keep working through compatibility dual paths.
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
    render_workspace_yaml,
    render_decisions_md,
    render_enterprise_vault_readme,
    render_enterprise_runbook_md,
    render_git_vault_policy_md,
    render_runbooks_md,
)
from cortex.workspace.layout import WorkspaceLayout


class SetupMode(str, Enum):
    AGENT = "agent"
    PIPELINE = "pipeline"
    FULL = "full"
    WEBGRAPH = "webgraph"
    ENTERPRISE = "enterprise"

class SetupOrchestrator:
    """Runs the setup pipeline based on mode and reports results.

    All file creation goes through ``self.layout`` (a
    ``WorkspaceLayout``) so that paths resolve correctly in both
    new-layout and legacy-layout projects.
    """

    def __init__(self, root: Path | None = None):
        self.root = root or Path.cwd()
        self.detector = ProjectDetector(self.root)
        self.ctx: ProjectContext | None = None
        self.created: list[str] = []
        self.skipped: list[str] = []
        self.warnings: list[str] = []
        # Layout will be resolved after detect() in run()
        self.layout: WorkspaceLayout | None = None

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
        # Resolve workspace layout — for a brand-new project this
        # will be new-layout (``repo_root / .cortex``).
        self.layout = WorkspaceLayout.discover(self.root)
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
        """Create the workspace directory structure.

        In new layout all directories go inside ``.cortex/``.
        In legacy layout they go to the repo root (backward compat).
        """
        layout = self.layout
        dirs = [
            layout.episodic_memory_path,
            layout.vault_path / "sessions",
            layout.vault_path / "decisions",
            layout.vault_path / "runbooks",
            layout.vault_path / "incidents",
            layout.vault_path / "hu",
            layout.vault_path / "specs",
        ]
        for d in dirs:
            if d.exists():
                # Show path relative to repo_root for consistency
                rel = d.relative_to(self.root) if d.is_relative_to(self.root) else d
                self.skipped.append(f"{rel}/ (already exists)")
            else:
                d.mkdir(parents=True, exist_ok=True)
                rel = d.relative_to(self.root) if d.is_relative_to(self.root) else d
                self.created.append(f"{rel}/")

    def _create_config(self) -> None:
        if not self.ctx:
            return
        layout = self.layout
        path = layout.config_path
        if path.exists():
            self.skipped.append(f"{path.relative_to(self.root)} (already exists)")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_config_yaml(self.ctx, layout=layout), encoding="utf-8")
        self.created.append(str(path.relative_to(self.root)))

    def _create_vault_docs(self) -> None:
        if not self.ctx:
            return
        layout = self.layout
        vault = layout.vault_path
        vault.mkdir(parents=True, exist_ok=True)
        for filename, renderer in [
            ("architecture.md", render_architecture_md),
            ("decisions.md", render_decisions_md),
            ("runbooks.md", render_runbooks_md),
            ("runbooks/enterprise-runbook.md", render_enterprise_runbook_md),
            ("runbooks/git-vault-policy.md", render_git_vault_policy_md),
        ]:
            path = vault / filename
            if path.exists():
                self.skipped.append(f"{path.relative_to(self.root)} (already exists)")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(renderer(self.ctx), encoding="utf-8")
                self.created.append(str(path.relative_to(self.root)))

    def _create_enterprise_org_config(
        self,
        profile: str = "small-company",
        overrides: dict[str, Any] | None = None,
    ) -> None:
        if not self.ctx:
            return
        layout = self.layout
        path = layout.org_config_path
        if path.exists():
            self.skipped.append(f"{path.relative_to(self.root)} (already exists)")
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
        self.created.append(str(path.relative_to(self.root)))

    def _create_enterprise_workspace(self) -> None:
        layout = self.layout
        path = layout.workspace_yaml_path
        if path.exists():
            self.skipped.append(f"{path.relative_to(self.root)} (already exists)")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_workspace_yaml(), encoding="utf-8")
        self.created.append(str(path.relative_to(self.root)))

    def _simulate_enterprise_flow(self) -> None:
        layout = self.layout
        # Build simulated paths relative to repo_root
        def _rel(p: Path) -> str:
            try:
                return str(p.relative_to(self.root))
            except ValueError:
                return str(p)

        simulated = [
            _rel(layout.episodic_memory_path) + "/",
            _rel(layout.vault_path) + "/",
            _rel(layout.vault_path / "sessions") + "/",
            _rel(layout.vault_path / "decisions") + "/",
            _rel(layout.vault_path / "runbooks") + "/",
            _rel(layout.vault_path / "incidents") + "/",
            _rel(layout.vault_path / "hu") + "/",
            _rel(layout.vault_path / "specs") + "/",
            _rel(layout.config_path),
            _rel(layout.org_config_path),
            _rel(layout.vault_path / "architecture.md"),
            _rel(layout.vault_path / "decisions.md"),
            _rel(layout.vault_path / "runbooks.md"),
            _rel(layout.vault_path / "runbooks" / "enterprise-runbook.md"),
            _rel(layout.vault_path / "runbooks" / "git-vault-policy.md"),
            _rel(layout.enterprise_vault_path / "runbooks") + "/",
            _rel(layout.enterprise_vault_path / "decisions") + "/",
            _rel(layout.enterprise_vault_path / "incidents") + "/",
            _rel(layout.enterprise_vault_path / "hu") + "/",
            _rel(layout.enterprise_vault_path / "README.md"),
            ".github/workflows/ci-pull-request.yml",
            ".github/workflows/ci-feature.yml",
            ".github/workflows/cd-deploy.yml",
            ".github/workflows/ci-enterprise-governance.yml",
            _rel(layout.scripts_dir / "devsecdocops.sh"),
            _rel(layout.workspace_yaml_path),
        ]
        for item in simulated:
            self.created.append(f"{item} (dry-run)")

    def _create_enterprise_vault(self) -> None:
        if not self.ctx:
            return
        layout = self.layout
        enterprise_root = layout.enterprise_vault_path
        created_any = False
        for dirname in ("runbooks", "decisions", "incidents", "hu"):
            target = enterprise_root / dirname
            if target.exists():
                self.skipped.append(f"{target.relative_to(self.root)}/ (already exists)")
            else:
                target.mkdir(parents=True, exist_ok=True)
                self.created.append(f"{target.relative_to(self.root)}/")
                created_any = True

        readme_path = enterprise_root / "README.md"
        if readme_path.exists():
            self.skipped.append(f"{readme_path.relative_to(self.root)} (already exists)")
        else:
            enterprise_root.mkdir(parents=True, exist_ok=True)
            readme_path.write_text(render_enterprise_vault_readme(self.ctx), encoding="utf-8")
            self.created.append(str(readme_path.relative_to(self.root)))
            created_any = True

        if not created_any and not enterprise_root.exists():
            enterprise_root.mkdir(parents=True, exist_ok=True)

    def _create_workflows(self) -> None:
        """Create GitHub Actions workflows.

        Workflows are ALWAYS written to ``.github/workflows/`` at the
        repo root (GitHub requirement), regardless of layout mode.
        """
        if not self.ctx:
            return
        layout = self.layout
        wdir = layout.workflows_dir
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
        layout = self.layout
        sdir = layout.scripts_dir
        sdir.mkdir(parents=True, exist_ok=True)
        path = sdir / "devsecdocops.sh"
        if path.exists():
            self.skipped.append(f"{path.relative_to(self.root)} (already exists)")
        else:
            path.write_text(DEVSECDOCSOPS_SCRIPT, encoding="utf-8")
            path.chmod(0o755)
            self.created.append(str(path.relative_to(self.root)))

    def _create_agent_guidelines(self) -> None:
        # ensure_cortex_workspace still writes to .cortex/ which is correct
        # for both layouts (in new layout .cortex/ IS the workspace_root)
        result = ensure_cortex_workspace(self.root)
        self.created.extend(result["created"])
        self.skipped.extend(f"{path} (already exists)" for path in result["skipped"])

    def _install_skills(self) -> None:
        """Copy bundled Obsidian skills into project's .cortex/skills/."""
        from cortex.skills import install_skills as _inst

        # Skills are always inside .cortex/skills/ which in new layout
        # is workspace_root/skills/ and in legacy is repo_root/.cortex/skills/
        layout = self.layout
        cortex_skills = layout.skills_dir
        installed = _inst(cortex_skills)
        for skill in installed:
            if "already exists" in skill:
                self.skipped.append(f"{cortex_skills.relative_to(self.root)}/{skill}")
            else:
                self.created.append(f"{cortex_skills.relative_to(self.root)}/{skill}")

    def _check_vault_pipeline_interactive(self) -> None:
        layout = self.layout
        vp = layout.vault_path
        if vp.exists():
            msg = (
                f"\n[?] Se detecto un vault en '{vp}'.\n"
                "    ¿Es el de Cortex? [yes] para usarlo, [no] para crear uno nuevo."
            )
            if typer.confirm(msg, default=True):
                self.skipped.append(f"{vp.relative_to(self.root)}/ (existing)")
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
            config_path = self.layout.config_path
            if config_path.exists():
                mem = AgentMemory(config_path=str(config_path))
                from cortex.setup.cold_start import run_cold_start
                layout = self.layout
                cs_res = run_cold_start(
                    self.root,
                    mem.episodic,
                    vault_path=str(layout.vault_path),
                    git_depth=self.git_depth,
                    workspace_layout=layout,
                )

                # Capturamos warnings de Git/README para el resumen final
                if cs_res.get("warnings"):
                    self.warnings.extend(cs_res["warnings"])

                mem.sync_vault()
                mem.remember("Cortex setup complete", memory_type="setup")
        except Exception as e:
            self.warnings.append(f"Mem fail: {e}")

    def _summary(self) -> dict:
        layout = self.layout
        return {
            "project_name": self.ctx.stack.project_name if self.ctx else "unknown",
            "language": self.ctx.stack.language if self.ctx else "unknown",
            "package_manager": self.ctx.stack.package_manager if self.ctx else "unknown",
            "layout_mode": "new" if (layout and layout.is_new_layout) else "legacy",
            "workspace_root": str(layout.workspace_root) if layout else "unknown",
            "created": self.created,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "dry_run": getattr(self, "dry_run", False),
        }

def format_summary(summary: dict) -> str:
    lines = ["", "═"*55, "🧠 Cortex Setup Complete", "═"*55, ""]
    lines.append(f"  Project: {summary['project_name']}")
    lines.append(f"  Language: {summary['language']} ({summary['package_manager']})")
    layout_mode = summary.get("layout_mode", "unknown")
    layout_icon = "🆕" if layout_mode == "new" else "📦"
    lines.append(f"  Layout: {layout_icon} {layout_mode}")
    ws_root = summary.get("workspace_root", "")
    if ws_root:
        lines.append(f"  Workspace: {ws_root}")
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
    lines.append("  3. Run `cortex doctor` to verify the setup.")
    lines.append("  4. Use cortex-sync inside the IDE to start a session.")
    lines.append("")
    return "\n".join(lines)
