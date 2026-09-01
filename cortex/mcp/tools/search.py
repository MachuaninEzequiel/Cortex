"""Handlers MCP del dominio búsqueda/contexto (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.
"""

from __future__ import annotations

import re
from typing import Any

from cortex.models import EnrichedContext
from cortex.security.paths import PathSecurityError, resolve_safe


class SearchToolsMixin:
    """Mixín: handlers MCP de búsqueda/contexto."""

    @staticmethod
    def _extract_query_keywords(query: str) -> list[str]:
        """Build lightweight keywords from a free-form context query."""
        words = re.findall(r"\b[a-zA-Z][\w./-]{2,}\b", query.lower())
        return list(dict.fromkeys(words))[:10]

    def _enrich_context(self, arguments: dict[str, Any]) -> EnrichedContext:
        """Convert MCP arguments into a useful context enrichment request.

        Phase 08 / T8.4: when the caller (typically SDDwork) passes a
        ``task_type``, the retrieval envelope is sized by
        :func:`cortex.context_enricher.budget_resolver.resolve_budget_profile`.
        Calls without ``task_type`` use the historical default and stay
        backward-compatible.
        """
        from cortex.context_enricher.budget_resolver import resolve_budget_profile

        query = str(arguments.get("query", "")).strip()
        changed_files = self._normalize_string_list(arguments.get("changed_files", []))
        keywords = self._normalize_string_list(arguments.get("keywords", []))

        if not keywords and query:
            keywords = self._extract_query_keywords(query)

        pr_title = str(arguments.get("pr_title", "")).strip() or query or None

        raw_task_type = arguments.get("task_type")
        task_type = (
            str(raw_task_type).strip()
            if raw_task_type not in (None, "")
            else None
        )
        raw_complexity = arguments.get("complexity")
        complexity = (
            str(raw_complexity).strip()
            if raw_complexity not in (None, "")
            else None
        )

        top_k: int | None
        if task_type is not None:
            profile = resolve_budget_profile(task_type, complexity)
            top_k = profile["top_k"]
        else:
            top_k = None

        return self.memory.enrich(
            changed_files=changed_files,
            keywords=keywords,
            pr_title=pr_title,
            top_k=top_k,
        )

    @staticmethod
    def _normalize_string_list(values: Any) -> list[str]:
        """Coerce ``values`` to a clean ``list[str]``.

        Tolerates two shapes commonly produced by LLM clients:

        - ``list``/``tuple`` of strings → strip + drop empties.
        - Single ``str`` → split on commas (CSV), strip + drop empties.

        Any other type collapses to an empty list. See
        ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.
        """
        if values is None:
            return []
        if isinstance(values, str):
            return [token.strip() for token in values.split(",") if token.strip()]
        if isinstance(values, (list, tuple)):
            return [str(v).strip() for v in values if str(v).strip()]
        return []

    def _extract_candidate_files(self, query: str) -> list[str]:
        project_root = self.project_root.resolve()
        candidates: list[str] = []

        for raw_path in re.findall(r"\b[\w./\\-]+\.[A-Za-z0-9]+\b", query):
            normalized = raw_path.strip().replace("\\", "/")
            try:
                candidate = resolve_safe(project_root, normalized)
            except PathSecurityError:
                continue

            if candidate.is_file():
                candidates.append(normalized)

        return list(dict.fromkeys(candidates))

    def _build_sync_ticket_context(self, arguments: dict[str, Any]) -> str:
        user_request = str(arguments.get("user_request", "")).strip()
        if not user_request:
            raise ValueError("user_request es obligatorio para cortex_sync_ticket.")

        changed_files = self._normalize_string_list(arguments.get("changed_files", []))
        if not changed_files:
            changed_files = self._extract_candidate_files(user_request)

        keywords = self._normalize_string_list(arguments.get("keywords", []))
        if not keywords:
            keywords = self._extract_query_keywords(user_request)

        title_hint = str(arguments.get("title_hint", "")).strip() or user_request
        top_k = int(arguments.get("top_k", 5) or 5)

        related = self.memory.retrieve(user_request, top_k=top_k)
        enriched = self.memory.enrich(
            changed_files=changed_files,
            keywords=keywords,
            pr_title=title_hint,
            top_k=top_k,
        )

        changed_files_text = (
            ", ".join(changed_files) if changed_files else "(sin archivos inferidos)"
        )
        keywords_text = ", ".join(keywords) if keywords else "(sin keywords)"

        sections = [
            "## Ticket actual",
            user_request,
            "",
            "## Scope detectado",
            changed_files_text,
            "",
            "## Keywords",
            keywords_text,
            "",
            "## Contexto historico similar (Vault + memoria episodica)",
            related.to_prompt(),
            "",
            "## Contexto enriquecido del proyecto",
            enriched.to_prompt_format(),
        ]
        return "\n".join(sections)

    def _search_text(self, query: str, limit: int = 5) -> str:
        results = self.memory.retrieve(query, top_k=limit)
        return str(results.to_prompt())

    def _search_vector_text(self, arguments: dict[str, Any]) -> str:
        """Handler para ``cortex_search_vector``: forces the semantic/vector path.

        Difiere de ``cortex_search`` en que NUNCA cae al modo ContextEnricher
        estructural — siempre invoca el path retrieval con ``use_embeddings=True``.
        Pensado para casos donde el caller quiere busqueda semantica pura
        aunque el costo de cargar el modelo ONNX sea mayor.
        """
        query = str(arguments.get("query", "") or "")
        limit = int(arguments.get("limit", 5) or 5)
        results = self.memory.retrieve(query, top_k=limit, use_embeddings=True)
        return str(results.to_prompt())

    _STRUCTURAL_KEYS = (
        "doc_type",
        "exclude_doc_type",
        "status",
        "tag",
        "tag_any",
        "max_age_days",
        "project_id",
        "strict",
    )

    def _search_text_dispatch(self, arguments: dict[str, Any]) -> str:
        """Route ``cortex_search`` to legacy RRF or structural enricher path."""
        query = arguments.get("query", "")
        limit = int(arguments.get("limit", 5) or 5)

        scope = arguments.get("scope", "local") or "local"
        structural = any(arguments.get(k) for k in self._STRUCTURAL_KEYS) or scope != "local"
        if not structural:
            return self._search_text(query, limit)

        from cortex.cli._search_filters import build_enrichment_filters_from_cli
        from cortex.context_enricher.config import ContextEnricherConfig
        from cortex.context_enricher.enricher import ContextEnricher
        from cortex.models import WorkContext

        try:
            filters = build_enrichment_filters_from_cli(
                doc_type=arguments.get("doc_type") or [],
                exclude_doc_type=arguments.get("exclude_doc_type") or [],
                status=arguments.get("status") or [],
                tag=arguments.get("tag") or [],
                tag_any=arguments.get("tag_any") or [],
                scope=scope,
                max_age_days=arguments.get("max_age_days"),
                project_id=arguments.get("project_id") or [],
                strict=bool(arguments.get("strict", False)),
            )
        except ValueError as exc:
            return f"cortex_search: invalid filter — {exc}"

        from cortex.context_enricher.telemetry import make_observer

        ws_root = getattr(self.memory, "workspace_root", None)
        enricher = ContextEnricher(
            episodic=self.memory.episodic,
            semantic=self.memory.semantic,
            config=ContextEnricherConfig(),
            observer=make_observer(project_root=ws_root) if ws_root else None,
        )
        work = WorkContext(
            source="manual",
            changed_files=[],
            keywords=str(query).split(),
            search_queries=[str(query)],
        )
        ctx = enricher.enrich(work, top_k=limit, filters=filters)
        return ctx.to_prompt_format()

    def _context_text(self, arguments: dict[str, Any]) -> str:
        return self._enrich_context(arguments).to_prompt_format()

    # Mensaje canónico de violación del guard de gobernanza.
    # Usado tanto desde ``handle_call_tool`` como desde ``_create_spec_text``
    # para que el contrato sea único, testeable y libre de mojibake.
    # NO duplicar la cadena en otra parte del archivo.
