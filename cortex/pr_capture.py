"""
cortex.pr_capture
-----------------
Captures pull request metadata and git diff information into a PRContext.

Designed to run inside GitHub Actions, but also supports local usage
by passing values manually.

Usage
-----
# In GitHub Actions (environment variables available):
    ctx = capture_from_github()

# Locally (manual values):
    ctx = capture_manual(
        title="Fix login bug",
        author="dev",
        branch="fix/login",
        commit="abc123",
    )

# From JSON (previously saved):
    ctx = capture_from_json("context.json")
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from cortex.models import PRContext


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return stdout, stripping whitespace."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.stdout.strip()


def _get_files_changed(base: str = "main", head: str = "HEAD") -> list[str]:
    """Get list of files changed between base and head."""
    try:
        output = _run_git(["diff", "--name-only", f"{base}...{head}"])
        if not output:
            # Fallback: try against origin/base
            output = _run_git(["diff", "--name-only", f"origin/{base}...{head}"])
        return [f for f in output.split("\n") if f]
    except Exception:
        return []


def _get_diff_summary(base: str = "main", head: str = "HEAD") -> str:
    """Get a compact diff summary (stat format)."""
    try:
        output = _run_git(["diff", "--stat", f"{base}...{head}"])
        if not output:
            output = _run_git(["diff", "--stat", f"origin/{base}...{head}"])
        return output
    except Exception:
        return ""


def _detect_db_migrations(files_changed: list[str]) -> list[str]:
    """Detect database migration files in the changed files."""
    migration_indicators = [
        "migration", "schema", "alembic", "flyway", "liquibase",
        ".sql", "prisma", "sequelize", "typeorm", "knex",
    ]
    return [
        f for f in files_changed
        if any(ind in f.lower() for ind in migration_indicators)
    ]


def _detect_api_changes(files_changed: list[str]) -> list[str]:
    """Detect API route/controller files in the changed files."""
    api_indicators = [
        "route", "controller", "endpoint", "api/", "handler",
        "view", "resource", "rest",
    ]
    return [
        f for f in files_changed
        if any(ind in f.lower() for ind in api_indicators)
    ]


def capture_from_github() -> PRContext:
    """
    Capture PR context from GitHub Actions environment variables.

    Uses the standard GITHUB_* env vars available in workflows.
    """
    pr_number = int(os.environ.get("PR_NUMBER", "0"))
    title = os.environ.get("PR_TITLE", "Untitled PR")
    body = os.environ.get("PR_BODY", "")
    author = os.environ.get("PR_AUTHOR", "unknown")
    source_branch = os.environ.get("PR_BRANCH", os.environ.get("GITHUB_HEAD_REF", ""))
    target_branch = os.environ.get("TARGET_BRANCH", os.environ.get("GITHUB_BASE_REF", "main"))
    commit_sha = os.environ.get("PR_COMMIT", os.environ.get("GITHUB_SHA", ""))

    # Labels from event payload (if available)
    labels_raw = os.environ.get("PR_LABELS", "")
    labels = [lbl.strip() for lbl in labels_raw.split(",") if lbl.strip()] if labels_raw else []

    files_changed = _get_files_changed(target_branch, commit_sha)

    return PRContext(
        pr_number=pr_number,
        title=title,
        body=body,
        author=author,
        source_branch=source_branch,
        target_branch=target_branch,
        commit_sha=commit_sha,
        files_changed=files_changed,
        diff_summary=_get_diff_summary(target_branch, commit_sha),
        db_migrations=_detect_db_migrations(files_changed),
        api_changes=_detect_api_changes(files_changed),
        labels=labels,
    )


def capture_manual(
    *,
    title: str,
    author: str,
    branch: str,
    commit: str,
    body: str = "",
    pr_number: int = 0,
    target_branch: str = "main",
    labels: list[str] | None = None,
) -> PRContext:
    """
    Capture PR context manually (for local testing or non-GH environments).
    """
    files_changed = _get_files_changed(target_branch, commit)

    return PRContext(
        pr_number=pr_number,
        title=title,
        body=body,
        author=author,
        source_branch=branch,
        target_branch=target_branch,
        commit_sha=commit,
        files_changed=files_changed,
        diff_summary=_get_diff_summary(target_branch, commit),
        db_migrations=_detect_db_migrations(files_changed),
        api_changes=_detect_api_changes(files_changed),
        labels=labels or [],
    )


def capture_from_json(path: str | Path) -> PRContext:
    """
    Load a PRContext from a previously saved JSON file.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PRContext.model_validate(data)


def save_context(ctx: PRContext, path: str | Path = ".pr-context.json") -> Path:
    """
    Save a PRContext to a JSON file.
    """
    p = Path(path)
    p.write_text(ctx.model_dump_json(indent=2), encoding="utf-8")
    return p


def enrich_with_pipeline(
    ctx: PRContext,
    *,
    lint_result: str | None = None,
    audit_result: str | None = None,
    test_result: str | None = None,
) -> PRContext:
    """
    Enrich an existing PRContext with pipeline results.
    Returns a new PRContext (immutable pattern).
    """
    data = ctx.model_dump()
    if lint_result is not None:
        data["lint_result"] = lint_result
    if audit_result is not None:
        data["audit_result"] = audit_result
    if test_result is not None:
        data["test_result"] = test_result
    return PRContext.model_validate(data)
