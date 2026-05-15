"""cortex.cli.review_knowledge - Manage the promotion review queue.

This module exposes ``cortex review-knowledge`` as a typer subapp with
three subcommands (Item #9 from PLAN-DEUDA-RESIDUAL):

    - ``pending``    List enterprise notes currently in ``status: draft``.
    - ``approve``    Move a draft note to ``status: accepted`` (with audit_trail).
    - ``reject``     Move a draft note into ``rejected/`` (or delete with --delete).

For the legacy promotion candidate workflow (``KnowledgePromotionService``
that records JSONL events under ``.cortex/enterprise/promotion/``), a
fourth subcommand ``candidate`` preserves the original single-command
behavior.
"""

from __future__ import annotations

import getpass
import json
from pathlib import Path

import typer

from cortex.enterprise.promotion_doctype import (
    PromotionError,
    list_pending_drafts,
    mark_as_accepted,
    mark_as_rejected,
)
from cortex.workspace.layout import WorkspaceLayout

review_app = typer.Typer(
    help="Manage the enterprise promotion review queue.",
    no_args_is_help=True,
)


def _resolve_layout(project_root: str | None) -> WorkspaceLayout:
    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    return WorkspaceLayout.discover(root)


def _enterprise_vault(layout: WorkspaceLayout) -> Path:
    return layout.enterprise_vault_path


@review_app.command("pending")
def pending_command(
    doc_type: list[str] = typer.Option(
        None,
        "--doc-type",
        help="Filter by doc_type (repeat to allow multiple).",
    ),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Project root containing .cortex/ (defaults to cwd).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List enterprise notes awaiting promotion review (status: draft)."""
    layout = _resolve_layout(project_root)
    vault_root = _enterprise_vault(layout)
    pending = list_pending_drafts(vault_root, doc_types=list(doc_type) if doc_type else None)

    if json_output:
        typer.echo(json.dumps(pending, indent=2, default=str))
        return

    if not pending:
        typer.echo("No drafts pending review.")
        return

    typer.echo(f"Pending review ({len(pending)}):")
    for entry in pending:
        typer.echo(
            f"  - {entry['path']:<60} doc_type={entry.get('doc_type') or '-':<10} "
            f"owner={entry.get('owner') or '-'}"
        )


@review_app.command("approve")
def approve_command(
    path: str = typer.Argument(..., help="Vault-relative path to the draft note."),
    reviewer: str = typer.Option(
        None,
        "--reviewer",
        help="Reviewer name for the audit_trail (default: current OS user).",
    ),
    reason: str = typer.Option("", "--reason", help="Optional rationale."),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Project root containing .cortex/ (defaults to cwd).",
    ),
) -> None:
    """Promote a draft note to status: accepted and append an audit_trail entry."""
    layout = _resolve_layout(project_root)
    vault_root = _enterprise_vault(layout)
    full_path = (vault_root / path).resolve()
    if not full_path.is_relative_to(vault_root.resolve()):
        typer.echo(f"Path escapes enterprise vault: {path}", err=True)
        raise typer.Exit(1)

    reviewer_name = reviewer or getpass.getuser()
    try:
        mark_as_accepted(full_path, reviewer=reviewer_name, reason=reason)
    except PromotionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"[OK] {path} -> status: accepted (reviewer={reviewer_name})")


@review_app.command("reject")
def reject_command(
    path: str = typer.Argument(..., help="Vault-relative path to the draft note."),
    reviewer: str = typer.Option(
        None,
        "--reviewer",
        help="Reviewer name for the audit_trail (default: current OS user).",
    ),
    reason: str = typer.Option(..., "--reason", help="Required rationale for the rejection."),
    delete: bool = typer.Option(
        False,
        "--delete",
        help="Permanently delete instead of moving the note to rejected/.",
    ),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Project root containing .cortex/ (defaults to cwd).",
    ),
) -> None:
    """Reject a draft note. Default: move to rejected/. With --delete: remove."""
    layout = _resolve_layout(project_root)
    vault_root = _enterprise_vault(layout)
    full_path = (vault_root / path).resolve()
    if not full_path.is_relative_to(vault_root.resolve()):
        typer.echo(f"Path escapes enterprise vault: {path}", err=True)
        raise typer.Exit(1)

    reviewer_name = reviewer or getpass.getuser()
    try:
        new_path = mark_as_rejected(
            full_path, reviewer=reviewer_name, reason=reason, delete=delete
        )
    except PromotionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if delete:
        typer.echo(f"[OK] {path} -> deleted (reviewer={reviewer_name})")
    else:
        rel = (new_path.relative_to(vault_root)) if new_path is not None else path
        typer.echo(f"[OK] {path} -> {rel} (reviewer={reviewer_name})")


@review_app.command("candidate")
def candidate_command(
    selector: str = typer.Argument(
        ..., help="Candidate selector: origin_id or vault-relative path."
    ),
    approve: bool = typer.Option(
        True,
        "--approve/--reject",
        help="Approve by default. Use --reject to reject a candidate.",
    ),
    actor: str | None = typer.Option(
        None,
        "--actor",
        help="Actor name for audit records (default: current OS user).",
    ),
    reason: str | None = typer.Option(
        None,
        "--reason",
        help="Optional rationale for approve/reject.",
    ),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Project root containing .cortex/org.yaml.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON record."),
) -> None:
    """Legacy candidate review (KnowledgePromotionService JSONL records)."""
    from cortex.enterprise.knowledge_promotion import KnowledgePromotionService

    root = (
        Path(project_root).expanduser().resolve()
        if project_root
        else Path.cwd().resolve()
    )
    actor_name = actor or getpass.getuser()
    layout = WorkspaceLayout.discover(root)
    service = KnowledgePromotionService.from_project_root(root, workspace_layout=layout)
    try:
        record = service.review(
            selector=selector, approve=approve, actor=actor_name, reason=reason
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if json_output:
        typer.echo(record.model_dump_json(indent=2))
        return

    typer.echo(f"Recorded review: {record.origin_id}")
    typer.echo(f"  status: {record.status}")
    if record.decision:
        typer.echo(f"  decision: {record.decision.decision} by {record.decision.actor}")


__all__ = ["review_app"]
