from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from cortex.doc_validator import DocValidator
from cortex.enterprise.config import describe_enterprise_topology, load_enterprise_config
from cortex.enterprise.models import EnterpriseOrgConfig
from cortex.git_policy import (
    LEGACY_GITIGNORE_PATTERNS,
    NEW_LAYOUT_GITIGNORE_PATTERNS,
    gitignore_contains,
)
from cortex.runtime_context import (
    detect_git_branch,
    detect_git_repo_path,
    resolve_episodic_persist_dir,
)
from cortex.webgraph.setup import get_missing_webgraph_dependencies
from cortex.workspace.layout import WorkspaceLayout

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
    layout = WorkspaceLayout.discover(root)
    is_new = layout.is_new_layout

    checks: list[DoctorCheck] = [
        DoctorCheck("project_root", root.exists(), "fail", str(root)),
        DoctorCheck(
            "layout_mode",
            True,
            "info",
            f"{'new' if is_new else 'legacy'} (workspace_root={layout.workspace_root})",
        ),
    ]
    if not root.exists():
        return DoctorReport(project_root=root, checks=checks)

    # ── Config ───────────────────────────────────────────────────────
    config_path = layout.config_path
    checks.append(DoctorCheck("config_yaml", config_path.exists(), "fail", str(config_path)))

    raw_config: dict = {}
    if config_path.exists():
        try:
            raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            from cortex.core import CortexConfig

            CortexConfig.model_validate(raw_config)
            checks.append(
                DoctorCheck("config_validation", True, "info", f"{config_path.name} is valid")
            )
        except Exception as exc:
            checks.append(DoctorCheck("config_validation", False, "fail", str(exc)))

    # ── Vault ─────────────────────────────────────────────────────────
    vault_path = layout.vault_path
    checks.append(DoctorCheck("vault_dir", vault_path.exists(), "fail", str(vault_path)))

    # ── Episodic memory ──────────────────────────────────────────────
    episodic_cfg = raw_config.get("episodic", {}) if isinstance(raw_config, dict) else {}
    runtime_persist_dir = (
        resolve_episodic_persist_dir(layout.workspace_root, episodic_cfg)
        if config_path.exists()
        else layout.episodic_memory_path / "chroma"
    )
    import os

    is_ci = os.getenv("GITHUB_ACTIONS") == "true"
    checks.append(
        DoctorCheck(
            "episodic_store",
            runtime_persist_dir.exists(),
            "warn" if is_ci else "fail",
            str(runtime_persist_dir),
        )
    )

    # ── Cortex workspace ─────────────────────────────────────────────
    checks.append(
        DoctorCheck(
            "cortex_workspace",
            layout.workspace_root.exists(),
            "warn",
            str(layout.workspace_root),
        )
    )
    checks.append(
        DoctorCheck(
            "agent_guidelines",
            layout.agent_guidelines_path.exists(),
            "warn",
            str(layout.agent_guidelines_path),
        )
    )

    # ── Workspace version ───────────────────────────────────────────
    ws_yaml = layout.workspace_yaml_path
    if ws_yaml.exists():
        try:
            ws_data = yaml.safe_load(ws_yaml.read_text(encoding="utf-8")) or {}
            layout_ver = ws_data.get("layout_version", 1)
            checks.append(
                DoctorCheck(
                    "workspace_layout_version",
                    True,
                    "info",
                    f"layout_version={layout_ver}",
                )
            )
        except Exception:
            checks.append(DoctorCheck("workspace_layout_version", False, "warn", str(ws_yaml)))
    else:
        checks.append(
            DoctorCheck(
                "workspace_yaml",
                False,
                "warn" if is_new else "info",
                f"Missing: {ws_yaml}",
            )
        )

    # ── Git ──────────────────────────────────────────────────────────
    repo_root = detect_git_repo_path(root)
    git_available = repo_root != root or (root / ".git").exists()
    checks.append(DoctorCheck("git_repository", git_available, "warn", str(repo_root)))
    checks.append(
        DoctorCheck(
            "git_branch",
            detect_git_branch(root) != "no-git-branch",
            "warn",
            detect_git_branch(root),
        )
    )

    # ── Gitignore (layout-aware) ─────────────────────────────────────
    # In new layout, the legacy ``.memory/`` and ``*.chroma/`` patterns
    # are irrelevant — the memory store lives under ``.cortex/memory/``.
    # Checking for them produced false FAILs in fresh new-layout setups
    # and was the #1 noise source in ``cortex doctor`` reports.
    if layout is not None and layout.is_new_layout:
        gitignore_patterns = NEW_LAYOUT_GITIGNORE_PATTERNS
    else:
        gitignore_patterns = LEGACY_GITIGNORE_PATTERNS
    for pattern in gitignore_patterns:
        # Memory paths are still required to be ignored (they contain
        # binary ChromaDB data). Session paths are recommended but
        # not strictly required for project correctness.
        severity: DoctorSeverity = (
            "fail" if "memory" in pattern or pattern.endswith(".chroma/") else "warn"
        )
        checks.append(
            DoctorCheck(
                f"gitignore:{pattern}",
                gitignore_contains(root, pattern),
                severity,
                pattern,
            )
        )

    # ── WebGraph ────────────────────────────────────────────────────
    missing_webgraph = get_missing_webgraph_dependencies()
    checks.append(
        DoctorCheck(
            "webgraph_dependencies",
            len(missing_webgraph) == 0,
            "warn",
            "ok" if not missing_webgraph else "missing: " + ", ".join(missing_webgraph),
        )
    )

    # ── Vault validation ────────────────────────────────────────────
    if vault_path.exists():
        checks.extend(_validate_vault(vault_path))

    # ── Sessions (Pluggable Middle, Phase 00 / T0.9) ─────────────────
    checks.extend(_validate_sessions(layout))

    # ── Autopilot policy + IDE hooks (Pluggable Middle, Phase 03) ────
    checks.extend(_validate_autopilot_policy(layout))
    checks.extend(_validate_session_hooks(layout))

    # ── Pluggable Middle health (Phase 04 / T4.4) ────────────────────
    checks.extend(_validate_pluggable_middle_health(layout))

    # ── Enterprise ──────────────────────────────────────────────────
    if scope in {"enterprise", "all"}:
        checks.extend(
            _validate_enterprise(root, raw_config, layout=layout, required=(scope == "enterprise"))
        )

    return DoctorReport(project_root=root, checks=checks)


def _validate_sessions(layout: WorkspaceLayout) -> list[DoctorCheck]:
    """Validate the integrity of ``.cortex/sessions/``.

    Checks:
        1. The sessions directory exists and is writable.
        2. The active pointer (if present) references an existing session.
        3. Every session file on disk parses correctly.
        4. Open sessions are uniquely identifiable: if multiple are OPEN,
           only one of them is the active. The other(s) trigger a warning.
        5. Lifecycle invariants: terminal sessions carry end_commit and
           closed_at; OPEN sessions don't.

    Issues with malformed YAML are surfaced as warnings (we still want
    ``cortex doctor`` to complete in degraded repos).
    """
    from cortex.session import SessionRecord, SessionStatus
    from cortex.session.errors import SessionStorageCorrupted
    from cortex.session.storage import SessionStorage

    checks: list[DoctorCheck] = []
    sessions_dir = layout.sessions_dir
    storage = SessionStorage(sessions_dir)

    # (1) Directory + writability
    if not sessions_dir.exists():
        checks.append(
            DoctorCheck(
                "sessions_dir",
                False,
                "warn",
                f"Missing: {sessions_dir} — run `cortex setup agent`.",
            )
        )
        return checks

    writable = _is_writable(sessions_dir)
    checks.append(
        DoctorCheck(
            "sessions_dir",
            writable,
            "fail" if not writable else "info",
            str(sessions_dir),
        )
    )

    # (2) Active pointer
    active_id = storage.get_active_session_id()
    if active_id is None:
        checks.append(
            DoctorCheck(
                "sessions_active_pointer",
                True,
                "info",
                "(no active session)",
            )
        )
    else:
        active_exists = storage.exists(active_id)
        checks.append(
            DoctorCheck(
                "sessions_active_pointer",
                active_exists,
                "warn" if not active_exists else "info",
                f"{active_id}{'' if active_exists else ' (stale — file missing)'}",
            )
        )

    # (3) Parse-all + (4) (5) invariants
    raw_files = sorted(sessions_dir.glob("*.yaml"))
    parsed_ok: list[SessionRecord] = []
    parse_failures: list[str] = []
    invariant_violations: list[str] = []
    for path in raw_files:
        try:
            record = storage.load(path.stem)
        except SessionStorageCorrupted as exc:
            parse_failures.append(f"{path.name}: {exc}")
            continue
        parsed_ok.append(record)
        # Lifecycle invariants are normally caught by Pydantic at construction,
        # but a stale on-disk file could violate them if hand-edited. Re-check
        # defensively.
        if record.status is SessionStatus.OPEN:
            if record.closed_at is not None or record.end_commit is not None:
                invariant_violations.append(f"{record.session_id}: OPEN with close-time fields set")
        else:  # terminal status
            if record.closed_at is None or record.end_commit is None:
                invariant_violations.append(
                    f"{record.session_id}: {record.status.value} but missing close-time fields"
                )

    checks.append(
        DoctorCheck(
            "sessions_parsed",
            not parse_failures,
            "warn" if parse_failures else "info",
            (
                f"{len(parsed_ok)} parsed, {len(parse_failures)} failed"
                if parse_failures
                else f"{len(parsed_ok)} session(s) on disk parsed correctly"
            ),
        )
    )

    if parse_failures:
        checks.append(
            DoctorCheck(
                "sessions_corrupted_files",
                False,
                "warn",
                "; ".join(parse_failures),
            )
        )

    if invariant_violations:
        checks.append(
            DoctorCheck(
                "sessions_invariants",
                False,
                "warn",
                "; ".join(invariant_violations),
            )
        )

    # (4) Uniqueness of OPEN: warn if more than one OPEN that isn't the active.
    opens = [r for r in parsed_ok if r.status is SessionStatus.OPEN]
    if len(opens) > 1:
        non_active = [r.session_id for r in opens if r.session_id != active_id]
        if non_active:
            checks.append(
                DoctorCheck(
                    "sessions_multiple_open",
                    False,
                    "warn",
                    (
                        f"{len(opens)} OPEN sessions; non-active: "
                        f"{', '.join(non_active)}. Switch or close to keep one active."
                    ),
                )
            )

    return checks


def _validate_autopilot_policy(layout: WorkspaceLayout) -> list[DoctorCheck]:
    """Validate that an :class:`AutopilotPolicy` can be built from the current config.

    Reads ``autopilot.yaml`` (optional) via :func:`load_autopilot_config` and
    feeds it into :meth:`AutopilotPolicy.from_config`. Reports:

    * The current ``mode`` and ``budget_profile``.
    * Any validation error (unknown mode, unknown profile) — surfaced as
      a warning because :meth:`from_config` falls back to safe defaults.
    """
    from cortex.autopilot.config import load_autopilot_config
    from cortex.autopilot.policies import AutopilotPolicy

    checks: list[DoctorCheck] = []
    try:
        cfg = load_autopilot_config(layout)
    except Exception as exc:
        checks.append(DoctorCheck("autopilot_config", False, "warn", f"could not load: {exc}"))
        return checks

    try:
        policy = AutopilotPolicy.from_config(cfg)
    except Exception as exc:
        checks.append(
            DoctorCheck("autopilot_policy", False, "warn", f"could not build policy: {exc}")
        )
        return checks

    checks.append(
        DoctorCheck(
            "autopilot_policy",
            True,
            "info",
            f"mode={policy.mode.value}, budget_profile={policy.budget_profile}",
        )
    )

    # Surface a mismatch between the YAML mode string and the recognized
    # AutopilotMode set — from_config silently falls back to ASSIST on a
    # typo, so doctor is the right place to flag it.
    declared = (cfg.mode or "").strip().lower()
    if declared and declared != policy.mode.value:
        checks.append(
            DoctorCheck(
                "autopilot_mode_typo",
                False,
                "warn",
                f"autopilot.yaml mode={declared!r} is not recognized; using {policy.mode.value!r}.",
            )
        )
    return checks


def _validate_session_hooks(layout: WorkspaceLayout) -> list[DoctorCheck]:
    """Report which IDE hooks are installed under the project root.

    Also surfaces a sample of ``ide-hook`` checkpoints in active sessions so
    operators can confirm the hooks are actually firing.
    """
    from cortex.session.hooks import default_installer
    from cortex.session.models import CheckpointSource
    from cortex.session.storage import SessionStorage

    checks: list[DoctorCheck] = []
    installer = default_installer()
    target = layout.repo_root
    statuses = installer.status_all(target)
    installed = [s.ide for s in statuses if s.installed]

    detail = (
        f"installed: {installed}"
        if installed
        else "none installed — run `cortex session hooks install --ide <name>`"
    )
    checks.append(
        DoctorCheck(
            "session_hooks_installed",
            bool(installed),
            "info" if installed else "warn",
            detail,
        )
    )

    # Detect any ide-hook checkpoint in the active session, as a "is the
    # hook firing?" sanity check.
    try:
        storage = SessionStorage(layout.sessions_dir)
        active_id = storage.get_active_session_id()
    except Exception:  # pragma: no cover - sessions_dir checked elsewhere
        return checks
    if active_id is None or not storage.exists(active_id):
        return checks
    record = storage.load(active_id)
    ide_hook_count = sum(1 for cp in record.checkpoints if cp.source is CheckpointSource.IDE_HOOK)
    checks.append(
        DoctorCheck(
            "session_hooks_recent_events",
            True,
            "info",
            f"{ide_hook_count} ide-hook checkpoint(s) in active session {active_id}",
        )
    )
    return checks


def _validate_pluggable_middle_health(layout: WorkspaceLayout) -> list[DoctorCheck]:
    """Exhaustive end-to-end check of the Pluggable Middle subsystem (Phase 04).

    Bundles checks that confirm the entire spec → middle → documenter →
    persistence pipeline can be instantiated. Each check is small and
    fast — anything heavyweight stays out of ``cortex doctor``.

    Checks:
        * ``pm_workspace_layout_v2`` — layout v2 detected.
        * ``pm_documenter_module``   — ``cortex.documenter`` imports cleanly.
        * ``pm_documenter_interactive`` — ``InteractiveSession`` constructs.
        * ``pm_documenter_default_mode`` — ``documenter.default_mode`` is valid.
        * ``pm_verification_runner`` — ``VerificationRunner`` instantiates.
        * ``pm_mcp_tools_registered`` — the 6 canonical session MCP tools
          are registered.
    """
    checks: list[DoctorCheck] = []

    # 1. Workspace v2
    checks.append(
        DoctorCheck(
            "pm_workspace_layout_v2",
            layout.is_new_layout,
            "info" if layout.is_new_layout else "warn",
            "layout v2 active" if layout.is_new_layout else "running on legacy layout",
        )
    )

    # 2. Documenter module importable
    try:
        import cortex.documenter  # noqa: F401
        from cortex.documenter import (  # noqa: F401
            DocumenterPersister,
            FinishOverrides,
            Reconstructor,
        )

        checks.append(
            DoctorCheck(
                "pm_documenter_module",
                True,
                "info",
                "cortex.documenter imports cleanly",
            )
        )
    except Exception as exc:
        checks.append(
            DoctorCheck(
                "pm_documenter_module",
                False,
                "fail",
                f"cortex.documenter failed to import: {exc}",
            )
        )
        return checks  # downstream checks need the module

    # 3. Interactive mode constructible (Phase 04 / T4.1)
    try:
        from cortex.documenter.interactive import InteractiveSession

        InteractiveSession()
        checks.append(
            DoctorCheck(
                "pm_documenter_interactive",
                True,
                "info",
                "InteractiveSession constructs OK (`--interactive` mode available)",
            )
        )
    except Exception as exc:
        checks.append(
            DoctorCheck(
                "pm_documenter_interactive",
                False,
                "warn",
                f"InteractiveSession failed to construct: {exc}",
            )
        )

    # 4. documenter.default_mode in config is valid
    try:
        import yaml

        config_path = layout.config_path
        raw = (
            yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            if config_path.exists()
            else {}
        )
        documenter_cfg = raw.get("documenter", {}) if isinstance(raw, dict) else {}
        mode = str(documenter_cfg.get("default_mode", "auto"))
        if mode in {"auto", "interactive"}:
            checks.append(
                DoctorCheck(
                    "pm_documenter_default_mode",
                    True,
                    "info",
                    f"documenter.default_mode = {mode}",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "pm_documenter_default_mode",
                    False,
                    "warn",
                    f"documenter.default_mode {mode!r} is not 'auto' or 'interactive'; "
                    "the CLI will treat anything else as 'auto'.",
                )
            )
    except Exception as exc:
        checks.append(
            DoctorCheck(
                "pm_documenter_default_mode",
                False,
                "warn",
                f"could not read documenter.default_mode: {exc}",
            )
        )

    # 5. Verification runner constructible
    try:
        from cortex.session.verification import VerificationRunner

        VerificationRunner(repo_root=layout.repo_root)
        checks.append(
            DoctorCheck(
                "pm_verification_runner",
                True,
                "info",
                "VerificationRunner ready",
            )
        )
    except Exception as exc:
        checks.append(
            DoctorCheck(
                "pm_verification_runner",
                False,
                "warn",
                f"VerificationRunner failed to construct: {exc}",
            )
        )

    # 6. Canonical session MCP tools registered
    expected_tools = {
        "cortex_session_open",
        "cortex_session_checkpoint",
        "cortex_session_close",
        "cortex_session_status",
        "cortex_session_list",
        "cortex_finish_session",
    }
    try:
        # Lightweight check: grep the server module text. The MCP server is
        # heavy to instantiate (full AgentMemory); a text-level check
        # confirms registration without the runtime cost.
        from importlib.resources import files

        server_src = files("cortex.mcp").joinpath("server.py").read_text(encoding="utf-8")
        missing = sorted(t for t in expected_tools if t not in server_src)
        if not missing:
            checks.append(
                DoctorCheck(
                    "pm_mcp_tools_registered",
                    True,
                    "info",
                    f"All {len(expected_tools)} canonical session MCP tools registered",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "pm_mcp_tools_registered",
                    False,
                    "warn",
                    f"missing canonical MCP tools in server.py: {missing}",
                )
            )
    except Exception as exc:
        checks.append(
            DoctorCheck(
                "pm_mcp_tools_registered",
                False,
                "warn",
                f"could not read cortex/mcp/server.py: {exc}",
            )
        )

    # pm_git_available — Phase 09.A+: detect workspaces without a usable
    # git repository. Severity is informational, not failure: gitless
    # mode is a supported configuration (see the
    # ``cortex.session.models.GITLESS_COMMIT_PLACEHOLDER`` sentinel).
    # The check exists so users running ``cortex doctor`` know up front
    # that the documenter will produce reduced-fidelity session notes.
    try:
        from cortex.session import git as session_git

        if session_git.is_git_repo(layout.repo_root):
            checks.append(
                DoctorCheck(
                    "pm_git_available",
                    True,
                    "info",
                    "git repository detected — full documenter fidelity",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "pm_git_available",
                    False,
                    "info",
                    "no git repository at workspace root — sessions will open "
                    "in gitless mode (documenter relies on checkpoints only)",
                )
            )
    except Exception as exc:
        checks.append(
            DoctorCheck(
                "pm_git_available",
                False,
                "warn",
                f"could not probe git availability: {exc}",
            )
        )

    return checks


def _is_writable(path: Path) -> bool:
    """Return True if *path* is a directory we can create files in."""
    try:
        probe = path / ".doctor_write_probe"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _validate_vault(vault_path: Path) -> list[DoctorCheck]:
    md_files = sorted(vault_path.rglob("*.md"))
    if not md_files:
        return [
            DoctorCheck("vault_markdown", False, "warn", "No markdown files found under vault/")
        ]

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
    layout: WorkspaceLayout | None = None,
    required: bool = False,
) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []

    # Prefer layout-aware path
    if layout is None:
        layout = WorkspaceLayout.discover(project_root)

    org_path = layout.org_config_path
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
        config = load_enterprise_config(
            project_root, required=True, path=org_path, workspace_layout=layout
        )
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
            describe_enterprise_topology(config, project_root, workspace_layout=layout),
        )
    )

    enterprise_vault = config.resolve_enterprise_vault_path(
        project_root, workspace_root=layout.workspace_root
    )
    if enterprise_vault is not None:
        checks.append(
            DoctorCheck(
                "enterprise_vault_dir",
                enterprise_vault.exists(),
                "fail" if required else "warn",
                str(enterprise_vault),
            )
        )
        if enterprise_vault.exists():
            checks.extend(_validate_enterprise_vault(enterprise_vault))
            checks.extend(_validate_enterprise_promotion(config, enterprise_vault))

    enterprise_memory = config.resolve_enterprise_memory_path(
        project_root, workspace_root=layout.workspace_root
    )
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


def _validate_enterprise_vault(enterprise_vault: Path) -> list[DoctorCheck]:
    md_files = sorted(enterprise_vault.rglob("*.md"))
    if not md_files:
        return [
            DoctorCheck(
                "enterprise_vault_markdown",
                False,
                "warn",
                "No markdown files found under vault-enterprise/",
            )
        ]

    validator = DocValidator(vault_path=enterprise_vault)
    results = validator.validate_batch(md_files)
    error_count = sum(len(result.errors) for result in results)
    warning_count = sum(len(result.warnings) for result in results)
    return [
        DoctorCheck(
            "enterprise_vault_validation_errors",
            error_count == 0,
            "fail",
            f"{error_count} error(s) across {len(md_files)} markdown file(s)",
        ),
        DoctorCheck(
            "enterprise_vault_validation_warnings",
            warning_count == 0,
            "warn",
            f"{warning_count} warning(s) across {len(md_files)} markdown file(s)",
        ),
    ]


def _validate_enterprise_promotion(
    config: EnterpriseOrgConfig, enterprise_vault: Path
) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    if not getattr(config, "promotion", None) or not config.promotion.enabled:
        return checks

    allowed = list(getattr(config.promotion, "allowed_doc_types", []) or [])
    checks.append(
        DoctorCheck(
            "enterprise_promotion_allowed_doc_types",
            len(allowed) > 0,
            "fail",
            "promotion.allowed_doc_types must be non-empty when promotion is enabled",
        )
    )

    promo_dir = enterprise_vault / ".cortex" / "promotion"
    try:
        promo_dir.mkdir(parents=True, exist_ok=True)
        ok = True
        detail = str(promo_dir)
    except Exception as exc:
        ok = False
        detail = f"{promo_dir} ({exc})"
    checks.append(DoctorCheck("enterprise_promotion_dir", ok, "fail", detail))

    records = promo_dir / "records.jsonl"
    checks.append(
        DoctorCheck(
            "enterprise_promotion_records_presence",
            records.exists(),
            "warn",
            str(records),
        )
    )

    return checks
