"""``cortex embedding-status`` y ``cortex reindex`` — superficie de embeddings.

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4). Dominio
de la Obra 04: estado de modelos por idioma y reindexación con
backup/rollback.
"""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from cortex.cli.common import _load_memory


def register(app) -> None:
    """Registra ``embedding-status`` y ``reindex`` en el app principal."""

    # ---------------------------------------------------------------------------
    # embedding-status (Obra 04 Fase C / E2b)
    # ---------------------------------------------------------------------------

    @app.command(name="embedding-status", hidden=True)
    def embedding_status(
        project_root: str = typer.Option(None, help="Project root (defaults to CWD discovery)."),
    ) -> None:
        """Show active embedding model/backend and per-language config.

        Diagnostic for post-migration checks: prints the effective single-model
        pair, whether the new ``embedding:`` block rules over legacy
        ``episodic.embedding_*``, detection mode and per-language entries.
        Does NOT instantiate embedders (no model download/load).
        """
        from cortex.core import CortexConfig, embedding_block_active, resolve_embedder
        from cortex.workspace import WorkspaceLayout

        start = Path(project_root).expanduser().resolve() if project_root else Path.cwd()
        layout = WorkspaceLayout.discover(start)
        config_path = layout.config_path
        if not config_path.exists():
            typer.echo(
                f"❌ No Cortex config found at `{config_path}`.\n"
                "   Run `cortex setup full --non-interactive` first.",
                err=True,
            )
            raise typer.Exit(1)

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        try:
            config = CortexConfig.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — CLI surface: show a clean error
            typer.echo(f"❌ Invalid config in {config_path}: {exc}", err=True)
            raise typer.Exit(1) from exc

        emb = config.embedding
        model, backend = resolve_embedder(config)
        typer.echo("Embedding configuration")
        typer.echo(f"  config file:    {config_path}")
        typer.echo(f"  mode:           {'per-language block' if embedding_block_active(config) else 'legacy single-model'}")
        typer.echo(f"  active model:   {model}")
        typer.echo(f"  active backend: {backend}")
        typer.echo(f"  detection:      {emb.language_detection}")
        if emb.per_language:
            typer.echo("  per_language:")
            for lang in sorted(emb.per_language):
                entry = emb.per_language[lang]
                eff_backend = entry.backend or emb.backend or config.episodic.embedding_backend
                typer.echo(f"    {lang}: model={entry.model} backend={eff_backend}")
        else:
            typer.echo("  per_language:   (empty → single-model mode)")
        if (
            embedding_block_active(config)
            and (
                config.episodic.embedding_model != "all-MiniLM-L6-v2"
                or config.episodic.embedding_backend != "onnx"
            )
        ):
            typer.echo(
                "  ⚠ Both 'embedding:' and legacy 'episodic.embedding_*' are set; "
                "the 'embedding:' block wins."
            )



    # ---------------------------------------------------------------------------
    # reindex (Obra 04 Fase E — model migration)
    # ---------------------------------------------------------------------------

    @app.command(name="reindex", hidden=True)
    def reindex(
        project_root: str = typer.Option(None, help="Project root (defaults to CWD discovery)."),
        prune_old_caches: bool = typer.Option(
            False, "--prune-old-caches", help="Delete previous .vectors.backup-* dirs after a successful rebuild.",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Show the plan without touching anything."),
        limit: int = typer.Option(None, help="Smoke mode: index at most N docs."),
    ) -> None:
        """Rebuild the semantic vector cache with the ACTIVE embedding model.

        Migration procedure (Obra 04 Fase E):
          1. Backs up `.cortex/vectors/` -> `.cortex/vectors.backup-<timestamp>/`.
          2. Re-embeds every vault doc with the effective (model, backend)
             from `embedding:` config / legacy episodic fields.
          3. Rollback: restore the backup dir over `.cortex/vectors/` (or run
             with the old model in config and `reindex` again).

        Changing the model in config already invalidates the cache automatically
        (A3 model identity); this command forces an immediate, observable rebuild.
        """
        import shutil as _shutil
        from datetime import datetime

        from cortex.core import CortexConfig, resolve_embedder
        from cortex.semantic.vault_reader import VaultReader
        from cortex.workspace import WorkspaceLayout

        start = Path(project_root).expanduser().resolve() if project_root else Path.cwd()
        layout = WorkspaceLayout.discover(start)
        config_path = layout.config_path
        if not config_path.exists():
            typer.echo(f"❌ No Cortex config found at `{config_path}`.", err=True)
            raise typer.Exit(1)

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        try:
            config = CortexConfig.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — CLI surface: clean error
            typer.echo(f"❌ Invalid config in {config_path}: {exc}", err=True)
            raise typer.Exit(1) from exc

        model, backend = resolve_embedder(config)
        vault_resolved = layout.resolve_workspace_relative(config.semantic.vault_path)
        workspace_root = Path(layout.workspace_root)
        vectors_dir = workspace_root / ".cortex" / "vectors"

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = workspace_root / ".cortex" / f"vectors.backup-{timestamp}"

        if dry_run:
            typer.echo("[dry-run] reindex plan:")
            typer.echo(f"  model/backend : {model} / {backend}")
            typer.echo(f"  vault         : {vault_resolved}")
            if vectors_dir.exists():
                typer.echo(f"  would move    : {vectors_dir} -> {backup_dir.name}")
            else:
                typer.echo("  no existing vector cache to back up")
            typer.echo("  would rebuild : full sync + embeddings for every vault doc")
            if prune_old_caches:
                typer.echo("  would prune   : previous .vectors.backup-* dirs")
            return

        # 1) Backup (move) the existing cache.
        if vectors_dir.exists():
            backup_dir.parent.mkdir(parents=True, exist_ok=True)
            _shutil.move(str(vectors_dir), str(backup_dir))
            typer.echo(f"Backup: {vectors_dir} -> {backup_dir.name}")

        # 2) Fresh sync with the effective model, rebuilding the persistent cache.
        try:
            from cortex.semantic.vector_cache import VectorCache

            vectors_dir.mkdir(parents=True, exist_ok=True)
            vector_cache = VectorCache(vectors_dir, model_name=model)
            reader = VaultReader(
                vault_path=str(vault_resolved),
                embedding_model=model,
                embedding_backend=backend,
                vector_cache=vector_cache,
            )
            count = reader.sync()
        except Exception as exc:  # noqa: BLE001 — restore backup on failure (rollback)
            typer.echo(f"❌ Reindex failed: {exc}", err=True)
            if backup_dir.exists() and not vectors_dir.exists():
                _shutil.move(str(backup_dir), str(vectors_dir))
                typer.echo(f"↩ Rollback: restored {vectors_dir} from backup.", err=True)
            raise typer.Exit(1) from exc

        typer.echo(f"✅ Reindexed {count} docs with {model} ({backend}).")
        typer.echo(
            "Rollback hint: restore "
            f"{backup_dir.name} over .cortex/vectors/ (and switch the model back "
            "in config.yaml) to revert."
        )

        # 3) Optional pruning of previous backups.
        if prune_old_caches:
            pruned = 0
            for old in sorted(workspace_root.glob(".cortex/vectors.backup-*")):
                if old == backup_dir:
                    continue
                _shutil.rmtree(old, ignore_errors=True)
                pruned += 1
            typer.echo(f"Pruned {pruned} old cache backups.")

    # ---------------------------------------------------------------------------
    # sync-vault
    # ---------------------------------------------------------------------------

    @app.command(name="sync-vault", hidden=True)
    def sync_vault() -> None:
        """Re-index the markdown vault."""
        mem = _load_memory()
        count = mem.sync_vault()
        typer.echo(f"Vault synced -- {count} documents indexed.")
