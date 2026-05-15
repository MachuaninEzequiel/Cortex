"""cortex.cli.docs_search - ``cortex docs search`` with structural filters (Fase 13).

The legacy ``cortex search`` exposes the raw hybrid-RRF retrieval over both
memory layers. This new subcommand sits on top of ``ContextEnricher.enrich()``
and exposes the structural filters (``doc_types``, ``vault_scope``,
``max_age_days``, ``tags_required``) plus DocIntent boost introduced in Fase 08.

Output formats:

    - text (default): human-readable, grouped by DocType.
    - json:           full ``EnrichedContext`` payload.
    - compact:        single-line per item, LLM-friendly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from cortex.cli._search_filters import build_enrichment_filters_from_cli
from cortex.context_enricher.config import ContextEnricherConfig
from cortex.context_enricher.enricher import ContextEnricher
from cortex.context_enricher.presenter import ContextPresenter


def search(
    query: str = typer.Argument(..., help="Natural-language search query."),
    project_root: Optional[str] = typer.Option(
        None, "--project-root", help="Project root (defaults to cwd).",
    ),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Max results."),
    doc_type: list[str] = typer.Option(
        [], "--doc-type",
        help="Filter by DocType slug (repeatable). E.g. --doc-type adr --doc-type runbook.",
    ),
    exclude_doc_type: list[str] = typer.Option(
        [], "--exclude-doc-type", help="Exclude these DocType slugs.",
    ),
    status: list[str] = typer.Option(
        [], "--status", help="Only items with one of these statuses.",
    ),
    tag: list[str] = typer.Option(
        [], "--tag", help="Items must contain ALL given tags.",
    ),
    tag_any: list[str] = typer.Option(
        [], "--tag-any", help="Items must contain AT LEAST ONE of the given tags.",
    ),
    scope: str = typer.Option(
        "all", "--scope", help="Vault scope: local | enterprise | all.",
    ),
    max_age_days: Optional[int] = typer.Option(
        None, "--max-age-days", help="Drop items older than this many days.",
    ),
    project_id: list[str] = typer.Option(
        [], "--project-id", help="Multi-tenant filter (repeatable).",
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Drop items without doc_type when --doc-type is set.",
    ),
    output_format: str = typer.Option(
        "text", "--format", "-f", help="Output: text | json | compact",
    ),
) -> None:
    """Search the canonical vault honouring structural filters."""
    if output_format not in {"text", "json", "compact"}:
        typer.echo(f"Invalid --format value: {output_format!r}", err=True)
        raise typer.Exit(1)

    try:
        filters = build_enrichment_filters_from_cli(
            doc_type=doc_type,
            exclude_doc_type=exclude_doc_type,
            status=status,
            tag=tag,
            tag_any=tag_any,
            scope=scope,
            max_age_days=max_age_days,
            project_id=project_id,
            strict=strict,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    # Build the WorkContext from the query string itself: keywords = query.
    from cortex.models import WorkContext
    work = WorkContext(
        source="manual",
        changed_files=[],
        keywords=query.split(),
        search_queries=[query],
    )

    enricher = _build_enricher(project_root)
    ctx = enricher.enrich(work, top_k=top_k, filters=filters)

    if output_format == "json":
        typer.echo(ContextPresenter.to_json(ctx))
        return
    if output_format == "compact":
        typer.echo(ContextPresenter.to_compact_grouped(ctx))
        return
    typer.echo(ContextPresenter.to_markdown_grouped(ctx))


def _build_enricher(project_root: Optional[str]) -> ContextEnricher:
    """Construct a ``ContextEnricher`` with the project's episodic + semantic stores."""
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()

    from cortex.core import AgentMemory
    mem = AgentMemory.from_config(project_root=root)
    config = ContextEnricherConfig()
    return ContextEnricher(
        episodic=mem.episodic,
        semantic=mem.semantic,
        config=config,
    )


__all__ = ["search"]
