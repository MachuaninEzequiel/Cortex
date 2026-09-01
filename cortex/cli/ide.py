"""``cortex ide`` — unified CLI surface for IDE adapters (Obra 02, Fase 3).

One command family for ALL IDEs:

    cortex ide list    [--json]
    cortex ide setup   --ide X [--project-root R] [--dry-run] [--sync-canonical/--no-sync-canonical]
    cortex ide remove  --ide X [--project-root R] [--dry-run]
    cortex ide status  [--ide X] [--json] [--project-root R]

Design rules (docs/transformacion/02-ESTANDAR-UNICO-IDE-CLI.md §3):

* ``project_root`` is EXPLICIT everywhere. When ``--project-root`` is not
  given the CLI resolves cwd → repo root once via
  ``WorkspaceLayout.discover`` with a plain-cwd fallback; no adapter ever
  calls ``Path.cwd()``.
* ``--dry-run`` reports what WOULD be done and never writes or deletes a
  single byte (fixes top-10 bug #4 for the whole IDE surface).
* No interactive prompts on this surface: missing ``--ide`` is a clear
  error listing the available IDEs by tier (exit code 2).
* The legacy commands (``install-ide``, ``uninstall-ide``, ``inject``,
  ``sync-ide``) delegate to the same ``run_*`` functions below, so old and
  new surface stay behaviorally identical during the deprecation window.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from cortex.ide.base import IDEAdapter
from cortex.ide.registry import (
    get_adapter,
    get_all_adapters,
    get_ide_tier,
    is_ide_validated,
)
from cortex.session.hooks import HookInstaller, default_installer
from cortex.workspace.layout import WorkspaceLayout

ide_app = typer.Typer(
    name="ide",
    help="Install / inspect / remove Cortex integration for IDEs (unified surface).",
    no_args_is_help=True,
)

_PROJECT_ROOT_HELP = "Path to the Cortex project root (defaults to current directory)."

DEPRECATION_SETUP = "Deprecated: use `cortex ide setup --ide <name>` instead."
DEPRECATION_REMOVE = "Deprecated: use `cortex ide remove --ide <name>` instead."


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def resolve_project_root(explicit: Path | None = None) -> Path:
    """Resolve the project root ONCE for the whole command.

    Explicit ``--project-root`` wins (resolved to an absolute path).
    Otherwise use WorkspaceLayout discovery from the cwd, falling back to
    the cwd itself when discovery cannot find a Cortex workspace — the new
    surface must never crash just because the caller stands outside a
    configured workspace (the adapters degrade gracefully).
    """
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    try:
        layout = WorkspaceLayout.discover(Path.cwd())
        return layout.repo_root
    except Exception:
        return Path.cwd().resolve()


def _fail(message: str, code: int = 1) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code)


def _get_adapter_or_exit(ide_name: str) -> IDEAdapter:
    """Resolve an adapter name/alias; unknown names exit with code 2."""
    try:
        return get_adapter(ide_name)
    except KeyError as exc:
        _fail(str(exc), code=2)
        raise  # pragma: no cover — _fail always raises


def _require_ide(ide_name: str | None, action: str) -> str:
    """No interactive prompts: missing --ide is an error listing options."""
    if ide_name:
        return ide_name
    from cortex.ide.registry import (
        _EXPERIMENTAL_IDES,
        COMMUNITY_IDES,
        TARGET_IDES,
    )

    message = (
        f"--ide is required for `cortex ide {action}` "
        "(no interactive prompt on this surface). Available IDEs:\n"
        f"  target:       {', '.join(sorted(TARGET_IDES))}\n"
        f"  community:    {', '.join(sorted(COMMUNITY_IDES))}\n"
        f"  experimental: {', '.join(sorted(_EXPERIMENTAL_IDES))}"
    )
    _fail(message, code=2)
    raise AssertionError  # pragma: no cover


def _absolute(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def _uninstall_supported(adapter: IDEAdapter) -> bool:
    """True when the adapter overrides the ABC's no-op uninstall."""
    return type(adapter).uninstall is not IDEAdapter.uninstall


def _hook_installer() -> HookInstaller:
    return default_installer()


def _hook_lookup(installer: HookInstaller, adapter_name: str):
    """Return the hook adapter for an IDE adapter name, or None."""
    hook_name = adapter_name.replace("_", "-")
    try:
        return installer.get(hook_name)
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# Runnable implementations (shared by the new surface AND the legacy
# deprecated commands in cli/main.py — parity is structural, not tested-by-
# coincidence).
# ---------------------------------------------------------------------------


def run_setup(
    ide_name: str,
    project_root: Path | None = None,
    *,
    sync_canonical: bool = True,
    dry_run: bool = False,
) -> list[str]:
    """Inject profiles + MCP for one IDE. Returns the files written."""
    import cortex.ide as cortex_ide

    root = resolve_project_root(project_root)
    adapter = _get_adapter_or_exit(ide_name)

    if dry_run:
        typer.echo(f"[DRY-RUN] Would set up {adapter.display_name} ({adapter.name}) in {root}:")
        typer.echo("  - inject agent profiles (from .cortex/skills/ and .cortex/subagents/)")
        typer.echo("  - inject MCP server configuration")
        for key, path in sorted(adapter.get_config_paths().items()):
            typer.echo(f"  - target [{key}]: {_absolute(path, root)}")
        typer.echo("Dry-run: no changes were written.")
        return []

    files = cortex_ide.inject(adapter.name, project_root=root, sync_canonical=sync_canonical)
    typer.echo(f"\n✅ Setup complete for {adapter.display_name}. Setup is idempotent; "
               f"re-run `cortex ide setup --ide {adapter.name}` anytime to re-sync.")
    return files


def run_remove(
    ide_name: str,
    project_root: Path | None = None,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove ONLY Cortex-created content for one IDE. Returns the report."""
    root = resolve_project_root(project_root)
    adapter = _get_adapter_or_exit(ide_name)

    if dry_run:
        typer.echo(f"[DRY-RUN] Would remove Cortex content from {adapter.display_name} "
                   f"({adapter.name}) in {root}:")
        candidates = [
            (key, _absolute(path, root))
            for key, path in sorted(adapter.get_config_paths().items())
            if _absolute(path, root).exists()
        ]
        if candidates:
            for key, path in candidates:
                state = "clean Cortex blocks / keys" if path.is_file() else "prune Cortex entries"
                typer.echo(f"  - [{key}] {path} ({state})")
        else:
            typer.echo("  - nothing found: no managed Cortex paths exist yet")
        typer.echo("Dry-run: nothing was removed.")
        return []

    typer.echo(f"[Cortex IDE] Removing Cortex from {adapter.display_name}...")
    report = adapter.uninstall(root)
    removed = skipped = 0
    for entry in report:
        typer.echo(f"  [REMOVED] {entry}")
        removed += 1
    still_present = [
        _absolute(p, root)
        for p in adapter.get_config_paths().values()
        if _absolute(p, root).exists()
    ]
    for path in still_present:
        typer.echo(f"  [SKIPPED] {path} still present (user-owned or shared file)")
        skipped += 1
    typer.echo(f"Remove complete for {adapter.display_name}: "
               f"{removed} entradas procesadas, {skipped} paths restantes.")
    return report


def run_bulk_inject(project_root: Path | None = None) -> dict[str, list[str]]:
    """Legacy bulk injection used only by the deprecated commands."""
    import cortex.ide as cortex_ide

    return cortex_ide.inject_all(project_root=resolve_project_root(project_root))


def run_bulk_uninstall(project_root: Path | None = None) -> dict[str, list[str]]:
    """Legacy bulk removal used only by the deprecated commands."""
    import cortex.ide as cortex_ide

    results = cortex_ide.uninstall_all()
    return results


def collect_status(
    adapter: IDEAdapter, root: Path, installer: HookInstaller
) -> dict[str, Any]:
    """Build the per-IDE status payload used by text and JSON output."""
    checks = {
        name: _absolute(path, root).exists()
        for name, path in adapter.get_config_paths().items()
    }
    expected_config_present = any(checks.values())

    mcp_path: Path | None = None
    mcp_key = next((k for k in adapter.get_config_paths() if "mcp" in k.lower()), None)
    if mcp_key is not None:
        mcp_path = _absolute(adapter.get_config_paths()[mcp_key], root)
    mcp_configured: bool | None = None if mcp_path is None else mcp_path.exists()

    hook_adapter = _hook_lookup(installer, adapter.name)
    hooks_installed: bool | None = None
    hooks_detail = ""
    if hook_adapter is not None:
        status = hook_adapter.status(root)
        hooks_installed = status.installed
        hooks_detail = status.detail

    return {
        "ide": adapter.name,
        "display_name": adapter.display_name,
        "tier": get_ide_tier(adapter.name),
        "validated": is_ide_validated(adapter.name),
        "expected_config_present": expected_config_present,
        "config_checks": checks,
        "mcp_configured": mcp_configured,
        "mcp_path": str(mcp_path) if mcp_path else None,
        "hooks_installed": hooks_installed,
        "hooks_detail": hooks_detail,
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@ide_app.command("list")
def list_command(
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List every registered IDE adapter with tier and uninstall support."""
    adapters = get_all_adapters(include_experimental=True)
    rows = [
        {
            "name": a.name,
            "display_name": a.display_name,
            "tier": get_ide_tier(a.name),
            "uninstall_supported": _uninstall_supported(a),
            "validated": is_ide_validated(a.name),
        }
        for a in adapters
    ]
    if output_json:
        typer.echo(json.dumps(rows, ensure_ascii=False))
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("IDE")
    table.add_column("DISPLAY NAME")
    table.add_column("TIER")
    table.add_column("UNINSTALL", justify="center")
    table.add_column("VALIDATED", justify="center")
    for row in rows:
        table.add_row(
            row["name"],
            row["display_name"],
            row["tier"],
            "✓" if row["uninstall_supported"] else "—",
            "✓" if row["validated"] else "—",
        )
    Console().print(table)


@ide_app.command("setup")
def setup_command(
    ide: str | None = typer.Option(None, "--ide", help="IDE name or alias (e.g. claude_code, codex, claude-code)."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without writing anything."),
    sync_canonical: bool = typer.Option(
        True,
        "--sync-canonical/--no-sync-canonical",
        help="(Pi only, legacy) kept for flag compatibility; has no effect.",
    ),
) -> None:
    """Install/update Cortex profiles + MCP for one IDE. Idempotent."""
    ide_name = _require_ide(ide, "setup")
    run_setup(ide_name, project_root=project_root, sync_canonical=sync_canonical, dry_run=dry_run)


@ide_app.command("remove")
def remove_command(
    ide: str | None = typer.Option(None, "--ide", help="IDE name or alias."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    dry_run: bool = typer.Option(False, "--dry-run", help="List what would be removed without removing anything."),
) -> None:
    """Remove ONLY Cortex-created content for one IDE (never destructive)."""
    ide_name = _require_ide(ide, "remove")
    run_remove(ide_name, project_root=project_root, dry_run=dry_run)


@ide_app.command("status")
def status_command(
    ide: str | None = typer.Option(None, "--ide", help="IDE name or alias (omit to report all)."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Report per-IDE: expected config present, MCP configured, session hooks installed."""
    root = resolve_project_root(project_root)
    installer = _hook_installer()
    if ide is not None:
        adapter = _get_adapter_or_exit(ide)
        adapters = [adapter]
    else:
        adapters = get_all_adapters(include_experimental=True)
    payloads = [collect_status(a, root, installer) for a in adapters]

    if output_json:
        typer.echo(json.dumps(payloads, ensure_ascii=False))
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("IDE")
    table.add_column("TIER")
    table.add_column("CONFIG", justify="center")
    table.add_column("MCP", justify="center")
    table.add_column("HOOKS", justify="center")
    table.add_column("DETAIL")
    for p in payloads:
        mcp = "—" if p["mcp_configured"] is None else ("✓" if p["mcp_configured"] else "✗")
        hooks = "—" if p["hooks_installed"] is None else ("✓" if p["hooks_installed"] else "✗")
        table.add_row(
            p["ide"],
            p["tier"],
            "✓" if p["expected_config_present"] else "✗",
            mcp,
            hooks,
            p["hooks_detail"] or ("n/a" if p["hooks_installed"] is None else ""),
        )
    Console().print(table)
