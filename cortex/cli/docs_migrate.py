"""cortex.cli.docs_migrate - ``cortex docs migrate/validate/restore`` (Fase 11)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from cortex.documentation.backup import (
    create_backup,
    list_backups,
    restore_backup,
)
from cortex.documentation.migration import (
    format_report,
    migrate_vault,
    validate_vault,
)

app = typer.Typer(help="Vault migration and validation operations.")


@app.callback()
def _main() -> None:
    """Vault migration tools (Fase 11)."""


def _default_vault(project_root: Optional[str]) -> Path:
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    return root / "vault"


@app.command()
def migrate(
    project_root: Optional[str] = typer.Option(
        None, "--project-root", help="Project root (defaults to cwd).",
    ),
    path: Optional[Path] = typer.Option(
        None, "--path", help="Subpath inside vault/ to migrate (default: all).",
    ),
    apply: bool = typer.Option(
        False, "--apply", help="Apply changes (default: dry-run).",
    ),
    force: bool = typer.Option(
        False, "--force", help="Re-migrate notes already at schema_version=1.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Write the report to this file.",
    ),
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip the tar.gz backup before --apply.",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Print the report as JSON.",
    ),
) -> None:
    """Backfill the vault to the canonical schema."""
    vault = _default_vault(project_root)
    result = migrate_vault(
        vault,
        apply=apply,
        force=force,
        path_filter=path,
        create_backup_archive=apply and not no_backup,
    )
    if json_output:
        payload = {
            "applied": result.applied,
            "total_scanned": result.total_scanned,
            "migrated": [str(d.path) for d in result.migrated],
            "already_migrated": [str(d.path) for d in result.already_migrated],
            "unclassifiable": [
                {"path": str(d.path), "reason": d.reason}
                for d in result.unclassifiable
            ],
            "errors": [
                {"path": str(d.path), "reason": d.reason}
                for d in result.errors
            ],
            "backup_path": str(result.backup_path) if result.backup_path else None,
        }
        typer.echo(json.dumps(payload, indent=2))
        return
    report = format_report(result)
    if output:
        output.write_text(report, encoding="utf-8")
        typer.echo(f"Report written to {output}")
    else:
        typer.echo(report)


@app.command()
def validate(
    project_root: Optional[str] = typer.Option(
        None, "--project-root", help="Project root (defaults to cwd).",
    ),
    all_files: bool = typer.Option(
        False, "--all", help="Validate every .md in the vault (default).",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="JSON output.",
    ),
) -> None:
    """Validate every note in the vault against the canonical schema."""
    vault = _default_vault(project_root)
    payload = validate_vault(vault)
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(f"Vault: {payload['vault_path']}")
    typer.echo(f"Total notes: {payload['total']}")
    typer.echo(f"Valid: {payload['valid']}")
    typer.echo(f"Invalid: {payload['invalid']}")
    typer.echo(f"No frontmatter: {payload['no_frontmatter']}")
    if payload["issues"]:
        typer.echo("\nIssues:")
        for issue in payload["issues"]:
            typer.echo(f"  - {issue['path']}: {issue['error']}")


@app.command()
def restore(
    backup: str = typer.Option(..., "--backup", help="Backup file or timestamp."),
    target: Optional[Path] = typer.Option(
        None, "--target", help="Where to restore (default: vault parent).",
    ),
    project_root: Optional[str] = typer.Option(
        None, "--project-root", help="Project root.",
    ),
) -> None:
    """Restore the vault from a backup tar.gz."""
    vault = _default_vault(project_root)
    backups_dir = vault.parent / ".cortex" / "backups"
    backup_path = Path(backup)
    if not backup_path.exists():
        # Resolve by short name.
        candidates = [p for p in list_backups(backups_dir) if backup in p.name]
        if not candidates:
            typer.echo(f"Backup not found: {backup}", err=True)
            raise typer.Exit(1)
        backup_path = candidates[-1]
    restored = restore_backup(backup_path, target or vault.parent)
    typer.echo(f"Restored: {restored}")


@app.command(name="list-backups")
def list_backups_cmd(
    project_root: Optional[str] = typer.Option(
        None, "--project-root", help="Project root.",
    ),
) -> None:
    """List backup snapshots."""
    vault = _default_vault(project_root)
    backups_dir = vault.parent / ".cortex" / "backups"
    backups = list_backups(backups_dir)
    if not backups:
        typer.echo(f"No backups found in {backups_dir}")
        return
    for b in backups:
        typer.echo(f"{b.name}\t{b.stat().st_size} bytes")
