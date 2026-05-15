"""Shared helper to build ``EnrichmentFilters`` from CLI/MCP flags.

Used by both ``cortex search`` (top-level command) and ``cortex docs search``
(canonical subcommand) so the parsing of ``--doc-type`` / ``--scope`` /
``--tag`` / ``--max-age-days`` / ``--strict`` stays in one place.

Extracted as part of Item #7 (deuda residual canonical-documentation).
"""

from __future__ import annotations

from collections.abc import Iterable

from cortex.context_enricher.filters import EnrichmentFilters
from cortex.documentation.doc_type import DocType


def _to_doc_types(slugs: Iterable[str], *, flag: str) -> list[DocType]:
    out: list[DocType] = []
    for slug in slugs:
        try:
            out.append(DocType(slug))
        except ValueError as exc:
            raise ValueError(f"Unknown {flag} {slug!r}") from exc
    return out


def build_enrichment_filters_from_cli(
    *,
    doc_type: Iterable[str] | None,
    exclude_doc_type: Iterable[str] | None,
    status: Iterable[str] | None,
    tag: Iterable[str] | None,
    tag_any: Iterable[str] | None,
    scope: str,
    max_age_days: int | None,
    project_id: Iterable[str] | None,
    strict: bool,
) -> EnrichmentFilters:
    """Build ``EnrichmentFilters`` from CLI flag values.

    Raises ``ValueError`` for unknown DocType slugs or invalid scope values.
    Empty / ``None`` collections become ``None`` in the filter to preserve
    "no filter" semantics in the enricher.
    """
    if scope not in {"local", "enterprise", "all"}:
        raise ValueError(f"Invalid --scope value: {scope!r}")

    doc_types_enum = _to_doc_types(doc_type or [], flag="--doc-type")
    exclude_doc_types_enum = _to_doc_types(
        exclude_doc_type or [], flag="--exclude-doc-type"
    )
    status_list = list(status or [])
    tag_list = list(tag or [])
    tag_any_list = list(tag_any or [])
    project_list = list(project_id or [])

    return EnrichmentFilters(
        doc_types=doc_types_enum or None,
        exclude_doc_types=exclude_doc_types_enum,
        statuses_allowed=status_list or None,
        tags_required=tag_list,
        tags_any_of=tag_any_list,
        vault_scope=scope,
        max_age_days=max_age_days,
        project_ids=project_list or None,
        strict=strict,
    )


def has_any_filter(
    *,
    doc_type: Iterable[str] | None,
    exclude_doc_type: Iterable[str] | None,
    status: Iterable[str] | None,
    tag: Iterable[str] | None,
    tag_any: Iterable[str] | None,
    max_age_days: int | None,
    project_id: Iterable[str] | None,
    strict: bool,
    scope: str = "local",
) -> bool:
    """Return True when at least one structural flag is engaged.

    ``scope`` is excluded from the check by default: it has a non-trivial
    default and changing it alone should not force the structural path.
    Callers that need the structural path purely because scope != local can
    pass ``scope`` explicitly and check the return.
    """
    return bool(
        (doc_type and list(doc_type))
        or (exclude_doc_type and list(exclude_doc_type))
        or (status and list(status))
        or (tag and list(tag))
        or (tag_any and list(tag_any))
        or max_age_days is not None
        or (project_id and list(project_id))
        or strict
        or scope not in {"local"}
    )


__all__ = ["build_enrichment_filters_from_cli", "has_any_filter"]
