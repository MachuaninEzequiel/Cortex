from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from cortex.doc_validator import DocValidator
from cortex.enterprise.config import describe_enterprise_topology, load_enterprise_config
from cortex.git_policy import RECOMMENDED_GITIGNORE_PATTERNS, gitignore_contains
from cortex.runtime_context import (
    detect_git_branch,
    detect_git_repo_path,
    resolve_episodic_persist_dir,
)
from cortex.webgraph.setup import get_missing_webgraph_dependencies

DoctorSeverity = Literal["fail", "warn", "info"]
DoctorScope = Literal["project", "enterprise", "all"]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    severity: DoctorSeverity
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    project_root: Path
    checks: list[DoctorCheck]

    @property
    def has_failures(self) -> bool:
        return any((not check.ok) and check.severity == "fail" for check in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any((not check.ok) and check.severity == "warn" for check in self.checks)


def run_doctor(project_root: Path, *, scope: DoctorScope = "project") -> DoctorReport:
    root = project_root.resolve()
    checks: list[DoctorCheck] = [
        DoctorCheck("project_root", root.exists(), "fail", str(root)),
    ]
    if not root.exists():
        return DoctorReport(project_root=root, checks=checks)

    config_path = root / "config.yaml"
    checks.append(DoctorCheck("config_yaml", config_path.exists(), "fail", str(config_path)))

    raw_config: dict = {}
    if config_path.exists():
        try:
            raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            from cortex.core import CortexConfig

            CortexConfig.model_validate(raw_config)
            checks.append(DoctorCheck("config_validation", True, "info", "config.yaml is valid"))
        except Exception as exc:
            checks.append(DoctorCheck("config_validation", False, "fail", str(exc)))

    vault_path = root / "vault"
    checks.append(DoctorCheck("vault_dir", vault_path.exists(), "fail", str(vault_path)))

    episodic_cfg = raw_config.get("episodic", {}) if isinstance(raw_config, dict) else {}
    runtime_persist_dir = resolve_episodic_persist_dir(root, episodic_cfg) if config_path.exists() else root / ".memory" / "chroma"
    checks.append(
        DoctorCheck(
            "episodic_store",
            runtime_persist_dir.exists(),
            "fail",
            str(runtime_persist_dir),
        )
    )

    cortex_workspace = root / ".cortex"
    checks.append(
        DoctorCheck(
            "cortex_workspace",
            cortex_workspace.exists(),
            "warn",
            str(cortex_workspace),
        )
    )
    checks.append(
        DoctorCheck(
            "agent_guidelines",
            (cortex_workspace / "AGENT.md").exists(),
            "warn",
            str(cortex_workspace / "AGENT.md"),
        )
    )

    repo_root = detect_git_repo_path(root)
    git_available = repo_root != root or (root / ".git").exists()
    checks.append(
        DoctorCheck(
            "git_repository",
            git_available,
            "warn",
            str(repo_root),
        )
    )
    checks.append(
        DoctorCheck(
            "git_branch",
            detect_git_branch(root) != "no-git-branch",
            "warn",
            detect_git_branch(root),
        )
    )

    for pattern in RECOMMENDED_GITIGNORE_PATTERNS:
        severity: DoctorSeverity = "fail" if pattern.startswith(".memory") or pattern.endswith(".chroma/") else "warn"
        checks.append(
            DoctorCheck(
                f"gitignore:{pattern}",
                gitignore_contains(root, pattern),
                severity,
                pattern,
            )
        )

    missing_webgraph = get_missing_webgraph_dependencies()
    checks.append(
        DoctorCheck(
            "webgraph_dependencies",
            len(missing_webgraph) == 0,
            "warn",
            "ok" if not missing_webgraph else "missing: " + ", ".join(missing_webgraph),
        )
    )

    if vault_path.exists():
        checks.extend(_validate_vault(vault_path))

    if scope in {"enterprise", "all"}:
        checks.extend(_validate_enterprise(root, raw_config, required=(scope == "enterprise")))

    return DoctorReport(project_root=root, checks=checks)


def _validate_vault(vault_path: Path) -> list[DoctorCheck]:
    md_files = sorted(vault_path.rglob("*.md"))
    if not md_files:
        return [DoctorCheck("vault_markdown", False, "warn", "No markdown files found under vault/")]

    validator = DocValidator(vault_path=vault_path)
    results = validator.validate_batch(md_files)
    error_count = sum(len(result.errors) for result in results)
    warning_count = sum(len(result.warnings) for result in results)
    checks = [
        DoctorCheck(
            "vault_validation_errors",
            error_count == 0,
            "fail",
            f"{error_count} error(s) across {len(md_files)} markdown file(s)",
        ),
        DoctorCheck(
            "vault_validation_warnings",
            warning_count == 0,
            "warn",
            f"{warning_count} warning(s) across {len(md_files)} markdown file(s)",
        ),
    ]
    return checks


def _validate_enterprise(
    project_root: Path,
    raw_config: dict,
    *,
    required: bool,
) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    org_path = project_root / ".cortex" / "org.yaml"
    checks.append(
        DoctorCheck(
            "enterprise_config",
            org_path.exists(),
            "fail" if required else "warn",
            str(org_path),
        )
    )
    if not org_path.exists():
        return checks

    try:
        config = load_enterprise_config(project_root, required=True, path=org_path)
    except Exception as exc:
        checks.append(DoctorCheck("enterprise_config_validation", False, "fail", str(exc)))
        return checks

    checks.append(
        DoctorCheck(
            "enterprise_config_validation",
            True,
            "info",
            "Enterprise org config is valid",
        )
    )
    checks.append(
        DoctorCheck(
            "enterprise_topology",
            True,
            "info",
            describe_enterprise_topology(config, project_root),
        )
    )

    enterprise_vault = config.resolve_enterprise_vault_path(project_root)
    if enterprise_vault is not None:
        checks.append(
            DoctorCheck(
                "enterprise_vault_dir",
                enterprise_vault.exists(),
                "fail" if required else "warn",
                str(enterprise_vault),
            )
        )

    enterprise_memory = config.resolve_enterprise_memory_path(project_root)
    if enterprise_memory is not None:
        checks.append(
            DoctorCheck(
                "enterprise_memory_dir",
                enterprise_memory.exists(),
                "warn",
                str(enterprise_memory),
            )
        )

    episodic_cfg = raw_config.get("episodic", {}) if isinstance(raw_config, dict) else {}
    namespace_mode = str(episodic_cfg.get("namespace_mode", "project")).strip().lower()
    branch_expected = namespace_mode == "branch"
    branch_matches = branch_expected == config.memory.branch_isolation_enabled
    checks.append(
        DoctorCheck(
            "enterprise_branch_isolation_alignment",
            branch_matches,
            "warn",
            (
                f"config.yaml namespace_mode={namespace_mode}, "
                f"org.yaml branch_isolation_enabled={config.memory.branch_isolation_enabled}"
            ),
        )
    )

    expected_scope = "all" if config.memory.enterprise_semantic_enabled else "local"
    scope_matches = (
        config.memory.retrieval_default_scope == expected_scope
        or config.memory.retrieval_default_scope == "local"
    )
    checks.append(
        DoctorCheck(
            "enterprise_retrieval_scope",
            scope_matches,
            "warn",
            (
                f"default_scope={config.memory.retrieval_default_scope}, "
                f"enterprise_semantic_enabled={config.memory.enterprise_semantic_enabled}"
            ),
        )
    )

    return checks
