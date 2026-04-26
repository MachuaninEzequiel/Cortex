from __future__ import annotations

from pathlib import Path

import typer

from cortex.webgraph.service import WebGraphService

app = typer.Typer(help="Hybrid memory graph commands for Cortex.")


def _resolve_project_root(project_root: str | None) -> Path:
    return Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()


def _require_config(project_root: Path) -> Path:
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        typer.secho(
            "config.yaml not found for this project root. "
            "Run `cortex setup agent` first or pass a valid --project-root.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    return config_path


def _resolve_workspace(workspace_file: str | None, project_root: str | None = None) -> Path | None:
    from cortex.webgraph.federation import resolve_workspace_file

    default_root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    path = resolve_workspace_file(workspace_file, default_root)
    if path is None:
        return None
    if not path.exists():
        typer.secho(f"Workspace file not found: {path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    return path


@app.command("export")
def export_snapshot(
    mode: str = typer.Option("hybrid", help="Graph mode: semantic, episodic, hybrid."),
    output: str = typer.Option(None, help="Output path for the JSON snapshot."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force snapshot rebuild."),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where config.yaml lives).",
    ),
    workspace_file: str | None = typer.Option(
        None,
        "--workspace-file",
        "--workspace",
        help="Path to a federation workspace YAML file (multi-project mode). Defaults to .cortex/webgraph/workspace.yaml when present.",
    ),
) -> None:
    workspace = _resolve_workspace(workspace_file, project_root)
    if workspace is not None:
        from cortex.webgraph.federation import FederatedWebGraphService

        service = FederatedWebGraphService(workspace)
    else:
        root = _resolve_project_root(project_root)
        _require_config(root)
        service = WebGraphService(root)
    path = service.export_snapshot(
        output_path=Path(output) if output else None,
        mode=mode,  # type: ignore[arg-type]
        use_cache=not no_cache,
    )
    typer.echo(f"Webgraph snapshot exported -> {path}")


@app.command("serve")
def serve(
    host: str = typer.Option(None, help="Bind host."),
    port: int = typer.Option(None, help="Bind port."),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open browser automatically."),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where config.yaml lives).",
    ),
    workspace_file: str | None = typer.Option(
        None,
        "--workspace-file",
        "--workspace",
        help="Path to a federation workspace YAML file (multi-project mode). Defaults to .cortex/webgraph/workspace.yaml when present.",
    ),
) -> None:
    try:
        from cortex.webgraph.server import run_server
    except ImportError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    workspace = _resolve_workspace(workspace_file, project_root)
    root = _resolve_project_root(project_root)
    if workspace is None:
        _require_config(root)

    try:
        run_server(root, host=host, port=port, open_browser=not no_open, workspace_file=workspace)
    except ImportError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command("doctor")
def doctor(
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where config.yaml lives).",
    ),
) -> None:
    """Validate WebGraph runtime prerequisites for one project."""
    from cortex.webgraph.setup import get_missing_webgraph_dependencies

    root = _resolve_project_root(project_root)
    config_path = root / "config.yaml"
    vault_path = root / "vault"
    memory_path = root / ".memory" / "chroma"

    checks: list[tuple[str, bool, str]] = [
        ("project_root", root.exists(), str(root)),
        ("config_yaml", config_path.exists(), str(config_path)),
        ("vault_dir", vault_path.exists(), str(vault_path)),
        ("episodic_store", memory_path.exists(), str(memory_path)),
    ]

    missing_deps = get_missing_webgraph_dependencies()
    checks.append(
        (
            "webgraph_dependencies",
            len(missing_deps) == 0,
            "missing: " + ", ".join(missing_deps) if missing_deps else "ok",
        )
    )

    has_failures = False
    for name, ok, detail in checks:
        mark = "OK" if ok else "FAIL"
        color = typer.colors.GREEN if ok else typer.colors.RED
        typer.secho(f"[{mark}] {name}: {detail}", fg=color)
        if not ok:
            has_failures = True

    if has_failures:
        typer.secho(
            "\nWebGraph doctor found blocking issues. "
            "Fix the failing checks and retry.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    typer.secho("\nWebGraph doctor passed.", fg=typer.colors.GREEN)
